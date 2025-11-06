"""
Force deletion utilities for stubborn files and processes.

Features:
- Process termination
- File lock detection and removal
- Service stopping
- Delayed deletion (reboot required)
"""

import os
import shutil
import subprocess
import time
import winreg
from typing import List, Optional, Tuple
from dataclasses import dataclass

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

from utils.logger import get_logger


@dataclass
class ProcessInfo:
    """Information about a process."""
    pid: int
    name: str
    exe: str
    cmdline: List[str]


class ForceDelete:
    """
    Handles forceful deletion of files, directories, and processes.

    Features:
    - Terminate processes using specific files
    - Stop Windows services
    - Schedule deletion on next reboot
    - Handle locked files
    """

    def __init__(self):
        self.logger = get_logger()

    def find_processes_using_file(self, file_path: str) -> List[ProcessInfo]:
        """
        Find all processes that are using a specific file.

        Args:
            file_path: Path to the file

        Returns:
            List of ProcessInfo objects
        """
        if not PSUTIL_AVAILABLE:
            self.logger.warning("psutil not available, cannot find processes using file")
            return []

        processes = []
        file_path_lower = file_path.lower()

        try:
            for proc in psutil.process_iter(['pid', 'name', 'exe', 'cmdline']):
                try:
                    # Check executable path
                    if proc.info['exe'] and proc.info['exe'].lower() == file_path_lower:
                        processes.append(ProcessInfo(
                            pid=proc.info['pid'],
                            name=proc.info['name'],
                            exe=proc.info['exe'],
                            cmdline=proc.info['cmdline'] or []
                        ))
                        continue

                    # Check open files
                    try:
                        for file in proc.open_files():
                            if file.path.lower() == file_path_lower:
                                processes.append(ProcessInfo(
                                    pid=proc.info['pid'],
                                    name=proc.info['name'],
                                    exe=proc.info['exe'] or '',
                                    cmdline=proc.info['cmdline'] or []
                                ))
                                break
                    except (psutil.AccessDenied, psutil.NoSuchProcess):
                        pass

                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

        except Exception as e:
            self.logger.warning(f"Error finding processes using file: {e}")

        return processes

    def find_processes_in_directory(self, directory: str) -> List[ProcessInfo]:
        """
        Find all processes running from a specific directory.

        Args:
            directory: Directory path

        Returns:
            List of ProcessInfo objects
        """
        if not PSUTIL_AVAILABLE:
            return []

        processes = []
        dir_lower = directory.lower()

        try:
            for proc in psutil.process_iter(['pid', 'name', 'exe', 'cmdline']):
                try:
                    if proc.info['exe'] and proc.info['exe'].lower().startswith(dir_lower):
                        processes.append(ProcessInfo(
                            pid=proc.info['pid'],
                            name=proc.info['name'],
                            exe=proc.info['exe'],
                            cmdline=proc.info['cmdline'] or []
                        ))
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

        except Exception as e:
            self.logger.warning(f"Error finding processes in directory: {e}")

        return processes

    def terminate_process(self, pid: int, force: bool = False) -> bool:
        """
        Terminate a process by PID.

        Args:
            pid: Process ID
            force: Use forceful termination (kill)

        Returns:
            True if successful
        """
        if not PSUTIL_AVAILABLE:
            # Fallback to taskkill
            return self._terminate_process_taskkill(pid, force)

        try:
            proc = psutil.Process(pid)
            proc_name = proc.name()

            if force:
                proc.kill()
                self.logger.info(f"Killed process {proc_name} (PID: {pid})")
            else:
                proc.terminate()
                self.logger.info(f"Terminated process {proc_name} (PID: {pid})")

            # Wait for process to exit
            proc.wait(timeout=5)
            return True

        except psutil.NoSuchProcess:
            return True  # Already terminated
        except psutil.AccessDenied:
            self.logger.warning(f"Access denied when terminating process {pid}")
            # Try taskkill as fallback
            return self._terminate_process_taskkill(pid, force)
        except psutil.TimeoutExpired:
            if not force:
                # Try force kill
                return self.terminate_process(pid, force=True)
            return False
        except Exception as e:
            self.logger.error(f"Error terminating process {pid}: {e}")
            return False

    def _terminate_process_taskkill(self, pid: int, force: bool = False) -> bool:
        """
        Terminate process using taskkill command.

        Args:
            pid: Process ID
            force: Use /F flag

        Returns:
            True if successful
        """
        try:
            cmd = ['taskkill', '/PID', str(pid)]
            if force:
                cmd.append('/F')

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )

            return result.returncode == 0

        except Exception as e:
            self.logger.error(f"Error using taskkill: {e}")
            return False

    def stop_service(self, service_name: str) -> bool:
        """
        Stop a Windows service.

        Args:
            service_name: Name of the service

        Returns:
            True if successful
        """
        try:
            # Use sc stop command
            result = subprocess.run(
                ['sc', 'stop', service_name],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                self.logger.info(f"Stopped service: {service_name}")
                # Wait for service to stop
                time.sleep(2)
                return True
            else:
                self.logger.warning(f"Failed to stop service {service_name}: {result.stderr}")
                return False

        except Exception as e:
            self.logger.error(f"Error stopping service {service_name}: {e}")
            return False

    def schedule_delete_on_reboot(self, path: str) -> bool:
        """
        Schedule a file or directory to be deleted on next reboot.
        Uses PendingFileRenameOperations registry key.

        Args:
            path: Path to file or directory

        Returns:
            True if successful
        """
        try:
            # Open the registry key
            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SYSTEM\CurrentControlSet\Control\Session Manager",
                0,
                winreg.KEY_ALL_ACCESS
            )

            # Get existing pending operations
            try:
                existing_ops, _ = winreg.QueryValueEx(key, "PendingFileRenameOperations")
                if not isinstance(existing_ops, list):
                    existing_ops = []
            except FileNotFoundError:
                existing_ops = []

            # Add new operation
            # Format: source path, empty string (means delete)
            new_ops = existing_ops + [f"\\??\\{path}", ""]

            # Set the registry value
            winreg.SetValueEx(
                key,
                "PendingFileRenameOperations",
                0,
                winreg.REG_MULTI_SZ,
                new_ops
            )

            winreg.CloseKey(key)

            self.logger.info(f"Scheduled deletion on reboot: {path}")
            return True

        except PermissionError:
            self.logger.error("Permission denied. Administrator rights required.")
            return False
        except Exception as e:
            self.logger.error(f"Error scheduling deletion on reboot: {e}")
            return False

    def force_delete_file(self, file_path: str, terminate_processes: bool = True) -> Tuple[bool, str]:
        """
        Forcefully delete a file, terminating processes if needed.

        Args:
            file_path: Path to the file
            terminate_processes: Whether to terminate processes using the file

        Returns:
            Tuple of (success, error_message)
        """
        if not os.path.exists(file_path):
            return True, ""  # Already deleted

        # Try normal deletion first
        try:
            os.remove(file_path)
            self.logger.info(f"Deleted file: {file_path}")
            return True, ""
        except PermissionError:
            pass  # Continue with force delete
        except Exception as e:
            return False, str(e)

        # Find and terminate processes using this file
        if terminate_processes:
            processes = self.find_processes_using_file(file_path)
            if processes:
                self.logger.info(f"Found {len(processes)} process(es) using {file_path}")
                for proc in processes:
                    self.logger.info(f"Terminating process: {proc.name} (PID: {proc.pid})")
                    self.terminate_process(proc.pid)

                # Wait a bit for processes to exit
                time.sleep(1)

        # Try deletion again
        try:
            os.remove(file_path)
            self.logger.info(f"Force deleted file: {file_path}")
            return True, ""
        except Exception as e:
            # Last resort: schedule deletion on reboot
            if self.schedule_delete_on_reboot(file_path):
                return True, "Scheduled for deletion on reboot"
            return False, str(e)

    def force_delete_directory(self, dir_path: str, terminate_processes: bool = True) -> Tuple[bool, str]:
        """
        Forcefully delete a directory and all its contents.

        Args:
            dir_path: Path to the directory
            terminate_processes: Whether to terminate processes in the directory

        Returns:
            Tuple of (success, error_message)
        """
        if not os.path.exists(dir_path):
            return True, ""  # Already deleted

        # Try normal deletion first
        try:
            shutil.rmtree(dir_path)
            self.logger.info(f"Deleted directory: {dir_path}")
            return True, ""
        except PermissionError:
            pass  # Continue with force delete
        except Exception as e:
            return False, str(e)

        # Find and terminate processes in this directory
        if terminate_processes:
            processes = self.find_processes_in_directory(dir_path)
            if processes:
                self.logger.info(f"Found {len(processes)} process(es) in {dir_path}")
                for proc in processes:
                    self.logger.info(f"Terminating process: {proc.name} (PID: {proc.pid})")
                    self.terminate_process(proc.pid)

                # Wait for processes to exit
                time.sleep(2)

        # Try deletion again
        try:
            shutil.rmtree(dir_path)
            self.logger.info(f"Force deleted directory: {dir_path}")
            return True, ""
        except Exception as e:
            # Last resort: schedule deletion on reboot
            if self.schedule_delete_on_reboot(dir_path):
                return True, "Scheduled for deletion on reboot"
            return False, str(e)

    def is_process_running(self, process_name: str) -> bool:
        """
        Check if a process with given name is running.

        Args:
            process_name: Name of the process (e.g., "notepad.exe")

        Returns:
            True if process is running
        """
        if not PSUTIL_AVAILABLE:
            # Fallback to tasklist
            try:
                result = subprocess.run(
                    ['tasklist', '/FI', f'IMAGENAME eq {process_name}'],
                    capture_output=True,
                    text=True
                )
                return process_name.lower() in result.stdout.lower()
            except:
                return False

        try:
            for proc in psutil.process_iter(['name']):
                if proc.info['name'].lower() == process_name.lower():
                    return True
            return False
        except:
            return False

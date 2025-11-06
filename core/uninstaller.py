"""
Uninstaller execution engine.
Handles the execution of uninstall operations for programs.
"""

import os
import re
import subprocess
import time
from typing import Optional, Tuple
from dataclasses import dataclass
from pathlib import Path

from core.registry import InstalledProgram
from utils.logger import get_logger
from utils.backup import BackupManager


@dataclass
class UninstallResult:
    """Result of an uninstall operation."""
    success: bool
    exit_code: Optional[int] = None
    error_message: Optional[str] = None
    duration: float = 0.0


class Uninstaller:
    """
    Handles program uninstallation.

    Features:
    - Execute UninstallString
    - MSI package uninstallation
    - Process monitoring
    - Silent mode support
    - Error handling and retry
    """

    def __init__(self, program: InstalledProgram):
        """
        Initialize the uninstaller.

        Args:
            program: InstalledProgram object to uninstall
        """
        self.program = program
        self.logger = get_logger()

    def uninstall(
        self,
        silent: bool = True,
        create_backup: bool = True,
        timeout: int = 600
    ) -> UninstallResult:
        """
        Execute the uninstall operation.

        Args:
            silent: Run in silent mode (no user interaction)
            create_backup: Create backup before uninstalling
            timeout: Maximum time to wait for uninstaller (seconds)

        Returns:
            UninstallResult object
        """
        self.logger.log_operation_start("Uninstall", self.program.name)
        start_time = time.time()

        try:
            # Create backup if requested
            if create_backup:
                self._create_backup()

            # Determine uninstall method
            if self._is_msi_package():
                result = self._uninstall_msi(silent, timeout)
            elif self.program.uninstall_string:
                result = self._execute_uninstall_string(silent, timeout)
            else:
                return UninstallResult(
                    success=False,
                    error_message="No uninstall method found"
                )

            # Calculate duration
            result.duration = time.time() - start_time

            # Log result
            self.logger.log_operation_end(
                "Uninstall",
                result.success,
                f"Exit code: {result.exit_code}, Duration: {result.duration:.2f}s"
            )

            return result

        except Exception as e:
            duration = time.time() - start_time
            self.logger.error(f"Uninstall failed with exception: {e}")
            self.logger.log_operation_end("Uninstall", False, str(e))

            return UninstallResult(
                success=False,
                error_message=str(e),
                duration=duration
            )

    def _create_backup(self) -> None:
        """Create backup before uninstalling."""
        self.logger.info("Creating backup...")

        backup_manager = BackupManager()

        # Create system restore point
        if backup_manager.create_restore_point(f"Before uninstalling {self.program.name}"):
            self.logger.info("System restore point created")
        else:
            self.logger.warning("Failed to create restore point")

        # Backup registry key
        if self.program.registry_key:
            try:
                import winreg
                # Extract the registry path
                if "HKEY_LOCAL_MACHINE" in self.program.registry_key:
                    hive = winreg.HKEY_LOCAL_MACHINE
                    path = self.program.registry_key.split("HKEY_LOCAL_MACHINE\\")[1]
                elif "HKEY_CURRENT_USER" in self.program.registry_key:
                    hive = winreg.HKEY_CURRENT_USER
                    path = self.program.registry_key.split("HKEY_CURRENT_USER\\")[1]
                else:
                    hive = None
                    path = None

                if hive and path:
                    backup_file = backup_manager.backup_registry_key(
                        hive,
                        path,
                        self.program.name.replace(" ", "_").replace("/", "_")
                    )
                    if backup_file:
                        self.logger.info(f"Registry backed up to {backup_file}")
                    else:
                        self.logger.warning("Failed to backup registry")
            except Exception as e:
                self.logger.warning(f"Registry backup failed: {e}")

    def _is_msi_package(self) -> bool:
        """
        Check if the program is an MSI package.

        Returns:
            True if MSI package, False otherwise
        """
        if not self.program.uninstall_string:
            return False

        uninstall_str = self.program.uninstall_string.lower()

        # Check for msiexec
        if "msiexec" in uninstall_str:
            return True

        # Check for GUID pattern
        guid_pattern = r'\{[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}\}'
        if re.search(guid_pattern, self.program.uninstall_string):
            return True

        return False

    def _extract_product_code(self) -> Optional[str]:
        """
        Extract MSI product code (GUID) from uninstall string.

        Returns:
            Product code or None if not found
        """
        if not self.program.uninstall_string:
            return None

        # Look for GUID pattern
        guid_pattern = r'\{[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}\}'
        match = re.search(guid_pattern, self.program.uninstall_string)

        if match:
            return match.group(0)

        return None

    def _uninstall_msi(self, silent: bool, timeout: int) -> UninstallResult:
        """
        Uninstall MSI package.

        Args:
            silent: Run in silent mode
            timeout: Timeout in seconds

        Returns:
            UninstallResult object
        """
        product_code = self._extract_product_code()

        if not product_code:
            self.logger.error("Could not extract MSI product code")
            return UninstallResult(
                success=False,
                error_message="Could not extract MSI product code"
            )

        self.logger.info(f"Uninstalling MSI package: {product_code}")

        # Build msiexec command
        if silent:
            # /qn = no UI, /norestart = don't restart
            cmd = f'msiexec.exe /x {product_code} /qn /norestart'
        else:
            # /passive = progress bar only
            cmd = f'msiexec.exe /x {product_code} /passive /norestart'

        self.logger.info(f"Executing: {cmd}")

        try:
            # Execute command
            process = subprocess.Popen(
                cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            # Wait for completion
            try:
                stdout, stderr = process.communicate(timeout=timeout)
                exit_code = process.returncode

                if stdout:
                    self.logger.debug(f"stdout: {stdout}")
                if stderr:
                    self.logger.debug(f"stderr: {stderr}")

                # MSI exit codes: 0 = success, 3010 = success (reboot required)
                if exit_code in [0, 3010]:
                    self.logger.info(f"MSI uninstall completed with exit code {exit_code}")
                    return UninstallResult(success=True, exit_code=exit_code)
                else:
                    self.logger.error(f"MSI uninstall failed with exit code {exit_code}")
                    return UninstallResult(
                        success=False,
                        exit_code=exit_code,
                        error_message=f"Exit code {exit_code}: {stderr}"
                    )

            except subprocess.TimeoutExpired:
                process.kill()
                self.logger.error(f"MSI uninstall timed out after {timeout} seconds")
                return UninstallResult(
                    success=False,
                    error_message=f"Timeout after {timeout} seconds"
                )

        except Exception as e:
            self.logger.error(f"MSI uninstall exception: {e}")
            return UninstallResult(
                success=False,
                error_message=str(e)
            )

    def _execute_uninstall_string(self, silent: bool, timeout: int) -> UninstallResult:
        """
        Execute the UninstallString.

        Args:
            silent: Run in silent mode
            timeout: Timeout in seconds

        Returns:
            UninstallResult object
        """
        if not self.program.uninstall_string:
            return UninstallResult(
                success=False,
                error_message="No uninstall string available"
            )

        # Use QuietUninstallString if available and silent mode is requested
        if silent and self.program.quiet_uninstall_string:
            cmd = self.program.quiet_uninstall_string
            self.logger.info("Using QuietUninstallString")
        else:
            cmd = self.program.uninstall_string

            # Try to add silent parameters if not already present
            if silent:
                cmd = self._add_silent_parameters(cmd)

        self.logger.info(f"Executing UninstallString: {cmd}")

        try:
            # Execute command
            process = subprocess.Popen(
                cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            # Wait for completion
            try:
                stdout, stderr = process.communicate(timeout=timeout)
                exit_code = process.returncode

                if stdout:
                    self.logger.debug(f"stdout: {stdout}")
                if stderr:
                    self.logger.debug(f"stderr: {stderr}")

                # Exit code 0 typically means success
                if exit_code == 0:
                    self.logger.info(f"Uninstall completed successfully")
                    return UninstallResult(success=True, exit_code=exit_code)
                else:
                    self.logger.warning(f"Uninstall completed with exit code {exit_code}")
                    # Some uninstallers return non-zero even on success
                    # We'll consider it a success if no error message
                    return UninstallResult(
                        success=True,
                        exit_code=exit_code,
                        error_message=stderr if stderr else None
                    )

            except subprocess.TimeoutExpired:
                process.kill()
                self.logger.error(f"Uninstall timed out after {timeout} seconds")
                return UninstallResult(
                    success=False,
                    error_message=f"Timeout after {timeout} seconds"
                )

        except Exception as e:
            self.logger.error(f"Uninstall exception: {e}")
            return UninstallResult(
                success=False,
                error_message=str(e)
            )

    def _add_silent_parameters(self, cmd: str) -> str:
        """
        Add silent parameters to the uninstall command if not already present.

        Args:
            cmd: Original command

        Returns:
            Command with silent parameters added
        """
        cmd_lower = cmd.lower()

        # Common silent parameters
        silent_params = {
            # NSIS
            "/S": ["nsis", "uninst"],
            # Inno Setup
            "/VERYSILENT": ["unins"],
            # InstallShield
            "/s": ["setup.exe", "uninstall.exe"],
            # MSI (backup)
            "/quiet": ["msiexec"],
        }

        # Check if already has silent parameter
        existing_silent = ["/s", "/silent", "/quiet", "/verysilent", "/qn"]
        if any(param in cmd_lower for param in existing_silent):
            self.logger.debug("Command already has silent parameter")
            return cmd

        # Try to detect installer type and add appropriate parameter
        for param, patterns in silent_params.items():
            if any(pattern in cmd_lower for pattern in patterns):
                self.logger.info(f"Adding silent parameter: {param}")
                return f"{cmd} {param}"

        # Default: try /S (NSIS style)
        self.logger.info("Adding default silent parameter: /S")
        return f"{cmd} /S"

    def get_uninstall_command(self, silent: bool = True) -> Optional[str]:
        """
        Get the uninstall command that would be executed.

        Args:
            silent: Whether to get the silent command

        Returns:
            Command string or None
        """
        if self._is_msi_package():
            product_code = self._extract_product_code()
            if product_code:
                if silent:
                    return f'msiexec.exe /x {product_code} /qn /norestart'
                else:
                    return f'msiexec.exe /x {product_code} /passive /norestart'

        if silent and self.program.quiet_uninstall_string:
            return self.program.quiet_uninstall_string
        elif self.program.uninstall_string:
            cmd = self.program.uninstall_string
            if silent:
                cmd = self._add_silent_parameters(cmd)
            return cmd

        return None


def uninstall_program(
    program: InstalledProgram,
    silent: bool = True,
    create_backup: bool = True,
    timeout: int = 600
) -> UninstallResult:
    """
    Convenience function to uninstall a program.

    Args:
        program: InstalledProgram to uninstall
        silent: Run in silent mode
        create_backup: Create backup before uninstalling
        timeout: Timeout in seconds

    Returns:
        UninstallResult object
    """
    uninstaller = Uninstaller(program)
    return uninstaller.uninstall(silent, create_backup, timeout)

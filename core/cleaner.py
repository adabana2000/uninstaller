"""
Cleaner for removing leftover files, directories, registry entries, and shortcuts.
"""

import os
import shutil
import winreg
import subprocess
from typing import List, Dict, Tuple
from dataclasses import dataclass

from core.scanner import Leftover
from utils.logger import get_logger
from utils.backup import BackupManager


@dataclass
class CleanResult:
    """Result of a cleaning operation."""
    total_items: int
    deleted_items: int
    failed_items: int
    errors: List[Tuple[str, str]]  # (path, error_message)
    size_freed: int = 0  # in bytes


class Cleaner:
    """
    Handles safe deletion of leftover items.

    Features:
    - Safe file and directory deletion
    - Registry key deletion
    - Shortcut deletion
    - Backup before deletion
    - Error handling and reporting
    """

    def __init__(self, create_backup: bool = True):
        """
        Initialize the cleaner.

        Args:
            create_backup: Create backup before deletion
        """
        self.logger = get_logger()
        self.create_backup = create_backup
        self.backup_manager = BackupManager() if create_backup else None

    def clean(self, leftovers: List[Leftover]) -> CleanResult:
        """
        Clean (delete) leftover items.

        Args:
            leftovers: List of Leftover objects to delete

        Returns:
            CleanResult object
        """
        self.logger.log_operation_start("Clean Leftovers", f"{len(leftovers)} items")

        result = CleanResult(
            total_items=len(leftovers),
            deleted_items=0,
            failed_items=0,
            errors=[]
        )

        # Group leftovers by type
        grouped = self._group_by_type(leftovers)

        # Create backups
        if self.create_backup:
            self._create_backups(grouped)

        # Delete items by type
        # Order matters: shortcuts first, then files, then directories, then registry
        for ltype in ['shortcut', 'file', 'directory', 'registry']:
            if ltype in grouped:
                for leftover in grouped[ltype]:
                    success, error = self._delete_item(leftover)
                    if success:
                        result.deleted_items += 1
                        if leftover.size:
                            result.size_freed += leftover.size
                    else:
                        result.failed_items += 1
                        result.errors.append((leftover.path, error))

        self.logger.log_operation_end(
            "Clean Leftovers",
            result.failed_items == 0,
            f"Deleted: {result.deleted_items}/{result.total_items}, Failed: {result.failed_items}"
        )

        return result

    def _group_by_type(self, leftovers: List[Leftover]) -> Dict[str, List[Leftover]]:
        """
        Group leftovers by type.

        Args:
            leftovers: List of Leftover objects

        Returns:
            Dictionary mapping type to list of leftovers
        """
        grouped = {}
        for leftover in leftovers:
            if leftover.type not in grouped:
                grouped[leftover.type] = []
            grouped[leftover.type].append(leftover)
        return grouped

    def _create_backups(self, grouped: Dict[str, List[Leftover]]) -> None:
        """
        Create backups before deletion.

        Args:
            grouped: Grouped leftovers
        """
        self.logger.info("Creating backups...")

        # Backup files
        if 'file' in grouped or 'directory' in grouped:
            file_paths = []
            if 'file' in grouped:
                file_paths.extend([l.path for l in grouped['file']])
            if 'directory' in grouped:
                file_paths.extend([l.path for l in grouped['directory']])

            if file_paths:
                backup_file = self.backup_manager.backup_files(
                    file_paths,
                    f"leftovers_{self._get_timestamp()}"
                )
                if backup_file:
                    self.logger.info(f"Files backed up to {backup_file}")
                else:
                    self.logger.warning("Failed to backup files")

        # Backup registry keys
        if 'registry' in grouped:
            for leftover in grouped['registry']:
                try:
                    # Extract hive and path
                    hive, path = self._parse_registry_path(leftover.path)
                    if hive and path:
                        backup_file = self.backup_manager.backup_registry_key(
                            hive,
                            path,
                            f"registry_{self._get_timestamp()}"
                        )
                        if backup_file:
                            self.logger.debug(f"Registry key backed up: {leftover.path}")
                except Exception as e:
                    self.logger.warning(f"Failed to backup registry key {leftover.path}: {e}")

    def _delete_item(self, leftover: Leftover) -> Tuple[bool, str]:
        """
        Delete a single leftover item.

        Args:
            leftover: Leftover object to delete

        Returns:
            Tuple of (success, error_message)
        """
        try:
            if leftover.type == 'file':
                return self._delete_file(leftover.path)
            elif leftover.type == 'directory':
                return self._delete_directory(leftover.path)
            elif leftover.type == 'registry':
                return self._delete_registry_key(leftover.path)
            elif leftover.type == 'shortcut':
                return self._delete_file(leftover.path)
            else:
                return False, f"Unknown leftover type: {leftover.type}"

        except Exception as e:
            return False, str(e)

    def _delete_file(self, file_path: str) -> Tuple[bool, str]:
        """
        Delete a file.

        Args:
            file_path: Path to the file

        Returns:
            Tuple of (success, error_message)
        """
        try:
            if not os.path.exists(file_path):
                return True, ""  # Already deleted

            os.remove(file_path)
            self.logger.log_file_deletion(file_path, True)
            return True, ""

        except PermissionError as e:
            self.logger.log_file_deletion(file_path, False)
            return False, f"Permission denied: {e}"
        except Exception as e:
            self.logger.log_file_deletion(file_path, False)
            return False, str(e)

    def _delete_directory(self, dir_path: str) -> Tuple[bool, str]:
        """
        Delete a directory and all its contents.

        Args:
            dir_path: Path to the directory

        Returns:
            Tuple of (success, error_message)
        """
        try:
            if not os.path.exists(dir_path):
                return True, ""  # Already deleted

            shutil.rmtree(dir_path)
            self.logger.info(f"Deleted directory: {dir_path}")
            return True, ""

        except PermissionError as e:
            self.logger.warning(f"Failed to delete directory {dir_path}: Permission denied")
            return False, f"Permission denied: {e}"
        except Exception as e:
            self.logger.warning(f"Failed to delete directory {dir_path}: {e}")
            return False, str(e)

    def _delete_registry_key(self, key_path: str) -> Tuple[bool, str]:
        """
        Delete a registry key.

        Args:
            key_path: Full registry key path (e.g., HKEY_LOCAL_MACHINE\\Software\\Example)

        Returns:
            Tuple of (success, error_message)
        """
        try:
            # Parse the registry path
            hive, path = self._parse_registry_path(key_path)

            if not hive or not path:
                return False, "Invalid registry path"

            # Check if key exists
            try:
                # Try to open the key to check if it exists
                test_key = winreg.OpenKey(hive, path, 0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY)
                winreg.CloseKey(test_key)
            except FileNotFoundError:
                # Key doesn't exist, consider it success
                return True, ""
            except OSError:
                # Try without WOW64 flag
                try:
                    test_key = winreg.OpenKey(hive, path, 0, winreg.KEY_READ)
                    winreg.CloseKey(test_key)
                except FileNotFoundError:
                    return True, ""
                except:
                    pass  # Continue to deletion attempt

            # Always try recursive deletion to handle subkeys
            return self._delete_registry_key_recursive(hive, path)

        except PermissionError as e:
            self.logger.log_registry_deletion(key_path, False)
            return False, f"Permission denied: {e}"
        except Exception as e:
            self.logger.log_registry_deletion(key_path, False)
            return False, str(e)

    def _delete_registry_key_recursive(self, hive: int, path: str) -> Tuple[bool, str]:
        """
        Recursively delete a registry key and all its subkeys.

        Args:
            hive: Registry hive
            path: Key path

        Returns:
            Tuple of (success, error_message)
        """
        try:
            # Try with WOW64_64KEY first (for 64-bit registry view)
            access_flags = [
                winreg.KEY_ALL_ACCESS | winreg.KEY_WOW64_64KEY,
                winreg.KEY_ALL_ACCESS | winreg.KEY_WOW64_32KEY,
                winreg.KEY_ALL_ACCESS,
            ]

            key_opened = False
            for access in access_flags:
                try:
                    # Open the key
                    with winreg.OpenKey(hive, path, 0, access) as key:
                        key_opened = True
                        # Delete all subkeys first
                        while True:
                            try:
                                subkey_name = winreg.EnumKey(key, 0)
                                success, error = self._delete_registry_key_recursive(
                                    hive,
                                    f"{path}\\{subkey_name}"
                                )
                                if not success:
                                    # Log but continue trying other subkeys
                                    self.logger.warning(f"Failed to delete subkey {subkey_name}: {error}")
                            except OSError:
                                # No more subkeys
                                break
                        break  # Successfully opened and processed
                except OSError:
                    continue  # Try next access flag

            if not key_opened:
                raise OSError("Could not open registry key with any access level")

            # Now delete the key itself
            # Try different access levels for deletion
            deleted = False
            for access in access_flags:
                try:
                    # For deletion, we need to use DeleteKeyEx if available (Windows Vista+)
                    if hasattr(winreg, 'DeleteKeyEx'):
                        winreg.DeleteKeyEx(hive, path, access, 0)
                    else:
                        winreg.DeleteKey(hive, path)
                    deleted = True
                    break
                except OSError:
                    continue

            if not deleted:
                # Last resort: try without special access flags
                try:
                    winreg.DeleteKey(hive, path)
                    deleted = True
                except:
                    pass

            full_path = f"{self._get_hive_name(hive)}\\{path}"

            if deleted:
                self.logger.log_registry_deletion(full_path, True)
                return True, ""
            else:
                raise OSError("Could not delete registry key")

        except Exception as e:
            full_path = f"{self._get_hive_name(hive)}\\{path}"
            self.logger.log_registry_deletion(full_path, False)
            return False, str(e)

    def _parse_registry_path(self, key_path: str) -> Tuple[int, str]:
        """
        Parse a registry path into hive and path.

        Args:
            key_path: Full registry path

        Returns:
            Tuple of (hive, path)
        """
        hive_map = {
            "HKEY_LOCAL_MACHINE": winreg.HKEY_LOCAL_MACHINE,
            "HKLM": winreg.HKEY_LOCAL_MACHINE,
            "HKEY_CURRENT_USER": winreg.HKEY_CURRENT_USER,
            "HKCU": winreg.HKEY_CURRENT_USER,
            "HKEY_CLASSES_ROOT": winreg.HKEY_CLASSES_ROOT,
            "HKCR": winreg.HKEY_CLASSES_ROOT,
            "HKEY_USERS": winreg.HKEY_USERS,
            "HKU": winreg.HKEY_USERS,
            "HKEY_CURRENT_CONFIG": winreg.HKEY_CURRENT_CONFIG,
            "HKCC": winreg.HKEY_CURRENT_CONFIG,
        }

        for hive_name, hive_const in hive_map.items():
            if key_path.startswith(hive_name + "\\"):
                path = key_path[len(hive_name) + 1:]
                return hive_const, path

        return None, None

    def _get_hive_name(self, hive: int) -> str:
        """Get registry hive name."""
        hive_names = {
            winreg.HKEY_LOCAL_MACHINE: "HKEY_LOCAL_MACHINE",
            winreg.HKEY_CURRENT_USER: "HKEY_CURRENT_USER",
            winreg.HKEY_CLASSES_ROOT: "HKEY_CLASSES_ROOT",
            winreg.HKEY_USERS: "HKEY_USERS",
            winreg.HKEY_CURRENT_CONFIG: "HKEY_CURRENT_CONFIG",
        }
        return hive_names.get(hive, "UNKNOWN")

    def _get_timestamp(self) -> str:
        """Get current timestamp string."""
        from datetime import datetime
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    def print_result(self, result: CleanResult) -> None:
        """
        Print cleaning result summary.

        Args:
            result: CleanResult object
        """
        print("\n" + "=" * 70)
        print("Cleaning Result")
        print("=" * 70)
        print(f"Total items:    {result.total_items}")
        print(f"Deleted:        {result.deleted_items}")
        print(f"Failed:         {result.failed_items}")

        if result.size_freed > 0:
            print(f"Space freed:    {self._format_size(result.size_freed)}")

        if result.errors:
            print(f"\nErrors ({len(result.errors)}):")
            for path, error in result.errors[:10]:  # Show first 10 errors
                print(f"  - {path}")
                print(f"    Error: {error}")
            if len(result.errors) > 10:
                print(f"  ... and {len(result.errors) - 10} more errors")

        print("=" * 70)

    def _format_size(self, size_bytes: int) -> str:
        """Format file size."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"


def clean_leftovers(leftovers: List[Leftover], create_backup: bool = True) -> CleanResult:
    """
    Convenience function to clean leftovers.

    Args:
        leftovers: List of Leftover objects to delete
        create_backup: Create backup before deletion

    Returns:
        CleanResult object
    """
    cleaner = Cleaner(create_backup)
    return cleaner.clean(leftovers)

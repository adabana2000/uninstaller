"""
Backup and restore utilities for the uninstaller application.
Provides functions to create system restore points, backup registry keys, and backup files.
"""

import os
import subprocess
import winreg
import zipfile
import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict
import shutil


class BackupManager:
    """
    Manages backups for uninstall operations.

    Features:
    - System restore point creation
    - Registry key backup
    - File backup
    - Backup restoration
    """

    def __init__(self, backup_dir: Optional[str] = None):
        """
        Initialize the backup manager.

        Args:
            backup_dir: Directory to store backups (default: %LOCALAPPDATA%/Uninstaller/backups)
        """
        if backup_dir is None:
            appdata = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
            backup_dir = os.path.join(appdata, "Uninstaller", "backups")

        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def create_restore_point(self, description: str = "Uninstaller Backup") -> bool:
        """
        Create a Windows System Restore Point.

        Args:
            description: Description for the restore point

        Returns:
            True if successful, False otherwise
        """
        try:
            # Use wmic to create a restore point
            # Restore point types: 0=Application Install, 7=Application Uninstall, 100=Custom
            cmd = (
                f'wmic.exe /Namespace:\\\\root\\default Path SystemRestore '
                f'Call CreateRestorePoint "{description}", 100, 7'
            )

            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode == 0:
                return True
            else:
                print(f"Failed to create restore point: {result.stderr}")
                return False

        except Exception as e:
            print(f"Error creating restore point: {e}")
            return False

    def backup_registry_key(
        self,
        hive: int,
        key_path: str,
        backup_name: str
    ) -> Optional[Path]:
        """
        Backup a registry key to a .reg file.

        Args:
            hive: Registry hive (e.g., winreg.HKEY_LOCAL_MACHINE)
            key_path: Path to the registry key
            backup_name: Name for the backup file

        Returns:
            Path to the backup file or None if failed
        """
        try:
            # Create backup subdirectory
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_subdir = self.backup_dir / f"registry_{timestamp}"
            backup_subdir.mkdir(parents=True, exist_ok=True)

            # Construct the full registry path
            hive_name = self._get_hive_name(hive)
            full_key = f"{hive_name}\\{key_path}"

            # Generate backup file path
            backup_file = backup_subdir / f"{backup_name}.reg"

            # Export registry key using reg export command
            cmd = f'reg export "{full_key}" "{backup_file}" /y'

            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                # Save metadata
                self._save_backup_metadata(
                    backup_subdir,
                    "registry",
                    {"key": full_key, "file": backup_file.name}
                )
                return backup_file
            else:
                print(f"Failed to export registry key: {result.stderr}")
                return None

        except Exception as e:
            print(f"Error backing up registry key: {e}")
            return None

    def backup_files(
        self,
        file_paths: List[str],
        backup_name: str
    ) -> Optional[Path]:
        """
        Backup files to a ZIP archive.

        Args:
            file_paths: List of file paths to backup
            backup_name: Name for the backup archive

        Returns:
            Path to the backup ZIP file or None if failed
        """
        try:
            # Create backup subdirectory
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_subdir = self.backup_dir / f"files_{timestamp}"
            backup_subdir.mkdir(parents=True, exist_ok=True)

            # Generate backup file path
            backup_file = backup_subdir / f"{backup_name}.zip"

            # Create ZIP archive
            with zipfile.ZipFile(backup_file, "w", zipfile.ZIP_DEFLATED) as zipf:
                backed_up_files = []

                for file_path in file_paths:
                    if os.path.exists(file_path):
                        try:
                            # Add file to ZIP with relative path preserved
                            if os.path.isfile(file_path):
                                arcname = os.path.basename(file_path)
                                zipf.write(file_path, arcname)
                                backed_up_files.append(file_path)
                            elif os.path.isdir(file_path):
                                # Backup entire directory
                                for root, dirs, files in os.walk(file_path):
                                    for file in files:
                                        full_path = os.path.join(root, file)
                                        rel_path = os.path.relpath(full_path, os.path.dirname(file_path))
                                        zipf.write(full_path, rel_path)
                                backed_up_files.append(file_path)

                        except Exception as e:
                            print(f"Failed to backup {file_path}: {e}")

            # Save metadata
            self._save_backup_metadata(
                backup_subdir,
                "files",
                {"files": backed_up_files, "archive": backup_file.name}
            )

            return backup_file

        except Exception as e:
            print(f"Error backing up files: {e}")
            return None

    def backup_directory(
        self,
        directory_path: str,
        backup_name: str
    ) -> Optional[Path]:
        """
        Backup an entire directory to a ZIP archive.

        Args:
            directory_path: Path to the directory to backup
            backup_name: Name for the backup archive

        Returns:
            Path to the backup ZIP file or None if failed
        """
        try:
            if not os.path.isdir(directory_path):
                print(f"Directory not found: {directory_path}")
                return None

            # Create backup subdirectory
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_subdir = self.backup_dir / f"directory_{timestamp}"
            backup_subdir.mkdir(parents=True, exist_ok=True)

            # Generate backup file path
            backup_file = backup_subdir / f"{backup_name}.zip"

            # Create ZIP archive using shutil
            base_name = str(backup_file).replace(".zip", "")
            shutil.make_archive(base_name, "zip", directory_path)

            # Save metadata
            self._save_backup_metadata(
                backup_subdir,
                "directory",
                {"directory": directory_path, "archive": backup_file.name}
            )

            return backup_file

        except Exception as e:
            print(f"Error backing up directory: {e}")
            return None

    def restore_registry_backup(self, backup_file: Path) -> bool:
        """
        Restore a registry backup from a .reg file.

        Args:
            backup_file: Path to the .reg backup file

        Returns:
            True if successful, False otherwise
        """
        try:
            if not backup_file.exists():
                print(f"Backup file not found: {backup_file}")
                return False

            # Import registry file using reg import command
            cmd = f'reg import "{backup_file}"'

            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                return True
            else:
                print(f"Failed to restore registry: {result.stderr}")
                return False

        except Exception as e:
            print(f"Error restoring registry backup: {e}")
            return False

    def restore_file_backup(self, backup_file: Path, restore_path: str) -> bool:
        """
        Restore files from a ZIP backup.

        Args:
            backup_file: Path to the ZIP backup file
            restore_path: Path to restore files to

        Returns:
            True if successful, False otherwise
        """
        try:
            if not backup_file.exists():
                print(f"Backup file not found: {backup_file}")
                return False

            # Extract ZIP archive
            with zipfile.ZipFile(backup_file, "r") as zipf:
                zipf.extractall(restore_path)

            return True

        except Exception as e:
            print(f"Error restoring file backup: {e}")
            return False

    def list_backups(self) -> List[Dict]:
        """
        List all available backups.

        Returns:
            List of backup information dictionaries
        """
        backups = []

        for backup_dir in self.backup_dir.iterdir():
            if backup_dir.is_dir():
                metadata_file = backup_dir / "metadata.json"
                if metadata_file.exists():
                    try:
                        with open(metadata_file, "r", encoding="utf-8") as f:
                            metadata = json.load(f)
                            metadata["path"] = str(backup_dir)
                            backups.append(metadata)
                    except Exception as e:
                        print(f"Failed to read metadata from {backup_dir}: {e}")

        # Sort by timestamp (newest first)
        backups.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

        return backups

    def cleanup_old_backups(self, keep_days: int = 30) -> int:
        """
        Delete backups older than specified days.

        Args:
            keep_days: Number of days to keep backups

        Returns:
            Number of deleted backups
        """
        deleted_count = 0
        current_time = datetime.now()

        for backup_dir in self.backup_dir.iterdir():
            if backup_dir.is_dir():
                try:
                    # Get directory modification time
                    dir_time = datetime.fromtimestamp(backup_dir.stat().st_mtime)
                    age_days = (current_time - dir_time).days

                    if age_days > keep_days:
                        shutil.rmtree(backup_dir)
                        deleted_count += 1

                except Exception as e:
                    print(f"Failed to delete old backup {backup_dir}: {e}")

        return deleted_count

    def _get_hive_name(self, hive: int) -> str:
        """
        Get the registry hive name from the hive constant.

        Args:
            hive: Registry hive constant

        Returns:
            Hive name string
        """
        hive_names = {
            winreg.HKEY_LOCAL_MACHINE: "HKEY_LOCAL_MACHINE",
            winreg.HKEY_CURRENT_USER: "HKEY_CURRENT_USER",
            winreg.HKEY_CLASSES_ROOT: "HKEY_CLASSES_ROOT",
            winreg.HKEY_USERS: "HKEY_USERS",
            winreg.HKEY_CURRENT_CONFIG: "HKEY_CURRENT_CONFIG",
        }
        return hive_names.get(hive, "UNKNOWN")

    def _save_backup_metadata(
        self,
        backup_dir: Path,
        backup_type: str,
        details: Dict
    ) -> None:
        """
        Save backup metadata to a JSON file.

        Args:
            backup_dir: Backup directory
            backup_type: Type of backup (registry, files, directory)
            details: Additional details about the backup
        """
        metadata = {
            "timestamp": datetime.now().isoformat(),
            "type": backup_type,
            "details": details,
        }

        metadata_file = backup_dir / "metadata.json"
        with open(metadata_file, "w", encoding="utf-8") as f:
            json.dump(metadata, indent=2, fp=f)


# Convenience functions
def create_restore_point(description: str = "Uninstaller Backup") -> bool:
    """
    Create a system restore point.

    Args:
        description: Description for the restore point

    Returns:
        True if successful, False otherwise
    """
    manager = BackupManager()
    return manager.create_restore_point(description)


def backup_registry(hive: int, key_path: str, backup_name: str) -> Optional[Path]:
    """
    Backup a registry key.

    Args:
        hive: Registry hive
        key_path: Path to the registry key
        backup_name: Name for the backup

    Returns:
        Path to the backup file or None if failed
    """
    manager = BackupManager()
    return manager.backup_registry_key(hive, key_path, backup_name)


if __name__ == "__main__":
    # Test the backup manager
    manager = BackupManager()

    print("Testing Backup Manager...")
    print(f"Backup directory: {manager.backup_dir}")

    # Test system restore point (requires admin privileges)
    # print("\nCreating system restore point...")
    # if manager.create_restore_point("Test Restore Point"):
    #     print("✓ Restore point created successfully")
    # else:
    #     print("✗ Failed to create restore point (admin privileges required)")

    # List existing backups
    print("\nExisting backups:")
    backups = manager.list_backups()
    if backups:
        for backup in backups:
            print(f"  - {backup['type']} backup at {backup['timestamp']}")
    else:
        print("  No backups found")

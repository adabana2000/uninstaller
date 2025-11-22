"""
Leftover scanner for detecting files, registry entries, and other remnants
after uninstallation.
"""

import os
import re
import winreg
from datetime import datetime
from typing import List, Set, Optional
from dataclasses import dataclass
from pathlib import Path

from core.registry import InstalledProgram
from utils.logger import get_logger
from utils.system_info import get_program_files_paths, get_appdata_paths, get_user_directories


@dataclass
class Leftover:
    """Represents a leftover item after uninstallation."""
    type: str  # file, directory, registry, service, shortcut
    path: str
    size: Optional[int] = None  # in bytes (for files)
    last_modified: Optional[datetime] = None
    description: Optional[str] = None

    def __str__(self) -> str:
        """String representation."""
        if self.type == "file":
            size_str = f" ({self._format_size(self.size)})" if self.size else ""
            return f"[File] {self.path}{size_str}"
        elif self.type == "directory":
            return f"[Dir]  {self.path}"
        elif self.type == "registry":
            return f"[Reg]  {self.path}"
        elif self.type == "shortcut":
            return f"[Link] {self.path}"
        else:
            return f"[{self.type}] {self.path}"

    def _format_size(self, size_bytes: int) -> str:
        """Format file size."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"


class LeftoverScanner:
    """
    Scans for leftover files, directories, registry entries, and other items
    after a program has been uninstalled.

    Features:
    - File and directory scanning
    - Registry scanning
    - Shortcut scanning
    - Service detection (basic)
    - Pattern-based matching
    """

    def __init__(self):
        """Initialize the scanner."""
        self.logger = get_logger()
        self.leftovers: List[Leftover] = []

    def scan(
        self,
        program: InstalledProgram,
        scan_files: bool = True,
        scan_registry: bool = True,
        scan_shortcuts: bool = True
    ) -> List[Leftover]:
        """
        Scan for leftovers of a program.

        Args:
            program: InstalledProgram to scan for
            scan_files: Scan for files and directories
            scan_registry: Scan registry
            scan_shortcuts: Scan for shortcuts

        Returns:
            List of Leftover objects
        """
        self.logger.log_operation_start("Leftover Scan", program.name)
        self.leftovers = []

        # Generate search patterns from program name and publisher
        patterns = self._generate_search_patterns(program)

        if scan_files:
            self._scan_files(patterns, program)

        if scan_registry:
            self._scan_registry(patterns, program)

        if scan_shortcuts:
            self._scan_shortcuts(patterns)

        self.logger.log_operation_end(
            "Leftover Scan",
            True,
            f"Found {len(self.leftovers)} leftover items"
        )

        return self.leftovers

    def _generate_search_patterns(self, program: InstalledProgram) -> List[str]:
        """
        Generate search patterns from program information.

        Args:
            program: InstalledProgram

        Returns:
            List of search patterns (lowercase)
        """
        patterns = []

        # Add program name
        if program.name:
            patterns.append(program.name.lower())
            # Also add name without version numbers
            name_no_version = re.sub(r'\s+\d+(\.\d+)*', '', program.name).lower()
            if name_no_version != program.name.lower():
                patterns.append(name_no_version)

        # Add publisher
        if program.publisher:
            patterns.append(program.publisher.lower())

        # Remove duplicates and very short patterns
        patterns = list(set(p for p in patterns if len(p) >= 3))

        self.logger.debug(f"Search patterns: {patterns}")
        return patterns

    def _scan_files(self, patterns: List[str], program: InstalledProgram) -> None:
        """
        Scan for leftover files and directories.

        Args:
            patterns: Search patterns
            program: InstalledProgram
        """
        self.logger.info("Scanning for leftover files...")

        # Directories to scan
        scan_dirs = []

        # Program Files
        for pf_path in get_program_files_paths():
            if os.path.exists(pf_path):
                scan_dirs.append(Path(pf_path))

        # AppData
        appdata = get_appdata_paths()
        for key in ['local', 'roaming', 'program_data']:
            if appdata[key] and os.path.exists(appdata[key]):
                scan_dirs.append(Path(appdata[key]))

        # Scan each directory
        for base_dir in scan_dirs:
            try:
                self._scan_directory(base_dir, patterns, max_depth=2)
            except PermissionError:
                self.logger.warning(f"Permission denied scanning directory: {base_dir}")
            except FileNotFoundError:
                self.logger.warning(f"Directory not found: {base_dir}")
            except OSError as e:
                self.logger.warning(f"OS error scanning {base_dir}: {e}")
            except Exception as e:
                # Catch-all for unexpected errors
                self.logger.error(f"Unexpected error scanning {base_dir}: {e}")

    def _scan_directory(
        self,
        directory: Path,
        patterns: List[str],
        max_depth: int = 2,
        current_depth: int = 0
    ) -> None:
        """
        Recursively scan a directory for matching items.

        Args:
            directory: Directory to scan
            patterns: Search patterns
            max_depth: Maximum recursion depth
            current_depth: Current recursion depth
        """
        if current_depth > max_depth:
            return

        try:
            for item in directory.iterdir():
                try:
                    item_name_lower = item.name.lower()

                    # Check if item name matches any pattern
                    if any(pattern in item_name_lower for pattern in patterns):
                        if item.is_file():
                            # Add file
                            try:
                                stat = item.stat()
                                self.leftovers.append(Leftover(
                                    type="file",
                                    path=str(item),
                                    size=stat.st_size,
                                    last_modified=datetime.fromtimestamp(stat.st_mtime)
                                ))
                            except (OSError, ValueError) as e:
                                self.logger.debug(f"Cannot stat file {item}: {e}")
                                # Add file without size info
                                self.leftovers.append(Leftover(
                                    type="file",
                                    path=str(item)
                                ))
                        elif item.is_dir():
                            # Add directory (and all its contents)
                            total_size = self._get_directory_size(item)
                            item_count = self._count_items(item)
                            self.leftovers.append(Leftover(
                                type="directory",
                                path=str(item),
                                size=total_size,
                                description=f"Directory with {item_count} items"
                            ))
                            # Don't recurse into matched directories
                            continue

                    # Recurse into non-matched directories
                    if item.is_dir() and current_depth < max_depth:
                        self._scan_directory(item, patterns, max_depth, current_depth + 1)

                except PermissionError:
                    # Skip items we can't access due to permissions
                    self.logger.debug(f"Permission denied: {item}")
                except FileNotFoundError:
                    # File was deleted during scan
                    self.logger.debug(f"File not found (deleted during scan): {item}")
                except OSError as e:
                    # Other OS errors (e.g., broken symlinks)
                    self.logger.debug(f"OS error accessing {item}: {e}")

        except PermissionError:
            self.logger.debug(f"Permission denied accessing directory: {directory}")
        except FileNotFoundError:
            self.logger.debug(f"Directory not found: {directory}")
        except OSError as e:
            self.logger.debug(f"OS error accessing directory {directory}: {e}")

    def _get_directory_size(self, directory: Path) -> int:
        """
        Calculate total size of a directory.

        Args:
            directory: Directory path

        Returns:
            Total size in bytes (0 if inaccessible)
        """
        total_size = 0
        try:
            for item in directory.rglob('*'):
                if item.is_file():
                    try:
                        total_size += item.stat().st_size
                    except (PermissionError, FileNotFoundError):
                        # Skip inaccessible or deleted files
                        continue
                    except OSError as e:
                        # Log other OS errors but continue
                        self.logger.debug(f"Error getting size of {item}: {e}")
                        continue
        except (PermissionError, FileNotFoundError):
            # Directory inaccessible or deleted
            self.logger.debug(f"Cannot access directory for size calculation: {directory}")
        except OSError as e:
            # Other OS errors
            self.logger.debug(f"OS error calculating directory size {directory}: {e}")
        return total_size

    def _count_items(self, directory: Path) -> int:
        """
        Count items in a directory.

        Args:
            directory: Directory path

        Returns:
            Number of items (0 if inaccessible)
        """
        try:
            return sum(1 for _ in directory.rglob('*'))
        except (PermissionError, FileNotFoundError):
            self.logger.debug(f"Cannot access directory for item count: {directory}")
            return 0
        except OSError as e:
            self.logger.debug(f"OS error counting items in {directory}: {e}")
            return 0

    def _scan_registry(self, patterns: List[str], program: InstalledProgram) -> None:
        """
        Scan registry for leftover entries.

        Args:
            patterns: Search patterns
            program: InstalledProgram
        """
        self.logger.info("Scanning registry for leftovers...")

        # Common registry locations to scan
        registry_paths = [
            (winreg.HKEY_LOCAL_MACHINE, r"Software"),
            (winreg.HKEY_CURRENT_USER, r"Software"),
            (winreg.HKEY_LOCAL_MACHINE, r"Software\Wow6432Node"),
        ]

        for hive, base_path in registry_paths:
            try:
                self._scan_registry_key(hive, base_path, patterns, max_depth=2)
            except Exception as e:
                self.logger.debug(f"Error scanning registry {base_path}: {e}")

    def _scan_registry_key(
        self,
        hive: int,
        key_path: str,
        patterns: List[str],
        max_depth: int = 2,
        current_depth: int = 0
    ) -> None:
        """
        Recursively scan a registry key.

        Args:
            hive: Registry hive
            key_path: Key path
            patterns: Search patterns
            max_depth: Maximum recursion depth
            current_depth: Current recursion depth
        """
        if current_depth > max_depth:
            return

        try:
            with winreg.OpenKey(hive, key_path) as key:
                # Enumerate subkeys
                index = 0
                while True:
                    try:
                        subkey_name = winreg.EnumKey(key, index)
                        subkey_name_lower = subkey_name.lower()

                        # Check if subkey name matches any pattern
                        if any(pattern in subkey_name_lower for pattern in patterns):
                            full_path = f"{self._get_hive_name(hive)}\\{key_path}\\{subkey_name}"
                            self.leftovers.append(Leftover(
                                type="registry",
                                path=full_path
                            ))
                        elif current_depth < max_depth:
                            # Recurse into non-matched keys
                            self._scan_registry_key(
                                hive,
                                f"{key_path}\\{subkey_name}",
                                patterns,
                                max_depth,
                                current_depth + 1
                            )

                        index += 1
                    except OSError:
                        # No more subkeys
                        break

        except (PermissionError, OSError) as e:
            # Skip keys we can't access
            pass

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

    def _scan_shortcuts(self, patterns: List[str]) -> None:
        """
        Scan for leftover shortcuts.

        Args:
            patterns: Search patterns
        """
        self.logger.info("Scanning for leftover shortcuts...")

        # Directories to scan for shortcuts
        user_dirs = get_user_directories()
        shortcut_dirs = [
            user_dirs['desktop'],
            user_dirs['start_menu'],
            user_dirs['programs'],
        ]

        # Also check common Start Menu location
        start_menu_common = r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs"
        if os.path.exists(start_menu_common):
            shortcut_dirs.append(start_menu_common)

        for shortcut_dir in shortcut_dirs:
            if not os.path.exists(shortcut_dir):
                continue

            try:
                for root, dirs, files in os.walk(shortcut_dir):
                    for file in files:
                        if file.lower().endswith('.lnk'):
                            file_name_lower = file.lower()
                            if any(pattern in file_name_lower for pattern in patterns):
                                full_path = os.path.join(root, file)
                                self.leftovers.append(Leftover(
                                    type="shortcut",
                                    path=full_path
                                ))
            except Exception as e:
                self.logger.debug(f"Error scanning shortcuts in {shortcut_dir}: {e}")

    def get_leftovers_by_type(self, leftover_type: str) -> List[Leftover]:
        """
        Get leftovers of a specific type.

        Args:
            leftover_type: Type of leftover (file, directory, registry, etc.)

        Returns:
            List of matching leftovers
        """
        return [l for l in self.leftovers if l.type == leftover_type]

    def get_total_size(self) -> int:
        """
        Get total size of all file leftovers.

        Returns:
            Total size in bytes
        """
        return sum(l.size for l in self.leftovers if l.size is not None)

    def print_summary(self) -> None:
        """Print a summary of found leftovers."""
        if not self.leftovers:
            print("No leftovers found.")
            return

        # Count by type
        type_counts = {}
        for leftover in self.leftovers:
            type_counts[leftover.type] = type_counts.get(leftover.type, 0) + 1

        print("\n" + "=" * 70)
        print("Leftover Scan Summary")
        print("=" * 70)
        print(f"Total items found: {len(self.leftovers)}")
        print("\nBy type:")
        for ltype, count in sorted(type_counts.items()):
            print(f"  {ltype.capitalize():12}: {count}")

        total_size = self.get_total_size()
        if total_size > 0:
            print(f"\nTotal size: {self._format_size(total_size)}")
        print("=" * 70)

    def _format_size(self, size_bytes: int) -> str:
        """Format file size."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"


def scan_leftovers(
    program: InstalledProgram,
    scan_files: bool = True,
    scan_registry: bool = True,
    scan_shortcuts: bool = True
) -> List[Leftover]:
    """
    Convenience function to scan for leftovers.

    Args:
        program: InstalledProgram to scan for
        scan_files: Scan for files and directories
        scan_registry: Scan registry
        scan_shortcuts: Scan for shortcuts

    Returns:
        List of Leftover objects
    """
    scanner = LeftoverScanner()
    return scanner.scan(program, scan_files, scan_registry, scan_shortcuts)

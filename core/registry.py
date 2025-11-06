"""
Registry operations for reading installed programs information.
Supports both 32-bit and 64-bit applications on Windows 10/11.
"""

import winreg
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class InstalledProgram:
    """Represents an installed program with its metadata."""

    name: str
    version: Optional[str] = None
    publisher: Optional[str] = None
    install_date: Optional[str] = None
    install_location: Optional[str] = None
    uninstall_string: Optional[str] = None
    quiet_uninstall_string: Optional[str] = None
    estimated_size: Optional[int] = None  # in KB
    display_icon: Optional[str] = None
    registry_key: Optional[str] = None
    is_system_component: bool = False
    architecture: str = "x64"  # x64 or x86

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "version": self.version,
            "publisher": self.publisher,
            "install_date": self.install_date,
            "install_location": self.install_location,
            "uninstall_string": self.uninstall_string,
            "quiet_uninstall_string": self.quiet_uninstall_string,
            "estimated_size": self.estimated_size,
            "display_icon": self.display_icon,
            "registry_key": self.registry_key,
            "is_system_component": self.is_system_component,
            "architecture": self.architecture,
        }


class RegistryReader:
    """
    Reads installed programs from Windows Registry.

    Searches in multiple registry locations:
    - HKEY_LOCAL_MACHINE\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall (64-bit apps)
    - HKEY_LOCAL_MACHINE\\Software\\Wow6432Node\\Microsoft\\Windows\\CurrentVersion\\Uninstall (32-bit apps on 64-bit Windows)
    - HKEY_CURRENT_USER\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall (User-level apps)
    """

    # Registry paths to search
    UNINSTALL_PATHS = [
        # 64-bit applications
        (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Uninstall", "x64"),
        # 32-bit applications on 64-bit Windows
        (winreg.HKEY_LOCAL_MACHINE, r"Software\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall", "x86"),
        # User-level applications
        (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Uninstall", "user"),
    ]

    def __init__(self):
        self.programs: List[InstalledProgram] = []

    def get_installed_programs(self, include_updates: bool = False) -> List[InstalledProgram]:
        """
        Retrieve all installed programs from the registry.

        Args:
            include_updates: If False, filters out Windows updates and patches

        Returns:
            List of InstalledProgram objects
        """
        self.programs = []

        for hive, path, arch in self.UNINSTALL_PATHS:
            try:
                self._scan_registry_path(hive, path, arch)
            except OSError as e:
                # Path might not exist (e.g., Wow6432Node on 32-bit Windows)
                print(f"Warning: Could not access {path}: {e}")
                continue

        # Filter out updates if requested
        if not include_updates:
            self.programs = [p for p in self.programs if not self._is_update(p)]

        # Remove duplicates (same program in multiple locations)
        self.programs = self._remove_duplicates(self.programs)

        return self.programs

    def _scan_registry_path(self, hive: int, path: str, arch: str) -> None:
        """
        Scan a specific registry path for installed programs.

        Args:
            hive: Registry hive (e.g., HKEY_LOCAL_MACHINE)
            path: Registry path to scan
            arch: Architecture identifier (x64, x86, or user)
        """
        try:
            with winreg.OpenKey(hive, path) as key:
                index = 0
                while True:
                    try:
                        subkey_name = winreg.EnumKey(key, index)
                        program = self._read_program_info(hive, f"{path}\\{subkey_name}", subkey_name, arch)

                        if program and program.name:  # Only add if it has a name
                            self.programs.append(program)

                        index += 1
                    except OSError:
                        # No more subkeys
                        break
        except OSError as e:
            raise OSError(f"Failed to open registry key {path}: {e}")

    def _read_program_info(self, hive: int, key_path: str, subkey_name: str, arch: str) -> Optional[InstalledProgram]:
        """
        Read program information from a specific registry key.

        Args:
            hive: Registry hive
            key_path: Full path to the registry key
            subkey_name: Name of the subkey (usually GUID or program name)
            arch: Architecture identifier

        Returns:
            InstalledProgram object or None if the key doesn't contain valid program info
        """
        try:
            with winreg.OpenKey(hive, key_path) as key:
                # Read all available values
                display_name = self._read_value(key, "DisplayName")

                # Skip if no display name
                if not display_name:
                    return None

                # Check if it's a system component (usually hidden)
                system_component = self._read_value(key, "SystemComponent", 0)

                program = InstalledProgram(
                    name=display_name,
                    version=self._read_value(key, "DisplayVersion"),
                    publisher=self._read_value(key, "Publisher"),
                    install_date=self._parse_install_date(self._read_value(key, "InstallDate")),
                    install_location=self._read_value(key, "InstallLocation"),
                    uninstall_string=self._read_value(key, "UninstallString"),
                    quiet_uninstall_string=self._read_value(key, "QuietUninstallString"),
                    estimated_size=self._read_value(key, "EstimatedSize", 0),
                    display_icon=self._read_value(key, "DisplayIcon"),
                    registry_key=key_path,
                    is_system_component=(system_component == 1),
                    architecture=arch,
                )

                return program

        except OSError as e:
            print(f"Warning: Could not read program info from {key_path}: {e}")
            return None

    def _read_value(self, key, value_name: str, default=None):
        """
        Safely read a value from a registry key.

        Args:
            key: Open registry key
            value_name: Name of the value to read
            default: Default value if the value doesn't exist

        Returns:
            Value or default if not found
        """
        try:
            value, _ = winreg.QueryValueEx(key, value_name)
            return value if value else default
        except OSError:
            return default

    def _parse_install_date(self, date_str: Optional[str]) -> Optional[str]:
        """
        Parse install date from registry format (YYYYMMDD) to readable format.

        Args:
            date_str: Date string in YYYYMMDD format

        Returns:
            Formatted date string or None
        """
        if not date_str or len(date_str) != 8:
            return None

        try:
            year = int(date_str[:4])
            month = int(date_str[4:6])
            day = int(date_str[6:8])
            date = datetime(year, month, day)
            return date.strftime("%Y-%m-%d")
        except (ValueError, TypeError):
            return None

    def _is_update(self, program: InstalledProgram) -> bool:
        """
        Check if a program is a Windows update or patch.

        Args:
            program: InstalledProgram to check

        Returns:
            True if it's an update, False otherwise
        """
        update_keywords = [
            "Update for",
            "Hotfix for",
            "Security Update",
            "Service Pack",
            "KB", # Knowledge Base articles
        ]

        name_lower = program.name.lower()
        for keyword in update_keywords:
            if keyword.lower() in name_lower:
                return True

        # Check if it's a Windows Update (usually starts with "KB")
        if program.name.startswith("KB") and program.name[2:].replace("-", "").isdigit():
            return True

        return False

    def _remove_duplicates(self, programs: List[InstalledProgram]) -> List[InstalledProgram]:
        """
        Remove duplicate programs (same name and version in different registry locations).

        Args:
            programs: List of programs that may contain duplicates

        Returns:
            List with duplicates removed
        """
        seen = {}
        unique_programs = []

        for program in programs:
            # Create a unique key based on name and version
            key = (program.name.lower(), program.version)

            if key not in seen:
                seen[key] = program
                unique_programs.append(program)
            else:
                # If duplicate found, prefer the one with more information
                existing = seen[key]
                if self._has_more_info(program, existing):
                    # Replace the existing one
                    unique_programs.remove(existing)
                    unique_programs.append(program)
                    seen[key] = program

        return unique_programs

    def _has_more_info(self, prog1: InstalledProgram, prog2: InstalledProgram) -> bool:
        """
        Compare two programs and return True if prog1 has more information.

        Args:
            prog1: First program
            prog2: Second program

        Returns:
            True if prog1 has more information than prog2
        """
        count1 = sum([
            bool(prog1.version),
            bool(prog1.publisher),
            bool(prog1.install_location),
            bool(prog1.uninstall_string),
        ])

        count2 = sum([
            bool(prog2.version),
            bool(prog2.publisher),
            bool(prog2.install_location),
            bool(prog2.uninstall_string),
        ])

        return count1 > count2

    def search_programs(self, query: str) -> List[InstalledProgram]:
        """
        Search for programs by name, publisher, or version.

        Args:
            query: Search query

        Returns:
            List of matching programs
        """
        query_lower = query.lower()
        results = []

        for program in self.programs:
            if (query_lower in program.name.lower() or
                (program.publisher and query_lower in program.publisher.lower()) or
                (program.version and query_lower in program.version.lower())):
                results.append(program)

        return results

    def get_program_by_name(self, name: str) -> Optional[InstalledProgram]:
        """
        Get a specific program by exact name match.

        Args:
            name: Program name

        Returns:
            InstalledProgram or None if not found
        """
        for program in self.programs:
            if program.name.lower() == name.lower():
                return program
        return None


# Convenience function
def get_installed_programs(include_updates: bool = False) -> List[InstalledProgram]:
    """
    Get all installed programs from the registry.

    Args:
        include_updates: If False, filters out Windows updates and patches

    Returns:
        List of InstalledProgram objects
    """
    reader = RegistryReader()
    return reader.get_installed_programs(include_updates)

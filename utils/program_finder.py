"""
Utility for finding installed programs from file paths.

Given an executable file or shortcut path, attempts to find the corresponding
installed program in the registry.
"""

import os
import win32com.client
from pathlib import Path
from typing import Optional
from core.registry import get_installed_programs, InstalledProgram
from utils.logger import get_logger

logger = get_logger(__name__)


class ProgramFinder:
    """Find installed programs from file paths."""

    def __init__(self):
        """Initialize program finder."""
        self.programs = None

    def _load_programs(self):
        """Load installed programs if not already loaded."""
        if self.programs is None:
            self.programs = get_installed_programs()
            logger.info(f"Loaded {len(self.programs)} installed programs")

    def find_program_from_file(self, file_path: str) -> Optional[InstalledProgram]:
        """
        Find an installed program from a file path.

        Args:
            file_path: Path to executable or shortcut file

        Returns:
            InstalledProgram if found, None otherwise
        """
        self._load_programs()

        # Normalize path
        file_path = os.path.abspath(file_path)
        logger.info(f"Searching for program from file: {file_path}")

        # If it's a shortcut, resolve it
        if file_path.lower().endswith('.lnk'):
            file_path = self._resolve_shortcut(file_path)
            if not file_path:
                logger.warning("Failed to resolve shortcut")
                return None
            logger.info(f"Resolved shortcut to: {file_path}")

        # Get directory of the executable
        exe_dir = os.path.dirname(file_path)
        exe_name = os.path.basename(file_path)

        # Search strategies
        # 1. Direct match by install location
        program = self._find_by_install_location(exe_dir)
        if program:
            return program

        # 2. Match by executable name in display name
        program = self._find_by_exe_name(exe_name)
        if program:
            return program

        # 3. Match by directory name in display name
        dir_name = os.path.basename(exe_dir)
        program = self._find_by_directory_name(dir_name)
        if program:
            return program

        logger.warning(f"No installed program found for: {file_path}")
        return None

    def _resolve_shortcut(self, shortcut_path: str) -> Optional[str]:
        """
        Resolve a .lnk shortcut to its target path.

        Args:
            shortcut_path: Path to .lnk file

        Returns:
            Target path if successful, None otherwise
        """
        try:
            shell = win32com.client.Dispatch("WScript.Shell")
            shortcut = shell.CreateShortCut(shortcut_path)
            return shortcut.Targetpath
        except Exception as e:
            logger.error(f"Failed to resolve shortcut: {e}")
            return None

    def _find_by_install_location(self, directory: str) -> Optional[InstalledProgram]:
        """
        Find program by install location.

        Args:
            directory: Directory path to search

        Returns:
            InstalledProgram if found
        """
        directory = directory.lower()

        for program in self.programs:
            if program.install_location:
                install_loc = program.install_location.lower()

                # Check if directory is the install location or a subdirectory
                if directory == install_loc or directory.startswith(install_loc + os.sep):
                    logger.info(f"Found program by install location: {program.name}")
                    return program

        return None

    def _find_by_exe_name(self, exe_name: str) -> Optional[InstalledProgram]:
        """
        Find program by executable name.

        Args:
            exe_name: Executable file name

        Returns:
            InstalledProgram if found
        """
        # Remove .exe extension for comparison
        name_without_ext = exe_name.lower().replace('.exe', '')

        # Try exact match first
        for program in self.programs:
            program_name_lower = program.name.lower()

            # Check if exe name is in program name
            if name_without_ext in program_name_lower or program_name_lower in name_without_ext:
                logger.info(f"Found program by exe name: {program.name}")
                return program

        return None

    def _find_by_directory_name(self, dir_name: str) -> Optional[InstalledProgram]:
        """
        Find program by directory name.

        Args:
            dir_name: Directory name to search

        Returns:
            InstalledProgram if found
        """
        dir_name_lower = dir_name.lower()

        for program in self.programs:
            program_name_lower = program.name.lower()

            # Check if directory name matches program name
            if dir_name_lower in program_name_lower or program_name_lower in dir_name_lower:
                logger.info(f"Found program by directory name: {program.name}")
                return program

        return None


def find_program_from_file(file_path: str) -> Optional[InstalledProgram]:
    """
    Find an installed program from a file path (convenience function).

    Args:
        file_path: Path to executable or shortcut file

    Returns:
        InstalledProgram if found, None otherwise
    """
    finder = ProgramFinder()
    return finder.find_program_from_file(file_path)

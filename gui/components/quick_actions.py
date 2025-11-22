"""
Quick actions handler for program operations.
Handles folder opening, program execution, and website launching.
"""

import os
import subprocess
import webbrowser
from typing import Optional
from pathlib import Path

from core.registry import InstalledProgram
from utils.logger import get_logger


class QuickActionsHandler:
    """
    Handles quick actions for installed programs.

    Actions:
    - Open program folder in Windows Explorer
    - Run program executable
    - Open program website in browser
    """

    def __init__(self):
        """Initialize the quick actions handler."""
        self.logger = get_logger()

    def open_folder(self, program: InstalledProgram) -> bool:
        """
        Open program's installation folder in Windows Explorer.

        Args:
            program: InstalledProgram to open folder for

        Returns:
            True if successful, False otherwise
        """
        if not program.install_location:
            self.logger.warning(f"No install location for {program.name}")
            return False

        folder_path = program.install_location.strip('"')

        if not os.path.exists(folder_path):
            self.logger.warning(f"Install location not found: {folder_path}")
            return False

        try:
            # Open folder in Windows Explorer
            subprocess.Popen(['explorer', folder_path], shell=False)
            self.logger.info(f"Opened folder for {program.name}: {folder_path}")
            return True
        except (OSError, subprocess.SubprocessError) as e:
            self.logger.error(f"Failed to open folder: {e}")
            return False

    def run_program(self, program: InstalledProgram) -> bool:
        """
        Run the program's executable.

        Args:
            program: InstalledProgram to run

        Returns:
            True if successful, False otherwise
        """
        executable_path = self._find_executable(program)

        if not executable_path:
            self.logger.warning(f"No executable found for {program.name}")
            return False

        if not os.path.exists(executable_path):
            self.logger.warning(f"Executable not found: {executable_path}")
            return False

        try:
            # Run the executable
            subprocess.Popen([executable_path], shell=False)
            self.logger.info(f"Started program {program.name}: {executable_path}")
            return True
        except (OSError, subprocess.SubprocessError) as e:
            self.logger.error(f"Failed to run program: {e}")
            return False

    def open_website(self, program: InstalledProgram) -> bool:
        """
        Open program's website in default browser.

        Args:
            program: InstalledProgram to open website for

        Returns:
            True if successful, False otherwise
        """
        url = self._find_website(program)

        if not url:
            self.logger.warning(f"No website found for {program.name}")
            return False

        try:
            # Open URL in default browser
            webbrowser.open(url)
            self.logger.info(f"Opened website for {program.name}: {url}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to open website: {e}")
            return False

    def _find_executable(self, program: InstalledProgram) -> Optional[str]:
        """
        Find executable path for a program.

        Args:
            program: InstalledProgram to find executable for

        Returns:
            Executable path or None
        """
        # Try display_icon first (often points to main exe)
        if program.display_icon:
            icon_path = program.display_icon.strip('"').split(',')[0]
            if icon_path.lower().endswith('.exe') and os.path.exists(icon_path):
                return icon_path

        # Try install_location with common executable names
        if program.install_location:
            install_dir = program.install_location.strip('"')
            if os.path.isdir(install_dir):
                # Try program name variations
                base_name = program.name.split()[0]  # First word of program name
                common_names = [
                    f"{base_name}.exe",
                    f"{program.name}.exe",
                    "launcher.exe",
                    "start.exe",
                ]

                for exe_name in common_names:
                    exe_path = os.path.join(install_dir, exe_name)
                    if os.path.exists(exe_path):
                        return exe_path

                # Look for any .exe in install directory
                try:
                    for file in os.listdir(install_dir):
                        if file.lower().endswith('.exe') and not file.lower().startswith('unins'):
                            exe_path = os.path.join(install_dir, file)
                            if os.path.isfile(exe_path):
                                return exe_path
                except (PermissionError, OSError):
                    pass

        return None

    def _find_website(self, program: InstalledProgram) -> Optional[str]:
        """
        Find website URL for a program.

        Args:
            program: InstalledProgram to find website for

        Returns:
            Website URL or None
        """
        # Try to construct search URL from publisher name
        if program.publisher:
            # Clean up publisher name
            publisher_clean = program.publisher.strip()

            # Remove common suffixes
            suffixes = [" Inc.", " Corp.", " Corporation", " Ltd.", " Limited", " LLC", " Co."]
            for suffix in suffixes:
                if publisher_clean.endswith(suffix):
                    publisher_clean = publisher_clean[:-len(suffix)].strip()

            # Create Google search URL
            # Format: "program name" publisher official site
            search_query = f'"{program.name}" {publisher_clean} official site'
            search_url = f"https://www.google.com/search?q={search_query.replace(' ', '+')}"
            return search_url

        return None


# Global instance
_quick_actions_handler: Optional[QuickActionsHandler] = None


def get_quick_actions_handler() -> QuickActionsHandler:
    """Get global quick actions handler instance."""
    global _quick_actions_handler
    if _quick_actions_handler is None:
        _quick_actions_handler = QuickActionsHandler()
    return _quick_actions_handler

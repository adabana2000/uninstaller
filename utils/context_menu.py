"""
Windows Explorer context menu integration.

Adds "Uninstall with Windows Uninstaller" option to right-click menu for:
- Executable files (.exe)
- Shortcuts (.lnk)
- Application folders
"""

import os
import sys
import winreg
from pathlib import Path
from typing import Optional
from utils.logger import get_logger

logger = get_logger(__name__)


class ContextMenuIntegration:
    """Handles Windows Explorer context menu integration."""

    # Registry paths
    EXE_SHELL_KEY = r"exefile\shell"
    LNK_SHELL_KEY = r"lnkfile\shell"
    DIRECTORY_SHELL_KEY = r"Directory\shell"

    # Menu command name
    COMMAND_NAME = "UninstallWithWindowsUninstaller"

    def __init__(self):
        """Initialize context menu integration."""
        self.exe_path = self._get_exe_path()

    def _get_exe_path(self) -> str:
        """
        Get the path to the Windows Uninstaller executable.

        Returns:
            Path to the executable
        """
        # If running as frozen app (PyInstaller)
        if getattr(sys, 'frozen', False):
            return sys.executable

        # If running as script, use python with script path
        script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'main.py'))
        return f'"{sys.executable}" "{script_path}"'

    def install(self) -> bool:
        """
        Install context menu integration.

        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info("Installing context menu integration...")

            # Add for executable files
            self._add_context_menu(
                winreg.HKEY_CLASSES_ROOT,
                self.EXE_SHELL_KEY,
                "このプログラムをアンインストール",
                f'{self.exe_path} --uninstall-from-file "%1"'
            )

            # Add for shortcuts
            self._add_context_menu(
                winreg.HKEY_CLASSES_ROOT,
                self.LNK_SHELL_KEY,
                "このプログラムをアンインストール",
                f'{self.exe_path} --uninstall-from-file "%1"'
            )

            logger.info("Context menu integration installed successfully")
            return True

        except PermissionError:
            logger.error("Permission denied - Administrator privileges required")
            return False
        except Exception as e:
            logger.error(f"Failed to install context menu: {e}")
            return False

    def uninstall(self) -> bool:
        """
        Uninstall context menu integration.

        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info("Uninstalling context menu integration...")

            # Remove from executable files
            self._remove_context_menu(
                winreg.HKEY_CLASSES_ROOT,
                self.EXE_SHELL_KEY
            )

            # Remove from shortcuts
            self._remove_context_menu(
                winreg.HKEY_CLASSES_ROOT,
                self.LNK_SHELL_KEY
            )

            logger.info("Context menu integration uninstalled successfully")
            return True

        except PermissionError:
            logger.error("Permission denied - Administrator privileges required")
            return False
        except Exception as e:
            logger.error(f"Failed to uninstall context menu: {e}")
            return False

    def is_installed(self) -> bool:
        """
        Check if context menu integration is installed.

        Returns:
            True if installed, False otherwise
        """
        try:
            # Check if the command exists for exe files
            key_path = f"{self.EXE_SHELL_KEY}\\{self.COMMAND_NAME}"
            with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, key_path):
                return True
        except FileNotFoundError:
            return False
        except Exception as e:
            logger.error(f"Error checking installation status: {e}")
            return False

    def _add_context_menu(
        self,
        root_key: int,
        shell_key_path: str,
        menu_text: str,
        command: str
    ):
        """
        Add context menu entry.

        Args:
            root_key: Registry root key
            shell_key_path: Path to shell key
            menu_text: Text to display in menu
            command: Command to execute
        """
        # Create menu key
        menu_key_path = f"{shell_key_path}\\{self.COMMAND_NAME}"
        with winreg.CreateKey(root_key, menu_key_path) as menu_key:
            # Set menu text
            winreg.SetValue(menu_key, "", winreg.REG_SZ, menu_text)

            # Set icon (use the app's icon if available)
            winreg.SetValueEx(menu_key, "Icon", 0, winreg.REG_SZ, self.exe_path.split('"')[1] if '"' in self.exe_path else self.exe_path)

        # Create command key
        command_key_path = f"{menu_key_path}\\command"
        with winreg.CreateKey(root_key, command_key_path) as command_key:
            winreg.SetValue(command_key, "", winreg.REG_SZ, command)

        logger.info(f"Added context menu to {shell_key_path}")

    def _remove_context_menu(self, root_key: int, shell_key_path: str):
        """
        Remove context menu entry.

        Args:
            root_key: Registry root key
            shell_key_path: Path to shell key
        """
        try:
            menu_key_path = f"{shell_key_path}\\{self.COMMAND_NAME}"

            # Delete command subkey first
            command_key_path = f"{menu_key_path}\\command"
            try:
                winreg.DeleteKey(root_key, command_key_path)
            except FileNotFoundError:
                pass

            # Delete menu key
            try:
                winreg.DeleteKey(root_key, menu_key_path)
            except FileNotFoundError:
                pass

            logger.info(f"Removed context menu from {shell_key_path}")

        except FileNotFoundError:
            pass  # Already removed
        except Exception as e:
            logger.warning(f"Error removing context menu from {shell_key_path}: {e}")


def install_context_menu() -> bool:
    """
    Install context menu integration (convenience function).

    Returns:
        True if successful
    """
    integration = ContextMenuIntegration()
    return integration.install()


def uninstall_context_menu() -> bool:
    """
    Uninstall context menu integration (convenience function).

    Returns:
        True if successful
    """
    integration = ContextMenuIntegration()
    return integration.uninstall()


def is_context_menu_installed() -> bool:
    """
    Check if context menu is installed (convenience function).

    Returns:
        True if installed
    """
    integration = ContextMenuIntegration()
    return integration.is_installed()

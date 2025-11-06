"""
UWP (Universal Windows Platform) / Windows Store apps uninstaller.

Uses PowerShell commands to manage Windows Store apps.
"""

import subprocess
import json
from typing import List, Optional
from dataclasses import dataclass

from utils.logger import get_logger


@dataclass
class UWPApp:
    """Represents a UWP/Windows Store application."""
    name: str
    package_full_name: str
    package_family_name: str
    publisher: str
    version: str
    install_location: str
    is_framework: bool = False
    is_bundle: bool = False
    is_resource_package: bool = False

    @staticmethod
    def from_powershell_object(obj: dict) -> 'UWPApp':
        """Create from PowerShell object dictionary."""
        return UWPApp(
            name=obj.get('Name', ''),
            package_full_name=obj.get('PackageFullName', ''),
            package_family_name=obj.get('PackageFamilyName', ''),
            publisher=obj.get('Publisher', ''),
            version=obj.get('Version', ''),
            install_location=obj.get('InstallLocation', ''),
            is_framework=obj.get('IsFramework', False),
            is_bundle=obj.get('IsBundle', False),
            is_resource_package=obj.get('IsResourcePackage', False)
        )


class UWPUninstaller:
    """
    Handles uninstallation of UWP/Windows Store apps.

    Uses PowerShell Get-AppxPackage and Remove-AppxPackage cmdlets.
    """

    def __init__(self):
        self.logger = get_logger()

    def get_installed_apps(self, include_frameworks: bool = False) -> List[UWPApp]:
        """
        Get list of installed UWP apps.

        Args:
            include_frameworks: Include framework packages

        Returns:
            List of UWPApp objects
        """
        try:
            # PowerShell command to get all installed apps
            ps_command = "Get-AppxPackage | Select-Object Name, PackageFullName, PackageFamilyName, Publisher, Version, InstallLocation, IsFramework, IsBundle, IsResourcePackage | ConvertTo-Json"

            result = subprocess.run(
                ['powershell', '-Command', ps_command],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                self.logger.error(f"PowerShell error: {result.stderr}")
                return []

            # Parse JSON output
            try:
                data = json.loads(result.stdout)
            except json.JSONDecodeError:
                self.logger.error("Failed to parse PowerShell JSON output")
                return []

            # Handle single app (not in array)
            if isinstance(data, dict):
                data = [data]

            # Convert to UWPApp objects
            apps = []
            for obj in data:
                try:
                    app = UWPApp.from_powershell_object(obj)

                    # Filter out frameworks unless requested
                    if not include_frameworks and (
                        app.is_framework or
                        app.is_resource_package
                    ):
                        continue

                    apps.append(app)

                except Exception as e:
                    self.logger.warning(f"Error parsing app object: {e}")

            self.logger.info(f"Found {len(apps)} UWP apps")
            return apps

        except subprocess.TimeoutExpired:
            self.logger.error("PowerShell command timed out")
            return []
        except Exception as e:
            self.logger.error(f"Error getting UWP apps: {e}")
            return []

    def uninstall_app(self, package_full_name: str) -> bool:
        """
        Uninstall a UWP app by package full name.

        Args:
            package_full_name: Full package name (e.g., "Microsoft.WindowsCalculator_...")

        Returns:
            True if successful
        """
        try:
            self.logger.info(f"Uninstalling UWP app: {package_full_name}")

            # PowerShell command to remove app
            ps_command = f"Remove-AppxPackage -Package '{package_full_name}'"

            result = subprocess.run(
                ['powershell', '-Command', ps_command],
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode == 0:
                self.logger.info(f"Successfully uninstalled UWP app: {package_full_name}")
                return True
            else:
                self.logger.error(f"Failed to uninstall UWP app: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            self.logger.error("PowerShell command timed out")
            return False
        except Exception as e:
            self.logger.error(f"Error uninstalling UWP app: {e}")
            return False

    def uninstall_app_for_all_users(self, package_name: str) -> bool:
        """
        Uninstall a UWP app for all users.

        Requires administrator privileges.

        Args:
            package_name: Package name or package family name

        Returns:
            True if successful
        """
        try:
            self.logger.info(f"Uninstalling UWP app for all users: {package_name}")

            # PowerShell command to remove app for all users
            ps_command = f"Get-AppxPackage -AllUsers '{package_name}' | Remove-AppxPackage -AllUsers"

            result = subprocess.run(
                ['powershell', '-Command', ps_command],
                capture_output=True,
                text=True,
                timeout=120
            )

            if result.returncode == 0:
                self.logger.info(f"Successfully uninstalled UWP app for all users: {package_name}")
                return True
            else:
                self.logger.error(f"Failed to uninstall UWP app for all users: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            self.logger.error("PowerShell command timed out")
            return False
        except Exception as e:
            self.logger.error(f"Error uninstalling UWP app for all users: {e}")
            return False

    def find_app_by_name(self, name: str) -> Optional[UWPApp]:
        """
        Find a UWP app by name (partial match).

        Args:
            name: App name to search for

        Returns:
            UWPApp if found, None otherwise
        """
        apps = self.get_installed_apps()
        name_lower = name.lower()

        for app in apps:
            if name_lower in app.name.lower():
                return app

        return None

    def is_uwp_app_installed(self, package_name: str) -> bool:
        """
        Check if a UWP app is installed.

        Args:
            package_name: Package name or package family name

        Returns:
            True if installed
        """
        try:
            ps_command = f"Get-AppxPackage '{package_name}'"

            result = subprocess.run(
                ['powershell', '-Command', ps_command],
                capture_output=True,
                text=True,
                timeout=10
            )

            # If output contains package info, it's installed
            return result.returncode == 0 and len(result.stdout.strip()) > 0

        except Exception as e:
            self.logger.warning(f"Error checking UWP app installation: {e}")
            return False

    def print_app_info(self, app: UWPApp):
        """
        Print detailed information about a UWP app.

        Args:
            app: UWPApp object
        """
        print("\n" + "=" * 70)
        print("UWP App Information")
        print("=" * 70)
        print(f"Name:                {app.name}")
        print(f"Package Full Name:   {app.package_full_name}")
        print(f"Package Family Name: {app.package_family_name}")
        print(f"Publisher:           {app.publisher}")
        print(f"Version:             {app.version}")
        print(f"Install Location:    {app.install_location}")
        print(f"Is Framework:        {app.is_framework}")
        print(f"Is Bundle:           {app.is_bundle}")
        print(f"Is Resource Package: {app.is_resource_package}")
        print("=" * 70)

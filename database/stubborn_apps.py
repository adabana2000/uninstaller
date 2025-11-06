"""
Stubborn applications database and handler.

Provides special handling for applications that are difficult to uninstall completely.
"""

import json
import os
from typing import Dict, List, Optional
from dataclasses import dataclass

from core.registry import InstalledProgram
from utils.logger import get_logger


@dataclass
class StubbornAppInfo:
    """Information about a stubborn application."""
    name: str
    publisher: str
    patterns: List[str]
    processes_to_kill: List[str]
    services_to_stop: List[str]
    additional_paths: List[str]
    registry_keys: List[str]
    notes: str = ""

    @staticmethod
    def from_dict(data: Dict) -> 'StubbornAppInfo':
        """Create from dictionary."""
        return StubbornAppInfo(
            name=data.get('name', ''),
            publisher=data.get('publisher', ''),
            patterns=data.get('patterns', []),
            processes_to_kill=data.get('processes_to_kill', []),
            services_to_stop=data.get('services_to_stop', []),
            additional_paths=data.get('additional_paths', []),
            registry_keys=data.get('registry_keys', []),
            notes=data.get('notes', '')
        )


class StubbornAppsDatabase:
    """
    Database of stubborn applications with special uninstall requirements.

    Loads application information from JSON database and provides
    methods to check if an application requires special handling.
    """

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize the database.

        Args:
            db_path: Path to the JSON database file
        """
        self.logger = get_logger()
        self.apps: List[StubbornAppInfo] = []

        # Default database path
        if db_path is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            db_path = os.path.join(current_dir, 'stubborn_apps.json')

        self.db_path = db_path
        self.load()

    def load(self) -> bool:
        """
        Load database from JSON file.

        Returns:
            True if successful
        """
        try:
            if not os.path.exists(self.db_path):
                self.logger.warning(f"Stubborn apps database not found: {self.db_path}")
                return False

            with open(self.db_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            self.apps = []
            for app_data in data.get('apps', []):
                try:
                    app = StubbornAppInfo.from_dict(app_data)
                    self.apps.append(app)
                except Exception as e:
                    self.logger.warning(f"Error loading app data: {e}")

            self.logger.info(f"Loaded {len(self.apps)} stubborn apps from database")
            return True

        except Exception as e:
            self.logger.error(f"Error loading stubborn apps database: {e}")
            return False

    def is_stubborn(self, program: InstalledProgram) -> bool:
        """
        Check if a program is known to be stubborn.

        Args:
            program: InstalledProgram object

        Returns:
            True if program is in the database
        """
        return self.get_app_info(program) is not None

    def get_app_info(self, program: InstalledProgram) -> Optional[StubbornAppInfo]:
        """
        Get stubborn app information for a program.

        Args:
            program: InstalledProgram object

        Returns:
            StubbornAppInfo if found, None otherwise
        """
        program_name_lower = program.name.lower()
        publisher_lower = (program.publisher or '').lower()

        for app in self.apps:
            # Check patterns against program name
            for pattern in app.patterns:
                if pattern.lower() in program_name_lower:
                    # Also check publisher if available
                    if app.publisher and publisher_lower:
                        if app.publisher.lower() in publisher_lower:
                            return app
                    else:
                        # No publisher check needed
                        return app

        return None

    def get_processes_to_kill(self, program: InstalledProgram) -> List[str]:
        """
        Get list of processes that should be killed before uninstalling.

        Args:
            program: InstalledProgram object

        Returns:
            List of process names
        """
        app_info = self.get_app_info(program)
        if app_info:
            return app_info.processes_to_kill
        return []

    def get_services_to_stop(self, program: InstalledProgram) -> List[str]:
        """
        Get list of services that should be stopped before uninstalling.

        Args:
            program: InstalledProgram object

        Returns:
            List of service names
        """
        app_info = self.get_app_info(program)
        if app_info:
            return app_info.services_to_stop
        return []

    def get_additional_paths(self, program: InstalledProgram) -> List[str]:
        """
        Get list of additional paths to scan for leftovers.

        Args:
            program: InstalledProgram object

        Returns:
            List of paths (may contain environment variables)
        """
        app_info = self.get_app_info(program)
        if app_info:
            # Expand environment variables
            expanded_paths = []
            for path in app_info.additional_paths:
                expanded = os.path.expandvars(path)
                if expanded != path:  # Variable was expanded
                    expanded_paths.append(expanded)
                else:
                    expanded_paths.append(path)
            return expanded_paths
        return []

    def get_additional_registry_keys(self, program: InstalledProgram) -> List[str]:
        """
        Get list of additional registry keys to check.

        Args:
            program: InstalledProgram object

        Returns:
            List of registry key paths
        """
        app_info = self.get_app_info(program)
        if app_info:
            return app_info.registry_keys
        return []

    def get_notes(self, program: InstalledProgram) -> str:
        """
        Get notes about uninstalling this program.

        Args:
            program: InstalledProgram object

        Returns:
            Notes string
        """
        app_info = self.get_app_info(program)
        if app_info:
            return app_info.notes
        return ""

    def list_all_apps(self) -> List[StubbornAppInfo]:
        """
        Get list of all stubborn apps in database.

        Returns:
            List of StubbornAppInfo objects
        """
        return self.apps.copy()


# Global instance
_database = None


def get_stubborn_apps_database() -> StubbornAppsDatabase:
    """Get global stubborn apps database instance."""
    global _database
    if _database is None:
        _database = StubbornAppsDatabase()
    return _database

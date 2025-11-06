"""
Configuration management for the uninstaller.

Provides centralized configuration management with JSON persistence.
"""

import os
import json
import copy
from typing import Dict, Any, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class Config:
    """Configuration manager for the uninstaller."""

    # Default configuration
    DEFAULT_CONFIG = {
        "backup": {
            "enabled": True,
            "keep_days": 30,
            "create_restore_point": True,
            "backup_registry": True,
            "backup_files": True,
        },
        "scan": {
            "scan_files": True,
            "scan_registry": True,
            "scan_shortcuts": True,
            "max_depth": 5,
            "auto_scan_after_uninstall": True,
        },
        "uninstall": {
            "confirm_before_delete": True,
            "force_delete_if_locked": False,
            "terminate_processes": True,
            "stop_services": True,
        },
        "ui": {
            "show_system_programs": False,
            "show_updates": False,
            "show_icons": True,
            "refresh_on_startup": True,
            "theme": "system",  # system, light, dark
        },
        "monitor": {
            "traces_dir": "traces",
            "auto_save_trace": True,
            "default_paths": [
                "%PROGRAMFILES%",
                "%PROGRAMFILES(X86)%",
                "%APPDATA%",
                "%LOCALAPPDATA%",
                "%PROGRAMDATA%",
            ],
        },
        "export": {
            "default_format": "csv",  # csv, json, html
            "include_system_info": True,
        },
        "logging": {
            "level": "INFO",  # DEBUG, INFO, WARNING, ERROR
            "keep_days": 30,
            "max_file_size_mb": 10,
        },
    }

    def __init__(self, config_file: Optional[str] = None):
        """Initialize configuration manager.

        Args:
            config_file: Path to configuration file. If None, uses default location.
        """
        if config_file is None:
            # Default location in user's AppData
            app_data = os.environ.get('LOCALAPPDATA', '')
            if app_data:
                config_dir = os.path.join(app_data, 'WindowsUninstaller')
                os.makedirs(config_dir, exist_ok=True)
                config_file = os.path.join(config_dir, 'config.json')
            else:
                # Fallback to current directory
                config_file = 'config.json'

        self.config_file = config_file
        self.config = copy.deepcopy(self.DEFAULT_CONFIG)
        self.load()

    def load(self) -> bool:
        """Load configuration from file.

        Returns:
            True if loaded successfully, False otherwise.
        """
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    user_config = json.load(f)

                # Merge with default config (deep merge)
                self._deep_merge(self.config, user_config)

                logger.info(f"Configuration loaded from {self.config_file}")
                return True
            else:
                logger.info("No configuration file found, using defaults")
                return False
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            return False

    def save(self) -> bool:
        """Save configuration to file.

        Returns:
            True if saved successfully, False otherwise.
        """
        try:
            # Create directory if it doesn't exist
            config_dir = os.path.dirname(self.config_file)
            if config_dir:
                os.makedirs(config_dir, exist_ok=True)

            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2)

            logger.info(f"Configuration saved to {self.config_file}")
            return True
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
            return False

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by dot-separated key.

        Args:
            key: Dot-separated key (e.g., "backup.enabled")
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        try:
            value = self.config
            for part in key.split('.'):
                value = value[part]
            return value
        except (KeyError, TypeError):
            return default

    def set(self, key: str, value: Any) -> bool:
        """Set configuration value by dot-separated key.

        Args:
            key: Dot-separated key (e.g., "backup.enabled")
            value: Value to set

        Returns:
            True if set successfully, False otherwise
        """
        try:
            parts = key.split('.')
            config = self.config

            # Navigate to the parent dictionary
            for part in parts[:-1]:
                if part not in config:
                    config[part] = {}
                config = config[part]

            # Set the value
            config[parts[-1]] = value
            return True
        except Exception as e:
            logger.error(f"Failed to set configuration key '{key}': {e}")
            return False

    def reset_to_defaults(self) -> bool:
        """Reset configuration to default values.

        Returns:
            True if reset successfully
        """
        self.config = copy.deepcopy(self.DEFAULT_CONFIG)
        return self.save()

    def get_section(self, section: str) -> Dict[str, Any]:
        """Get entire configuration section.

        Args:
            section: Section name (e.g., "backup")

        Returns:
            Configuration section dictionary
        """
        return self.config.get(section, {})

    def _deep_merge(self, base: Dict, update: Dict) -> None:
        """Deep merge update dictionary into base dictionary.

        Args:
            base: Base dictionary to merge into
            update: Dictionary with updates
        """
        for key, value in update.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value

    def expand_paths(self, paths: list) -> list:
        """Expand environment variables in paths.

        Args:
            paths: List of paths with environment variables

        Returns:
            List of expanded paths
        """
        expanded = []
        for path in paths:
            expanded_path = os.path.expandvars(path)
            if os.path.exists(expanded_path):
                expanded.append(expanded_path)
        return expanded

    def __repr__(self) -> str:
        return f"Config(file='{self.config_file}')"


# Global configuration instance
_config_instance: Optional[Config] = None


def get_config() -> Config:
    """Get global configuration instance.

    Returns:
        Global Config instance
    """
    global _config_instance
    if _config_instance is None:
        _config_instance = Config()
    return _config_instance


def reload_config() -> Config:
    """Reload configuration from file.

    Returns:
        Reloaded Config instance
    """
    global _config_instance
    _config_instance = Config()
    return _config_instance

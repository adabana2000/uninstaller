"""
Icon extraction utilities for Windows applications.
Extracts icons from executables and icon files.
"""

import os
import tempfile
from functools import lru_cache
from typing import Optional
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtCore import QSize
from PyQt6.QtWidgets import QFileIconProvider
from PyQt6.QtCore import QFileInfo

try:
    import win32gui
    import win32api
    import win32con
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False


class IconExtractor:
    """
    Extracts and converts Windows application icons.

    Supports:
    - .ico files
    - .exe files with embedded icons
    - Icon paths with index (e.g., "app.exe,0")

    Features:
    - LRU cache with configurable size (default: 512 icons)
    - Automatic memory management
    """

    def __init__(self, cache_size: int = 512):
        """
        Initialize the icon extractor.

        Args:
            cache_size: Maximum number of icons to cache (default: 512)
        """
        self.cache = {}  # Cache extracted icons
        self.cache_size = cache_size
        self.cache_order = []  # Track access order for LRU
        self.default_size = QSize(32, 32)
        self.icon_provider = QFileIconProvider()

    def get_icon(self, icon_path: Optional[str], default: Optional[QIcon] = None) -> QIcon:
        """
        Get QIcon from icon path with LRU caching.

        Args:
            icon_path: Path to icon file or executable
            default: Default icon if extraction fails

        Returns:
            QIcon object
        """
        if not icon_path:
            return default or QIcon()

        # Check cache (LRU)
        if icon_path in self.cache:
            # Move to end (most recently used)
            self.cache_order.remove(icon_path)
            self.cache_order.append(icon_path)
            return self.cache[icon_path]

        # Parse icon path (may include index like "app.exe,0")
        file_path, icon_index = self._parse_icon_path(icon_path)

        if not file_path or not os.path.exists(file_path):
            return default or QIcon()

        try:
            # Try different extraction methods
            icon = self._extract_icon(file_path, icon_index)

            if not icon.isNull():
                # Add to cache with LRU eviction
                self._add_to_cache(icon_path, icon)
                return icon

        except Exception as e:
            # Silent fail, return default
            pass

        return default or QIcon()

    def _add_to_cache(self, icon_path: str, icon: QIcon) -> None:
        """
        Add icon to cache with LRU eviction.

        Args:
            icon_path: Icon path (cache key)
            icon: QIcon object
        """
        # Evict least recently used if cache is full
        if len(self.cache) >= self.cache_size:
            if self.cache_order:
                lru_key = self.cache_order.pop(0)
                del self.cache[lru_key]

        # Add new icon
        self.cache[icon_path] = icon
        self.cache_order.append(icon_path)

    def _parse_icon_path(self, icon_path: str) -> tuple[str, int]:
        """
        Parse icon path that may include index.

        Args:
            icon_path: Icon path (e.g., "C:\\app.exe" or "C:\\app.exe,0")

        Returns:
            Tuple of (file_path, icon_index)
        """
        # Remove quotes if present
        icon_path = icon_path.strip('"\'')

        # Check if path includes icon index
        if ',' in icon_path:
            parts = icon_path.rsplit(',', 1)
            file_path = parts[0].strip()
            try:
                icon_index = int(parts[1].strip())
            except ValueError:
                icon_index = 0
        else:
            file_path = icon_path
            icon_index = 0

        return file_path, icon_index

    def _extract_icon(self, file_path: str, icon_index: int = 0) -> QIcon:
        """
        Extract icon from file.

        Args:
            file_path: Path to file
            icon_index: Icon index (for exe files)

        Returns:
            QIcon object
        """
        # Use QFileIconProvider for system icons
        # This is the most reliable method on Windows
        file_info = QFileInfo(file_path)
        icon = self.icon_provider.icon(file_info)

        if not icon.isNull():
            return icon

        # Fallback: try to load directly
        file_ext = os.path.splitext(file_path)[1].lower()

        # For .ico files, directly load
        if file_ext == '.ico':
            try:
                return QIcon(file_path)
            except:
                pass

        return QIcon()

    def clear_cache(self):
        """Clear the icon cache."""
        self.cache.clear()
        self.cache_order.clear()

    def get_cache_stats(self) -> dict:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache stats (size, capacity, hit_rate)
        """
        return {
            'size': len(self.cache),
            'capacity': self.cache_size,
            'usage_percent': (len(self.cache) / self.cache_size * 100) if self.cache_size > 0 else 0
        }


# Global instance
_icon_extractor = None


def get_icon_extractor() -> IconExtractor:
    """Get global icon extractor instance."""
    global _icon_extractor
    if _icon_extractor is None:
        _icon_extractor = IconExtractor()
    return _icon_extractor


def get_program_icon(program) -> QIcon:
    """
    Get icon for an installed program.

    Args:
        program: InstalledProgram object

    Returns:
        QIcon object
    """
    extractor = get_icon_extractor()

    # Try display_icon first
    if program.display_icon:
        icon = extractor.get_icon(program.display_icon)
        if not icon.isNull():
            return icon

    # Try uninstall_string
    if program.uninstall_string:
        # Extract exe path from uninstall string
        uninstall_exe = program.uninstall_string.strip('"').split()[0]
        icon = extractor.get_icon(uninstall_exe)
        if not icon.isNull():
            return icon

    # Try install_location
    if program.install_location and os.path.exists(program.install_location):
        # Look for common executable names
        for exe_name in [f"{program.name}.exe", "uninstall.exe", "uninst.exe"]:
            exe_path = os.path.join(program.install_location, exe_name)
            if os.path.exists(exe_path):
                icon = extractor.get_icon(exe_path)
                if not icon.isNull():
                    return icon

    # Return default icon
    return QIcon()

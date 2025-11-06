"""
System information utilities for Windows.
Provides functions to detect Windows version, architecture, and other system details.
"""

import platform
import os
import sys
from typing import Dict, Tuple


def get_windows_version() -> str:
    """
    Get Windows version string.

    Returns:
        Windows version (e.g., "Windows 10", "Windows 11")
    """
    version_info = sys.getwindowsversion()

    # Windows 11 has the same version number as Windows 10 (10.0)
    # but build number >= 22000
    if version_info.major == 10 and version_info.minor == 0:
        if version_info.build >= 22000:
            return "Windows 11"
        else:
            return "Windows 10"
    elif version_info.major == 6:
        if version_info.minor == 3:
            return "Windows 8.1"
        elif version_info.minor == 2:
            return "Windows 8"
        elif version_info.minor == 1:
            return "Windows 7"
        elif version_info.minor == 0:
            return "Windows Vista"
    elif version_info.major == 5:
        if version_info.minor == 1:
            return "Windows XP"
        elif version_info.minor == 0:
            return "Windows 2000"

    return f"Windows {version_info.major}.{version_info.minor}"


def get_windows_build() -> int:
    """
    Get Windows build number.

    Returns:
        Build number (e.g., 19045 for Windows 10, 22621 for Windows 11)
    """
    return sys.getwindowsversion().build


def get_architecture() -> str:
    """
    Get system architecture.

    Returns:
        Architecture string ("x64" or "x86")
    """
    machine = platform.machine().lower()
    if "64" in machine or "amd64" in machine:
        return "x64"
    else:
        return "x86"


def is_64bit() -> bool:
    """
    Check if the system is 64-bit.

    Returns:
        True if 64-bit, False if 32-bit
    """
    return get_architecture() == "x64"


def get_python_architecture() -> str:
    """
    Get the architecture of the Python interpreter.

    Returns:
        "64-bit" or "32-bit"
    """
    return "64-bit" if sys.maxsize > 2**32 else "32-bit"


def get_program_files_paths() -> Tuple[str, ...]:
    """
    Get all Program Files directories.

    Returns:
        Tuple of Program Files paths
    """
    paths = []

    # Standard Program Files
    if "ProgramFiles" in os.environ:
        paths.append(os.environ["ProgramFiles"])

    # Program Files (x86) on 64-bit systems
    if "ProgramFiles(x86)" in os.environ:
        paths.append(os.environ["ProgramFiles(x86)"])

    # Alternative Program Files path
    if "ProgramW6432" in os.environ:
        paths.append(os.environ["ProgramW6432"])

    return tuple(set(paths))  # Remove duplicates


def get_appdata_paths() -> Dict[str, str]:
    """
    Get all AppData directories.

    Returns:
        Dictionary with AppData paths
    """
    return {
        "local": os.environ.get("LOCALAPPDATA", ""),
        "roaming": os.environ.get("APPDATA", ""),
        "program_data": os.environ.get("ProgramData", ""),
    }


def get_user_directories() -> Dict[str, str]:
    """
    Get common user directories.

    Returns:
        Dictionary with user directory paths
    """
    return {
        "desktop": os.path.join(os.environ.get("USERPROFILE", ""), "Desktop"),
        "documents": os.path.join(os.environ.get("USERPROFILE", ""), "Documents"),
        "downloads": os.path.join(os.environ.get("USERPROFILE", ""), "Downloads"),
        "start_menu": os.path.join(os.environ.get("APPDATA", ""), "Microsoft", "Windows", "Start Menu"),
        "programs": os.path.join(os.environ.get("APPDATA", ""), "Microsoft", "Windows", "Start Menu", "Programs"),
    }


def get_system_info() -> Dict[str, any]:
    """
    Get comprehensive system information.

    Returns:
        Dictionary with all system information
    """
    return {
        "os": get_windows_version(),
        "build": get_windows_build(),
        "architecture": get_architecture(),
        "is_64bit": is_64bit(),
        "python_version": platform.python_version(),
        "python_architecture": get_python_architecture(),
        "computer_name": platform.node(),
        "processor": platform.processor(),
        "program_files": get_program_files_paths(),
        "appdata": get_appdata_paths(),
        "user_directories": get_user_directories(),
    }


def print_system_info() -> None:
    """
    Print system information in a formatted way.
    """
    info = get_system_info()

    print("=" * 60)
    print("System Information")
    print("=" * 60)
    print(f"Operating System:    {info['os']} (Build {info['build']})")
    print(f"Architecture:        {info['architecture']}")
    print(f"Computer Name:       {info['computer_name']}")
    print(f"Processor:           {info['processor']}")
    print(f"\nPython Version:      {info['python_version']} ({info['python_architecture']})")
    print(f"\nProgram Files:")
    for path in info['program_files']:
        print(f"  - {path}")
    print(f"\nAppData:")
    print(f"  Local:       {info['appdata']['local']}")
    print(f"  Roaming:     {info['appdata']['roaming']}")
    print(f"  ProgramData: {info['appdata']['program_data']}")
    print("=" * 60)


if __name__ == "__main__":
    # Test the module
    print_system_info()

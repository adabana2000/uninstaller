"""
Permission management utilities for Windows.
Provides functions to check and request administrator privileges.
"""

import ctypes
import sys
import os


def is_admin() -> bool:
    """
    Check if the current process has administrator privileges.

    Returns:
        True if running as administrator, False otherwise
    """
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def request_admin_privileges() -> bool:
    """
    Request administrator privileges by restarting the script with UAC elevation.

    This will show a UAC prompt and restart the script if accepted.
    If already running as admin, returns True without restarting.

    Returns:
        True if already admin or if restart was successful, False if user declined
    """
    if is_admin():
        return True

    try:
        # Get the current script path
        script = os.path.abspath(sys.argv[0])

        # Get the current working directory
        cwd = os.getcwd()

        # Parameters to pass to the elevated process
        params = " ".join([f'"{arg}"' for arg in sys.argv[1:]])

        # Request elevation using ShellExecute with "runas" verb
        ret = ctypes.windll.shell32.ShellExecuteW(
            None,           # hwnd
            "runas",        # operation (runas = run as administrator)
            sys.executable, # file (python.exe)
            f'"{script}" {params}',  # parameters
            cwd,            # directory (current working directory)
            1               # show command (SW_SHOWNORMAL)
        )

        # If ShellExecute succeeds (ret > 32), exit the current process
        if ret > 32:
            sys.exit(0)
        else:
            return False

    except Exception as e:
        print(f"Failed to request admin privileges: {e}")
        return False


def ensure_admin() -> None:
    """
    Ensure the script is running with administrator privileges.
    If not, request elevation and exit.

    Raises:
        SystemExit: If not running as admin and elevation was successful
        PermissionError: If user declined the UAC prompt
    """
    if not is_admin():
        print("Administrator privileges required.")
        print("Requesting elevation...")

        if not request_admin_privileges():
            raise PermissionError(
                "Administrator privileges are required to run this application.\n"
                "Please run as administrator or accept the UAC prompt."
            )


def check_write_permission(path: str) -> bool:
    """
    Check if the current process has write permission to a specific path.

    Args:
        path: Path to check (file or directory)

    Returns:
        True if writable, False otherwise
    """
    try:
        # If it's a directory
        if os.path.isdir(path):
            test_file = os.path.join(path, ".permission_test")
            try:
                with open(test_file, "w") as f:
                    f.write("test")
                os.remove(test_file)
                return True
            except (IOError, OSError):
                return False

        # If it's a file
        elif os.path.isfile(path):
            return os.access(path, os.W_OK)

        # If path doesn't exist, check parent directory
        else:
            parent = os.path.dirname(path)
            if os.path.exists(parent):
                return check_write_permission(parent)
            else:
                return False

    except Exception:
        return False


def can_access_registry() -> bool:
    """
    Check if the current process can access protected registry keys.

    Returns:
        True if registry access is available, False otherwise
    """
    try:
        import winreg

        # Try to open a protected registry key
        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
            0,
            winreg.KEY_READ
        )
        winreg.CloseKey(key)
        return True

    except Exception:
        return False


def get_privilege_info() -> dict:
    """
    Get information about current privileges and access levels.

    Returns:
        Dictionary with privilege information
    """
    return {
        "is_admin": is_admin(),
        "can_access_registry": can_access_registry(),
        "program_files_writable": check_write_permission(os.environ.get("ProgramFiles", "C:\\Program Files")),
        "system32_writable": check_write_permission(os.path.join(os.environ.get("SystemRoot", "C:\\Windows"), "System32")),
    }


def print_privilege_info() -> None:
    """
    Print current privilege information.
    """
    info = get_privilege_info()

    print("=" * 60)
    print("Privilege Information")
    print("=" * 60)
    print(f"Running as Administrator:  {info['is_admin']}")
    print(f"Registry Access:           {info['can_access_registry']}")
    print(f"Program Files Writable:    {info['program_files_writable']}")
    print(f"System32 Writable:         {info['system32_writable']}")
    print("=" * 60)

    if not info['is_admin']:
        print("\n[WARNING] Not running with administrator privileges.")
        print("Some operations may fail or require elevation.")


if __name__ == "__main__":
    # Test the module
    print_privilege_info()

    if len(sys.argv) > 1 and sys.argv[1] == "--request-admin":
        if not is_admin():
            print("\nRequesting administrator privileges...")
            request_admin_privileges()
        else:
            print("\nAlready running as administrator.")

"""
Basic test script to verify core functionality.
Tests registry reading, system info, permissions, and logging.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.registry import RegistryReader, get_installed_programs
from utils.system_info import get_system_info, print_system_info
from utils.permissions import is_admin, get_privilege_info, print_privilege_info
from utils.logger import get_logger
from utils.backup import BackupManager


def test_system_info():
    """Test system information retrieval."""
    print("\n" + "=" * 70)
    print("TEST 1: System Information")
    print("=" * 70)

    try:
        print_system_info()
        print("[PASS] System information test passed")
        return True
    except Exception as e:
        print(f"[FAIL] System information test failed: {e}")
        return False


def test_privileges():
    """Test privilege detection."""
    print("\n" + "=" * 70)
    print("TEST 2: Privilege Information")
    print("=" * 70)

    try:
        print_privilege_info()
        print("[PASS] Privilege test passed")
        return True
    except Exception as e:
        print(f"[FAIL] Privilege test failed: {e}")
        return False


def test_registry_reading():
    """Test registry reading."""
    print("\n" + "=" * 70)
    print("TEST 3: Registry Reading")
    print("=" * 70)

    try:
        print("Scanning registry for installed programs...")
        programs = get_installed_programs(include_updates=False)

        print(f"Found {len(programs)} installed programs")

        if programs:
            print("\nFirst 5 programs:")
            for i, prog in enumerate(programs[:5], 1):
                print(f"{i}. {prog.name}")
                print(f"   Version: {prog.version or 'Unknown'}")
                print(f"   Publisher: {prog.publisher or 'Unknown'}")
                print(f"   Architecture: {prog.architecture}")
                print()

        print("[PASS] Registry reading test passed")
        return True
    except Exception as e:
        print(f"[FAIL] Registry reading test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_logger():
    """Test logging functionality."""
    print("\n" + "=" * 70)
    print("TEST 4: Logging")
    print("=" * 70)

    try:
        logger = get_logger("test")

        logger.info("Testing info message")
        logger.warning("Testing warning message")
        logger.error("Testing error message")

        logger.log_operation_start("Test Operation", "Test Target")
        logger.log_operation_end("Test Operation", True, "Test completed successfully")

        log_file = logger.get_log_file_path()
        print(f"\nLog file created at: {log_file}")

        if log_file.exists():
            print(f"Log file size: {log_file.stat().st_size} bytes")
            print("[PASS] Logging test passed")
            return True
        else:
            print("[FAIL] Log file not created")
            return False

    except Exception as e:
        print(f"[FAIL] Logging test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_backup_manager():
    """Test backup manager."""
    print("\n" + "=" * 70)
    print("TEST 5: Backup Manager")
    print("=" * 70)

    try:
        manager = BackupManager()
        print(f"Backup directory: {manager.backup_dir}")

        # List existing backups
        backups = manager.list_backups()
        print(f"Existing backups: {len(backups)}")

        if backups:
            print("\nRecent backups:")
            for backup in backups[:3]:
                print(f"  - {backup['type']} backup at {backup['timestamp']}")

        print("[PASS] Backup manager test passed")
        return True

    except Exception as e:
        print(f"[FAIL] Backup manager test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("WINDOWS UNINSTALLER - BASIC FUNCTIONALITY TEST")
    print("=" * 70)

    results = {
        "System Info": test_system_info(),
        "Privileges": test_privileges(),
        "Registry Reading": test_registry_reading(),
        "Logging": test_logger(),
        "Backup Manager": test_backup_manager(),
    }

    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    passed = sum(results.values())
    total = len(results)

    for test_name, result in results.items():
        status = "[PASS]" if result else "[FAIL]"
        print(f"{test_name:20} : {status}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n*** All tests passed! ***")
        return 0
    else:
        print(f"\n*** {total - passed} test(s) failed ***")
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())

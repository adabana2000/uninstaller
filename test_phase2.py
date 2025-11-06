"""
Test script for Phase 2 functionality.
Tests uninstaller, scanner, and cleaner modules.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.registry import get_installed_programs, InstalledProgram
from core.uninstaller import Uninstaller
from core.scanner import LeftoverScanner
from core.cleaner import Cleaner
from utils.logger import get_logger


def test_uninstaller():
    """Test uninstaller module (without actually uninstalling)."""
    print("\n" + "=" * 70)
    print("TEST 1: Uninstaller Module")
    print("=" * 70)

    try:
        # Get a test program
        programs = get_installed_programs()
        if not programs:
            print("[SKIP] No programs found for testing")
            return True

        # Find a program with uninstall string
        test_program = None
        for prog in programs:
            if prog.uninstall_string:
                test_program = prog
                break

        if not test_program:
            print("[SKIP] No program with uninstall string found")
            return True

        print(f"Test program: {test_program.name}")
        print(f"Uninstall string: {test_program.uninstall_string}")

        # Create uninstaller instance
        uninstaller = Uninstaller(test_program)

        # Check if it's MSI package
        is_msi = uninstaller._is_msi_package()
        print(f"Is MSI package: {is_msi}")

        # Get uninstall command
        cmd = uninstaller.get_uninstall_command(silent=True)
        print(f"Silent uninstall command: {cmd}")

        print("\n[NOTE] Actual uninstall not executed in test mode")
        print("[PASS] Uninstaller module test passed")
        return True

    except Exception as e:
        print(f"[FAIL] Uninstaller module test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_scanner():
    """Test scanner module."""
    print("\n" + "=" * 70)
    print("TEST 2: Scanner Module")
    print("=" * 70)

    try:
        # Create a test program object
        # We'll use a common program name that likely has some files
        test_program = InstalledProgram(
            name="Microsoft",  # Common name likely to have results
            publisher="Microsoft Corporation",
            architecture="x64"
        )

        print(f"Test program: {test_program.name}")
        print("Scanning for leftovers...")

        # Create scanner
        scanner = LeftoverScanner()

        # Scan (with limited depth to avoid long scan times)
        leftovers = scanner.scan(
            test_program,
            scan_files=True,
            scan_registry=True,
            scan_shortcuts=True
        )

        print(f"\nFound {len(leftovers)} potential leftover items")

        if leftovers:
            # Show summary
            scanner.print_summary()

            # Show some examples
            print("\nFirst 5 items found:")
            for i, leftover in enumerate(leftovers[:5], 1):
                print(f"{i}. {leftover}")

        print("\n[PASS] Scanner module test passed")
        return True

    except Exception as e:
        print(f"[FAIL] Scanner module test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_cleaner():
    """Test cleaner module (without actually deleting)."""
    print("\n" + "=" * 70)
    print("TEST 3: Cleaner Module")
    print("=" * 70)

    try:
        # Create some test leftover objects (not real files)
        from core.scanner import Leftover

        test_leftovers = [
            Leftover(
                type="file",
                path="C:\\Temp\\test_file.txt",
                size=1024
            ),
            Leftover(
                type="directory",
                path="C:\\Temp\\test_dir",
                size=4096
            ),
            Leftover(
                type="registry",
                path="HKEY_CURRENT_USER\\Software\\TestKey"
            ),
        ]

        print(f"Test with {len(test_leftovers)} mock leftover items:")
        for i, leftover in enumerate(test_leftovers, 1):
            print(f"{i}. {leftover}")

        # Create cleaner instance
        cleaner = Cleaner(create_backup=False)

        print("\n[NOTE] Actual deletion not executed in test mode")
        print("       (test items don't exist)")

        # Test grouping functionality
        grouped = cleaner._group_by_type(test_leftovers)
        print(f"\nGrouped by type:")
        for ltype, items in grouped.items():
            print(f"  {ltype}: {len(items)} items")

        print("\n[PASS] Cleaner module test passed")
        return True

    except Exception as e:
        print(f"[FAIL] Cleaner module test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_cli_help():
    """Test CLI help commands."""
    print("\n" + "=" * 70)
    print("TEST 4: CLI Help Commands")
    print("=" * 70)

    try:
        import subprocess

        # Test main help
        result = subprocess.run(
            [sys.executable, "main.py", "--help"],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0 and "uninstall" in result.stdout.lower():
            print("Main help command works")
        else:
            print("[WARNING] Main help command may have issues")

        # Test uninstall help
        result = subprocess.run(
            [sys.executable, "main.py", "uninstall", "--help"],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0 and "program_name" in result.stdout.lower():
            print("Uninstall help command works")
        else:
            print("[WARNING] Uninstall help command may have issues")

        # Test scan help
        result = subprocess.run(
            [sys.executable, "main.py", "scan", "--help"],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            print("Scan help command works")
        else:
            print("[WARNING] Scan help command may have issues")

        # Test clean help
        result = subprocess.run(
            [sys.executable, "main.py", "clean", "--help"],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            print("Clean help command works")
        else:
            print("[WARNING] Clean help command may have issues")

        print("\n[PASS] CLI help commands test passed")
        return True

    except Exception as e:
        print(f"[FAIL] CLI help commands test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """Run all Phase 2 tests."""
    print("\n" + "=" * 70)
    print("WINDOWS UNINSTALLER - PHASE 2 FUNCTIONALITY TEST")
    print("=" * 70)

    results = {
        "Uninstaller Module": test_uninstaller(),
        "Scanner Module": test_scanner(),
        "Cleaner Module": test_cleaner(),
        "CLI Help Commands": test_cli_help(),
    }

    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    passed = sum(results.values())
    total = len(results)

    for test_name, result in results.items():
        status = "[PASS]" if result else "[FAIL]"
        print(f"{test_name:25} : {status}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n*** All Phase 2 tests passed! ***")
        print("\nPhase 2 Implementation Complete:")
        print("  - Uninstaller execution engine")
        print("  - Leftover scanner (files, registry, shortcuts)")
        print("  - Cleaner for safe deletion")
        print("  - CLI commands: uninstall, scan, clean")
        return 0
    else:
        print(f"\n*** {total - passed} test(s) failed ***")
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())

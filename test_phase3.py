"""
Test script for Phase 3: GUI Implementation

This script tests the GUI components:
- Main window creation
- Dialog instantiation
- Widget functionality
"""

import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtTest import QTest
from PyQt6.QtCore import Qt

from core.registry import InstalledProgram
from gui.main_window import MainWindow
from gui.widgets.uninstall_dialog import UninstallDialog
from gui.widgets.scan_dialog import ScanDialog
from utils.icon_extractor import get_program_icon, IconExtractor

# Test markers
PASS = "[PASS]"
FAIL = "[FAIL]"
INFO = "[INFO]"


def print_test(message, success=None):
    """Print test result."""
    if success is None:
        print(f"{INFO} {message}")
    elif success:
        print(f"{PASS} {message}")
    else:
        print(f"{FAIL} {message}")


def test_main_window_creation():
    """Test main window can be created."""
    try:
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)

        window = MainWindow()

        # Check basic attributes
        assert window.windowTitle() == "Windows Uninstaller"
        assert window.programs == []
        assert window.filtered_programs == []
        assert window.selected_program is None

        # Check widgets exist
        assert window.program_table is not None
        assert window.search_box is not None
        assert window.sort_combo is not None
        assert window.details_text is not None
        assert window.uninstall_button is not None
        assert window.scan_button is not None

        print_test("Main window creation", True)
        return True
    except Exception as e:
        print_test(f"Main window creation: {e}", False)
        return False


def test_uninstall_dialog_creation():
    """Test uninstall dialog can be created."""
    try:
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)

        # Create a dummy program
        program = InstalledProgram(
            name="Test Program",
            version="1.0",
            publisher="Test Publisher",
            install_location="C:\\Test",
            uninstall_string="test.exe /uninstall",
            install_date="2024-01-01",
            estimated_size=1024,
            registry_key="HKLM\\Software\\Test",
            architecture="x64"
        )

        dialog = UninstallDialog(program)

        # Check basic attributes
        assert "Test Program" in dialog.windowTitle()
        assert dialog.program == program
        assert dialog.leftovers == []

        # Check widgets exist
        assert dialog.log_text is not None
        assert dialog.start_button is not None
        assert dialog.close_button is not None
        assert dialog.backup_checkbox is not None
        assert dialog.scan_checkbox is not None

        print_test("Uninstall dialog creation", True)
        return True
    except Exception as e:
        print_test(f"Uninstall dialog creation: {e}", False)
        return False


def test_scan_dialog_creation():
    """Test scan dialog can be created."""
    try:
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)

        # Create a dummy program
        program = InstalledProgram(
            name="Test Program",
            version="1.0",
            publisher="Test Publisher",
            install_location="C:\\Test",
            uninstall_string="test.exe /uninstall",
            install_date="2024-01-01",
            estimated_size=1024,
            registry_key="HKLM\\Software\\Test",
            architecture="x64"
        )

        dialog = ScanDialog(program)

        # Check basic attributes
        assert "Test Program" in dialog.windowTitle()
        assert dialog.program == program
        assert dialog.leftovers == []

        # Check widgets exist
        assert dialog.results_list is not None
        assert dialog.scan_button is not None
        assert dialog.clean_button is not None
        assert dialog.close_button is not None
        assert dialog.files_checkbox is not None
        assert dialog.registry_checkbox is not None
        assert dialog.shortcuts_checkbox is not None

        print_test("Scan dialog creation", True)
        return True
    except Exception as e:
        print_test(f"Scan dialog creation: {e}", False)
        return False


def test_main_window_filter():
    """Test program filtering in main window."""
    try:
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)

        window = MainWindow()

        # Add some dummy programs
        window.programs = [
            InstalledProgram(
                name="Test Program A",
                version="1.0",
                publisher="Publisher A",
                install_location="C:\\Test",
                uninstall_string="test.exe",
                install_date="2024-01-01",
                estimated_size=1024,
                registry_key="HKLM\\Software\\TestA",
                architecture="x64"
            ),
            InstalledProgram(
                name="Test Program B",
                version="2.0",
                publisher="Publisher B",
                install_location="C:\\Test",
                uninstall_string="test.exe",
                install_date="2024-01-02",
                estimated_size=2048,
                registry_key="HKLM\\Software\\TestB",
                architecture="x64"
            ),
        ]
        window.filtered_programs = window.programs.copy()

        # Test filtering
        window.filter_programs("Program A")
        assert len(window.filtered_programs) == 1
        assert window.filtered_programs[0].name == "Test Program A"

        # Test clear filter
        window.filter_programs("")
        assert len(window.filtered_programs) == 2

        print_test("Main window filtering", True)
        return True
    except Exception as e:
        print_test(f"Main window filtering: {e}", False)
        return False


def test_main_window_sorting():
    """Test program sorting in main window."""
    try:
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)

        window = MainWindow()

        # Add some dummy programs
        window.programs = [
            InstalledProgram(
                name="B Program",
                version="1.0",
                publisher="Publisher B",
                install_location="C:\\Test",
                uninstall_string="test.exe",
                install_date="2024-01-01",
                estimated_size=1024,
                registry_key="HKLM\\Software\\TestB",
                architecture="x64"
            ),
            InstalledProgram(
                name="A Program",
                version="2.0",
                publisher="Publisher A",
                install_location="C:\\Test",
                uninstall_string="test.exe",
                install_date="2024-01-02",
                estimated_size=2048,
                registry_key="HKLM\\Software\\TestA",
                architecture="x64"
            ),
        ]
        window.filtered_programs = window.programs.copy()

        # Test sorting by name
        window.sort_programs("名前")
        assert window.filtered_programs[0].name == "A Program"
        assert window.filtered_programs[1].name == "B Program"

        # Test sorting by size
        window.sort_programs("サイズ")
        assert window.filtered_programs[0].estimated_size == 2048
        assert window.filtered_programs[1].estimated_size == 1024

        print_test("Main window sorting", True)
        return True
    except Exception as e:
        print_test(f"Main window sorting: {e}", False)
        return False


def test_icon_extraction():
    """Test icon extraction functionality."""
    try:
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)

        extractor = IconExtractor()

        # Test with non-existent file (should return empty icon)
        icon = extractor.get_icon("C:\\nonexistent.exe")
        assert icon is not None  # Icon object should exist even if empty

        # Test with system file (should have icon)
        # Most Windows systems have notepad.exe
        import os
        if os.path.exists("C:\\Windows\\System32\\notepad.exe"):
            icon = extractor.get_icon("C:\\Windows\\System32\\notepad.exe")
            assert icon is not None
            # Icon may or may not be null depending on system

        # Test path parsing
        path, index = extractor._parse_icon_path("C:\\test.exe,0")
        assert path == "C:\\test.exe"
        assert index == 0

        path, index = extractor._parse_icon_path("C:\\test.exe")
        assert path == "C:\\test.exe"
        assert index == 0

        # Test with program object
        program = InstalledProgram(
            name="Test Program",
            version="1.0",
            publisher="Test",
            install_location="C:\\Test",
            uninstall_string="test.exe",
            install_date="2024-01-01",
            estimated_size=1024,
            registry_key="HKLM\\Software\\Test",
            architecture="x64",
            display_icon="C:\\nonexistent.ico"
        )

        icon = get_program_icon(program)
        assert icon is not None

        print_test("Icon extraction", True)
        return True
    except Exception as e:
        print_test(f"Icon extraction: {e}", False)
        return False


def main():
    """Run all Phase 3 tests."""
    print("\n" + "=" * 70)
    print("Phase 3: GUI Implementation Tests")
    print("=" * 70 + "\n")

    results = []

    print_test("Testing GUI components...")
    print()

    # Test 1: Main window creation
    results.append(test_main_window_creation())

    # Test 2: Uninstall dialog creation
    results.append(test_uninstall_dialog_creation())

    # Test 3: Scan dialog creation
    results.append(test_scan_dialog_creation())

    # Test 4: Main window filtering
    results.append(test_main_window_filter())

    # Test 5: Main window sorting
    results.append(test_main_window_sorting())

    # Test 6: Icon extraction
    results.append(test_icon_extraction())

    # Summary
    print("\n" + "=" * 70)
    passed = sum(results)
    total = len(results)

    if passed == total:
        print(f"All tests passed! ({passed}/{total})")
        print("=" * 70)
        print("\nPhase 3 GUI implementation is complete!")
        print("\nNext steps:")
        print("- Run the GUI with: python main.py --gui")
        print("- Test uninstalling a program")
        print("- Test scanning for leftovers")
        return 0
    else:
        print(f"Some tests failed: {passed}/{total} passed")
        print("=" * 70)
        return 1


if __name__ == "__main__":
    sys.exit(main())

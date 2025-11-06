"""
Test script for Phase 6: Additional Features and Optimization

Tests:
- Configuration management
- Export functionality (CSV, JSON, HTML)
- Statistics and reporting
"""

import sys
import os
import tempfile
import json
from datetime import datetime

from utils.config import Config
from utils.exporter import Exporter
from utils.statistics import Statistics, UninstallRecord
from core.registry import InstalledProgram
from utils.logger import get_logger

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


def test_config_management():
    """Test configuration management."""
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = os.path.join(temp_dir, "test_config.json")
            config = Config(config_file)

            # Test default values
            assert config.get("backup.enabled") == True
            assert config.get("scan.max_depth") == 5

            # Test set and get
            config.set("backup.keep_days", 60)
            assert config.get("backup.keep_days") == 60

            # Test save and load
            config.save()
            assert os.path.exists(config_file)

            config2 = Config(config_file)
            assert config2.get("backup.keep_days") == 60

            # Test nested get
            assert config.get("ui.show_icons") == True

            # Test default for missing key
            assert config.get("nonexistent.key", "default") == "default"

            print_test("Configuration management", True)
            return True

    except Exception as e:
        print_test(f"Configuration management: {e}", False)
        import traceback
        traceback.print_exc()
        return False


def test_exporter_csv():
    """Test CSV export."""
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            exporter = Exporter(temp_dir)

            # Create test programs
            programs = [
                InstalledProgram(
                    name="Test Program 1",
                    version="1.0",
                    publisher="Test Publisher",
                    install_location="C:\\Test1",
                    uninstall_string="uninstall.exe",
                    install_date="2024-01-01",
                    estimated_size=1024,
                    registry_key="HKLM\\Software\\Test1",
                    architecture="x64"
                ),
                InstalledProgram(
                    name="Test Program 2",
                    version="2.0",
                    publisher="Test Publisher 2",
                    install_location="C:\\Test2",
                    uninstall_string="uninstall.exe",
                    install_date="2024-01-02",
                    estimated_size=2048,
                    registry_key="HKLM\\Software\\Test2",
                    architecture="x86"
                ),
            ]

            # Export to CSV
            csv_file = exporter.export_programs_csv(programs, "test_programs.csv")
            assert os.path.exists(csv_file)

            # Check file content
            with open(csv_file, 'r', encoding='utf-8-sig') as f:
                content = f.read()
                assert "Test Program 1" in content
                assert "Test Program 2" in content

            print_test("CSV export", True)
            return True

    except Exception as e:
        print_test(f"CSV export: {e}", False)
        import traceback
        traceback.print_exc()
        return False


def test_exporter_json():
    """Test JSON export."""
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            exporter = Exporter(temp_dir)

            programs = [
                InstalledProgram(
                    name="Test Program",
                    version="1.0",
                    publisher="Test Publisher",
                    install_location="C:\\Test",
                    uninstall_string="uninstall.exe",
                    install_date="2024-01-01",
                    estimated_size=1024,
                    registry_key="HKLM\\Software\\Test",
                    architecture="x64"
                ),
            ]

            # Export to JSON
            json_file = exporter.export_programs_json(
                programs, "test_programs.json", include_system_info=False
            )
            assert os.path.exists(json_file)

            # Check JSON structure
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                assert "programs" in data
                assert len(data["programs"]) == 1
                assert data["programs"][0]["name"] == "Test Program"

            print_test("JSON export", True)
            return True

    except Exception as e:
        print_test(f"JSON export: {e}", False)
        import traceback
        traceback.print_exc()
        return False


def test_exporter_html():
    """Test HTML export."""
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            exporter = Exporter(temp_dir)

            programs = [
                InstalledProgram(
                    name="Test Program",
                    version="1.0",
                    publisher="Test Publisher",
                    install_location="C:\\Test",
                    uninstall_string="uninstall.exe",
                    install_date="2024-01-01",
                    estimated_size=1024,
                    registry_key="HKLM\\Software\\Test",
                    architecture="x64"
                ),
            ]

            # Export to HTML
            html_file = exporter.export_programs_html(
                programs, "test_programs.html", include_system_info=False
            )
            assert os.path.exists(html_file)

            # Check HTML content
            with open(html_file, 'r', encoding='utf-8') as f:
                content = f.read()
                assert "<!DOCTYPE html>" in content
                assert "Test Program" in content
                assert "<table>" in content

            print_test("HTML export", True)
            return True

    except Exception as e:
        print_test(f"HTML export: {e}", False)
        import traceback
        traceback.print_exc()
        return False


def test_statistics():
    """Test statistics tracking."""
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            stats = Statistics(temp_dir)

            # Add test records
            record1 = UninstallRecord(
                program_name="Test Program 1",
                version="1.0",
                publisher="Publisher 1",
                uninstall_date=datetime.now().isoformat(),
                success=True,
                files_removed_count=100,
                registry_removed_count=50,
                space_freed_kb=10240,
                errors=[],
                duration_seconds=30.5
            )

            record2 = UninstallRecord(
                program_name="Test Program 2",
                version="2.0",
                publisher="Publisher 2",
                uninstall_date=datetime.now().isoformat(),
                success=False,
                files_removed_count=50,
                registry_removed_count=25,
                space_freed_kb=5120,
                errors=["Test error"],
                duration_seconds=15.2
            )

            stats.add_record(record1)
            stats.add_record(record2)

            # Test statistics
            assert stats.get_total_uninstalls() == 2
            assert stats.get_successful_uninstalls() == 1
            assert stats.get_failed_uninstalls() == 1
            assert stats.get_total_files_removed() == 150
            assert stats.get_total_registry_removed() == 75

            # Test summary
            summary = stats.get_summary()
            assert summary['total_uninstalls'] == 2
            assert summary['successful_uninstalls'] == 1
            assert summary['success_rate'] == 50.0

            # Test save and load
            stats.save()
            stats2 = Statistics(temp_dir)
            assert len(stats2.records) == 2

            print_test("Statistics tracking", True)
            return True

    except Exception as e:
        print_test(f"Statistics tracking: {e}", False)
        import traceback
        traceback.print_exc()
        return False


def test_uninstall_report():
    """Test uninstall report generation."""
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            exporter = Exporter(temp_dir)

            files_removed = [
                "C:\\Test\\file1.txt",
                "C:\\Test\\file2.dll",
                "C:\\Test\\file3.exe"
            ]

            registry_removed = [
                "HKLM\\Software\\Test\\Key1",
                "HKLM\\Software\\Test\\Key2"
            ]

            errors = ["Test error 1", "Test error 2"]

            # Generate report
            report_file = exporter.export_uninstall_report(
                program_name="Test Program",
                uninstall_success=True,
                files_removed=files_removed,
                registry_removed=registry_removed,
                errors=errors,
                filename="test_report.html"
            )

            assert os.path.exists(report_file)

            # Check report content
            with open(report_file, 'r', encoding='utf-8') as f:
                content = f.read()
                assert "Test Program" in content
                assert "SUCCESS" in content
                assert "file1.txt" in content
                assert "Test error 1" in content

            print_test("Uninstall report generation", True)
            return True

    except Exception as e:
        print_test(f"Uninstall report generation: {e}", False)
        import traceback
        traceback.print_exc()
        return False


def test_config_sections():
    """Test configuration sections."""
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = os.path.join(temp_dir, "test_config.json")
            config = Config(config_file)

            # Test get_section
            backup_section = config.get_section("backup")
            assert "enabled" in backup_section
            assert "keep_days" in backup_section

            scan_section = config.get_section("scan")
            assert "scan_files" in scan_section
            assert "max_depth" in scan_section

            # Test reset to defaults
            config.set("backup.keep_days", 999)
            config.save()
            assert config.get("backup.keep_days") == 999

            # Reset to defaults and verify
            result = config.reset_to_defaults()
            assert result == True
            actual_value = config.get("backup.keep_days")
            print(f"DEBUG: After reset, backup.keep_days = {actual_value}, expected 30")
            assert actual_value == 30

            # Load again to verify it was saved
            config2 = Config(config_file)
            assert config2.get("backup.keep_days") == 30

            print_test("Configuration sections", True)
            return True

    except Exception as e:
        print_test(f"Configuration sections: {e}", False)
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all Phase 6 tests."""
    print("\n" + "=" * 70)
    print("PHASE 6: ADDITIONAL FEATURES AND OPTIMIZATION TEST")
    print("=" * 70 + "\n")

    logger = get_logger()

    results = []

    # Test 1: Configuration management
    print_test("Testing configuration management...")
    results.append(test_config_management())
    print()

    # Test 2: CSV export
    print_test("Testing CSV export...")
    results.append(test_exporter_csv())
    print()

    # Test 3: JSON export
    print_test("Testing JSON export...")
    results.append(test_exporter_json())
    print()

    # Test 4: HTML export
    print_test("Testing HTML export...")
    results.append(test_exporter_html())
    print()

    # Test 5: Statistics
    print_test("Testing statistics tracking...")
    results.append(test_statistics())
    print()

    # Test 6: Uninstall report
    print_test("Testing uninstall report generation...")
    results.append(test_uninstall_report())
    print()

    # Test 7: Configuration sections
    print_test("Testing configuration sections...")
    results.append(test_config_sections())
    print()

    # Summary
    print("=" * 70)
    passed = sum(results)
    total = len(results)

    if passed == total:
        print(f"All tests passed! ({passed}/{total})")
        print("=" * 70)
        print("\nPhase 6 implementation is complete!")
        print("\nKey features:")
        print("- Configuration management with JSON persistence")
        print("- Export to CSV, JSON, and HTML formats")
        print("- Statistics tracking and reporting")
        print("- Uninstall report generation")
        print("- GUI integration for all features")
        return 0
    else:
        print(f"Some tests failed: {passed}/{total} passed")
        print("=" * 70)
        return 1


if __name__ == "__main__":
    sys.exit(main())

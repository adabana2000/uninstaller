"""
Test script for Phase 5: Installation Monitor

Tests:
- System snapshot functionality
- File system change detection
- Registry change detection
- Installation trace saving and loading
"""

import sys
import os
import tempfile
import winreg
from pathlib import Path

from core.monitor import (
    SystemSnapshot, InstallationMonitor,
    FileChange, RegistryChange, InstallationTrace
)
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


def test_system_snapshot():
    """Test system snapshot functionality."""
    try:
        snapshot = SystemSnapshot()

        # Test filesystem capture
        test_dir = os.environ.get('TEMP', 'C:\\Windows\\Temp')
        if os.path.exists(test_dir):
            snapshot.capture_filesystem([test_dir], max_depth=2)
            assert len(snapshot.files) > 0, "Should capture some files"
            print_test(f"Filesystem snapshot ({len(snapshot.files)} files)", True)
        else:
            print_test("Filesystem snapshot (skipped - no test dir)", True)

        # Test registry capture
        snapshot.capture_registry([
            (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows")
        ])
        assert len(snapshot.registry_keys) > 0, "Should capture some registry keys"
        print_test(f"Registry snapshot ({len(snapshot.registry_keys)} keys)", True)

        return True
    except Exception as e:
        print_test(f"System snapshot: {e}", False)
        return False


def test_snapshot_comparison():
    """Test snapshot comparison."""
    try:
        # Create two snapshots
        snapshot1 = SystemSnapshot()
        snapshot2 = SystemSnapshot()

        # Add some test data
        snapshot1.files = {
            "C:\\test1.txt": (100, "2024-01-01T00:00:00"),
            "C:\\test2.txt": (200, "2024-01-01T00:00:00"),
            "C:\\test3.txt": (300, "2024-01-01T00:00:00"),
        }

        snapshot2.files = {
            "C:\\test1.txt": (100, "2024-01-01T00:00:00"),  # Unchanged
            "C:\\test2.txt": (250, "2024-01-02T00:00:00"),  # Modified
            "C:\\test4.txt": (400, "2024-01-02T00:00:00"),  # Added
            # test3.txt deleted
        }

        # Compare
        changes = snapshot2.compare_filesystem(snapshot1)

        # Verify changes
        added = [c for c in changes if c.change_type == 'added']
        modified = [c for c in changes if c.change_type == 'modified']
        deleted = [c for c in changes if c.change_type == 'deleted']

        assert len(added) == 1, "Should detect 1 added file"
        assert len(modified) == 1, "Should detect 1 modified file"
        assert len(deleted) == 1, "Should detect 1 deleted file"

        print_test("Filesystem comparison", True)
        return True
    except Exception as e:
        print_test(f"Filesystem comparison: {e}", False)
        return False


def test_registry_comparison():
    """Test registry comparison."""
    try:
        # Create two snapshots
        snapshot1 = SystemSnapshot()
        snapshot2 = SystemSnapshot()

        # Add test registry data
        snapshot1.registry_keys = {
            "HKEY_CURRENT_USER\\Software\\Test1": {"Value1": "Data1"},
            "HKEY_CURRENT_USER\\Software\\Test2": {"Value1": "Data1"},
        }

        snapshot2.registry_keys = {
            "HKEY_CURRENT_USER\\Software\\Test1": {"Value1": "Data1Modified"},  # Modified
            "HKEY_CURRENT_USER\\Software\\Test3": {"Value1": "Data1"},  # Added
            # Test2 deleted
        }

        # Compare
        changes = snapshot2.compare_registry(snapshot1)

        # Verify changes
        added = [c for c in changes if c.change_type == 'added']
        modified = [c for c in changes if c.change_type == 'modified']
        deleted = [c for c in changes if c.change_type == 'deleted']

        assert len(added) >= 1, "Should detect at least 1 addition"
        assert len(modified) >= 1, "Should detect at least 1 modification"
        assert len(deleted) == 1, "Should detect 1 deletion"

        print_test("Registry comparison", True)
        return True
    except Exception as e:
        print_test(f"Registry comparison: {e}", False)
        return False


def test_installation_trace():
    """Test installation trace creation and serialization."""
    try:
        # Create a test trace
        file_changes = [
            FileChange("C:\\test1.txt", "added", 100, "2024-01-01T00:00:00"),
            FileChange("C:\\test2.txt", "modified", 200, "2024-01-01T00:00:00"),
        ]

        registry_changes = [
            RegistryChange("HKLM\\Software\\Test", "added", "Value1", "Data1"),
        ]

        trace = InstallationTrace(
            program_name="Test Program",
            install_date="2024-01-01T00:00:00",
            file_changes=file_changes,
            registry_changes=registry_changes,
            total_size=300
        )

        # Test serialization
        trace_dict = trace.to_dict()
        assert trace_dict['program_name'] == "Test Program"
        assert len(trace_dict['file_changes']) == 2
        assert len(trace_dict['registry_changes']) == 1

        # Test deserialization
        trace2 = InstallationTrace.from_dict(trace_dict)
        assert trace2.program_name == trace.program_name
        assert len(trace2.file_changes) == len(trace.file_changes)
        assert len(trace2.registry_changes) == len(trace.registry_changes)

        print_test("Installation trace serialization", True)
        return True
    except Exception as e:
        print_test(f"Installation trace: {e}", False)
        return False


def test_installation_monitor():
    """Test installation monitor."""
    try:
        # Create temp directory for traces
        with tempfile.TemporaryDirectory() as temp_dir:
            monitor = InstallationMonitor(traces_dir=temp_dir)

            # Test monitoring workflow
            test_paths = [os.environ.get('TEMP', 'C:\\Windows\\Temp')]
            test_registry = [
                (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows")
            ]

            # Start monitoring
            monitor.start_monitoring(paths=test_paths, registry_keys=test_registry)
            assert monitor.before_snapshot is not None

            # Simulate some changes by creating a temporary file
            temp_file = os.path.join(test_paths[0], f"test_monitor_{os.getpid()}.tmp")
            try:
                with open(temp_file, 'w') as f:
                    f.write("Test content")

                # Stop monitoring
                trace = monitor.stop_monitoring(
                    "Test Program",
                    paths=test_paths,
                    registry_keys=test_registry
                )

                assert monitor.after_snapshot is not None
                assert len(trace.file_changes) > 0, "Should detect file changes"

                # Test saving trace
                trace_file = monitor.save_trace(trace)
                assert os.path.exists(trace_file)

                # Test loading trace
                loaded_trace = monitor.load_trace(trace_file)
                assert loaded_trace.program_name == trace.program_name

                # Test listing traces
                traces = monitor.list_traces()
                assert len(traces) > 0

            finally:
                # Cleanup
                if os.path.exists(temp_file):
                    os.remove(temp_file)

        print_test("Installation monitor workflow", True)
        return True
    except Exception as e:
        print_test(f"Installation monitor: {e}", False)
        import traceback
        traceback.print_exc()
        return False


def test_snapshot_save_load():
    """Test snapshot save and load."""
    try:
        snapshot = SystemSnapshot()

        # Add test data
        snapshot.files = {
            "C:\\test.txt": (100, "2024-01-01T00:00:00"),
        }
        snapshot.registry_keys = {
            "HKLM\\Software\\Test": {"Value": "Data"},
        }

        # Save to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_file = f.name

        try:
            snapshot.save(temp_file)
            assert os.path.exists(temp_file)

            # Load snapshot
            loaded_snapshot = SystemSnapshot.load(temp_file)
            assert len(loaded_snapshot.files) == len(snapshot.files)
            assert len(loaded_snapshot.registry_keys) == len(snapshot.registry_keys)

            print_test("Snapshot save/load", True)
            return True
        finally:
            if os.path.exists(temp_file):
                os.remove(temp_file)

    except Exception as e:
        print_test(f"Snapshot save/load: {e}", False)
        return False


def main():
    """Run all Phase 5 tests."""
    print("\n" + "=" * 70)
    print("PHASE 5: INSTALLATION MONITOR TEST")
    print("=" * 70 + "\n")

    logger = get_logger()

    results = []

    # Test 1: System snapshot
    print_test("Testing system snapshot...")
    results.append(test_system_snapshot())
    print()

    # Test 2: Snapshot comparison (filesystem)
    print_test("Testing snapshot comparison (filesystem)...")
    results.append(test_snapshot_comparison())
    print()

    # Test 3: Snapshot comparison (registry)
    print_test("Testing snapshot comparison (registry)...")
    results.append(test_registry_comparison())
    print()

    # Test 4: Installation trace
    print_test("Testing installation trace...")
    results.append(test_installation_trace())
    print()

    # Test 5: Snapshot save/load
    print_test("Testing snapshot save/load...")
    results.append(test_snapshot_save_load())
    print()

    # Test 6: Installation monitor
    print_test("Testing installation monitor...")
    results.append(test_installation_monitor())
    print()

    # Summary
    print("=" * 70)
    passed = sum(results)
    total = len(results)

    if passed == total:
        print(f"All tests passed! ({passed}/{total})")
        print("=" * 70)
        print("\nPhase 5 implementation is complete!")
        print("\nKey features:")
        print("- System state snapshots (files + registry)")
        print("- Change detection (added, modified, deleted)")
        print("- Installation trace recording")
        print("- Trace persistence (save/load)")
        print("\nUsage:")
        print("1. Start monitoring before installation")
        print("2. Install the software")
        print("3. Stop monitoring to capture changes")
        print("4. Save trace for later complete removal")
        return 0
    else:
        print(f"Some tests failed: {passed}/{total} passed")
        print("=" * 70)
        return 1


if __name__ == "__main__":
    sys.exit(main())

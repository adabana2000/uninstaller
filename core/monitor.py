"""
Installation monitor that tracks system changes during software installation.

Features:
- Snapshot system state before installation
- Compare system state after installation
- Track file system changes
- Track registry changes
- Save installation traces for later removal
"""

import os
import json
import hashlib
import winreg
from typing import Dict, List, Set, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path

from utils.logger import get_logger


@dataclass
class FileChange:
    """Represents a file system change."""
    path: str
    change_type: str  # 'added', 'modified', 'deleted'
    size: Optional[int] = None
    timestamp: Optional[str] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return asdict(self)

    @staticmethod
    def from_dict(data: Dict) -> 'FileChange':
        """Create from dictionary."""
        return FileChange(**data)


@dataclass
class RegistryChange:
    """Represents a registry change."""
    key_path: str
    change_type: str  # 'added', 'modified', 'deleted'
    value_name: Optional[str] = None
    value_data: Optional[str] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return asdict(self)

    @staticmethod
    def from_dict(data: Dict) -> 'RegistryChange':
        """Create from dictionary."""
        return RegistryChange(**data)


@dataclass
class InstallationTrace:
    """Complete trace of an installation."""
    program_name: str
    install_date: str
    file_changes: List[FileChange]
    registry_changes: List[RegistryChange]
    total_size: int = 0

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'program_name': self.program_name,
            'install_date': self.install_date,
            'file_changes': [fc.to_dict() for fc in self.file_changes],
            'registry_changes': [rc.to_dict() for rc in self.registry_changes],
            'total_size': self.total_size
        }

    @staticmethod
    def from_dict(data: Dict) -> 'InstallationTrace':
        """Create from dictionary."""
        return InstallationTrace(
            program_name=data['program_name'],
            install_date=data['install_date'],
            file_changes=[FileChange.from_dict(fc) for fc in data.get('file_changes', [])],
            registry_changes=[RegistryChange.from_dict(rc) for rc in data.get('registry_changes', [])],
            total_size=data.get('total_size', 0)
        )


class SystemSnapshot:
    """
    Captures a snapshot of the system state.

    Includes:
    - File system state (specific directories)
    - Registry state (specific keys)
    """

    def __init__(self):
        self.logger = get_logger()
        self.files: Dict[str, Tuple[int, str]] = {}  # path -> (size, timestamp)
        self.registry_keys: Dict[str, Dict[str, str]] = {}  # key_path -> {value_name: value_data}

    def capture_filesystem(self, paths: List[str], max_depth: int = 5):
        """
        Capture file system state for specified paths.

        Args:
            paths: List of directory paths to scan
            max_depth: Maximum directory depth to scan
        """
        self.logger.info(f"Capturing filesystem snapshot for {len(paths)} paths...")

        for base_path in paths:
            if not os.path.exists(base_path):
                continue

            try:
                for root, dirs, files in os.walk(base_path):
                    # Check depth
                    depth = root.replace(base_path, '').count(os.sep)
                    if depth > max_depth:
                        dirs[:] = []  # Don't recurse deeper
                        continue

                    for filename in files:
                        file_path = os.path.join(root, filename)
                        try:
                            stat = os.stat(file_path)
                            self.files[file_path] = (
                                stat.st_size,
                                datetime.fromtimestamp(stat.st_mtime).isoformat()
                            )
                        except (OSError, PermissionError):
                            pass

            except Exception as e:
                self.logger.warning(f"Error scanning {base_path}: {e}")

        self.logger.info(f"Captured {len(self.files)} files")

    def capture_registry(self, key_paths: List[Tuple[int, str]]):
        """
        Capture registry state for specified keys.

        Args:
            key_paths: List of (hive, key_path) tuples
        """
        self.logger.info(f"Capturing registry snapshot for {len(key_paths)} keys...")

        for hive, key_path in key_paths:
            try:
                self._capture_registry_key(hive, key_path)
            except Exception as e:
                self.logger.warning(f"Error capturing registry key {key_path}: {e}")

        self.logger.info(f"Captured {len(self.registry_keys)} registry keys")

    def _capture_registry_key(self, hive: int, key_path: str, recursive: bool = True):
        """
        Capture a single registry key and optionally its subkeys.

        Args:
            hive: Registry hive
            key_path: Key path
            recursive: Whether to capture subkeys
        """
        try:
            # Try different access flags
            for access in [winreg.KEY_READ | winreg.KEY_WOW64_64KEY, winreg.KEY_READ]:
                try:
                    key = winreg.OpenKey(hive, key_path, 0, access)
                    break
                except OSError:
                    continue
            else:
                return  # Couldn't open key

            # Get values
            full_key_path = f"{self._get_hive_name(hive)}\\{key_path}"
            values = {}

            try:
                index = 0
                while True:
                    try:
                        value_name, value_data, value_type = winreg.EnumValue(key, index)
                        values[value_name or "(Default)"] = str(value_data)
                        index += 1
                    except OSError:
                        break
            except Exception as e:
                pass

            if values:
                self.registry_keys[full_key_path] = values

            # Get subkeys if recursive
            if recursive:
                try:
                    index = 0
                    while True:
                        try:
                            subkey_name = winreg.EnumKey(key, index)
                            subkey_path = f"{key_path}\\{subkey_name}"
                            self._capture_registry_key(hive, subkey_path, recursive=False)
                            index += 1
                        except OSError:
                            break
                except Exception as e:
                    pass

            winreg.CloseKey(key)

        except Exception as e:
            pass

    def _get_hive_name(self, hive: int) -> str:
        """Get registry hive name."""
        hive_names = {
            winreg.HKEY_LOCAL_MACHINE: "HKEY_LOCAL_MACHINE",
            winreg.HKEY_CURRENT_USER: "HKEY_CURRENT_USER",
            winreg.HKEY_CLASSES_ROOT: "HKEY_CLASSES_ROOT",
            winreg.HKEY_USERS: "HKEY_USERS",
            winreg.HKEY_CURRENT_CONFIG: "HKEY_CURRENT_CONFIG",
        }
        return hive_names.get(hive, "UNKNOWN")

    def compare_filesystem(self, other: 'SystemSnapshot') -> List[FileChange]:
        """
        Compare file system state with another snapshot.

        Args:
            other: Another SystemSnapshot to compare with

        Returns:
            List of FileChange objects
        """
        changes = []

        # Find added and modified files
        for path, (size, timestamp) in self.files.items():
            if path not in other.files:
                changes.append(FileChange(
                    path=path,
                    change_type='added',
                    size=size,
                    timestamp=timestamp
                ))
            elif other.files[path] != (size, timestamp):
                changes.append(FileChange(
                    path=path,
                    change_type='modified',
                    size=size,
                    timestamp=timestamp
                ))

        # Find deleted files
        for path in other.files:
            if path not in self.files:
                changes.append(FileChange(
                    path=path,
                    change_type='deleted'
                ))

        return changes

    def compare_registry(self, other: 'SystemSnapshot') -> List[RegistryChange]:
        """
        Compare registry state with another snapshot.

        Args:
            other: Another SystemSnapshot to compare with

        Returns:
            List of RegistryChange objects
        """
        changes = []

        # Find added and modified keys
        for key_path, values in self.registry_keys.items():
            if key_path not in other.registry_keys:
                # Entire key is new
                changes.append(RegistryChange(
                    key_path=key_path,
                    change_type='added'
                ))
            else:
                # Check for value changes
                other_values = other.registry_keys[key_path]
                for value_name, value_data in values.items():
                    if value_name not in other_values:
                        changes.append(RegistryChange(
                            key_path=key_path,
                            change_type='added',
                            value_name=value_name,
                            value_data=value_data
                        ))
                    elif other_values[value_name] != value_data:
                        changes.append(RegistryChange(
                            key_path=key_path,
                            change_type='modified',
                            value_name=value_name,
                            value_data=value_data
                        ))

        # Find deleted keys
        for key_path in other.registry_keys:
            if key_path not in self.registry_keys:
                changes.append(RegistryChange(
                    key_path=key_path,
                    change_type='deleted'
                ))

        return changes

    def save(self, file_path: str):
        """
        Save snapshot to file.

        Args:
            file_path: Path to save snapshot
        """
        data = {
            'files': self.files,
            'registry_keys': self.registry_keys,
            'timestamp': datetime.now().isoformat()
        }

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

        self.logger.info(f"Snapshot saved to {file_path}")

    @staticmethod
    def load(file_path: str) -> 'SystemSnapshot':
        """
        Load snapshot from file.

        Args:
            file_path: Path to snapshot file

        Returns:
            SystemSnapshot object
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        snapshot = SystemSnapshot()
        snapshot.files = {k: tuple(v) for k, v in data.get('files', {}).items()}
        snapshot.registry_keys = data.get('registry_keys', {})

        return snapshot


class InstallationMonitor:
    """
    Monitors system changes during software installation.

    Usage:
    1. Start monitoring before installation
    2. Install the software
    3. Stop monitoring and get changes
    4. Save trace for later removal
    """

    # Default paths to monitor
    DEFAULT_PATHS = [
        os.environ.get('PROGRAMFILES', 'C:\\Program Files'),
        os.environ.get('PROGRAMFILES(X86)', 'C:\\Program Files (x86)'),
        os.environ.get('APPDATA', ''),
        os.environ.get('LOCALAPPDATA', ''),
        os.environ.get('PROGRAMDATA', ''),
    ]

    # Default registry keys to monitor
    DEFAULT_REGISTRY_KEYS = [
        (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_LOCAL_MACHINE, r"Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_LOCAL_MACHINE, r"Software"),
        (winreg.HKEY_CURRENT_USER, r"Software"),
    ]

    def __init__(self, traces_dir: Optional[str] = None):
        """
        Initialize installation monitor.

        Args:
            traces_dir: Directory to store installation traces
        """
        self.logger = get_logger()
        self.before_snapshot: Optional[SystemSnapshot] = None
        self.after_snapshot: Optional[SystemSnapshot] = None

        # Traces directory
        if traces_dir is None:
            traces_dir = os.path.join(os.getcwd(), 'data', 'traces')
        self.traces_dir = traces_dir
        os.makedirs(self.traces_dir, exist_ok=True)

    def start_monitoring(self, paths: Optional[List[str]] = None,
                        registry_keys: Optional[List[Tuple[int, str]]] = None):
        """
        Start monitoring by taking a before snapshot.

        Args:
            paths: List of paths to monitor (uses defaults if None)
            registry_keys: List of registry keys to monitor (uses defaults if None)
        """
        self.logger.info("Starting installation monitoring...")

        if paths is None:
            paths = [p for p in self.DEFAULT_PATHS if p and os.path.exists(p)]

        if registry_keys is None:
            registry_keys = self.DEFAULT_REGISTRY_KEYS

        self.before_snapshot = SystemSnapshot()
        self.before_snapshot.capture_filesystem(paths)
        self.before_snapshot.capture_registry(registry_keys)

        self.logger.info("Before snapshot captured")

    def stop_monitoring(self, program_name: str,
                       paths: Optional[List[str]] = None,
                       registry_keys: Optional[List[str]] = None) -> InstallationTrace:
        """
        Stop monitoring and calculate changes.

        Args:
            program_name: Name of the installed program
            paths: List of paths to monitor (uses defaults if None)
            registry_keys: List of registry keys to monitor (uses defaults if None)

        Returns:
            InstallationTrace object
        """
        if self.before_snapshot is None:
            raise RuntimeError("Monitoring not started")

        self.logger.info("Stopping installation monitoring...")

        if paths is None:
            paths = [p for p in self.DEFAULT_PATHS if p and os.path.exists(p)]

        if registry_keys is None:
            registry_keys = self.DEFAULT_REGISTRY_KEYS

        self.after_snapshot = SystemSnapshot()
        self.after_snapshot.capture_filesystem(paths)
        self.after_snapshot.capture_registry(registry_keys)

        self.logger.info("After snapshot captured")

        # Compare snapshots
        file_changes = self.after_snapshot.compare_filesystem(self.before_snapshot)
        registry_changes = self.after_snapshot.compare_registry(self.before_snapshot)

        # Calculate total size
        total_size = sum(fc.size or 0 for fc in file_changes if fc.change_type == 'added')

        trace = InstallationTrace(
            program_name=program_name,
            install_date=datetime.now().isoformat(),
            file_changes=file_changes,
            registry_changes=registry_changes,
            total_size=total_size
        )

        self.logger.info(f"Detected {len(file_changes)} file changes, {len(registry_changes)} registry changes")

        return trace

    def save_trace(self, trace: InstallationTrace) -> str:
        """
        Save installation trace to file.

        Args:
            trace: InstallationTrace object

        Returns:
            Path to saved trace file
        """
        # Sanitize program name for filename
        safe_name = "".join(c for c in trace.program_name if c.isalnum() or c in (' ', '-', '_')).strip()
        filename = f"{safe_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        file_path = os.path.join(self.traces_dir, filename)

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(trace.to_dict(), f, indent=2)

        self.logger.info(f"Trace saved to {file_path}")
        return file_path

    def load_trace(self, file_path: str) -> InstallationTrace:
        """
        Load installation trace from file.

        Args:
            file_path: Path to trace file

        Returns:
            InstallationTrace object
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        return InstallationTrace.from_dict(data)

    def list_traces(self) -> List[Tuple[str, InstallationTrace]]:
        """
        List all saved installation traces.

        Returns:
            List of (file_path, InstallationTrace) tuples
        """
        traces = []

        if not os.path.exists(self.traces_dir):
            return traces

        for filename in os.listdir(self.traces_dir):
            if filename.endswith('.json'):
                file_path = os.path.join(self.traces_dir, filename)
                try:
                    trace = self.load_trace(file_path)
                    traces.append((file_path, trace))
                except Exception as e:
                    self.logger.warning(f"Error loading trace {filename}: {e}")

        return traces

    def print_trace_summary(self, trace: InstallationTrace):
        """
        Print summary of installation trace.

        Args:
            trace: InstallationTrace object
        """
        print("\n" + "=" * 70)
        print(f"Installation Trace: {trace.program_name}")
        print("=" * 70)
        print(f"Install Date:      {trace.install_date}")
        print(f"File Changes:      {len(trace.file_changes)}")
        print(f"Registry Changes:  {len(trace.registry_changes)}")
        print(f"Total Size:        {self._format_size(trace.total_size)}")

        # File changes summary
        added = sum(1 for fc in trace.file_changes if fc.change_type == 'added')
        modified = sum(1 for fc in trace.file_changes if fc.change_type == 'modified')
        deleted = sum(1 for fc in trace.file_changes if fc.change_type == 'deleted')

        print(f"\nFile Changes Breakdown:")
        print(f"  Added:    {added}")
        print(f"  Modified: {modified}")
        print(f"  Deleted:  {deleted}")

        # Registry changes summary
        added = sum(1 for rc in trace.registry_changes if rc.change_type == 'added')
        modified = sum(1 for rc in trace.registry_changes if rc.change_type == 'modified')
        deleted = sum(1 for rc in trace.registry_changes if rc.change_type == 'deleted')

        print(f"\nRegistry Changes Breakdown:")
        print(f"  Added:    {added}")
        print(f"  Modified: {modified}")
        print(f"  Deleted:  {deleted}")

        print("=" * 70)

    def _format_size(self, size_bytes: int) -> str:
        """Format file size."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"

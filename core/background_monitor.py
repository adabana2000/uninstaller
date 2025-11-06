"""
Background installation monitor that runs continuously to detect new software installations.

Features:
- Runs in background thread
- Periodically checks for new program installations
- Automatically creates snapshots for detected installations
- Configurable check interval
- Can be enabled/disabled from GUI
"""

import time
import threading
from typing import Set, Optional, Callable, Dict
from datetime import datetime

from core.registry import get_installed_programs
from core.monitor import SystemSnapshot, InstallationMonitor
from utils.logger import get_logger
from utils.config import ConfigManager

logger = get_logger(__name__)


class BackgroundMonitor:
    """
    Background monitor that continuously checks for new software installations.
    """

    def __init__(self, on_installation_detected: Optional[Callable[[str], None]] = None):
        """
        Initialize background monitor.

        Args:
            on_installation_detected: Callback when new installation is detected.
                                     Receives program name as argument.
        """
        self.on_installation_detected = on_installation_detected
        self.config = ConfigManager()

        # Monitor state
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._known_programs: Set[str] = set()
        self._lock = threading.Lock()

        # Configuration
        self._check_interval = self.config.get('monitor.check_interval', 60)  # seconds
        self._enabled = self.config.get('monitor.enabled', False)

        # Initialize known programs
        self._initialize_known_programs()

    def _initialize_known_programs(self):
        """Initialize the set of currently installed programs."""
        try:
            programs = get_installed_programs()
            with self._lock:
                self._known_programs = {p.name for p in programs if p.name}
            logger.info(f"Initialized with {len(self._known_programs)} known programs")
        except Exception as e:
            logger.error(f"Failed to initialize known programs: {e}")

    def start(self):
        """Start the background monitor."""
        with self._lock:
            if self._running:
                logger.warning("Background monitor is already running")
                return

            self._running = True

        # Start monitoring thread
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()

        logger.info("Background monitor started")

    def stop(self):
        """Stop the background monitor."""
        with self._lock:
            if not self._running:
                logger.warning("Background monitor is not running")
                return

            self._running = False

        # Wait for thread to finish
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)

        logger.info("Background monitor stopped")

    def is_running(self) -> bool:
        """Check if monitor is currently running."""
        with self._lock:
            return self._running

    def set_check_interval(self, seconds: int):
        """
        Set the check interval.

        Args:
            seconds: Number of seconds between checks (minimum 10)
        """
        if seconds < 10:
            seconds = 10
            logger.warning("Check interval too low, set to minimum 10 seconds")

        self._check_interval = seconds
        self.config.set('monitor.check_interval', seconds)
        self.config.save()
        logger.info(f"Check interval set to {seconds} seconds")

    def get_check_interval(self) -> int:
        """Get current check interval in seconds."""
        return self._check_interval

    def _monitor_loop(self):
        """Main monitoring loop (runs in background thread)."""
        logger.info("Monitor loop started")

        while True:
            with self._lock:
                if not self._running:
                    break

            try:
                # Check for new installations
                new_programs = self._check_for_new_installations()

                if new_programs:
                    for program_name in new_programs:
                        logger.info(f"New installation detected: {program_name}")

                        # Notify callback
                        if self.on_installation_detected:
                            try:
                                self.on_installation_detected(program_name)
                            except Exception as e:
                                logger.error(f"Error in callback: {e}")

                        # Add to known programs
                        with self._lock:
                            self._known_programs.add(program_name)

            except Exception as e:
                logger.error(f"Error in monitor loop: {e}")

            # Sleep for check interval
            time.sleep(self._check_interval)

        logger.info("Monitor loop ended")

    def _check_for_new_installations(self) -> Set[str]:
        """
        Check for new program installations.

        Returns:
            Set of newly installed program names
        """
        try:
            # Get current programs
            current_programs = get_installed_programs()
            current_names = {p.name for p in current_programs if p.name}

            # Find new programs
            with self._lock:
                new_programs = current_names - self._known_programs

            return new_programs

        except Exception as e:
            logger.error(f"Failed to check for new installations: {e}")
            return set()

    def get_statistics(self) -> Dict:
        """
        Get monitoring statistics.

        Returns:
            Dictionary with statistics
        """
        with self._lock:
            return {
                'running': self._running,
                'check_interval': self._check_interval,
                'known_programs': len(self._known_programs),
                'enabled': self._enabled
            }

    def refresh_known_programs(self):
        """Refresh the list of known programs (useful after manual changes)."""
        self._initialize_known_programs()
        logger.info("Known programs list refreshed")


class BackgroundMonitorManager:
    """
    Singleton manager for the background monitor.
    """

    _instance: Optional[BackgroundMonitor] = None
    _lock = threading.Lock()

    @classmethod
    def get_instance(cls, on_installation_detected: Optional[Callable[[str], None]] = None) -> BackgroundMonitor:
        """
        Get the singleton instance of BackgroundMonitor.

        Args:
            on_installation_detected: Callback for installation detection (only used on first call)

        Returns:
            BackgroundMonitor instance
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = BackgroundMonitor(on_installation_detected)

        return cls._instance

    @classmethod
    def reset(cls):
        """Reset the singleton instance (for testing)."""
        with cls._lock:
            if cls._instance and cls._instance.is_running():
                cls._instance.stop()
            cls._instance = None

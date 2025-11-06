"""
Logging utilities for the uninstaller application.
Provides structured logging with file output and console output.
"""

import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


class UninstallerLogger:
    """
    Custom logger for the uninstaller application.

    Features:
    - Console output with color coding
    - File output with detailed information
    - Automatic log rotation
    - Operation-specific log files
    """

    def __init__(
        self,
        name: str = "uninstaller",
        log_dir: Optional[str] = None,
        console_level: int = logging.INFO,
        file_level: int = logging.DEBUG
    ):
        """
        Initialize the logger.

        Args:
            name: Logger name
            log_dir: Directory to store log files (default: %LOCALAPPDATA%/Uninstaller/logs)
            console_level: Logging level for console output
            file_level: Logging level for file output
        """
        self.name = name
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)

        # Prevent duplicate handlers
        if self.logger.handlers:
            self.logger.handlers.clear()

        # Set up log directory
        if log_dir is None:
            appdata = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
            log_dir = os.path.join(appdata, "Uninstaller", "logs")

        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Create handlers
        self._setup_console_handler(console_level)
        self._setup_file_handler(file_level)

        self.logger.info(f"Logger initialized: {name}")

    def _setup_console_handler(self, level: int) -> None:
        """
        Set up console output handler.

        Args:
            level: Logging level
        """
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)

        # Simple format for console
        console_formatter = logging.Formatter(
            "%(levelname)-8s | %(message)s"
        )
        console_handler.setFormatter(console_formatter)

        self.logger.addHandler(console_handler)

    def _setup_file_handler(self, level: int) -> None:
        """
        Set up file output handler.

        Args:
            level: Logging level
        """
        # Generate log filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = self.log_dir / f"uninstaller_{timestamp}.log"

        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(level)

        # Detailed format for file
        file_formatter = logging.Formatter(
            "[%(asctime)s] %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        file_handler.setFormatter(file_formatter)

        self.logger.addHandler(file_handler)

        self.current_log_file = log_file

    def debug(self, message: str) -> None:
        """Log debug message."""
        self.logger.debug(message)

    def info(self, message: str) -> None:
        """Log info message."""
        self.logger.info(message)

    def warning(self, message: str) -> None:
        """Log warning message."""
        self.logger.warning(message)

    def error(self, message: str) -> None:
        """Log error message."""
        self.logger.error(message)

    def critical(self, message: str) -> None:
        """Log critical message."""
        self.logger.critical(message)

    def log_operation_start(self, operation: str, target: str) -> None:
        """
        Log the start of an operation.

        Args:
            operation: Operation name (e.g., "Uninstall", "Scan")
            target: Target of the operation (e.g., program name)
        """
        separator = "=" * 70
        self.logger.info(separator)
        self.logger.info(f"OPERATION START: {operation}")
        self.logger.info(f"Target: {target}")
        self.logger.info(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info(separator)

    def log_operation_end(self, operation: str, success: bool, details: str = "") -> None:
        """
        Log the end of an operation.

        Args:
            operation: Operation name
            success: Whether the operation succeeded
            details: Additional details about the result
        """
        separator = "=" * 70
        status = "SUCCESS" if success else "FAILED"
        log_func = self.logger.info if success else self.logger.error

        log_func(separator)
        log_func(f"OPERATION END: {operation} - {status}")
        if details:
            log_func(f"Details: {details}")
        log_func(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        log_func(separator)

    def log_file_deletion(self, file_path: str, success: bool) -> None:
        """
        Log file deletion.

        Args:
            file_path: Path to the file
            success: Whether deletion succeeded
        """
        if success:
            self.logger.debug(f"Deleted file: {file_path}")
        else:
            self.logger.warning(f"Failed to delete file: {file_path}")

    def log_registry_deletion(self, key_path: str, success: bool) -> None:
        """
        Log registry key deletion.

        Args:
            key_path: Registry key path
            success: Whether deletion succeeded
        """
        if success:
            self.logger.debug(f"Deleted registry key: {key_path}")
        else:
            self.logger.warning(f"Failed to delete registry key: {key_path}")

    def log_process_output(self, process_name: str, output: str) -> None:
        """
        Log process output.

        Args:
            process_name: Name of the process
            output: Output from the process
        """
        self.logger.debug(f"Process '{process_name}' output:")
        for line in output.strip().split("\n"):
            self.logger.debug(f"  {line}")

    def get_log_file_path(self) -> Path:
        """
        Get the current log file path.

        Returns:
            Path to the current log file
        """
        return self.current_log_file

    def cleanup_old_logs(self, keep_days: int = 30) -> int:
        """
        Clean up log files older than specified days.

        Args:
            keep_days: Number of days to keep logs

        Returns:
            Number of deleted log files
        """
        deleted_count = 0
        current_time = datetime.now()

        for log_file in self.log_dir.glob("uninstaller_*.log"):
            try:
                # Get file modification time
                file_time = datetime.fromtimestamp(log_file.stat().st_mtime)
                age_days = (current_time - file_time).days

                if age_days > keep_days:
                    log_file.unlink()
                    deleted_count += 1
                    self.logger.debug(f"Deleted old log file: {log_file.name}")

            except Exception as e:
                self.logger.warning(f"Failed to delete old log file {log_file.name}: {e}")

        if deleted_count > 0:
            self.logger.info(f"Cleaned up {deleted_count} old log file(s)")

        return deleted_count


# Global logger instance
_global_logger: Optional[UninstallerLogger] = None


def get_logger(
    name: str = "uninstaller",
    log_dir: Optional[str] = None
) -> UninstallerLogger:
    """
    Get or create the global logger instance.

    Args:
        name: Logger name
        log_dir: Directory to store log files

    Returns:
        UninstallerLogger instance
    """
    global _global_logger

    if _global_logger is None:
        _global_logger = UninstallerLogger(name=name, log_dir=log_dir)

    return _global_logger


def log_info(message: str) -> None:
    """Convenience function to log info message."""
    get_logger().info(message)


def log_error(message: str) -> None:
    """Convenience function to log error message."""
    get_logger().error(message)


def log_warning(message: str) -> None:
    """Convenience function to log warning message."""
    get_logger().warning(message)


def log_debug(message: str) -> None:
    """Convenience function to log debug message."""
    get_logger().debug(message)


if __name__ == "__main__":
    # Test the logger
    logger = get_logger()

    logger.info("Testing the logger...")
    logger.debug("This is a debug message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")

    logger.log_operation_start("Test Operation", "Test Target")
    logger.info("Performing test operation...")
    logger.log_operation_end("Test Operation", True, "Operation completed successfully")

    print(f"\nLog file created at: {logger.get_log_file_path()}")

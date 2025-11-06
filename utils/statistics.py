"""
Statistics and reporting functionality.

Tracks uninstall history and provides usage statistics.
"""

import os
import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


@dataclass
class UninstallRecord:
    """Record of a program uninstallation."""
    program_name: str
    version: Optional[str]
    publisher: Optional[str]
    uninstall_date: str
    success: bool
    files_removed_count: int
    registry_removed_count: int
    space_freed_kb: int
    errors: List[str]
    duration_seconds: float

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UninstallRecord':
        """Create from dictionary."""
        return cls(**data)


class Statistics:
    """Statistics tracker for uninstallations."""

    def __init__(self, data_dir: Optional[str] = None):
        """Initialize statistics tracker.

        Args:
            data_dir: Directory for statistics data. If None, uses default location.
        """
        if data_dir is None:
            app_data = os.environ.get('LOCALAPPDATA', '')
            if app_data:
                data_dir = os.path.join(app_data, 'WindowsUninstaller', 'data')
            else:
                data_dir = 'data'

        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)

        self.history_file = os.path.join(data_dir, 'uninstall_history.json')
        self.records: List[UninstallRecord] = []
        self.load()

    def load(self) -> bool:
        """Load statistics from file.

        Returns:
            True if loaded successfully, False otherwise.
        """
        try:
            if os.path.exists(self.history_file):
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.records = [UninstallRecord.from_dict(r) for r in data]

                logger.info(f"Loaded {len(self.records)} uninstall records")
                return True
            else:
                logger.info("No history file found")
                return False
        except Exception as e:
            logger.error(f"Failed to load statistics: {e}")
            return False

    def save(self) -> bool:
        """Save statistics to file.

        Returns:
            True if saved successfully, False otherwise.
        """
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                data = [r.to_dict() for r in self.records]
                json.dump(data, f, indent=2)

            logger.info(f"Saved {len(self.records)} uninstall records")
            return True
        except Exception as e:
            logger.error(f"Failed to save statistics: {e}")
            return False

    def add_record(self, record: UninstallRecord) -> None:
        """Add uninstall record.

        Args:
            record: Uninstall record to add
        """
        self.records.append(record)
        self.save()

    def get_total_uninstalls(self) -> int:
        """Get total number of uninstalls.

        Returns:
            Total uninstalls count
        """
        return len(self.records)

    def get_successful_uninstalls(self) -> int:
        """Get number of successful uninstalls.

        Returns:
            Successful uninstalls count
        """
        return sum(1 for r in self.records if r.success)

    def get_failed_uninstalls(self) -> int:
        """Get number of failed uninstalls.

        Returns:
            Failed uninstalls count
        """
        return sum(1 for r in self.records if not r.success)

    def get_total_space_freed_mb(self) -> float:
        """Get total space freed in MB.

        Returns:
            Total space freed in megabytes
        """
        total_kb = sum(r.space_freed_kb for r in self.records)
        return total_kb / 1024

    def get_total_files_removed(self) -> int:
        """Get total number of files removed.

        Returns:
            Total files removed count
        """
        return sum(r.files_removed_count for r in self.records)

    def get_total_registry_removed(self) -> int:
        """Get total number of registry keys removed.

        Returns:
            Total registry keys removed count
        """
        return sum(r.registry_removed_count for r in self.records)

    def get_recent_uninstalls(self, days: int = 7) -> List[UninstallRecord]:
        """Get uninstalls from the last N days.

        Args:
            days: Number of days to look back

        Returns:
            List of recent uninstall records
        """
        cutoff_date = datetime.now() - timedelta(days=days)
        recent = []

        for record in self.records:
            try:
                record_date = datetime.fromisoformat(record.uninstall_date)
                if record_date >= cutoff_date:
                    recent.append(record)
            except ValueError:
                continue

        return recent

    def get_uninstalls_by_publisher(self) -> Dict[str, int]:
        """Get uninstalls grouped by publisher.

        Returns:
            Dictionary mapping publisher to uninstall count
        """
        publishers: Dict[str, int] = {}

        for record in self.records:
            publisher = record.publisher or "Unknown"
            publishers[publisher] = publishers.get(publisher, 0) + 1

        return publishers

    def get_average_duration(self) -> float:
        """Get average uninstall duration in seconds.

        Returns:
            Average duration in seconds
        """
        if not self.records:
            return 0.0

        total = sum(r.duration_seconds for r in self.records)
        return total / len(self.records)

    def get_most_common_errors(self, limit: int = 10) -> List[tuple]:
        """Get most common errors.

        Args:
            limit: Maximum number of errors to return

        Returns:
            List of (error_message, count) tuples
        """
        error_counts: Dict[str, int] = {}

        for record in self.records:
            for error in record.errors:
                error_counts[error] = error_counts.get(error, 0) + 1

        # Sort by count
        sorted_errors = sorted(error_counts.items(), key=lambda x: x[1], reverse=True)
        return sorted_errors[:limit]

    def get_summary(self) -> Dict[str, Any]:
        """Get comprehensive statistics summary.

        Returns:
            Dictionary with all statistics
        """
        return {
            "total_uninstalls": self.get_total_uninstalls(),
            "successful_uninstalls": self.get_successful_uninstalls(),
            "failed_uninstalls": self.get_failed_uninstalls(),
            "success_rate": (
                self.get_successful_uninstalls() / self.get_total_uninstalls() * 100
                if self.get_total_uninstalls() > 0 else 0
            ),
            "total_space_freed_mb": self.get_total_space_freed_mb(),
            "total_files_removed": self.get_total_files_removed(),
            "total_registry_removed": self.get_total_registry_removed(),
            "average_duration_seconds": self.get_average_duration(),
            "recent_uninstalls_7days": len(self.get_recent_uninstalls(7)),
            "recent_uninstalls_30days": len(self.get_recent_uninstalls(30)),
        }

    def clear_old_records(self, days: int = 90) -> int:
        """Clear records older than specified days.

        Args:
            days: Age threshold in days

        Returns:
            Number of records removed
        """
        cutoff_date = datetime.now() - timedelta(days=days)
        original_count = len(self.records)

        self.records = [
            r for r in self.records
            if datetime.fromisoformat(r.uninstall_date) >= cutoff_date
        ]

        removed_count = original_count - len(self.records)

        if removed_count > 0:
            self.save()
            logger.info(f"Removed {removed_count} old records")

        return removed_count

    def export_to_csv(self, file_path: str) -> bool:
        """Export records to CSV file.

        Args:
            file_path: Output CSV file path

        Returns:
            True if exported successfully
        """
        try:
            import csv

            with open(file_path, 'w', newline='', encoding='utf-8-sig') as f:
                if not self.records:
                    return True

                writer = csv.DictWriter(f, fieldnames=self.records[0].to_dict().keys())
                writer.writeheader()

                for record in self.records:
                    row = record.to_dict()
                    # Convert list to string for CSV
                    row['errors'] = '; '.join(row['errors'])
                    writer.writerow(row)

            logger.info(f"Exported {len(self.records)} records to {file_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to export to CSV: {e}")
            return False

    def generate_report(self) -> str:
        """Generate text report of statistics.

        Returns:
            Formatted text report
        """
        summary = self.get_summary()

        report = f"""
=============================================================
               UNINSTALLER STATISTICS REPORT
=============================================================

OVERVIEW:
---------
Total Uninstalls:        {summary['total_uninstalls']}
Successful:              {summary['successful_uninstalls']}
Failed:                  {summary['failed_uninstalls']}
Success Rate:            {summary['success_rate']:.1f}%

CLEANUP RESULTS:
----------------
Space Freed:             {summary['total_space_freed_mb']:.2f} MB
Files Removed:           {summary['total_files_removed']:,}
Registry Keys Removed:   {summary['total_registry_removed']:,}

PERFORMANCE:
------------
Average Duration:        {summary['average_duration_seconds']:.1f} seconds

RECENT ACTIVITY:
----------------
Last 7 Days:             {summary['recent_uninstalls_7days']} uninstalls
Last 30 Days:            {summary['recent_uninstalls_30days']} uninstalls

"""

        # Add most common errors if any
        common_errors = self.get_most_common_errors(5)
        if common_errors:
            report += "\nMOST COMMON ERRORS:\n"
            report += "-------------------\n"
            for error, count in common_errors:
                report += f"  [{count}x] {error[:80]}...\n"

        report += "\n=============================================================\n"

        return report


# Global statistics instance
_stats_instance: Optional[Statistics] = None


def get_statistics() -> Statistics:
    """Get global statistics instance.

    Returns:
        Global Statistics instance
    """
    global _stats_instance
    if _stats_instance is None:
        _stats_instance = Statistics()
    return _stats_instance


def reload_statistics() -> Statistics:
    """Reload statistics from file.

    Returns:
        Reloaded Statistics instance
    """
    global _stats_instance
    _stats_instance = Statistics()
    return _stats_instance

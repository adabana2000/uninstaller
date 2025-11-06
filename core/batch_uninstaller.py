"""
Batch uninstaller for multiple programs.

Features:
- Uninstall multiple programs in sequence
- Progress tracking
- Error handling and reporting
- Leftover scanning and cleaning
"""

from typing import List, Callable, Optional
from dataclasses import dataclass
from datetime import datetime

from core.registry import InstalledProgram
from core.uninstaller import Uninstaller, UninstallResult
from core.scanner import LeftoverScanner
from core.cleaner import Cleaner, CleanResult
from utils.logger import get_logger


@dataclass
class BatchUninstallResult:
    """Result of batch uninstallation."""
    total_programs: int
    successful: int
    failed: int
    skipped: int
    results: List[tuple[InstalledProgram, UninstallResult]]
    leftovers_found: int = 0
    leftovers_cleaned: int = 0
    errors: List[tuple[str, str]] = None  # (program_name, error_message)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []

    @property
    def duration(self) -> float:
        """Get duration in seconds."""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0


class BatchUninstaller:
    """
    Handles batch uninstallation of multiple programs.

    Features:
    - Sequential uninstallation
    - Progress callbacks
    - Automatic leftover scanning and cleaning
    - Detailed error reporting
    """

    def __init__(
        self,
        progress_callback: Optional[Callable[[str, int, int], None]] = None
    ):
        """
        Initialize batch uninstaller.

        Args:
            progress_callback: Callback function(message, current, total)
        """
        self.logger = get_logger()
        self.progress_callback = progress_callback

    def uninstall_multiple(
        self,
        programs: List[InstalledProgram],
        silent: bool = True,
        create_backup: bool = True,
        scan_leftovers: bool = True,
        clean_leftovers: bool = True
    ) -> BatchUninstallResult:
        """
        Uninstall multiple programs.

        Args:
            programs: List of programs to uninstall
            silent: Use silent uninstallation
            create_backup: Create backups before uninstalling
            scan_leftovers: Scan for leftovers after each uninstall
            clean_leftovers: Clean leftovers automatically

        Returns:
            BatchUninstallResult object
        """
        start_time = datetime.now()

        result = BatchUninstallResult(
            total_programs=len(programs),
            successful=0,
            failed=0,
            skipped=0,
            results=[],
            start_time=start_time
        )

        self.logger.log_operation_start(
            "Batch Uninstall",
            f"{len(programs)} programs"
        )

        for index, program in enumerate(programs, 1):
            # Report progress
            self._report_progress(
                f"Uninstalling {program.name}... ({index}/{len(programs)})",
                index,
                len(programs)
            )

            try:
                # Uninstall the program
                uninstaller = Uninstaller(program)
                uninstall_result = uninstaller.uninstall(
                    silent=silent,
                    create_backup=create_backup
                )

                result.results.append((program, uninstall_result))

                if uninstall_result.success:
                    result.successful += 1
                    self.logger.info(f"Successfully uninstalled: {program.name}")

                    # Scan for leftovers if requested
                    if scan_leftovers:
                        self._report_progress(
                            f"Scanning leftovers for {program.name}...",
                            index,
                            len(programs)
                        )

                        scanner = LeftoverScanner()
                        leftovers = scanner.scan(program)
                        result.leftovers_found += len(leftovers)

                        # Clean leftovers if requested and found
                        if clean_leftovers and leftovers:
                            self._report_progress(
                                f"Cleaning {len(leftovers)} leftovers...",
                                index,
                                len(programs)
                            )

                            cleaner = Cleaner(create_backup=create_backup)
                            clean_result = cleaner.clean(leftovers)
                            result.leftovers_cleaned += clean_result.deleted_items

                else:
                    result.failed += 1
                    error_msg = uninstall_result.error_message or "Unknown error"
                    result.errors.append((program.name, error_msg))
                    self.logger.error(f"Failed to uninstall {program.name}: {error_msg}")

            except Exception as e:
                result.failed += 1
                result.errors.append((program.name, str(e)))
                self.logger.error(f"Error uninstalling {program.name}: {e}")

        result.end_time = datetime.now()

        self.logger.log_operation_end(
            "Batch Uninstall",
            result.failed == 0,
            f"Success: {result.successful}, Failed: {result.failed}, " +
            f"Leftovers cleaned: {result.leftovers_cleaned}"
        )

        return result

    def _report_progress(self, message: str, current: int, total: int):
        """
        Report progress via callback.

        Args:
            message: Progress message
            current: Current item number
            total: Total items
        """
        if self.progress_callback:
            try:
                self.progress_callback(message, current, total)
            except Exception as e:
                self.logger.warning(f"Error in progress callback: {e}")

    def print_result(self, result: BatchUninstallResult):
        """
        Print batch uninstall result summary.

        Args:
            result: BatchUninstallResult object
        """
        print("\n" + "=" * 70)
        print("Batch Uninstall Result")
        print("=" * 70)
        print(f"Total programs:     {result.total_programs}")
        print(f"Successful:         {result.successful}")
        print(f"Failed:             {result.failed}")
        print(f"Skipped:            {result.skipped}")
        print(f"Leftovers found:    {result.leftovers_found}")
        print(f"Leftovers cleaned:  {result.leftovers_cleaned}")
        print(f"Duration:           {result.duration:.2f} seconds")

        if result.errors:
            print(f"\nErrors ({len(result.errors)}):")
            for program_name, error in result.errors:
                print(f"  - {program_name}")
                print(f"    Error: {error}")

        print("=" * 70)


def uninstall_multiple_programs(
    programs: List[InstalledProgram],
    silent: bool = True,
    create_backup: bool = True,
    scan_leftovers: bool = True,
    clean_leftovers: bool = True,
    progress_callback: Optional[Callable[[str, int, int], None]] = None
) -> BatchUninstallResult:
    """
    Convenience function to uninstall multiple programs.

    Args:
        programs: List of programs to uninstall
        silent: Use silent uninstallation
        create_backup: Create backups before uninstalling
        scan_leftovers: Scan for leftovers after each uninstall
        clean_leftovers: Clean leftovers automatically
        progress_callback: Callback function(message, current, total)

    Returns:
        BatchUninstallResult object
    """
    batch = BatchUninstaller(progress_callback)
    return batch.uninstall_multiple(
        programs,
        silent,
        create_backup,
        scan_leftovers,
        clean_leftovers
    )

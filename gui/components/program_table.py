"""
Program table management component.
Handles table creation, population, filtering, and sorting.
"""

from typing import List, Optional, Final
from PyQt6.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView, QMenu
from PyQt6.QtGui import QAction
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QObject

from core.registry import InstalledProgram
from utils.icon_extractor import get_program_icon

# Constants for table columns
COLUMN_CHECKBOX: Final[int] = 0
COLUMN_ICON: Final[int] = 1
COLUMN_NAME: Final[int] = 2
COLUMN_VERSION: Final[int] = 3
COLUMN_PUBLISHER: Final[int] = 4
COLUMN_SIZE: Final[int] = 5
COLUMN_INSTALL_DATE: Final[int] = 6

# UI Constants
CHECKBOX_COLUMN_WIDTH: Final[int] = 40
ICON_COLUMN_WIDTH: Final[int] = 40
DEFAULT_ROW_HEIGHT: Final[int] = 36
ICON_SIZE: Final[int] = 32


class ProgramTableManager(QObject):
    """
    Manages the program list table.

    Responsibilities:
    - Table initialization and configuration
    - Data population
    - Filtering and sorting
    - Checkbox management
    - Context menu and quick actions

    Signals:
        open_folder_requested: Open program's installation folder
        run_program_requested: Run the program
        open_website_requested: Open program's website
    """

    # Signals for quick actions
    open_folder_requested = pyqtSignal(InstalledProgram)
    run_program_requested = pyqtSignal(InstalledProgram)
    open_website_requested = pyqtSignal(InstalledProgram)

    def __init__(self, table_widget: QTableWidget, parent=None):
        """
        Initialize the table manager.

        Args:
            table_widget: QTableWidget to manage
            parent: Parent QObject
        """
        super().__init__(parent)
        self.table = table_widget
        self.programs: List[InstalledProgram] = []
        self.filtered_programs: List[InstalledProgram] = []

        self._configure_table()
        self._setup_context_menu()

    def _configure_table(self) -> None:
        """Configure table settings."""
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "☐", "", "プログラム名", "バージョン", "発行元", "サイズ (KB)", "インストール日"
        ])

        # Set column widths
        self.table.setColumnWidth(COLUMN_CHECKBOX, CHECKBOX_COLUMN_WIDTH)
        self.table.setColumnWidth(COLUMN_ICON, ICON_COLUMN_WIDTH)

        # Make program name column stretch
        self.table.horizontalHeader().setSectionResizeMode(
            COLUMN_NAME, QHeaderView.ResizeMode.Stretch
        )

        # Set row height for icons
        self.table.verticalHeader().setDefaultSectionSize(DEFAULT_ROW_HEIGHT)

        # Hide vertical header (row numbers)
        self.table.verticalHeader().setVisible(False)

        # Selection behavior
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)

        # Enable icon rendering
        self.table.setIconSize(QSize(ICON_SIZE, ICON_SIZE))

        # Enable sorting
        self.table.setSortingEnabled(True)

    def set_programs(self, programs: List[InstalledProgram]) -> None:
        """
        Set the programs list.

        Args:
            programs: List of InstalledProgram objects
        """
        self.programs = programs
        self.filtered_programs = programs.copy()
        self.populate_table()

    def populate_table(self) -> None:
        """Populate the table with filtered programs."""
        # Disable sorting while populating to avoid issues
        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)

        for program in self.filtered_programs:
            row = self.table.rowCount()
            self.table.insertRow(row)

            # Checkbox
            checkbox_item = QTableWidgetItem()
            checkbox_item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            checkbox_item.setCheckState(Qt.CheckState.Unchecked)
            self.table.setItem(row, COLUMN_CHECKBOX, checkbox_item)

            # Icon
            icon = get_program_icon(program)
            icon_item = QTableWidgetItem()
            icon_item.setIcon(icon)
            self.table.setItem(row, COLUMN_ICON, icon_item)

            # Name
            self.table.setItem(row, COLUMN_NAME, QTableWidgetItem(program.name))

            # Version
            version = program.version or "不明"
            self.table.setItem(row, COLUMN_VERSION, QTableWidgetItem(version))

            # Publisher
            publisher = program.publisher or "不明"
            self.table.setItem(row, COLUMN_PUBLISHER, QTableWidgetItem(publisher))

            # Size (use DisplayRole for proper sorting)
            size_item = QTableWidgetItem()
            size_item.setData(Qt.ItemDataRole.DisplayRole, program.estimated_size or 0)
            self.table.setItem(row, COLUMN_SIZE, size_item)

            # Install date
            install_date = program.install_date or "不明"
            self.table.setItem(row, COLUMN_INSTALL_DATE, QTableWidgetItem(install_date))

        # Re-enable sorting after population
        self.table.setSortingEnabled(True)

    def filter_programs(self, search_text: str) -> int:
        """
        Filter programs by search text.

        Args:
            search_text: Search text

        Returns:
            Number of filtered programs
        """
        if not search_text:
            self.filtered_programs = self.programs.copy()
        else:
            text_lower = search_text.lower()
            self.filtered_programs = [
                p for p in self.programs
                if text_lower in p.name.lower() or
                   (p.publisher and text_lower in p.publisher.lower())
            ]

        self.populate_table()
        return len(self.filtered_programs)

    def sort_programs(self, sort_by: str) -> None:
        """
        Sort programs by specified field.

        Args:
            sort_by: Sort field ("名前", "サイズ", "インストール日")
        """
        if sort_by == "名前":
            self.filtered_programs.sort(key=lambda p: p.name.lower())
        elif sort_by == "サイズ":
            self.filtered_programs.sort(key=lambda p: p.estimated_size or 0, reverse=True)
        elif sort_by == "インストール日":
            self.filtered_programs.sort(key=lambda p: p.install_date or "", reverse=True)

        self.populate_table()

    def get_checked_programs(self) -> List[InstalledProgram]:
        """
        Get list of checked programs.

        Returns:
            List of checked InstalledProgram objects
        """
        checked_programs: List[InstalledProgram] = []
        for row in range(self.table.rowCount()):
            checkbox_item = self.table.item(row, COLUMN_CHECKBOX)
            if checkbox_item and checkbox_item.checkState() == Qt.CheckState.Checked:
                # Get program name from name column
                name_item = self.table.item(row, COLUMN_NAME)
                if name_item:
                    program_name = name_item.text()
                    # Find program in filtered_programs
                    for program in self.filtered_programs:
                        if program.name == program_name:
                            checked_programs.append(program)
                            break
        return checked_programs

    def get_checked_programs_count(self) -> int:
        """
        Get count of checked programs.

        Returns:
            Number of checked programs
        """
        count = 0
        for row in range(self.table.rowCount()):
            checkbox_item = self.table.item(row, COLUMN_CHECKBOX)
            if checkbox_item and checkbox_item.checkState() == Qt.CheckState.Checked:
                count += 1
        return count

    def toggle_all_checkboxes(self) -> None:
        """Toggle all checkboxes (select all or deselect all)."""
        # Check if any are unchecked
        has_unchecked = False
        for row in range(self.table.rowCount()):
            checkbox_item = self.table.item(row, COLUMN_CHECKBOX)
            if checkbox_item and checkbox_item.checkState() == Qt.CheckState.Unchecked:
                has_unchecked = True
                break

        # Set all to checked if any are unchecked, otherwise uncheck all
        new_state = Qt.CheckState.Checked if has_unchecked else Qt.CheckState.Unchecked

        # Block signals to avoid multiple updates
        self.table.blockSignals(True)
        for row in range(self.table.rowCount()):
            checkbox_item = self.table.item(row, COLUMN_CHECKBOX)
            if checkbox_item:
                checkbox_item.setCheckState(new_state)
        self.table.blockSignals(False)

    def get_selected_program(self) -> Optional[InstalledProgram]:
        """
        Get currently selected program.

        Returns:
            Selected InstalledProgram or None
        """
        selected_items = self.table.selectedItems()
        if not selected_items:
            return None

        row = selected_items[0].row()
        if 0 <= row < len(self.filtered_programs):
            return self.filtered_programs[row]
        return None

    def clear(self) -> None:
        """Clear the table and reset program lists."""
        self.table.setRowCount(0)
        self.programs = []
        self.filtered_programs = []

    def _setup_context_menu(self) -> None:
        """Set up context menu for the table."""
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)

    def _show_context_menu(self, position) -> None:
        """
        Show context menu at the given position.

        Args:
            position: Position where menu should be shown
        """
        # Get the program at the clicked row
        item = self.table.itemAt(position)
        if not item:
            return

        row = item.row()
        if row < 0 or row >= len(self.filtered_programs):
            return

        program = self.filtered_programs[row]

        # Create context menu
        menu = QMenu(self.table)

        # Open folder action
        if program.install_location:
            open_folder_action = QAction("フォルダを開く(&F)", self.table)
            open_folder_action.triggered.connect(lambda: self.open_folder_requested.emit(program))
            menu.addAction(open_folder_action)

        # Run program action
        if self._can_run_program(program):
            run_program_action = QAction("プログラムを実行(&R)", self.table)
            run_program_action.triggered.connect(lambda: self.run_program_requested.emit(program))
            menu.addAction(run_program_action)

        # Open website action
        if program.publisher:
            open_website_action = QAction("ウェブサイトを開く(&W)", self.table)
            open_website_action.triggered.connect(lambda: self.open_website_requested.emit(program))
            menu.addAction(open_website_action)

        # Show menu if it has actions
        if not menu.isEmpty():
            menu.addSeparator()
            # Add program info at the bottom
            info_action = QAction(f"プログラム: {program.name}", self.table)
            info_action.setEnabled(False)
            menu.addAction(info_action)

            menu.exec(self.table.viewport().mapToGlobal(position))

    def _can_run_program(self, program: InstalledProgram) -> bool:
        """
        Check if a program can be executed.

        Args:
            program: InstalledProgram to check

        Returns:
            True if program has an executable path
        """
        # Check if we can extract an executable from display_icon or install_location
        if program.display_icon and program.display_icon.lower().endswith('.exe'):
            return True
        if program.install_location:
            return True
        return False

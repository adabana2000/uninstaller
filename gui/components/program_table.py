"""
Program table management component.
Handles table creation, population, filtering, and sorting.
"""

from typing import List, Optional
from PyQt6.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView
from PyQt6.QtCore import Qt, QSize

from core.registry import InstalledProgram
from utils.icon_extractor import get_program_icon


class ProgramTableManager:
    """
    Manages the program list table.

    Responsibilities:
    - Table initialization and configuration
    - Data population
    - Filtering and sorting
    - Checkbox management
    """

    def __init__(self, table_widget: QTableWidget):
        """
        Initialize the table manager.

        Args:
            table_widget: QTableWidget to manage
        """
        self.table = table_widget
        self.programs: List[InstalledProgram] = []
        self.filtered_programs: List[InstalledProgram] = []

        self._configure_table()

    def _configure_table(self):
        """Configure table settings."""
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "☐", "", "プログラム名", "バージョン", "発行元", "サイズ (KB)", "インストール日"
        ])

        # Set column widths
        self.table.setColumnWidth(0, 40)  # Checkbox
        self.table.setColumnWidth(1, 40)  # Icon

        # Make program name column stretch
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)

        # Set row height for icons
        self.table.verticalHeader().setDefaultSectionSize(36)

        # Hide vertical header (row numbers)
        self.table.verticalHeader().setVisible(False)

        # Selection behavior
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)

        # Enable icon rendering
        self.table.setIconSize(QSize(32, 32))

        # Enable sorting
        self.table.setSortingEnabled(True)

    def set_programs(self, programs: List[InstalledProgram]):
        """
        Set the programs list.

        Args:
            programs: List of InstalledProgram objects
        """
        self.programs = programs
        self.filtered_programs = programs.copy()
        self.populate_table()

    def populate_table(self):
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
            self.table.setItem(row, 0, checkbox_item)

            # Icon
            icon = get_program_icon(program)
            icon_item = QTableWidgetItem()
            icon_item.setIcon(icon)
            self.table.setItem(row, 1, icon_item)

            # Name
            self.table.setItem(row, 2, QTableWidgetItem(program.name))

            # Version
            version = program.version or "不明"
            self.table.setItem(row, 3, QTableWidgetItem(version))

            # Publisher
            publisher = program.publisher or "不明"
            self.table.setItem(row, 4, QTableWidgetItem(publisher))

            # Size (use DisplayRole for proper sorting)
            size_item = QTableWidgetItem()
            size_item.setData(Qt.ItemDataRole.DisplayRole, program.estimated_size or 0)
            self.table.setItem(row, 5, size_item)

            # Install date
            install_date = program.install_date or "不明"
            self.table.setItem(row, 6, QTableWidgetItem(install_date))

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

    def sort_programs(self, sort_by: str):
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
        checked_programs = []
        for row in range(self.table.rowCount()):
            checkbox_item = self.table.item(row, 0)
            if checkbox_item and checkbox_item.checkState() == Qt.CheckState.Checked:
                # Get program name from column 2
                name_item = self.table.item(row, 2)
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
            checkbox_item = self.table.item(row, 0)
            if checkbox_item and checkbox_item.checkState() == Qt.CheckState.Checked:
                count += 1
        return count

    def toggle_all_checkboxes(self):
        """Toggle all checkboxes (select all or deselect all)."""
        # Check if any are unchecked
        has_unchecked = False
        for row in range(self.table.rowCount()):
            checkbox_item = self.table.item(row, 0)
            if checkbox_item and checkbox_item.checkState() == Qt.CheckState.Unchecked:
                has_unchecked = True
                break

        # Set all to checked if any are unchecked, otherwise uncheck all
        new_state = Qt.CheckState.Checked if has_unchecked else Qt.CheckState.Unchecked

        # Block signals to avoid multiple updates
        self.table.blockSignals(True)
        for row in range(self.table.rowCount()):
            checkbox_item = self.table.item(row, 0)
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

    def clear(self):
        """Clear the table."""
        self.table.setRowCount(0)
        self.programs = []
        self.filtered_programs = []

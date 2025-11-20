"""
Search bar component.
Handles search and sort controls.
"""

from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QLineEdit, QComboBox, QPushButton
from PyQt6.QtCore import pyqtSignal


class SearchBarComponent(QWidget):
    """
    Search and sort control bar.

    Signals:
        search_changed: Emitted when search text changes
        sort_changed: Emitted when sort option changes
        refresh_clicked: Emitted when refresh button is clicked
    """

    # Signals
    search_changed = pyqtSignal(str)  # search text
    sort_changed = pyqtSignal(str)    # sort option
    refresh_clicked = pyqtSignal()

    def __init__(self, parent=None):
        """
        Initialize the search bar.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        """Initialize the UI components."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Search label and box
        self.search_label = QLabel("検索:")
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("プログラム名で検索...")
        self.search_box.textChanged.connect(self.search_changed.emit)

        # Sort label and combo
        self.sort_label = QLabel("並び替え:")
        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["名前", "サイズ", "インストール日"])
        self.sort_combo.currentTextChanged.connect(self.sort_changed.emit)

        # Refresh button
        self.refresh_button = QPushButton("更新")
        self.refresh_button.clicked.connect(self.refresh_clicked.emit)

        # Add widgets to layout
        layout.addWidget(self.search_label)
        layout.addWidget(self.search_box, 1)  # Stretch factor 1
        layout.addWidget(self.sort_label)
        layout.addWidget(self.sort_combo)
        layout.addWidget(self.refresh_button)

    def get_search_text(self) -> str:
        """
        Get current search text.

        Returns:
            Search text
        """
        return self.search_box.text()

    def get_sort_option(self) -> str:
        """
        Get current sort option.

        Returns:
            Sort option
        """
        return self.sort_combo.currentText()

    def clear_search(self):
        """Clear the search box."""
        self.search_box.clear()

    def focus_search(self):
        """Focus and select all text in search box."""
        self.search_box.setFocus()
        self.search_box.selectAll()

    def set_refresh_enabled(self, enabled: bool):
        """
        Enable or disable the refresh button.

        Args:
            enabled: Whether to enable the button
        """
        self.refresh_button.setEnabled(enabled)

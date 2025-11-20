"""
Menu bar handler component.
Handles menu bar creation and actions.
"""

from PyQt6.QtWidgets import QMenuBar, QMenu
from PyQt6.QtGui import QAction
from PyQt6.QtCore import QObject, pyqtSignal


class MenuBarHandler(QObject):
    """
    Handles menu bar creation and actions.

    Signals:
        refresh_requested: Refresh program list
        export_requested: Export programs (format: csv/json/html)
        monitor_requested: Show installation monitor
        bg_monitor_settings_requested: Show background monitor settings
        context_menu_requested: Show context menu integration dialog
        stats_requested: Show statistics
        cleanup_requested: Clean up old backups
        about_requested: Show about dialog
        exit_requested: Exit application
    """

    # Signals
    refresh_requested = pyqtSignal()
    export_requested = pyqtSignal(str)  # format: csv, json, html
    monitor_requested = pyqtSignal()
    bg_monitor_settings_requested = pyqtSignal()
    context_menu_requested = pyqtSignal()
    stats_requested = pyqtSignal()
    cleanup_requested = pyqtSignal()
    about_requested = pyqtSignal()
    exit_requested = pyqtSignal()

    def __init__(self, menubar: QMenuBar, parent=None):
        """
        Initialize the menu handler.

        Args:
            menubar: QMenuBar to populate
            parent: Parent QObject
        """
        super().__init__(parent)
        self.menubar = menubar
        self._create_menus()

    def _create_menus(self):
        """Create all menu items."""
        self._create_file_menu()
        self._create_tools_menu()
        self._create_help_menu()

    def _create_file_menu(self):
        """Create File menu."""
        file_menu = self.menubar.addMenu("ファイル(&F)")

        # Refresh action
        refresh_action = QAction("更新(&R)", self.menubar)
        refresh_action.setShortcut("F5")
        refresh_action.triggered.connect(self.refresh_requested.emit)
        file_menu.addAction(refresh_action)

        file_menu.addSeparator()

        # Export submenu
        export_menu = file_menu.addMenu("エクスポート(&E)")

        export_csv_action = QAction("CSV形式(&C)", self.menubar)
        export_csv_action.triggered.connect(lambda: self.export_requested.emit("csv"))
        export_menu.addAction(export_csv_action)

        export_json_action = QAction("JSON形式(&J)", self.menubar)
        export_json_action.triggered.connect(lambda: self.export_requested.emit("json"))
        export_menu.addAction(export_json_action)

        export_html_action = QAction("HTML形式(&H)", self.menubar)
        export_html_action.triggered.connect(lambda: self.export_requested.emit("html"))
        export_menu.addAction(export_html_action)

        file_menu.addSeparator()

        # Exit action
        exit_action = QAction("終了(&X)", self.menubar)
        exit_action.setShortcut("Alt+F4")
        exit_action.triggered.connect(self.exit_requested.emit)
        file_menu.addAction(exit_action)

    def _create_tools_menu(self):
        """Create Tools menu."""
        tools_menu = self.menubar.addMenu("ツール(&T)")

        # Installation monitor
        monitor_action = QAction("インストールモニター(&M)", self.menubar)
        monitor_action.triggered.connect(self.monitor_requested.emit)
        tools_menu.addAction(monitor_action)

        # Background monitor settings
        bg_monitor_action = QAction("バックグラウンドモニター設定(&B)", self.menubar)
        bg_monitor_action.triggered.connect(self.bg_monitor_settings_requested.emit)
        tools_menu.addAction(bg_monitor_action)

        # Context menu integration
        context_menu_action = QAction("右クリックメニュー統合(&R)", self.menubar)
        context_menu_action.triggered.connect(self.context_menu_requested.emit)
        tools_menu.addAction(context_menu_action)

        # Statistics
        stats_action = QAction("統計(&S)", self.menubar)
        stats_action.triggered.connect(self.stats_requested.emit)
        tools_menu.addAction(stats_action)

        tools_menu.addSeparator()

        # Cleanup old backups
        cleanup_action = QAction("古いバックアップを削除(&C)", self.menubar)
        cleanup_action.triggered.connect(self.cleanup_requested.emit)
        tools_menu.addAction(cleanup_action)

    def _create_help_menu(self):
        """Create Help menu."""
        help_menu = self.menubar.addMenu("ヘルプ(&H)")

        # About action
        about_action = QAction("バージョン情報(&A)", self.menubar)
        about_action.triggered.connect(self.about_requested.emit)
        help_menu.addAction(about_action)

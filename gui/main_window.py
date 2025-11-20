"""
Main window for the GUI application.
"""

import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QStatusBar, QMessageBox, QSplitter, QTextEdit,
    QProgressBar, QSystemTrayIcon, QMenu, QTableWidget
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QAction, QCloseEvent

from core.registry import RegistryReader, InstalledProgram
from utils.logger import get_logger
from utils.permissions import is_admin
from gui.components import ProgramTableManager, SearchBarComponent, MenuBarHandler
from gui.widgets.uninstall_dialog import UninstallDialog
from gui.widgets.scan_dialog import ScanDialog
from gui.widgets.monitor_dialog import MonitorDialog
from gui.widgets.background_monitor_settings_dialog import BackgroundMonitorSettingsDialog
from gui.widgets.context_menu_dialog import ContextMenuDialog
from core.background_monitor import BackgroundMonitorManager


class ProgramLoaderThread(QThread):
    """Thread for loading installed programs."""

    finished = pyqtSignal(list)
    progress = pyqtSignal(str)

    def run(self):
        """Load programs in background."""
        self.progress.emit("レジストリをスキャン中...")
        reader = RegistryReader()
        programs = reader.get_installed_programs()
        self.progress.emit(f"{len(programs)}個のプログラムを検出")
        self.finished.emit(programs)


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self):
        super().__init__()
        self.logger = get_logger()
        self.selected_program = None

        # Components will be initialized in init_ui
        self.table_manager = None
        self.search_bar = None
        self.menu_handler = None

        self.init_ui()
        self.init_system_tray()
        self.init_background_monitor()
        self.load_programs()

    def init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("Windows Uninstaller")
        self.setGeometry(100, 100, 1200, 700)

        # Create menu bar with handler
        self.menu_handler = MenuBarHandler(self.menuBar(), self)
        self._connect_menu_signals()

        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout
        main_layout = QVBoxLayout(central_widget)

        # Search bar component
        self.search_bar = SearchBarComponent()
        self.search_bar.search_changed.connect(self.on_search_changed)
        self.search_bar.sort_changed.connect(self.on_sort_changed)
        self.search_bar.refresh_clicked.connect(self.load_programs)
        main_layout.addWidget(self.search_bar)

        # Splitter for table and details
        splitter = QSplitter(Qt.Orientation.Vertical)

        # Program table with manager
        self.program_table = QTableWidget()
        self.table_manager = ProgramTableManager(self.program_table)
        self.program_table.itemSelectionChanged.connect(self.on_selection_changed)
        self.program_table.itemChanged.connect(self.on_item_changed)

        splitter.addWidget(self.program_table)

        # Details panel
        details_widget = QWidget()
        details_layout = QVBoxLayout(details_widget)

        details_label = QLabel("詳細情報")
        details_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        details_layout.addWidget(details_label)

        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        self.details_text.setMaximumHeight(200)
        details_layout.addWidget(self.details_text)

        # Action buttons
        button_layout = QHBoxLayout()

        self.uninstall_button = QPushButton("アンインストール")
        self.uninstall_button.setEnabled(False)
        self.uninstall_button.clicked.connect(self.uninstall_program)

        self.batch_uninstall_button = QPushButton("選択項目をアンインストール")
        self.batch_uninstall_button.setEnabled(False)
        self.batch_uninstall_button.clicked.connect(self.batch_uninstall_programs)

        self.scan_button = QPushButton("残留物スキャン")
        self.scan_button.setEnabled(False)
        self.scan_button.clicked.connect(self.scan_leftovers)

        button_layout.addWidget(self.uninstall_button)
        button_layout.addWidget(self.batch_uninstall_button)
        button_layout.addWidget(self.scan_button)
        button_layout.addStretch()

        details_layout.addLayout(button_layout)

        splitter.addWidget(details_widget)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)

        main_layout.addWidget(splitter)

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        # Progress bar (hidden by default)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.status_bar.addPermanentWidget(self.progress_bar)

        # Admin status
        if is_admin():
            self.status_bar.showMessage("✓ 管理者権限で実行中")
        else:
            self.status_bar.showMessage("⚠ 管理者権限なし - 一部機能が制限されます")

    def init_system_tray(self):
        """Initialize system tray icon."""
        # Create system tray icon
        self.tray_icon = QSystemTrayIcon(self)

        # Set icon (use a simple icon for now)
        # In production, you would use a proper icon file
        self.tray_icon.setIcon(self.style().standardIcon(self.style().StandardPixmap.SP_ComputerIcon))

        # Create tray menu
        tray_menu = QMenu()

        # Show/Hide action
        show_action = QAction("表示", self)
        show_action.triggered.connect(self.show_from_tray)
        tray_menu.addAction(show_action)

        # Refresh action
        refresh_action = QAction("更新", self)
        refresh_action.triggered.connect(self.load_programs)
        tray_menu.addAction(refresh_action)

        tray_menu.addSeparator()

        # Background monitor settings
        bg_monitor_action = QAction("バックグラウンドモニター設定", self)
        bg_monitor_action.triggered.connect(self.show_background_monitor_settings)
        tray_menu.addAction(bg_monitor_action)

        tray_menu.addSeparator()

        # Exit action
        exit_action = QAction("終了", self)
        exit_action.triggered.connect(self.quit_application)
        tray_menu.addAction(exit_action)

        # Set menu
        self.tray_icon.setContextMenu(tray_menu)

        # Double click to show window
        self.tray_icon.activated.connect(self.on_tray_activated)

        # Set tooltip
        self.tray_icon.setToolTip("Windows Uninstaller")

        # Show tray icon
        self.tray_icon.show()

    def on_tray_activated(self, reason):
        """Handle tray icon activation."""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show_from_tray()

    def show_from_tray(self):
        """Show window from system tray."""
        self.show()
        self.setWindowState(self.windowState() & ~Qt.WindowState.WindowMinimized | Qt.WindowState.WindowActive)
        self.activateWindow()
        self.raise_()

    def quit_application(self):
        """Quit application completely."""
        # Stop background monitor
        try:
            monitor = BackgroundMonitorManager.get_instance()
            if monitor.is_running():
                monitor.stop()
                self.logger.info("Background monitor stopped on exit")
        except Exception as e:
            self.logger.error(f"Error stopping background monitor: {e}")

        self.tray_icon.hide()
        QApplication.quit()

    def _connect_menu_signals(self):
        """Connect menu bar signals to handlers."""
        self.menu_handler.refresh_requested.connect(self.load_programs)
        self.menu_handler.export_requested.connect(self.export_programs)
        self.menu_handler.monitor_requested.connect(self.show_monitor)
        self.menu_handler.bg_monitor_settings_requested.connect(self.show_background_monitor_settings)
        self.menu_handler.context_menu_requested.connect(self.show_context_menu_dialog)
        self.menu_handler.stats_requested.connect(self.show_statistics)
        self.menu_handler.cleanup_requested.connect(self.cleanup_backups)
        self.menu_handler.about_requested.connect(self.show_about)
        self.menu_handler.exit_requested.connect(self.close)

    def init_background_monitor(self):
        """Initialize background monitor with callback."""
        def on_installation_detected(program_name: str):
            """Handle new installation detection."""
            self.logger.info(f"New installation detected: {program_name}")

            # Show tray notification
            if hasattr(self, 'tray_icon'):
                self.tray_icon.showMessage(
                    "新しいインストールを検知",
                    f"プログラム: {program_name}\n\n自動的に記録されました。",
                    QSystemTrayIcon.MessageIcon.Information,
                    5000
                )

        # Initialize monitor (singleton)
        try:
            self.background_monitor = BackgroundMonitorManager.get_instance(on_installation_detected)

            # Start if enabled in config
            from utils.config import ConfigManager
            config = ConfigManager()
            if config.get('monitor.enabled', False):
                if not self.background_monitor.is_running():
                    self.background_monitor.start()
                    self.logger.info("Background monitor started on app launch")

        except Exception as e:
            self.logger.error(f"Failed to initialize background monitor: {e}")

    def load_programs(self):
        """Load installed programs."""
        self.status_bar.showMessage("プログラムを読み込み中...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate

        # Disable controls
        self.search_bar.set_refresh_enabled(False)

        # Start loading thread
        self.loader_thread = ProgramLoaderThread()
        self.loader_thread.finished.connect(self.on_programs_loaded)
        self.loader_thread.progress.connect(self.status_bar.showMessage)
        self.loader_thread.start()

    def on_programs_loaded(self, programs):
        """Called when programs are loaded."""
        self.table_manager.set_programs(programs)

        self.progress_bar.setVisible(False)
        self.search_bar.set_refresh_enabled(True)
        self.status_bar.showMessage(f"{len(programs)}個のプログラムを読み込みました", 3000)

    def on_search_changed(self, text):
        """Handle search text changes."""
        count = self.table_manager.filter_programs(text)
        self.status_bar.showMessage(f"{count}個のプログラムを表示中", 3000)

    def on_sort_changed(self, sort_by):
        """Handle sort option changes."""
        self.table_manager.sort_programs(sort_by)

    def on_item_changed(self, item):
        """Called when an item changes (e.g., checkbox state)."""
        # Update button states when checkbox is toggled
        if item.column() == 0:  # Checkbox column
            self.update_button_states()

    def update_button_states(self):
        """Update button states based on checked items."""
        checked_count = self.table_manager.get_checked_programs_count()
        self.batch_uninstall_button.setEnabled(checked_count > 0)
        if checked_count > 0:
            self.batch_uninstall_button.setText(f"選択項目をアンインストール ({checked_count})")
        else:
            self.batch_uninstall_button.setText("選択項目をアンインストール")

    def on_selection_changed(self):
        """Called when selection changes."""
        # Get selected program
        self.selected_program = self.table_manager.get_selected_program()

        if not self.selected_program:
            self.details_text.clear()
            self.uninstall_button.setEnabled(False)
            self.scan_button.setEnabled(False)
        else:
            # Update details
            details = f"""
<b>プログラム名:</b> {self.selected_program.name}<br>
<b>バージョン:</b> {self.selected_program.version or '不明'}<br>
<b>発行元:</b> {self.selected_program.publisher or '不明'}<br>
<b>インストール日:</b> {self.selected_program.install_date or '不明'}<br>
<b>インストール場所:</b> {self.selected_program.install_location or '不明'}<br>
<b>サイズ:</b> {self.selected_program.estimated_size or 0} KB<br>
<b>アーキテクチャ:</b> {self.selected_program.architecture}<br>
<b>アンインストール文字列:</b> {self.selected_program.uninstall_string or '不明'}<br>
<b>レジストリキー:</b> {self.selected_program.registry_key or '不明'}<br>
            """
            self.details_text.setHtml(details)

            # Enable buttons
            self.uninstall_button.setEnabled(True)
            self.scan_button.setEnabled(True)

        # Update batch uninstall button
        self.update_button_states()

    def uninstall_program(self):
        """Uninstall selected program."""
        if not self.selected_program:
            return

        # Check admin privileges
        if not is_admin():
            QMessageBox.warning(
                self,
                "権限不足",
                "アンインストールには管理者権限が必要です。\n"
                "アプリケーションを管理者として実行してください。"
            )
            return

        # Show uninstall dialog
        dialog = UninstallDialog(self.selected_program, self)
        dialog.exec()

        # Reload programs after dialog closes
        self.load_programs()

    def scan_leftovers(self):
        """Scan for leftovers of selected program."""
        if not self.selected_program:
            return

        # Show scan dialog
        dialog = ScanDialog(self.selected_program, self)
        dialog.exec()

    def batch_uninstall_programs(self):
        """Batch uninstall checked programs."""
        checked_programs = self.table_manager.get_checked_programs()

        if not checked_programs:
            return

        # Check admin privileges
        if not is_admin():
            QMessageBox.warning(
                self,
                "権限不足",
                "アンインストールには管理者権限が必要です。\n"
                "アプリケーションを管理者として実行してください。"
            )
            return

        # Confirm
        reply = QMessageBox.question(
            self,
            "確認",
            f"{len(checked_programs)}個のプログラムをアンインストールします。\n"
            "この操作は取り消せません。続行しますか？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        # Import batch uninstall dialog
        from gui.widgets.batch_uninstall_dialog import BatchUninstallDialog

        # Show batch uninstall dialog
        dialog = BatchUninstallDialog(checked_programs, self)
        dialog.exec()

        # Reload programs after dialog closes
        self.load_programs()

    def cleanup_backups(self):
        """Clean up old backups."""
        from utils.backup import BackupManager

        reply = QMessageBox.question(
            self,
            "確認",
            "30日以上前のバックアップを削除しますか？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            manager = BackupManager()
            deleted = manager.cleanup_old_backups(30)

            QMessageBox.information(
                self,
                "完了",
                f"{deleted}個のバックアップを削除しました。"
            )

    def show_monitor(self):
        """Show installation monitor dialog."""
        dialog = MonitorDialog(self)
        dialog.exec()

    def show_statistics(self):
        """Show statistics dialog."""
        from utils.statistics import get_statistics

        stats = get_statistics()
        summary = stats.get_summary()

        report = f"""
<h2>統計情報</h2>

<h3>概要</h3>
<table>
<tr><td><b>総アンインストール数:</b></td><td>{summary['total_uninstalls']}</td></tr>
<tr><td><b>成功:</b></td><td>{summary['successful_uninstalls']}</td></tr>
<tr><td><b>失敗:</b></td><td>{summary['failed_uninstalls']}</td></tr>
<tr><td><b>成功率:</b></td><td>{summary['success_rate']:.1f}%</td></tr>
</table>

<h3>クリーンアップ結果</h3>
<table>
<tr><td><b>解放された容量:</b></td><td>{summary['total_space_freed_mb']:.2f} MB</td></tr>
<tr><td><b>削除されたファイル:</b></td><td>{summary['total_files_removed']:,}</td></tr>
<tr><td><b>削除されたレジストリキー:</b></td><td>{summary['total_registry_removed']:,}</td></tr>
</table>

<h3>パフォーマンス</h3>
<table>
<tr><td><b>平均所要時間:</b></td><td>{summary['average_duration_seconds']:.1f} 秒</td></tr>
</table>

<h3>最近のアクティビティ</h3>
<table>
<tr><td><b>過去7日間:</b></td><td>{summary['recent_uninstalls_7days']} 個</td></tr>
<tr><td><b>過去30日間:</b></td><td>{summary['recent_uninstalls_30days']} 個</td></tr>
</table>
        """

        msg = QMessageBox(self)
        msg.setWindowTitle("統計情報")
        msg.setTextFormat(Qt.TextFormat.RichText)
        msg.setText(report)
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.exec()

    def export_programs(self, format_type: str):
        """Export programs list to file."""
        from utils.exporter import get_exporter

        if not self.programs:
            QMessageBox.warning(
                self,
                "エクスポートエラー",
                "エクスポートするプログラムがありません。"
            )
            return

        try:
            exporter = get_exporter()

            if format_type == "csv":
                file_path = exporter.export_programs_csv(self.programs)
            elif format_type == "json":
                file_path = exporter.export_programs_json(self.programs)
            elif format_type == "html":
                file_path = exporter.export_programs_html(self.programs)
            else:
                return

            QMessageBox.information(
                self,
                "エクスポート完了",
                f"プログラム一覧をエクスポートしました:\n{file_path}"
            )

        except Exception as e:
            QMessageBox.critical(
                self,
                "エクスポートエラー",
                f"エクスポート中にエラーが発生しました:\n{str(e)}"
            )

    def changeEvent(self, event):
        """Handle window state changes."""
        if event.type() == event.Type.WindowStateChange:
            # Hide to tray when minimized
            if self.windowState() & Qt.WindowState.WindowMinimized:
                self.hide()
                self.tray_icon.showMessage(
                    "Windows Uninstaller",
                    "アプリケーションはシステムトレイに最小化されました",
                    QSystemTrayIcon.MessageIcon.Information,
                    2000
                )
                event.ignore()
                return
        super().changeEvent(event)

    def closeEvent(self, event: QCloseEvent):
        """Handle close event."""
        # Ask user if they want to minimize to tray or exit
        reply = QMessageBox.question(
            self,
            "確認",
            "アプリケーションを終了しますか？\n\n"
            "「いいえ」を選択するとシステムトレイに最小化されます。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            # Exit application
            self.tray_icon.hide()
            event.accept()
        elif reply == QMessageBox.StandardButton.No:
            # Minimize to tray
            self.hide()
            self.tray_icon.showMessage(
                "Windows Uninstaller",
                "アプリケーションはシステムトレイに最小化されました",
                QSystemTrayIcon.MessageIcon.Information,
                2000
            )
            event.ignore()
        else:
            # Cancel
            event.ignore()

    def keyPressEvent(self, event):
        """Handle key press events."""
        from PyQt6.QtGui import QKeyEvent
        from PyQt6.QtCore import Qt

        # Delete key - Uninstall selected program
        if event.key() == Qt.Key.Key_Delete:
            if self.selected_program and self.uninstall_button.isEnabled():
                self.uninstall_program()
            elif self.table_manager.get_checked_programs_count() > 0:
                self.batch_uninstall_programs()

        # F5 - Refresh program list
        elif event.key() == Qt.Key.Key_F5:
            self.load_programs()

        # Ctrl+F - Focus search box
        elif event.key() == Qt.Key.Key_F and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self.search_bar.focus_search()

        # Ctrl+A - Select/check all items
        elif event.key() == Qt.Key.Key_A and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self.toggle_all_checkboxes()

        # Escape - Clear search
        elif event.key() == Qt.Key.Key_Escape:
            if self.search_bar.get_search_text():
                self.search_bar.clear_search()
            else:
                super().keyPressEvent(event)

        else:
            super().keyPressEvent(event)

    def toggle_all_checkboxes(self):
        """Toggle all checkboxes (select all or deselect all)."""
        self.table_manager.toggle_all_checkboxes()
        self.update_button_states()

    def show_background_monitor_settings(self):
        """Show background monitor settings dialog."""
        dialog = BackgroundMonitorSettingsDialog(self)
        dialog.exec()

        # Refresh program list after settings change
        # (in case monitor detected new programs while dialog was open)
        self.load_programs()

    def show_context_menu_dialog(self):
        """Show context menu integration dialog."""
        dialog = ContextMenuDialog(self)
        dialog.exec()

    def show_about(self):
        """Show about dialog."""
        QMessageBox.about(
            self,
            "バージョン情報",
            "<h2>Windows Uninstaller</h2>"
            "<p>バージョン: 0.7.0 (Phase 7 完了)</p>"
            "<p>IObit Uninstallerのような高機能なアンインストーラー</p>"
            "<p><b>機能:</b></p>"
            "<ul>"
            "<li>完全なアンインストール</li>"
            "<li>残留物の検出と削除</li>"
            "<li>自動バックアップ</li>"
            "<li>グラフィカルユーザーインターフェイス (GUI)</li>"
            "<li>インストールモニター</li>"
            "<li>バックグラウンドモニター (常駐型インストール検知)</li>"
            "<li>統計とレポート</li>"
            "<li>エクスポート機能 (CSV/JSON/HTML)</li>"
            "<li>バッチアンインストール (複数選択)</li>"
            "<li>テーブルヘッダークリックソート</li>"
            "<li>キーボードショートカット対応</li>"
            "<li>システムトレイ統合</li>"
            "<li>右クリックメニュー統合 (エクスプローラーから直接アンインストール)</li>"
            "</ul>"
        )


def launch_gui():
    """Launch the GUI application."""
    app = QApplication(sys.argv)
    app.setStyle("Fusion")  # Modern look

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


def launch_gui_with_file(file_path: str):
    """
    Launch the GUI application and attempt to uninstall program from file path.

    This is called when the application is launched from Windows Explorer context menu.

    Args:
        file_path: Path to the executable or shortcut file
    """
    from utils.program_finder import find_program_from_file

    app = QApplication(sys.argv)
    app.setStyle("Fusion")  # Modern look

    # Find the program
    program = find_program_from_file(file_path)

    if not program:
        # Show error message
        QMessageBox.critical(
            None,
            "プログラムが見つかりません",
            f"このファイルに対応するインストール済みプログラムが見つかりませんでした:\n\n{file_path}\n\n"
            "通常のアンインストール方法を使用してください。"
        )
        sys.exit(1)

    # Launch main window
    window = MainWindow()
    window.show()

    # Select the program in the table
    for row in range(window.program_table.rowCount()):
        # Column 2 is the program name column (after checkbox and icon)
        name_item = window.program_table.item(row, 2)
        if name_item and name_item.text() == program.name:
            window.program_table.selectRow(row)
            window.selected_program = program
            window.update_details()
            window.update_button_states()
            break

    # Show confirmation dialog
    reply = QMessageBox.question(
        window,
        "アンインストール確認",
        f"次のプログラムをアンインストールしますか？\n\n{program.name}\n\n"
        f"発行元: {program.publisher or '不明'}\n"
        f"バージョン: {program.version or '不明'}",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
    )

    if reply == QMessageBox.StandardButton.Yes:
        # Start uninstall process
        window.uninstall_program()

    sys.exit(app.exec())


if __name__ == "__main__":
    launch_gui()

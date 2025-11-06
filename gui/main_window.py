"""
Main window for the GUI application.
"""

import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QStatusBar, QMessageBox, QSplitter, QTextEdit,
    QComboBox, QProgressBar, QMenuBar, QMenu
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt6.QtGui import QAction, QIcon

from core.registry import RegistryReader, InstalledProgram
from core.uninstaller import Uninstaller
from core.scanner import LeftoverScanner
from core.cleaner import Cleaner
from utils.logger import get_logger
from utils.permissions import is_admin
from utils.icon_extractor import get_program_icon
from gui.widgets.uninstall_dialog import UninstallDialog
from gui.widgets.scan_dialog import ScanDialog
from gui.widgets.monitor_dialog import MonitorDialog


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
        self.programs = []
        self.filtered_programs = []
        self.selected_program = None

        self.init_ui()
        self.load_programs()

    def init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("Windows Uninstaller")
        self.setGeometry(100, 100, 1200, 700)

        # Create menu bar
        self.create_menu_bar()

        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout
        main_layout = QVBoxLayout(central_widget)

        # Top controls
        top_layout = QHBoxLayout()

        # Search box
        self.search_label = QLabel("検索:")
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("プログラム名で検索...")
        self.search_box.textChanged.connect(self.filter_programs)

        # Sort combo
        self.sort_label = QLabel("並び替え:")
        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["名前", "サイズ", "インストール日"])
        self.sort_combo.currentTextChanged.connect(self.sort_programs)

        # Refresh button
        self.refresh_button = QPushButton("更新")
        self.refresh_button.clicked.connect(self.load_programs)

        top_layout.addWidget(self.search_label)
        top_layout.addWidget(self.search_box, 1)
        top_layout.addWidget(self.sort_label)
        top_layout.addWidget(self.sort_combo)
        top_layout.addWidget(self.refresh_button)

        main_layout.addLayout(top_layout)

        # Splitter for table and details
        splitter = QSplitter(Qt.Orientation.Vertical)

        # Program table
        self.program_table = QTableWidget()
        self.program_table.setColumnCount(6)
        self.program_table.setHorizontalHeaderLabels([
            "", "プログラム名", "バージョン", "発行元", "サイズ (KB)", "インストール日"
        ])
        # Set icon column width
        self.program_table.setColumnWidth(0, 40)
        # Make program name column stretch
        self.program_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        # Set row height for icons
        self.program_table.verticalHeader().setDefaultSectionSize(36)
        # Hide vertical header (row numbers)
        self.program_table.verticalHeader().setVisible(False)
        self.program_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.program_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.program_table.itemSelectionChanged.connect(self.on_selection_changed)
        # Enable icon rendering
        self.program_table.setIconSize(QSize(32, 32))

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

        self.scan_button = QPushButton("残留物スキャン")
        self.scan_button.setEnabled(False)
        self.scan_button.clicked.connect(self.scan_leftovers)

        button_layout.addWidget(self.uninstall_button)
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

    def create_menu_bar(self):
        """Create menu bar."""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("ファイル(&F)")

        refresh_action = QAction("更新(&R)", self)
        refresh_action.setShortcut("F5")
        refresh_action.triggered.connect(self.load_programs)
        file_menu.addAction(refresh_action)

        file_menu.addSeparator()

        # Export submenu
        export_menu = file_menu.addMenu("エクスポート(&E)")

        export_csv_action = QAction("CSV形式(&C)", self)
        export_csv_action.triggered.connect(lambda: self.export_programs("csv"))
        export_menu.addAction(export_csv_action)

        export_json_action = QAction("JSON形式(&J)", self)
        export_json_action.triggered.connect(lambda: self.export_programs("json"))
        export_menu.addAction(export_json_action)

        export_html_action = QAction("HTML形式(&H)", self)
        export_html_action.triggered.connect(lambda: self.export_programs("html"))
        export_menu.addAction(export_html_action)

        file_menu.addSeparator()

        exit_action = QAction("終了(&X)", self)
        exit_action.setShortcut("Alt+F4")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Tools menu
        tools_menu = menubar.addMenu("ツール(&T)")

        monitor_action = QAction("インストールモニター(&M)", self)
        monitor_action.triggered.connect(self.show_monitor)
        tools_menu.addAction(monitor_action)

        stats_action = QAction("統計(&S)", self)
        stats_action.triggered.connect(self.show_statistics)
        tools_menu.addAction(stats_action)

        tools_menu.addSeparator()

        cleanup_action = QAction("古いバックアップを削除(&C)", self)
        cleanup_action.triggered.connect(self.cleanup_backups)
        tools_menu.addAction(cleanup_action)

        # Help menu
        help_menu = menubar.addMenu("ヘルプ(&H)")

        about_action = QAction("バージョン情報(&A)", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def load_programs(self):
        """Load installed programs."""
        self.status_bar.showMessage("プログラムを読み込み中...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate

        # Disable controls
        self.refresh_button.setEnabled(False)

        # Start loading thread
        self.loader_thread = ProgramLoaderThread()
        self.loader_thread.finished.connect(self.on_programs_loaded)
        self.loader_thread.progress.connect(self.status_bar.showMessage)
        self.loader_thread.start()

    def on_programs_loaded(self, programs):
        """Called when programs are loaded."""
        self.programs = programs
        self.filtered_programs = programs.copy()
        self.populate_table()

        self.progress_bar.setVisible(False)
        self.refresh_button.setEnabled(True)
        self.status_bar.showMessage(f"{len(programs)}個のプログラムを読み込みました", 3000)

    def populate_table(self):
        """Populate the program table."""
        self.program_table.setRowCount(0)

        for program in self.filtered_programs:
            row = self.program_table.rowCount()
            self.program_table.insertRow(row)

            # Icon
            icon = get_program_icon(program)
            icon_item = QTableWidgetItem()
            icon_item.setIcon(icon)
            self.program_table.setItem(row, 0, icon_item)

            # Name
            self.program_table.setItem(row, 1, QTableWidgetItem(program.name))

            # Version
            version = program.version or "不明"
            self.program_table.setItem(row, 2, QTableWidgetItem(version))

            # Publisher
            publisher = program.publisher or "不明"
            self.program_table.setItem(row, 3, QTableWidgetItem(publisher))

            # Size
            size = str(program.estimated_size) if program.estimated_size else "不明"
            self.program_table.setItem(row, 4, QTableWidgetItem(size))

            # Install date
            install_date = program.install_date or "不明"
            self.program_table.setItem(row, 5, QTableWidgetItem(install_date))

    def filter_programs(self, text):
        """Filter programs by search text."""
        if not text:
            self.filtered_programs = self.programs.copy()
        else:
            text_lower = text.lower()
            self.filtered_programs = [
                p for p in self.programs
                if text_lower in p.name.lower() or
                   (p.publisher and text_lower in p.publisher.lower())
            ]

        self.populate_table()
        self.status_bar.showMessage(f"{len(self.filtered_programs)}個のプログラムを表示中", 3000)

    def sort_programs(self, sort_by):
        """Sort programs."""
        if sort_by == "名前":
            self.filtered_programs.sort(key=lambda p: p.name.lower())
        elif sort_by == "サイズ":
            self.filtered_programs.sort(key=lambda p: p.estimated_size or 0, reverse=True)
        elif sort_by == "インストール日":
            self.filtered_programs.sort(key=lambda p: p.install_date or "", reverse=True)

        self.populate_table()

    def on_selection_changed(self):
        """Called when selection changes."""
        selected_items = self.program_table.selectedItems()
        if not selected_items:
            self.selected_program = None
            self.details_text.clear()
            self.uninstall_button.setEnabled(False)
            self.scan_button.setEnabled(False)
            return

        # Get selected row
        row = selected_items[0].row()
        self.selected_program = self.filtered_programs[row]

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

    def show_about(self):
        """Show about dialog."""
        QMessageBox.about(
            self,
            "バージョン情報",
            "<h2>Windows Uninstaller</h2>"
            "<p>バージョン: 0.6.0 (Phase 6 完了)</p>"
            "<p>IObit Uninstallerのような高機能なアンインストーラー</p>"
            "<p><b>機能:</b></p>"
            "<ul>"
            "<li>完全なアンインストール</li>"
            "<li>残留物の検出と削除</li>"
            "<li>自動バックアップ</li>"
            "<li>グラフィカルユーザーインターフェイス (GUI)</li>"
            "<li>インストールモニター</li>"
            "<li>統計とレポート</li>"
            "<li>エクスポート機能 (CSV/JSON/HTML)</li>"
            "</ul>"
        )


def launch_gui():
    """Launch the GUI application."""
    app = QApplication(sys.argv)
    app.setStyle("Fusion")  # Modern look

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    launch_gui()

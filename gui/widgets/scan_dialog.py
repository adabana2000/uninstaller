"""
Leftover scan dialog for GUI.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QProgressBar, QCheckBox, QMessageBox, QListWidget
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QTextCursor

from core.registry import InstalledProgram
from core.scanner import LeftoverScanner
from core.cleaner import Cleaner
from utils.logger import get_logger


class ScanThread(QThread):
    """Thread for scanning leftovers."""

    progress = pyqtSignal(str)
    finished = pyqtSignal(list)

    def __init__(self, program):
        super().__init__()
        self.program = program

    def run(self):
        """Scan for leftovers."""
        try:
            self.progress.emit("残留物をスキャンしています...")

            scanner = LeftoverScanner()
            leftovers = scanner.scan(self.program)

            self.finished.emit(leftovers)

        except Exception as e:
            self.progress.emit(f"スキャンエラー: {str(e)}")
            self.finished.emit([])


class CleanThread(QThread):
    """Thread for cleaning leftovers."""

    progress = pyqtSignal(str)
    finished = pyqtSignal(bool, int, int)  # success, deleted, failed

    def __init__(self, leftovers, create_backup=True):
        super().__init__()
        self.leftovers = leftovers
        self.create_backup = create_backup

    def run(self):
        """Clean leftovers."""
        try:
            self.progress.emit("残留物を削除しています...")

            cleaner = Cleaner(create_backup=self.create_backup)
            result = cleaner.clean(self.leftovers)

            self.finished.emit(
                result.failed_items == 0,
                result.deleted_items,
                result.failed_items
            )

        except Exception as e:
            self.progress.emit(f"削除エラー: {str(e)}")
            self.finished.emit(False, 0, len(self.leftovers))


class ScanDialog(QDialog):
    """Dialog for scanning leftovers."""

    def __init__(self, program: InstalledProgram, parent=None):
        super().__init__(parent)
        self.program = program
        self.leftovers = []
        self.logger = get_logger()

        self.init_ui()

    def init_ui(self):
        """Initialize UI."""
        self.setWindowTitle(f"残留物スキャン - {self.program.name}")
        self.setMinimumSize(700, 600)

        layout = QVBoxLayout(self)

        # Program info
        info_label = QLabel(f"<h3>{self.program.name}</h3>")
        layout.addWidget(info_label)

        desc_label = QLabel("このプログラムの残留ファイルとレジストリエントリをスキャンします。")
        layout.addWidget(desc_label)

        # Scan options
        options_layout = QHBoxLayout()

        self.files_checkbox = QCheckBox("ファイルとディレクトリ")
        self.files_checkbox.setChecked(True)
        options_layout.addWidget(self.files_checkbox)

        self.registry_checkbox = QCheckBox("レジストリ")
        self.registry_checkbox.setChecked(True)
        options_layout.addWidget(self.registry_checkbox)

        self.shortcuts_checkbox = QCheckBox("ショートカット")
        self.shortcuts_checkbox.setChecked(True)
        options_layout.addWidget(self.shortcuts_checkbox)

        options_layout.addStretch()
        layout.addLayout(options_layout)

        # Progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Status label
        self.status_label = QLabel("")
        layout.addWidget(self.status_label)

        # Results list
        results_label = QLabel("検出された残留物:")
        layout.addWidget(results_label)

        self.results_list = QListWidget()
        layout.addWidget(self.results_list)

        # Summary
        self.summary_label = QLabel("")
        layout.addWidget(self.summary_label)

        # Buttons
        button_layout = QHBoxLayout()

        self.scan_button = QPushButton("スキャン開始")
        self.scan_button.clicked.connect(self.start_scan)
        button_layout.addWidget(self.scan_button)

        self.clean_button = QPushButton("削除")
        self.clean_button.setEnabled(False)
        self.clean_button.clicked.connect(self.clean_leftovers)
        button_layout.addWidget(self.clean_button)

        self.close_button = QPushButton("閉じる")
        self.close_button.clicked.connect(self.close)
        button_layout.addWidget(self.close_button)

        button_layout.addStretch()
        layout.addLayout(button_layout)

    def start_scan(self):
        """Start scanning for leftovers."""
        # Disable scan button
        self.scan_button.setEnabled(False)
        self.clean_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.results_list.clear()
        self.summary_label.clear()

        # Start scan thread
        self.status_label.setText("スキャン中...")

        self.scan_thread = ScanThread(self.program)
        self.scan_thread.progress.connect(self.status_label.setText)
        self.scan_thread.finished.connect(self.on_scan_finished)
        self.scan_thread.start()

    def on_scan_finished(self, leftovers):
        """Called when scan finishes."""
        self.leftovers = leftovers
        self.progress_bar.setVisible(False)
        self.scan_button.setEnabled(True)

        if not leftovers:
            self.status_label.setText("残留物は見つかりませんでした。")
            self.summary_label.setText("<b>結果:</b> 残留物なし")
            QMessageBox.information(
                self,
                "スキャン完了",
                "残留物は見つかりませんでした。"
            )
            return

        # Display results
        self.status_label.setText(f"{len(leftovers)}個の残留物が見つかりました。")

        # Calculate total size
        total_size = sum(l.size for l in leftovers if l.size is not None)

        # Group by type
        type_counts = {}
        for leftover in leftovers:
            type_counts[leftover.type] = type_counts.get(leftover.type, 0) + 1

        # Update summary
        summary_parts = []
        for ltype, count in sorted(type_counts.items()):
            summary_parts.append(f"{ltype}: {count}個")

        summary_text = f"<b>合計:</b> {len(leftovers)}個 ({', '.join(summary_parts)})"
        if total_size > 0:
            summary_text += f", <b>サイズ:</b> {self.format_size(total_size)}"

        self.summary_label.setText(summary_text)

        # Add to list
        for leftover in leftovers[:100]:  # Limit to 100 items for performance
            self.results_list.addItem(str(leftover))

        if len(leftovers) > 100:
            self.results_list.addItem(f"... 他 {len(leftovers) - 100}個")

        # Enable clean button
        self.clean_button.setEnabled(True)

    def clean_leftovers(self):
        """Clean the found leftovers."""
        if not self.leftovers:
            return

        # Confirmation
        reply = QMessageBox.question(
            self,
            "確認",
            f"{len(self.leftovers)}個の残留物を削除しますか？\n\n"
            f"この操作は元に戻せません。\n"
            f"バックアップが自動的に作成されます。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.No:
            return

        # Disable buttons
        self.scan_button.setEnabled(False)
        self.clean_button.setEnabled(False)
        self.progress_bar.setVisible(True)

        # Start clean thread
        self.status_label.setText("削除中...")

        self.clean_thread = CleanThread(self.leftovers, create_backup=True)
        self.clean_thread.progress.connect(self.status_label.setText)
        self.clean_thread.finished.connect(self.on_clean_finished)
        self.clean_thread.start()

    def on_clean_finished(self, success, deleted, failed):
        """Called when cleaning finishes."""
        self.progress_bar.setVisible(False)
        self.scan_button.setEnabled(True)

        self.status_label.setText(f"削除完了: {deleted}個成功, {failed}個失敗")

        if success:
            QMessageBox.information(
                self,
                "完了",
                f"全ての残留物を削除しました。\n\n削除: {deleted}個"
            )
            # Clear the list
            self.results_list.clear()
            self.summary_label.setText("<b>全て削除されました</b>")
            self.leftovers = []
        else:
            QMessageBox.warning(
                self,
                "一部失敗",
                f"一部の残留物を削除できませんでした。\n\n"
                f"削除: {deleted}個\n失敗: {failed}個\n\n"
                f"管理者権限で再試行してください。"
            )

    def format_size(self, size_bytes):
        """Format file size."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"

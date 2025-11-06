"""
Uninstall dialog for GUI.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QProgressBar, QCheckBox, QMessageBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QTextCursor

from core.registry import InstalledProgram
from core.uninstaller import Uninstaller
from core.scanner import LeftoverScanner
from core.cleaner import Cleaner
from utils.logger import get_logger


class UninstallThread(QThread):
    """Thread for uninstalling a program."""

    progress = pyqtSignal(str)
    finished = pyqtSignal(bool, str)

    def __init__(self, program, silent=True, create_backup=True):
        super().__init__()
        self.program = program
        self.silent = silent
        self.create_backup = create_backup

    def run(self):
        """Run uninstallation."""
        try:
            self.progress.emit("アンインストールを開始しています...")

            uninstaller = Uninstaller(self.program)
            result = uninstaller.uninstall(
                silent=self.silent,
                create_backup=self.create_backup
            )

            if result.success:
                self.finished.emit(True, f"アンインストール完了 (所要時間: {result.duration:.2f}秒)")
            else:
                self.finished.emit(False, f"アンインストール失敗: {result.error_message}")

        except Exception as e:
            self.finished.emit(False, f"エラー: {str(e)}")


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


class UninstallDialog(QDialog):
    """Dialog for uninstalling a program."""

    def __init__(self, program: InstalledProgram, parent=None):
        super().__init__(parent)
        self.program = program
        self.leftovers = []
        self.logger = get_logger()

        self.init_ui()

    def init_ui(self):
        """Initialize UI."""
        self.setWindowTitle(f"アンインストール - {self.program.name}")
        self.setMinimumSize(600, 500)

        layout = QVBoxLayout(self)

        # Program info
        info_label = QLabel(f"<h3>{self.program.name}</h3>")
        layout.addWidget(info_label)

        version_label = QLabel(f"バージョン: {self.program.version or '不明'}")
        layout.addWidget(version_label)

        publisher_label = QLabel(f"発行元: {self.program.publisher or '不明'}")
        layout.addWidget(publisher_label)

        # Options
        options_layout = QHBoxLayout()

        self.backup_checkbox = QCheckBox("バックアップを作成")
        self.backup_checkbox.setChecked(True)
        options_layout.addWidget(self.backup_checkbox)

        self.scan_checkbox = QCheckBox("残留物をスキャン")
        self.scan_checkbox.setChecked(True)
        options_layout.addWidget(self.scan_checkbox)

        options_layout.addStretch()
        layout.addLayout(options_layout)

        # Progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Log output
        log_label = QLabel("ログ:")
        layout.addWidget(log_label)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text)

        # Buttons
        button_layout = QHBoxLayout()

        self.start_button = QPushButton("開始")
        self.start_button.clicked.connect(self.start_uninstall)
        button_layout.addWidget(self.start_button)

        self.close_button = QPushButton("閉じる")
        self.close_button.clicked.connect(self.close)
        button_layout.addWidget(self.close_button)

        button_layout.addStretch()
        layout.addLayout(button_layout)

    def append_log(self, message):
        """Append message to log."""
        self.log_text.append(message)
        # Auto-scroll to bottom
        self.log_text.moveCursor(QTextCursor.MoveOperation.End)

    def start_uninstall(self):
        """Start uninstallation process."""
        # Disable start button
        self.start_button.setEnabled(False)
        self.progress_bar.setVisible(True)

        # Start uninstall thread
        self.append_log("=" * 60)
        self.append_log(f"アンインストール開始: {self.program.name}")
        self.append_log("=" * 60)

        self.uninstall_thread = UninstallThread(
            self.program,
            silent=True,
            create_backup=self.backup_checkbox.isChecked()
        )
        self.uninstall_thread.progress.connect(self.append_log)
        self.uninstall_thread.finished.connect(self.on_uninstall_finished)
        self.uninstall_thread.start()

    def on_uninstall_finished(self, success, message):
        """Called when uninstallation finishes."""
        self.append_log(message)

        if success:
            if self.scan_checkbox.isChecked():
                # Start leftover scan
                self.scan_leftovers()
            else:
                self.progress_bar.setVisible(False)
                self.append_log("\nアンインストールが完了しました。")
                QMessageBox.information(self, "完了", "アンインストールが完了しました。")
        else:
            self.progress_bar.setVisible(False)
            QMessageBox.warning(self, "失敗", f"アンインストールに失敗しました:\n{message}")

    def scan_leftovers(self):
        """Scan for leftovers."""
        self.append_log("\n残留物スキャンを開始...")

        self.scan_thread = ScanThread(self.program)
        self.scan_thread.progress.connect(self.append_log)
        self.scan_thread.finished.connect(self.on_scan_finished)
        self.scan_thread.start()

    def on_scan_finished(self, leftovers):
        """Called when scan finishes."""
        self.leftovers = leftovers

        if not leftovers:
            self.append_log("\n残留物は見つかりませんでした。")
            self.progress_bar.setVisible(False)
            QMessageBox.information(self, "完了", "残留物は見つかりませんでした。\nクリーンにアンインストールされました。")
            return

        # Show leftover count
        self.append_log(f"\n{len(leftovers)}個の残留物が見つかりました:")

        # Show some examples
        for i, leftover in enumerate(leftovers[:10], 1):
            self.append_log(f"  {i}. {leftover}")

        if len(leftovers) > 10:
            self.append_log(f"  ... 他 {len(leftovers) - 10}個")

        # Ask to clean
        reply = QMessageBox.question(
            self,
            "残留物の削除",
            f"{len(leftovers)}個の残留物が見つかりました。\n削除しますか？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.clean_leftovers()
        else:
            self.progress_bar.setVisible(False)
            self.append_log("\n残留物は削除されませんでした。")

    def clean_leftovers(self):
        """Clean leftovers."""
        self.append_log("\n残留物を削除中...")

        self.clean_thread = CleanThread(
            self.leftovers,
            create_backup=self.backup_checkbox.isChecked()
        )
        self.clean_thread.progress.connect(self.append_log)
        self.clean_thread.finished.connect(self.on_clean_finished)
        self.clean_thread.start()

    def on_clean_finished(self, success, deleted, failed):
        """Called when cleaning finishes."""
        self.progress_bar.setVisible(False)

        self.append_log(f"\n削除完了: {deleted}個成功, {failed}個失敗")

        if success:
            QMessageBox.information(
                self,
                "完了",
                f"全ての残留物を削除しました。\n削除: {deleted}個"
            )
        else:
            QMessageBox.warning(
                self,
                "一部失敗",
                f"一部の残留物を削除できませんでした。\n\n"
                f"削除: {deleted}個\n失敗: {failed}個\n\n"
                f"管理者権限で再試行してください。"
            )

        self.append_log("\n" + "=" * 60)
        self.append_log("全ての処理が完了しました。")
        self.append_log("=" * 60)

"""
Batch Uninstall Dialog for the GUI.

Provides interface for batch uninstalling multiple programs.
"""

from typing import List
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton, QTextEdit, QProgressBar,
    QMessageBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont

from core.registry import InstalledProgram
from core.batch_uninstaller import BatchUninstaller, BatchUninstallResult
from utils.logger import get_logger

import logging

logger = logging.getLogger(__name__)


class BatchUninstallThread(QThread):
    """Thread for batch uninstalling programs."""

    progress = pyqtSignal(str, int, int)  # message, current, total
    finished = pyqtSignal(object)  # BatchUninstallResult
    error = pyqtSignal(str)

    def __init__(self, programs: List[InstalledProgram]):
        super().__init__()
        self.programs = programs

    def run(self):
        """Run batch uninstall operation."""
        try:
            # Progress callback
            def on_progress(message: str, current: int, total: int):
                self.progress.emit(message, current, total)

            # Create batch uninstaller
            batch = BatchUninstaller(on_progress)

            # Run batch uninstall
            result = batch.uninstall_multiple(
                self.programs,
                create_backup=True,
                scan_leftovers=True
            )

            self.finished.emit(result)

        except Exception as e:
            logger.error(f"Batch uninstall failed: {e}")
            self.error.emit(str(e))


class BatchUninstallDialog(QDialog):
    """Dialog for batch uninstalling programs."""

    def __init__(self, programs: List[InstalledProgram], parent=None):
        super().__init__(parent)
        self.programs = programs
        self.result = None
        self.init_ui()
        self.start_uninstall()

    def init_ui(self):
        """Initialize UI."""
        self.setWindowTitle(f"バッチアンインストール - {len(self.programs)}個のプログラム")
        self.setMinimumSize(700, 500)
        self.setModal(True)

        layout = QVBoxLayout()

        # Title
        title = QLabel(f"{len(self.programs)}個のプログラムをアンインストール中...")
        title.setStyleSheet("font-size: 14pt; font-weight: bold;")
        layout.addWidget(title)

        # Program list
        list_label = QLabel("対象プログラム:")
        layout.addWidget(list_label)

        program_list = "\n".join([f"• {p.name}" for p in self.programs])
        programs_text = QLabel(program_list)
        programs_text.setMaximumHeight(100)
        programs_text.setWordWrap(True)
        programs_text.setStyleSheet("background-color: #f0f0f0; padding: 5px;")
        layout.addWidget(programs_text)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(len(self.programs))
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        # Status label
        self.status_label = QLabel("準備中...")
        layout.addWidget(self.status_label)

        # Log output
        log_label = QLabel("ログ:")
        layout.addWidget(log_label)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 9))
        layout.addWidget(self.log_text)

        # Close button (disabled until complete)
        self.close_button = QPushButton("閉じる")
        self.close_button.setEnabled(False)
        self.close_button.clicked.connect(self.accept)
        layout.addWidget(self.close_button)

        self.setLayout(layout)

    def start_uninstall(self):
        """Start batch uninstall process."""
        self.log_text.append(f"バッチアンインストールを開始します ({len(self.programs)}個のプログラム)")
        self.log_text.append("")

        # Start uninstall thread
        self.uninstall_thread = BatchUninstallThread(self.programs)
        self.uninstall_thread.progress.connect(self.on_progress)
        self.uninstall_thread.finished.connect(self.on_finished)
        self.uninstall_thread.error.connect(self.on_error)
        self.uninstall_thread.start()

    def on_progress(self, message: str, current: int, total: int):
        """Handle progress update."""
        self.progress_bar.setValue(current)
        self.status_label.setText(f"処理中: {current}/{total}")
        self.log_text.append(message)
        self.log_text.ensureCursorVisible()

    def on_finished(self, result: BatchUninstallResult):
        """Handle completion."""
        self.result = result

        self.log_text.append("")
        self.log_text.append("=" * 70)
        self.log_text.append("バッチアンインストール完了")
        self.log_text.append("=" * 70)
        self.log_text.append(f"総プログラム数: {result.total_programs}")
        self.log_text.append(f"成功: {result.successful}")
        self.log_text.append(f"失敗: {result.failed}")
        self.log_text.append(f"スキップ: {result.skipped}")
        self.log_text.append(f"削除されたファイル: {result.total_files_removed}")
        self.log_text.append(f"削除されたレジストリキー: {result.total_registry_removed}")
        self.log_text.append(f"解放された容量: {result.total_space_freed / 1024:.2f} MB")

        if result.errors:
            self.log_text.append("")
            self.log_text.append("エラー:")
            for error in result.errors:
                self.log_text.append(f"  - {error}")

        self.status_label.setText("完了")
        self.close_button.setEnabled(True)

        # Show summary message
        if result.failed == 0:
            QMessageBox.information(
                self,
                "完了",
                f"{result.successful}個のプログラムを正常にアンインストールしました。"
            )
        else:
            QMessageBox.warning(
                self,
                "一部失敗",
                f"{result.successful}個成功、{result.failed}個失敗しました。\n"
                "詳細はログを確認してください。"
            )

    def on_error(self, error: str):
        """Handle error."""
        self.log_text.append("")
        self.log_text.append(f"エラー: {error}")
        self.status_label.setText("エラーが発生しました")
        self.close_button.setEnabled(True)

        QMessageBox.critical(
            self,
            "エラー",
            f"バッチアンインストール中にエラーが発生しました:\n{error}"
        )

    def closeEvent(self, event):
        """Handle close event."""
        if self.uninstall_thread and self.uninstall_thread.isRunning():
            reply = QMessageBox.question(
                self,
                "確認",
                "アンインストール処理が実行中です。\n"
                "キャンセルしますか？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )

            if reply == QMessageBox.StandardButton.Yes:
                self.uninstall_thread.terminate()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()

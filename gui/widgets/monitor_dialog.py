"""
Installation Monitor Dialog for the GUI.

Provides interface for monitoring software installations.
"""

import os
import winreg
from typing import Optional
from datetime import datetime

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QGroupBox, QListWidget, QMessageBox, QFileDialog,
    QTableWidget, QTableWidgetItem
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont

from core.monitor import InstallationMonitor, InstallationTrace
import logging

logger = logging.getLogger(__name__)


class MonitorThread(QThread):
    """Thread for monitoring operations."""

    progress = pyqtSignal(str)
    finished = pyqtSignal(object, str)  # trace, message
    error = pyqtSignal(str)

    def __init__(self, monitor: InstallationMonitor, program_name: str, stop: bool = False):
        super().__init__()
        self.monitor = monitor
        self.program_name = program_name
        self.stop = stop

    def run(self):
        """Run monitoring operation."""
        try:
            if self.stop:
                self.progress.emit("システムスナップショットを取得中...")

                # Default monitoring paths
                paths = [
                    os.environ.get('PROGRAMFILES', 'C:\\Program Files'),
                    os.environ.get('PROGRAMFILES(X86)', 'C:\\Program Files (x86)'),
                    os.environ.get('APPDATA', ''),
                    os.environ.get('LOCALAPPDATA', ''),
                    os.environ.get('PROGRAMDATA', ''),
                ]
                paths = [p for p in paths if p and os.path.exists(p)]

                registry_keys = [
                    (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Uninstall"),
                    (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Uninstall"),
                    (winreg.HKEY_LOCAL_MACHINE, r"Software"),
                    (winreg.HKEY_CURRENT_USER, r"Software"),
                ]

                self.progress.emit("変更を検出中...")
                trace = self.monitor.stop_monitoring(
                    self.program_name,
                    paths=paths,
                    registry_keys=registry_keys
                )

                self.progress.emit(f"検出完了: {len(trace.file_changes)}個のファイル変更, "
                                 f"{len(trace.registry_changes)}個のレジストリ変更")

                self.finished.emit(trace, "監視を停止しました")
            else:
                # Start monitoring
                self.progress.emit("初期スナップショットを作成中...")

                paths = [
                    os.environ.get('PROGRAMFILES', 'C:\\Program Files'),
                    os.environ.get('PROGRAMFILES(X86)', 'C:\\Program Files (x86)'),
                    os.environ.get('APPDATA', ''),
                    os.environ.get('LOCALAPPDATA', ''),
                    os.environ.get('PROGRAMDATA', ''),
                ]
                paths = [p for p in paths if p and os.path.exists(p)]

                registry_keys = [
                    (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Uninstall"),
                    (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Uninstall"),
                ]

                self.monitor.start_monitoring(paths=paths, registry_keys=registry_keys)
                self.finished.emit(None, "監視を開始しました")

        except Exception as e:
            logger.error(f"Monitor operation failed: {e}")
            self.error.emit(str(e))


class MonitorDialog(QDialog):
    """Dialog for installation monitoring."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.monitor = InstallationMonitor()
        self.current_trace: Optional[InstallationTrace] = None
        self.monitoring = False
        self.init_ui()

    def init_ui(self):
        """Initialize UI."""
        self.setWindowTitle("インストールモニター")
        self.setMinimumSize(800, 600)

        layout = QVBoxLayout()

        # Status section
        status_group = QGroupBox("ステータス")
        status_layout = QVBoxLayout()

        self.status_label = QLabel("監視停止中")
        self.status_label.setStyleSheet("font-size: 14pt; font-weight: bold;")
        status_layout.addWidget(self.status_label)

        self.info_label = QLabel("ソフトウェアをインストールする前に「監視開始」をクリックしてください")
        status_layout.addWidget(self.info_label)

        status_group.setLayout(status_layout)
        layout.addWidget(status_group)

        # Control buttons
        button_layout = QHBoxLayout()

        self.start_button = QPushButton("監視開始")
        self.start_button.clicked.connect(self.start_monitoring)
        button_layout.addWidget(self.start_button)

        self.stop_button = QPushButton("監視停止")
        self.stop_button.clicked.connect(self.stop_monitoring)
        self.stop_button.setEnabled(False)
        button_layout.addWidget(self.stop_button)

        self.save_button = QPushButton("トレースを保存")
        self.save_button.clicked.connect(self.save_trace)
        self.save_button.setEnabled(False)
        button_layout.addWidget(self.save_button)

        self.load_button = QPushButton("トレースを読み込み")
        self.load_button.clicked.connect(self.load_trace)
        button_layout.addWidget(self.load_button)

        button_layout.addStretch()
        layout.addLayout(button_layout)

        # Results section
        results_group = QGroupBox("検出された変更")
        results_layout = QVBoxLayout()

        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.setFont(QFont("Consolas", 9))
        results_layout.addWidget(self.results_text)

        results_group.setLayout(results_layout)
        layout.addWidget(results_group)

        # Close button
        close_button = QPushButton("閉じる")
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button)

        self.setLayout(layout)

    def start_monitoring(self):
        """Start monitoring."""
        self.monitoring = True
        self.status_label.setText("監視中...")
        self.status_label.setStyleSheet("font-size: 14pt; font-weight: bold; color: green;")
        self.info_label.setText("ソフトウェアをインストールしてから「監視停止」をクリックしてください")
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.results_text.clear()

        # Start monitoring in thread
        self.monitor_thread = MonitorThread(self.monitor, "", stop=False)
        self.monitor_thread.progress.connect(self.update_progress)
        self.monitor_thread.finished.connect(self.on_start_finished)
        self.monitor_thread.error.connect(self.on_error)
        self.monitor_thread.start()

    def stop_monitoring(self):
        """Stop monitoring."""
        from PyQt6.QtWidgets import QInputDialog

        # Ask for program name
        program_name, ok = QInputDialog.getText(
            self,
            "プログラム名",
            "インストールしたプログラムの名前を入力してください:"
        )

        if not ok or not program_name:
            return

        self.monitoring = False
        self.status_label.setText("変更を検出中...")
        self.stop_button.setEnabled(False)

        # Stop monitoring in thread
        self.monitor_thread = MonitorThread(self.monitor, program_name, stop=True)
        self.monitor_thread.progress.connect(self.update_progress)
        self.monitor_thread.finished.connect(self.on_stop_finished)
        self.monitor_thread.error.connect(self.on_error)
        self.monitor_thread.start()

    def save_trace(self):
        """Save current trace."""
        if not self.current_trace:
            return

        try:
            file_path = self.monitor.save_trace(self.current_trace)
            QMessageBox.information(
                self,
                "保存完了",
                f"トレースを保存しました:\n{file_path}"
            )
            logger.info(f"Saved trace: {file_path}")
        except Exception as e:
            QMessageBox.critical(
                self,
                "エラー",
                f"トレースの保存に失敗しました:\n{str(e)}"
            )
            logger.error(f"Failed to save trace: {e}")

    def load_trace(self):
        """Load trace from file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "トレースを読み込み",
            self.monitor.traces_dir,
            "JSON Files (*.json)"
        )

        if not file_path:
            return

        try:
            trace = self.monitor.load_trace(file_path)
            self.current_trace = trace
            self.display_trace(trace)
            self.save_button.setEnabled(False)  # Already saved

            QMessageBox.information(
                self,
                "読み込み完了",
                f"トレースを読み込みました:\n{trace.program_name}"
            )
            logger.info(f"Loaded trace: {file_path}")

        except Exception as e:
            QMessageBox.critical(
                self,
                "エラー",
                f"トレースの読み込みに失敗しました:\n{str(e)}"
            )
            logger.error(f"Failed to load trace: {e}")

    def update_progress(self, message: str):
        """Update progress display."""
        self.results_text.append(message)

    def on_start_finished(self, trace, message: str):
        """Handle start monitoring completion."""
        self.results_text.append(f"\n{message}")

    def on_stop_finished(self, trace: InstallationTrace, message: str):
        """Handle stop monitoring completion."""
        self.current_trace = trace
        self.status_label.setText("監視停止 - 検出完了")
        self.status_label.setStyleSheet("font-size: 14pt; font-weight: bold; color: blue;")
        self.info_label.setText("検出された変更を確認し、必要に応じてトレースを保存してください")
        self.start_button.setEnabled(True)
        self.save_button.setEnabled(True)

        self.display_trace(trace)

    def display_trace(self, trace: InstallationTrace):
        """Display trace information."""
        self.results_text.clear()

        # Summary
        self.results_text.append(f"プログラム: {trace.program_name}")
        self.results_text.append(f"インストール日時: {trace.install_date}")
        self.results_text.append(f"合計サイズ: {trace.total_size / 1024 / 1024:.2f} MB")
        self.results_text.append(f"\nファイル変更: {len(trace.file_changes)}個")
        self.results_text.append(f"レジストリ変更: {len(trace.registry_changes)}個")
        self.results_text.append("\n" + "=" * 70)

        # File changes
        added_files = [f for f in trace.file_changes if f.change_type == 'added']
        modified_files = [f for f in trace.file_changes if f.change_type == 'modified']

        if added_files:
            self.results_text.append(f"\n追加されたファイル ({len(added_files)}個):")
            for f in added_files[:20]:  # Show first 20
                self.results_text.append(f"  + {f.path}")
            if len(added_files) > 20:
                self.results_text.append(f"  ... 他 {len(added_files) - 20}個")

        if modified_files:
            self.results_text.append(f"\n変更されたファイル ({len(modified_files)}個):")
            for f in modified_files[:20]:  # Show first 20
                self.results_text.append(f"  * {f.path}")
            if len(modified_files) > 20:
                self.results_text.append(f"  ... 他 {len(modified_files) - 20}個")

        # Registry changes
        added_reg = [r for r in trace.registry_changes if r.change_type == 'added']
        modified_reg = [r for r in trace.registry_changes if r.change_type == 'modified']

        if added_reg:
            self.results_text.append(f"\n追加されたレジストリ ({len(added_reg)}個):")
            for r in added_reg[:20]:  # Show first 20
                self.results_text.append(f"  + {r.key_path}")
                if r.value_name:
                    self.results_text.append(f"    {r.value_name} = {r.value_data}")
            if len(added_reg) > 20:
                self.results_text.append(f"  ... 他 {len(added_reg) - 20}個")

        if modified_reg:
            self.results_text.append(f"\n変更されたレジストリ ({len(modified_reg)}個):")
            for r in modified_reg[:20]:  # Show first 20
                self.results_text.append(f"  * {r.key_path}")
                if r.value_name:
                    self.results_text.append(f"    {r.value_name} = {r.value_data}")
            if len(modified_reg) > 20:
                self.results_text.append(f"  ... 他 {len(modified_reg) - 20}個")

    def on_error(self, error: str):
        """Handle error."""
        self.status_label.setText("エラー")
        self.status_label.setStyleSheet("font-size: 14pt; font-weight: bold; color: red;")
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)

        QMessageBox.critical(
            self,
            "エラー",
            f"監視中にエラーが発生しました:\n{error}"
        )
        logger.error(f"Monitor error: {error}")

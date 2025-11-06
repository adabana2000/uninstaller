"""
Background Monitor Settings Dialog for the GUI.

Provides interface for configuring the background installation monitor.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QCheckBox, QSpinBox, QGroupBox, QMessageBox, QTextEdit
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont

from core.background_monitor import BackgroundMonitorManager
from utils.config import ConfigManager
from utils.logger import get_logger

import logging

logger = logging.getLogger(__name__)


class BackgroundMonitorSettingsDialog(QDialog):
    """Dialog for configuring the background installation monitor."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.config = ConfigManager()
        self.monitor = BackgroundMonitorManager.get_instance()
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_statistics)
        self.init_ui()
        self.load_settings()
        self.update_statistics()

    def init_ui(self):
        """Initialize UI."""
        self.setWindowTitle("バックグラウンドモニター設定")
        self.setMinimumSize(600, 500)
        self.setModal(True)

        layout = QVBoxLayout()

        # Title
        title = QLabel("バックグラウンドインストールモニター")
        title.setStyleSheet("font-size: 14pt; font-weight: bold;")
        layout.addWidget(title)

        # Description
        desc = QLabel(
            "バックグラウンドで常駐し、新しいソフトウェアのインストールを自動的に検知します。\n"
            "検知したプログラムは自動的に記録され、後で完全にアンインストールできます。"
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #666; margin-bottom: 10px;")
        layout.addWidget(desc)

        # Enable/Disable group
        enable_group = QGroupBox("モニター設定")
        enable_layout = QVBoxLayout()

        # Enable checkbox
        enable_row = QHBoxLayout()
        self.enable_checkbox = QCheckBox("バックグラウンドモニターを有効にする")
        self.enable_checkbox.stateChanged.connect(self.on_enable_changed)
        enable_row.addWidget(self.enable_checkbox)
        enable_row.addStretch()
        enable_layout.addLayout(enable_row)

        # Check interval
        interval_row = QHBoxLayout()
        interval_row.addWidget(QLabel("チェック間隔:"))
        self.interval_spin = QSpinBox()
        self.interval_spin.setMinimum(10)
        self.interval_spin.setMaximum(3600)
        self.interval_spin.setSuffix(" 秒")
        self.interval_spin.setValue(60)
        self.interval_spin.valueChanged.connect(self.on_interval_changed)
        interval_row.addWidget(self.interval_spin)
        interval_row.addWidget(QLabel("(推奨: 60秒)"))
        interval_row.addStretch()
        enable_layout.addLayout(interval_row)

        enable_group.setLayout(enable_layout)
        layout.addWidget(enable_group)

        # Status group
        status_group = QGroupBox("モニター状態")
        status_layout = QVBoxLayout()

        # Status labels
        self.status_label = QLabel("状態: 停止中")
        self.status_label.setStyleSheet("font-weight: bold;")
        status_layout.addWidget(self.status_label)

        self.programs_label = QLabel("監視中のプログラム数: 0")
        status_layout.addWidget(self.programs_label)

        self.interval_status_label = QLabel("チェック間隔: 60秒")
        status_layout.addWidget(self.interval_status_label)

        # Control buttons
        control_row = QHBoxLayout()
        self.start_button = QPushButton("モニター開始")
        self.start_button.clicked.connect(self.start_monitor)
        control_row.addWidget(self.start_button)

        self.stop_button = QPushButton("モニター停止")
        self.stop_button.clicked.connect(self.stop_monitor)
        self.stop_button.setEnabled(False)
        control_row.addWidget(self.stop_button)

        self.refresh_button = QPushButton("プログラムリスト更新")
        self.refresh_button.clicked.connect(self.refresh_programs)
        control_row.addWidget(self.refresh_button)

        control_row.addStretch()
        status_layout.addLayout(control_row)

        status_group.setLayout(status_layout)
        layout.addWidget(status_group)

        # Log group
        log_group = QGroupBox("最近の検知")
        log_layout = QVBoxLayout()

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        self.log_text.setFont(QFont("Consolas", 9))
        self.log_text.setPlaceholderText("新しいインストールが検知されるとここに表示されます...")
        log_layout.addWidget(self.log_text)

        log_group.setLayout(log_layout)
        layout.addWidget(log_group)

        # Buttons
        button_row = QHBoxLayout()
        button_row.addStretch()

        self.save_button = QPushButton("設定を保存")
        self.save_button.clicked.connect(self.save_settings)
        button_row.addWidget(self.save_button)

        self.close_button = QPushButton("閉じる")
        self.close_button.clicked.connect(self.accept)
        button_row.addWidget(self.close_button)

        layout.addLayout(button_row)

        self.setLayout(layout)

        # Start update timer
        self.update_timer.start(1000)  # Update every second

    def load_settings(self):
        """Load settings from config."""
        enabled = self.config.get('monitor.enabled', False)
        interval = self.config.get('monitor.check_interval', 60)

        self.enable_checkbox.setChecked(enabled)
        self.interval_spin.setValue(interval)

        # Update monitor
        self.monitor.set_check_interval(interval)

        # Start if enabled
        if enabled and not self.monitor.is_running():
            self.monitor.start()

    def save_settings(self):
        """Save settings to config."""
        enabled = self.enable_checkbox.isChecked()
        interval = self.interval_spin.value()

        self.config.set('monitor.enabled', enabled)
        self.config.set('monitor.check_interval', interval)
        self.config.save()

        logger.info(f"Background monitor settings saved: enabled={enabled}, interval={interval}")

        QMessageBox.information(
            self,
            "保存完了",
            "設定を保存しました。"
        )

    def on_enable_changed(self, state):
        """Handle enable checkbox change."""
        enabled = (state == Qt.CheckState.Checked.value)

        if enabled:
            if not self.monitor.is_running():
                self.start_monitor()
        else:
            if self.monitor.is_running():
                self.stop_monitor()

    def on_interval_changed(self, value):
        """Handle interval change."""
        self.monitor.set_check_interval(value)

    def start_monitor(self):
        """Start the background monitor."""
        if self.monitor.is_running():
            QMessageBox.warning(
                self,
                "警告",
                "モニターは既に実行中です。"
            )
            return

        self.monitor.start()
        self.update_buttons()
        logger.info("Background monitor started from settings dialog")

    def stop_monitor(self):
        """Stop the background monitor."""
        if not self.monitor.is_running():
            QMessageBox.warning(
                self,
                "警告",
                "モニターは実行されていません。"
            )
            return

        reply = QMessageBox.question(
            self,
            "確認",
            "バックグラウンドモニターを停止しますか？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.monitor.stop()
            self.update_buttons()
            logger.info("Background monitor stopped from settings dialog")

    def refresh_programs(self):
        """Refresh the known programs list."""
        self.monitor.refresh_known_programs()
        self.update_statistics()

        QMessageBox.information(
            self,
            "更新完了",
            "プログラムリストを更新しました。"
        )

    def update_statistics(self):
        """Update statistics display."""
        stats = self.monitor.get_statistics()

        # Update status
        if stats['running']:
            self.status_label.setText("状態: 実行中")
            self.status_label.setStyleSheet("font-weight: bold; color: green;")
        else:
            self.status_label.setText("状態: 停止中")
            self.status_label.setStyleSheet("font-weight: bold; color: red;")

        # Update other info
        self.programs_label.setText(f"監視中のプログラム数: {stats['known_programs']}")
        self.interval_status_label.setText(f"チェック間隔: {stats['check_interval']}秒")

        self.update_buttons()

    def update_buttons(self):
        """Update button states."""
        is_running = self.monitor.is_running()
        self.start_button.setEnabled(not is_running)
        self.stop_button.setEnabled(is_running)

    def add_detection_log(self, program_name: str):
        """
        Add a detection log entry.

        Args:
            program_name: Name of detected program
        """
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.log_text.append(f"[{timestamp}] 新しいインストールを検知: {program_name}")

    def closeEvent(self, event):
        """Handle close event."""
        # Stop update timer
        self.update_timer.stop()
        event.accept()

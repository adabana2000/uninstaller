"""
Context Menu Integration Dialog for the GUI.

Provides interface for managing Windows Explorer context menu integration.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QMessageBox, QGroupBox, QTextEdit
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from utils.context_menu import ContextMenuIntegration
from utils.permissions import is_admin
from utils.logger import get_logger

import logging

logger = logging.getLogger(__name__)


class ContextMenuDialog(QDialog):
    """Dialog for managing Windows Explorer context menu integration."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.integration = ContextMenuIntegration()
        self.init_ui()
        self.update_status()

    def init_ui(self):
        """Initialize UI."""
        self.setWindowTitle("右クリックメニュー統合")
        self.setMinimumSize(600, 500)
        self.setModal(True)

        layout = QVBoxLayout()

        # Title
        title = QLabel("Windows エクスプローラー 右クリックメニュー統合")
        title.setStyleSheet("font-size: 14pt; font-weight: bold;")
        layout.addWidget(title)

        # Description
        desc = QLabel(
            "Windowsエクスプローラーでファイルを右クリックしたときに、"
            "「このプログラムをアンインストール」メニューを追加できます。\n\n"
            "この機能を有効にすると、実行ファイル（.exe）やショートカット（.lnk）を"
            "右クリックして、直接アンインストールを開始できます。"
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #666; margin-bottom: 10px;")
        layout.addWidget(desc)

        # Admin warning
        if not is_admin():
            warning = QLabel(
                "⚠ この機能を使用するには管理者権限が必要です。\n"
                "アプリケーションを管理者として再起動してください。"
            )
            warning.setWordWrap(True)
            warning.setStyleSheet(
                "background-color: #fff3cd; color: #856404; "
                "padding: 10px; border: 1px solid #ffeeba; border-radius: 4px;"
            )
            layout.addWidget(warning)

        # Status group
        status_group = QGroupBox("統合状態")
        status_layout = QVBoxLayout()

        self.status_label = QLabel("状態: 確認中...")
        self.status_label.setStyleSheet("font-weight: bold; font-size: 12pt;")
        status_layout.addWidget(self.status_label)

        self.details_label = QLabel()
        self.details_label.setWordWrap(True)
        status_layout.addWidget(self.details_label)

        status_group.setLayout(status_layout)
        layout.addWidget(status_group)

        # Actions group
        actions_group = QGroupBox("操作")
        actions_layout = QVBoxLayout()

        # Install button
        self.install_button = QPushButton("右クリックメニューを有効にする")
        self.install_button.clicked.connect(self.install_context_menu)
        self.install_button.setMinimumHeight(40)
        actions_layout.addWidget(self.install_button)

        # Uninstall button
        self.uninstall_button = QPushButton("右クリックメニューを無効にする")
        self.uninstall_button.clicked.connect(self.uninstall_context_menu)
        self.uninstall_button.setMinimumHeight(40)
        actions_layout.addWidget(self.uninstall_button)

        actions_group.setLayout(actions_layout)
        layout.addWidget(actions_group)

        # Info group
        info_group = QGroupBox("使用方法")
        info_layout = QVBoxLayout()

        info_text = QTextEdit()
        info_text.setReadOnly(True)
        info_text.setMaximumHeight(150)
        info_text.setFont(QFont("Segoe UI", 9))
        info_text.setHtml("""
        <ol>
        <li><b>有効化:</b> 上の「右クリックメニューを有効にする」ボタンをクリック</li>
        <li><b>使用:</b> Windowsエクスプローラーで実行ファイルやショートカットを右クリック</li>
        <li><b>選択:</b> 「このプログラムをアンインストール」を選択</li>
        <li><b>アンインストール:</b> Windows Uninstallerが起動し、対応するプログラムが選択されます</li>
        </ol>

        <p><b>注意:</b> すべてのファイルでプログラムを特定できるわけではありません。
        プログラムが見つからない場合は、通常の方法でアンインストールしてください。</p>
        """)
        info_layout.addWidget(info_text)

        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

        # Close button
        button_row = QHBoxLayout()
        button_row.addStretch()

        close_button = QPushButton("閉じる")
        close_button.clicked.connect(self.accept)
        close_button.setMinimumWidth(100)
        button_row.addWidget(close_button)

        layout.addLayout(button_row)

        self.setLayout(layout)

        # Update button states based on admin status
        if not is_admin():
            self.install_button.setEnabled(False)
            self.uninstall_button.setEnabled(False)

    def update_status(self):
        """Update status display."""
        is_installed = self.integration.is_installed()

        if is_installed:
            self.status_label.setText("状態: 有効")
            self.status_label.setStyleSheet("font-weight: bold; font-size: 12pt; color: green;")
            self.details_label.setText(
                "右クリックメニュー統合が有効になっています。\n"
                "実行ファイルやショートカットを右クリックして、"
                "「このプログラムをアンインストール」を選択できます。"
            )

            if is_admin():
                self.install_button.setEnabled(False)
                self.uninstall_button.setEnabled(True)

        else:
            self.status_label.setText("状態: 無効")
            self.status_label.setStyleSheet("font-weight: bold; font-size: 12pt; color: red;")
            self.details_label.setText(
                "右クリックメニュー統合が無効になっています。\n"
                "有効にするには、下のボタンをクリックしてください。"
            )

            if is_admin():
                self.install_button.setEnabled(True)
                self.uninstall_button.setEnabled(False)

    def install_context_menu(self):
        """Install context menu integration."""
        if not is_admin():
            QMessageBox.warning(
                self,
                "権限エラー",
                "管理者権限が必要です。\n"
                "アプリケーションを管理者として再起動してください。"
            )
            return

        reply = QMessageBox.question(
            self,
            "確認",
            "Windowsエクスプローラーの右クリックメニューに\n"
            "「このプログラムをアンインストール」を追加しますか？\n\n"
            "この操作はレジストリを変更します。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            success = self.integration.install()

            if success:
                QMessageBox.information(
                    self,
                    "完了",
                    "右クリックメニュー統合を有効にしました。\n\n"
                    "実行ファイルやショートカットを右クリックして、"
                    "「このプログラムをアンインストール」を選択できます。"
                )
                self.update_status()
                logger.info("Context menu integration installed")
            else:
                QMessageBox.critical(
                    self,
                    "エラー",
                    "右クリックメニュー統合の有効化に失敗しました。\n"
                    "詳細はログを確認してください。"
                )

    def uninstall_context_menu(self):
        """Uninstall context menu integration."""
        if not is_admin():
            QMessageBox.warning(
                self,
                "権限エラー",
                "管理者権限が必要です。\n"
                "アプリケーションを管理者として再起動してください。"
            )
            return

        reply = QMessageBox.question(
            self,
            "確認",
            "Windowsエクスプローラーの右クリックメニューから\n"
            "「このプログラムをアンインストール」を削除しますか？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            success = self.integration.uninstall()

            if success:
                QMessageBox.information(
                    self,
                    "完了",
                    "右クリックメニュー統合を無効にしました。"
                )
                self.update_status()
                logger.info("Context menu integration uninstalled")
            else:
                QMessageBox.critical(
                    self,
                    "エラー",
                    "右クリックメニュー統合の無効化に失敗しました。\n"
                    "詳細はログを確認してください。"
                )

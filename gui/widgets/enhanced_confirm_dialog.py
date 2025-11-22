"""
Enhanced confirmation dialog for uninstallation.
Shows detailed information before uninstalling a program.
"""

import os
from typing import List, Set
from pathlib import Path

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QCheckBox, QGroupBox, QTextEdit, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from core.registry import InstalledProgram
from utils.logger import get_logger


class DependencyChecker:
    """Check if other programs depend on this program."""

    def __init__(self):
        """Initialize dependency checker."""
        self.logger = get_logger()

    def check_dependencies(self, program: InstalledProgram, all_programs: List[InstalledProgram]) -> Set[str]:
        """
        Check if other programs might depend on this program.

        Args:
            program: Program to check dependencies for
            all_programs: List of all installed programs

        Returns:
            Set of program names that might depend on this program
        """
        dependencies = set()

        # Check for common dependency patterns
        program_name_lower = program.name.lower()

        # Runtime dependencies (e.g., Visual C++, .NET Framework, Java)
        runtime_keywords = [
            'visual c++', 'vcredist', 'microsoft visual c++',
            '.net framework', 'dotnet',
            'java runtime', 'jre', 'java(tm)',
            'directx',
        ]

        is_runtime = any(keyword in program_name_lower for keyword in runtime_keywords)

        if is_runtime:
            # This is a runtime - many programs might depend on it
            # Count programs that might use it
            for other_program in all_programs:
                if other_program.name == program.name:
                    continue

                # Check if program likely depends on this runtime
                if self._likely_depends_on(other_program, program):
                    dependencies.add(other_program.name)

        return dependencies

    def _likely_depends_on(self, program: InstalledProgram, runtime: InstalledProgram) -> bool:
        """
        Check if a program likely depends on a runtime.

        Args:
            program: Program to check
            runtime: Runtime to check dependency on

        Returns:
            True if program likely depends on runtime
        """
        # For now, we'll use simple heuristics
        # A more sophisticated approach would analyze DLL dependencies

        runtime_name_lower = runtime.name.lower()

        # Visual C++ dependencies
        if 'visual c++' in runtime_name_lower or 'vcredist' in runtime_name_lower:
            # Most native Windows programs depend on Visual C++ runtime
            # But don't flag other Microsoft runtimes
            if program.publisher and 'microsoft' in program.publisher.lower():
                return False

        # .NET dependencies
        if '.net' in runtime_name_lower or 'dotnet' in runtime_name_lower:
            # Programs with certain publishers are likely .NET apps
            if program.publisher and any(keyword in program.publisher.lower()
                                          for keyword in ['.net', 'unity', 'xamarin']):
                return True

        # Java dependencies
        if 'java' in runtime_name_lower or 'jre' in runtime_name_lower:
            # Programs with Java-related names
            if 'java' in program.name.lower():
                return True

        return False


class EnhancedConfirmDialog(QDialog):
    """
    Enhanced confirmation dialog for uninstallation.

    Shows:
    - Program details
    - Estimated size
    - Dependency warnings
    - "Don't show this again" option
    """

    def __init__(self, program: InstalledProgram, all_programs: List[InstalledProgram] = None, parent=None):
        """
        Initialize the enhanced confirmation dialog.

        Args:
            program: Program to uninstall
            all_programs: List of all installed programs (for dependency checking)
            parent: Parent widget
        """
        super().__init__(parent)
        self.program = program
        self.all_programs = all_programs or []
        self.logger = get_logger()
        self.dependency_checker = DependencyChecker()

        # Check dependencies
        self.dependencies = self.dependency_checker.check_dependencies(program, self.all_programs)

        self.init_ui()

    def init_ui(self):
        """Initialize UI."""
        self.setWindowTitle("アンインストール確認")
        self.setMinimumSize(550, 450)

        layout = QVBoxLayout(self)

        # Warning icon and title
        title_layout = QHBoxLayout()
        title_label = QLabel("<h2>⚠️ プログラムをアンインストールしますか？</h2>")
        title_layout.addWidget(title_label)
        layout.addLayout(title_layout)

        # Program information group
        info_group = QGroupBox("プログラム情報")
        info_layout = QVBoxLayout()

        # Program name
        name_label = QLabel(f"<b>プログラム名:</b> {self.program.name}")
        name_label.setWordWrap(True)
        info_layout.addWidget(name_label)

        # Version
        version = self.program.version or "不明"
        version_label = QLabel(f"<b>バージョン:</b> {version}")
        info_layout.addWidget(version_label)

        # Publisher
        publisher = self.program.publisher or "不明"
        publisher_label = QLabel(f"<b>発行元:</b> {publisher}")
        publisher_label.setWordWrap(True)
        info_layout.addWidget(publisher_label)

        # Install location
        if self.program.install_location:
            location_label = QLabel(f"<b>インストール先:</b> {self.program.install_location}")
            location_label.setWordWrap(True)
            info_layout.addWidget(location_label)

        # Size
        size_text = self._format_size()
        size_label = QLabel(f"<b>推定サイズ:</b> {size_text}")
        info_layout.addWidget(size_label)

        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

        # Dependency warnings
        if self.dependencies:
            warning_group = QGroupBox("⚠️ 依存関係の警告")
            warning_layout = QVBoxLayout()

            warning_text = QLabel(
                f"<b>このプログラムは {len(self.dependencies)} 個の他のプログラムから使用されている可能性があります。</b><br>"
                f"アンインストールすると、他のプログラムが正常に動作しなくなる可能性があります。"
            )
            warning_text.setWordWrap(True)
            warning_text.setStyleSheet("QLabel { color: #d32f2f; }")
            warning_layout.addWidget(warning_text)

            # Show first 5 dependencies
            if len(self.dependencies) <= 5:
                deps_text = "<br>".join(f"• {dep}" for dep in sorted(self.dependencies))
            else:
                deps_list = sorted(self.dependencies)[:5]
                deps_text = "<br>".join(f"• {dep}" for dep in deps_list)
                deps_text += f"<br>... 他 {len(self.dependencies) - 5} 個"

            deps_label = QLabel(deps_text)
            deps_label.setWordWrap(True)
            deps_label.setStyleSheet("QLabel { margin-left: 20px; }")
            warning_layout.addWidget(deps_label)

            warning_group.setLayout(warning_layout)
            layout.addWidget(warning_group)

        # Information text
        info_text = QLabel(
            "<b>アンインストールすると:</b><br>"
            "• プログラムファイルが削除されます<br>"
            "• レジストリエントリが削除されます<br>"
            "• ショートカットが削除されます<br>"
            "• バックアップが作成されます (オプション)"
        )
        info_text.setWordWrap(True)
        layout.addWidget(info_text)

        layout.addStretch()

        # "Don't show this again" checkbox
        self.dont_show_checkbox = QCheckBox("今後この確認を表示しない")
        self.dont_show_checkbox.setToolTip("この確認ダイアログをスキップして直接アンインストールを開始します")
        layout.addWidget(self.dont_show_checkbox)

        # Buttons
        button_layout = QHBoxLayout()

        self.uninstall_button = QPushButton("アンインストール")
        self.uninstall_button.setStyleSheet("""
            QPushButton {
                background-color: #d32f2f;
                color: white;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #b71c1c;
            }
        """)
        self.uninstall_button.clicked.connect(self.accept)
        button_layout.addWidget(self.uninstall_button)

        self.cancel_button = QPushButton("キャンセル")
        self.cancel_button.setStyleSheet("padding: 8px 16px;")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)

        button_layout.addStretch()
        layout.addLayout(button_layout)

    def _format_size(self) -> str:
        """
        Format program size.

        Returns:
            Formatted size string
        """
        if not self.program.estimated_size:
            return "不明"

        # Size is in KB
        size_kb = self.program.estimated_size

        if size_kb < 1024:
            return f"{size_kb} KB"
        elif size_kb < 1024 * 1024:
            size_mb = size_kb / 1024
            return f"{size_mb:.1f} MB"
        else:
            size_gb = size_kb / (1024 * 1024)
            return f"{size_gb:.2f} GB"

    def should_skip_in_future(self) -> bool:
        """
        Check if user wants to skip this dialog in the future.

        Returns:
            True if checkbox is checked
        """
        return self.dont_show_checkbox.isChecked()


def show_enhanced_confirm_dialog(
    program: InstalledProgram,
    all_programs: List[InstalledProgram] = None,
    parent=None
) -> tuple[bool, bool]:
    """
    Show enhanced confirmation dialog.

    Args:
        program: Program to uninstall
        all_programs: List of all installed programs (for dependency checking)
        parent: Parent widget

    Returns:
        Tuple of (confirmed, skip_in_future)
    """
    dialog = EnhancedConfirmDialog(program, all_programs, parent)
    result = dialog.exec()

    confirmed = result == QDialog.DialogCode.Accepted
    skip_in_future = dialog.should_skip_in_future()

    return confirmed, skip_in_future

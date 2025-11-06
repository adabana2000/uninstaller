"""
Export functionality for the uninstaller.

Supports exporting program lists and reports in multiple formats.
"""

import os
import csv
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
import logging

from core.registry import InstalledProgram
from utils.system_info import get_system_info

logger = logging.getLogger(__name__)


class Exporter:
    """Exporter for program lists and reports."""

    def __init__(self, output_dir: Optional[str] = None):
        """Initialize exporter.

        Args:
            output_dir: Output directory for exports. If None, uses current directory.
        """
        self.output_dir = output_dir or os.getcwd()
        os.makedirs(self.output_dir, exist_ok=True)

    def export_programs_csv(
        self,
        programs: List[InstalledProgram],
        filename: Optional[str] = None
    ) -> str:
        """Export programs list to CSV file.

        Args:
            programs: List of installed programs
            filename: Output filename. If None, generates timestamp-based name.

        Returns:
            Path to exported file
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"programs_{timestamp}.csv"

        file_path = os.path.join(self.output_dir, filename)

        try:
            with open(file_path, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)

                # Header
                writer.writerow([
                    'Name',
                    'Version',
                    'Publisher',
                    'Install Date',
                    'Size (KB)',
                    'Install Location',
                    'Uninstall String',
                    'Architecture',
                    'Registry Key'
                ])

                # Data
                for program in programs:
                    writer.writerow([
                        program.name,
                        program.version or '',
                        program.publisher or '',
                        program.install_date or '',
                        program.estimated_size or 0,
                        program.install_location or '',
                        program.uninstall_string or '',
                        program.architecture or '',
                        program.registry_key or ''
                    ])

            logger.info(f"Exported {len(programs)} programs to CSV: {file_path}")
            return file_path

        except Exception as e:
            logger.error(f"Failed to export to CSV: {e}")
            raise

    def export_programs_json(
        self,
        programs: List[InstalledProgram],
        filename: Optional[str] = None,
        include_system_info: bool = True
    ) -> str:
        """Export programs list to JSON file.

        Args:
            programs: List of installed programs
            filename: Output filename. If None, generates timestamp-based name.
            include_system_info: Whether to include system information

        Returns:
            Path to exported file
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"programs_{timestamp}.json"

        file_path = os.path.join(self.output_dir, filename)

        try:
            data = {
                "export_date": datetime.now().isoformat(),
                "total_programs": len(programs),
                "programs": []
            }

            if include_system_info:
                data["system_info"] = get_system_info()

            for program in programs:
                data["programs"].append({
                    "name": program.name,
                    "version": program.version,
                    "publisher": program.publisher,
                    "install_date": program.install_date,
                    "estimated_size": program.estimated_size,
                    "install_location": program.install_location,
                    "uninstall_string": program.uninstall_string,
                    "architecture": program.architecture,
                    "registry_key": program.registry_key,
                    "display_icon": program.display_icon,
                })

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            logger.info(f"Exported {len(programs)} programs to JSON: {file_path}")
            return file_path

        except Exception as e:
            logger.error(f"Failed to export to JSON: {e}")
            raise

    def export_programs_html(
        self,
        programs: List[InstalledProgram],
        filename: Optional[str] = None,
        include_system_info: bool = True
    ) -> str:
        """Export programs list to HTML file.

        Args:
            programs: List of installed programs
            filename: Output filename. If None, generates timestamp-based name.
            include_system_info: Whether to include system information

        Returns:
            Path to exported file
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"programs_{timestamp}.html"

        file_path = os.path.join(self.output_dir, filename)

        try:
            html = self._generate_html_report(programs, include_system_info)

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(html)

            logger.info(f"Exported {len(programs)} programs to HTML: {file_path}")
            return file_path

        except Exception as e:
            logger.error(f"Failed to export to HTML: {e}")
            raise

    def export_uninstall_report(
        self,
        program_name: str,
        uninstall_success: bool,
        files_removed: List[str],
        registry_removed: List[str],
        errors: List[str],
        filename: Optional[str] = None
    ) -> str:
        """Export uninstall report.

        Args:
            program_name: Name of uninstalled program
            uninstall_success: Whether uninstall was successful
            files_removed: List of removed files
            registry_removed: List of removed registry keys
            errors: List of errors encountered
            filename: Output filename

        Returns:
            Path to exported file
        """
        if filename is None:
            safe_name = "".join(c if c.isalnum() or c in (' ', '_') else '_' for c in program_name)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"uninstall_report_{safe_name}_{timestamp}.html"

        file_path = os.path.join(self.output_dir, filename)

        try:
            html = self._generate_uninstall_report_html(
                program_name,
                uninstall_success,
                files_removed,
                registry_removed,
                errors
            )

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(html)

            logger.info(f"Exported uninstall report: {file_path}")
            return file_path

        except Exception as e:
            logger.error(f"Failed to export uninstall report: {e}")
            raise

    def _generate_html_report(
        self,
        programs: List[InstalledProgram],
        include_system_info: bool
    ) -> str:
        """Generate HTML report for programs list.

        Args:
            programs: List of installed programs
            include_system_info: Whether to include system information

        Returns:
            HTML string
        """
        html = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Installed Programs Report</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
            background-color: white;
            padding: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        h1 {
            color: #333;
            border-bottom: 2px solid #007acc;
            padding-bottom: 10px;
        }
        h2 {
            color: #555;
            margin-top: 30px;
        }
        .info {
            background-color: #e7f3ff;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
        }
        .info p {
            margin: 5px 0;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }
        th {
            background-color: #007acc;
            color: white;
            padding: 12px;
            text-align: left;
            font-weight: bold;
        }
        td {
            padding: 10px;
            border-bottom: 1px solid #ddd;
        }
        tr:hover {
            background-color: #f5f5f5;
        }
        .footer {
            margin-top: 30px;
            text-align: center;
            color: #777;
            font-size: 0.9em;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Installed Programs Report</h1>
"""

        # System info
        if include_system_info:
            sys_info = get_system_info()
            html += f"""
        <div class="info">
            <h2>System Information</h2>
            <p><strong>Computer Name:</strong> {sys_info.get('computer_name', 'N/A')}</p>
            <p><strong>OS:</strong> {sys_info.get('os_name', 'N/A')} {sys_info.get('os_version', 'N/A')}</p>
            <p><strong>Architecture:</strong> {sys_info.get('architecture', 'N/A')}</p>
            <p><strong>Processor:</strong> {sys_info.get('processor', 'N/A')}</p>
            <p><strong>Total Programs:</strong> {len(programs)}</p>
            <p><strong>Report Date:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
"""

        # Programs table
        html += """
        <h2>Installed Programs</h2>
        <table>
            <thead>
                <tr>
                    <th>Name</th>
                    <th>Version</th>
                    <th>Publisher</th>
                    <th>Install Date</th>
                    <th>Size (MB)</th>
                    <th>Architecture</th>
                </tr>
            </thead>
            <tbody>
"""

        for program in programs:
            size_mb = (program.estimated_size or 0) / 1024
            html += f"""
                <tr>
                    <td>{program.name}</td>
                    <td>{program.version or 'N/A'}</td>
                    <td>{program.publisher or 'N/A'}</td>
                    <td>{program.install_date or 'N/A'}</td>
                    <td>{size_mb:.2f}</td>
                    <td>{program.architecture or 'N/A'}</td>
                </tr>
"""

        html += """
            </tbody>
        </table>
        <div class="footer">
            <p>Generated by Windows Uninstaller</p>
        </div>
    </div>
</body>
</html>
"""
        return html

    def _generate_uninstall_report_html(
        self,
        program_name: str,
        uninstall_success: bool,
        files_removed: List[str],
        registry_removed: List[str],
        errors: List[str]
    ) -> str:
        """Generate HTML report for uninstallation.

        Args:
            program_name: Name of uninstalled program
            uninstall_success: Whether uninstall was successful
            files_removed: List of removed files
            registry_removed: List of removed registry keys
            errors: List of errors

        Returns:
            HTML string
        """
        status_color = "#28a745" if uninstall_success else "#dc3545"
        status_text = "SUCCESS" if uninstall_success else "FAILED"

        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Uninstall Report - {program_name}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #333;
        }}
        .status {{
            padding: 15px;
            border-radius: 5px;
            margin: 20px 0;
            font-size: 1.2em;
            font-weight: bold;
            text-align: center;
            background-color: {status_color};
            color: white;
        }}
        .section {{
            margin: 30px 0;
        }}
        .section h2 {{
            color: #555;
            border-bottom: 2px solid #007acc;
            padding-bottom: 5px;
        }}
        ul {{
            list-style-type: none;
            padding: 0;
        }}
        li {{
            padding: 5px 0;
            border-bottom: 1px solid #eee;
            word-break: break-all;
        }}
        .error {{
            background-color: #fff3cd;
            border: 1px solid #ffc107;
            padding: 10px;
            margin: 5px 0;
            border-radius: 3px;
        }}
        .footer {{
            margin-top: 30px;
            text-align: center;
            color: #777;
            font-size: 0.9em;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Uninstall Report</h1>
        <p><strong>Program:</strong> {program_name}</p>
        <p><strong>Date:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>

        <div class="status">
            {status_text}
        </div>
"""

        if errors:
            html += """
        <div class="section">
            <h2>Errors</h2>
"""
            for error in errors:
                html += f'            <div class="error">{error}</div>\n'
            html += "        </div>\n"

        html += f"""
        <div class="section">
            <h2>Files Removed ({len(files_removed)})</h2>
            <ul>
"""
        for file in files_removed[:100]:  # Limit to first 100
            html += f"                <li>{file}</li>\n"

        if len(files_removed) > 100:
            html += f"                <li><em>... and {len(files_removed) - 100} more files</em></li>\n"

        html += """
            </ul>
        </div>
"""

        html += f"""
        <div class="section">
            <h2>Registry Keys Removed ({len(registry_removed)})</h2>
            <ul>
"""
        for key in registry_removed[:100]:  # Limit to first 100
            html += f"                <li>{key}</li>\n"

        if len(registry_removed) > 100:
            html += f"                <li><em>... and {len(registry_removed) - 100} more keys</em></li>\n"

        html += """
            </ul>
        </div>
        <div class="footer">
            <p>Generated by Windows Uninstaller</p>
        </div>
    </div>
</body>
</html>
"""
        return html


def get_exporter(output_dir: Optional[str] = None) -> Exporter:
    """Get Exporter instance.

    Args:
        output_dir: Output directory for exports

    Returns:
        Exporter instance
    """
    return Exporter(output_dir)

# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller specification file for Windows Uninstaller.
"""

import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Collect all submodules
hiddenimports = [
    'PyQt6.QtCore',
    'PyQt6.QtGui',
    'PyQt6.QtWidgets',
    'win32api',
    'win32con',
    'win32file',
    'win32security',
    'pywintypes',
    'click',
    'tabulate',
    'psutil',
    'dateutil',
]

# Add all submodules from our package
hiddenimports += collect_submodules('core')
hiddenimports += collect_submodules('gui')
hiddenimports += collect_submodules('cli')
hiddenimports += collect_submodules('utils')
hiddenimports += collect_submodules('database')

# Collect data files
datas = []

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'IPython',
        'jupyter',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='WindowsUninstaller',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # No console window for GUI
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Add icon file path here if available
    version='version_info.txt',  # Will create this next
)

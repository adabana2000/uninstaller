# ビルド手順

このドキュメントでは、Windows UninstallerをEXE化し、Windowsインストーラーを作成する手順を説明します。

## 必要な環境

### 1. Python環境
- Python 3.8以降
- 必要なパッケージがインストールされていること

```bash
pip install -r requirements.txt
```

### 2. PyInstaller
EXEファイルの作成に必要です。

```bash
pip install pyinstaller
```

### 3. Inno Setup（インストーラー作成時のみ）
Windowsインストーラーの作成に必要です。

- ダウンロード: https://jrsoftware.org/isinfo.php
- インストール先: `C:\Program Files (x86)\Inno Setup 6\`

## ビルド方法

### オプション1: バッチファイルを使用（推奨）

#### EXEファイルの作成
```batch
build_exe.bat
```

このスクリプトは以下を実行します：
1. 以前のビルドをクリーンアップ
2. PyInstallerでEXEをビルド
3. `dist\WindowsUninstaller.exe` を生成

#### Windowsインストーラーの作成
```batch
build_installer.bat
```

このスクリプトは以下を実行します：
1. EXEファイルの存在を確認
2. Inno Setupでインストーラーをビルド
3. `Output\WindowsUninstaller-Setup-0.7.0.exe` を生成

### オプション2: 手動ビルド

#### EXEファイルの作成
```bash
# 以前のビルドをクリーンアップ
rmdir /s /q build dist

# PyInstallerでビルド
pyinstaller windows-uninstaller.spec
```

#### Windowsインストーラーの作成
```bash
# Inno Setupでビルド
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss
```

## ビルド成果物

### EXEファイル
- 場所: `dist\WindowsUninstaller.exe`
- サイズ: 約30-50MB（すべての依存関係を含む）
- 単一実行ファイル（ポータブル）

### インストーラー
- 場所: `Output\WindowsUninstaller-Setup-0.7.0.exe`
- サイズ: 約30-50MB
- 機能:
  - Program Filesへのインストール
  - スタートメニューへのショートカット作成
  - デスクトップアイコン作成（オプション）
  - アンインストーラーの登録

## トラブルシューティング

### PyInstallerエラー

**問題**: モジュールが見つからないエラー
```
ModuleNotFoundError: No module named 'xxx'
```

**解決策**: `windows-uninstaller.spec` の `hiddenimports` リストにモジュールを追加:
```python
hiddenimports = [
    'PyQt6.QtCore',
    'PyQt6.QtGui',
    # ... その他のモジュール
    'xxx',  # 追加
]
```

**問題**: EXEが起動しない

**解決策**: コンソールモードで実行してエラーを確認:
```bash
# .specファイルで console=True に変更
exe = EXE(
    ...
    console=True,  # False から True に変更
    ...
)
```

### Inno Setupエラー

**問題**: EXEファイルが見つからない
```
Error: Source file not found: dist\WindowsUninstaller.exe
```

**解決策**: 先にEXEをビルド:
```batch
build_exe.bat
```

**問題**: Inno Setupが見つからない

**解決策**: インストール先を確認し、`build_installer.bat` のパスを修正:
```batch
set INNO_SETUP="C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
```

## カスタマイズ

### アイコンの変更

1. `.ico` ファイルを用意（推奨サイズ: 256x256）
2. プロジェクトルートに配置（例: `icon.ico`）
3. `windows-uninstaller.spec` を更新:
```python
exe = EXE(
    ...
    icon='icon.ico',
    ...
)
```
4. `installer.iss` を更新:
```ini
[Setup]
...
SetupIconFile=icon.ico
...
```

### バージョン情報の更新

`version_info.txt` を編集:
```python
filevers=(0, 7, 0, 0),  # メジャー, マイナー, パッチ, ビルド
prodvers=(0, 7, 0, 0),
...
StringStruct(u'FileVersion', u'0.7.0.0'),
StringStruct(u'ProductVersion', u'0.7.0.0')
```

`installer.iss` も更新:
```ini
#define MyAppVersion "0.7.0"
```

## 配布

### EXE単体配布
`dist\WindowsUninstaller.exe` を配布するだけで動作します。
- メリット: シンプル、ポータブル
- デメリット: スタートメニュー登録なし、アンインストーラーなし

### インストーラー配布（推奨）
`Output\WindowsUninstaller-Setup-0.7.0.exe` を配布します。
- メリット: 正式なインストール、アンインストーラー、ショートカット
- デメリット: インストールが必要

## 自動ビルド

すべてのステップを一度に実行する場合:

```batch
@echo off
call build_exe.bat
if errorlevel 1 exit /b 1
call build_installer.bat
```

このスクリプトを `build_all.bat` として保存できます。

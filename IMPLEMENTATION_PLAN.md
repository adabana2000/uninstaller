# Windows Uninstaller - 実装計画書

**プロジェクト名**: Windows Uninstaller
**目標**: IObit Uninstallerのような高機能なWindowsアンインストーラーの開発
**バージョン**: 0.1.0
**最終更新**: 2025-11-06

---

## 目次

1. [プロジェクト概要](#プロジェクト概要)
2. [技術仕様](#技術仕様)
3. [アーキテクチャ](#アーキテクチャ)
4. [実装フェーズ](#実装フェーズ)
5. [各モジュールの詳細](#各モジュールの詳細)
6. [セキュリティとバックアップ](#セキュリティとバックアップ)
7. [テスト計画](#テスト計画)
8. [配布計画](#配布計画)

---

## プロジェクト概要

### 目的

Windows向けの包括的なアプリケーションアンインストーラーを開発する。標準のWindowsアンインストーラーでは削除しきれない残留ファイルやレジストリエントリを検出・削除し、システムをクリーンに保つことを目的とする。

### 主要機能

1. **完全なアンインストール**: プログラムと全ての関連ファイル・レジストリを削除
2. **残留物スキャン**: アンインストール後の残留物を自動検出
3. **インストールモニター**: インストール時の変更を追跡
4. **強制削除**: 通常の方法で削除できないプログラムを強制削除
5. **バッチアンインストール**: 複数のプログラムを一括アンインストール
6. **バックアップと復元**: システム復元ポイント、レジストリバックアップ
7. **詳細なログ記録**: 全操作の記録と追跡
8. **GUI + CLI**: 両方のインターフェースを提供

### 開発期間

- **Phase 1 (完了)**: 1-2週間 - 基礎インフラ
- **Phase 2**: 1-2週間 - 基本アンインストール機能
- **Phase 3**: 2-3週間 - GUI実装
- **Phase 4**: 2週間 - 高度な削除機能
- **Phase 5**: 2-3週間 - インストールモニター
- **Phase 6**: 2週間 - 追加機能と最適化

**合計**: 10-14週間

---

## 技術仕様

### 開発環境

- **プログラミング言語**: Python 3.8+
- **対象OS**: Windows 10/11 (64bit推奨)
- **アーキテクチャ**: 32bit/64bit両対応

### 技術スタック

#### コアライブラリ
- **winreg**: レジストリ操作 (標準ライブラリ)
- **subprocess**: プロセス実行とコマンド実行
- **pathlib**: ファイルパス操作
- **zipfile**: ファイルアーカイブ

#### GUIフレームワーク
- **PyQt6**: モダンで美しいGUIの実装
  - 豊富なウィジェット
  - カスタマイズ可能なスタイル
  - マルチスレッドサポート

#### CLIフレームワーク
- **Click**: 強力なコマンドラインインターフェース
  - サブコマンドサポート
  - オプション解析
  - ヘルプ生成

#### Windows API
- **pywin32**: Windows API へのアクセス
  - プロセス管理
  - 権限操作
  - システム情報取得

#### ユーティリティ
- **tabulate**: テーブル形式の出力
- **python-dateutil**: 日付操作

---

## アーキテクチャ

### モジュール構成

```
uninstaller/
├── core/                    # コア機能
│   ├── __init__.py
│   ├── registry.py         # レジストリ操作 [✓ 完了]
│   ├── uninstaller.py      # アンインストール実行 [Phase 2]
│   ├── scanner.py          # 残留物スキャン [Phase 2]
│   ├── monitor.py          # インストールモニター [Phase 5]
│   └── force_delete.py     # 強制削除機能 [Phase 4]
│
├── utils/                   # ユーティリティ
│   ├── __init__.py
│   ├── backup.py           # バックアップ/復元 [✓ 完了]
│   ├── logger.py           # ログ記録 [✓ 完了]
│   ├── permissions.py      # 権限管理 [✓ 完了]
│   └── system_info.py      # システム情報取得 [✓ 完了]
│
├── gui/                     # GUIインターフェース [Phase 3]
│   ├── __init__.py
│   ├── main_window.py      # メインウィンドウ
│   ├── widgets/
│   │   ├── program_list.py # プログラム一覧ウィジェット
│   │   ├── progress.py     # 進捗表示
│   │   └── log_viewer.py   # ログビューア
│   └── resources/          # アイコン、スタイル
│
├── cli/                     # CLIインターフェース [✓ 完了]
│   ├── __init__.py
│   └── commands.py         # コマンド定義
│
├── database/                # データベース [Phase 4]
│   └── stubborn_apps.json  # 頑固なアプリ情報
│
├── tests/                   # テストコード
│   ├── test_registry.py
│   ├── test_uninstaller.py
│   └── test_scanner.py
│
├── main.py                  # エントリーポイント [✓ 完了]
├── test_basic.py            # 基本テスト [✓ 完了]
├── requirements.txt         # 依存関係 [✓ 完了]
├── setup.py                 # セットアップスクリプト [✓ 完了]
└── README.md                # ドキュメント [✓ 完了]
```

### データフロー

```
[ユーザー]
    ↓
[GUI/CLI インターフェース]
    ↓
[コア機能 (registry, uninstaller, scanner)]
    ↓
[ユーティリティ (logger, backup, permissions)]
    ↓
[Windows API / レジストリ / ファイルシステム]
```

---

## 実装フェーズ

### Phase 1: 基礎インフラ [✓ 完了]

**期間**: 1-2週間
**状態**: ✓ 完了

#### 実装内容

1. **プロジェクト構造**
   - ディレクトリ構造の作成
   - `__init__.py` ファイルの配置
   - 依存関係の定義 (`requirements.txt`)
   - セットアップスクリプト (`setup.py`)

2. **レジストリ読み取り機能** (`core/registry.py`)
   - 32bit/64bit両対応のレジストリスキャン
   - インストール済みプログラム情報の取得
   - プログラム情報のデータクラス定義
   - 検索機能
   - 重複削除

3. **システム情報取得** (`utils/system_info.py`)
   - Windows バージョン検出
   - アーキテクチャ検出
   - Program Files パスの取得
   - AppData パスの取得
   - ユーザーディレクトリの取得

4. **権限管理** (`utils/permissions.py`)
   - 管理者権限チェック
   - UAC昇格機能
   - ファイル書き込み権限チェック
   - レジストリアクセスチェック

5. **ロギングシステム** (`utils/logger.py`)
   - コンソール出力
   - ファイル出力
   - ログローテーション
   - 操作履歴の記録
   - エラーログ

6. **バックアップシステム** (`utils/backup.py`)
   - システム復元ポイントの作成
   - レジストリキーのバックアップ
   - ファイル・ディレクトリのバックアップ
   - バックアップの一覧表示
   - バックアップのクリーンアップ

7. **基本的なCLI** (`cli/commands.py`)
   - `list`: プログラム一覧表示
   - `info`: プログラム詳細情報
   - `sysinfo`: システム情報表示
   - `privileges`: 権限情報表示
   - `backups`: バックアップ一覧
   - `cleanup`: 古いバックアップ削除

8. **テストプログラム** (`test_basic.py`)
   - 全モジュールの基本機能テスト
   - 統合テスト

#### 成果

- 424個のインストール済みプログラムを検出 (テスト環境)
- 全5つのテストが成功
- ログファイル自動生成機能が動作
- レジストリから正確にプログラム情報を取得

### Phase 2: 基本アンインストール機能 [予定]

**期間**: 1-2週間
**状態**: 未着手

#### 実装予定

1. **アンインストール実行エンジン** (`core/uninstaller.py`)
   - UninstallString の解析と実行
   - MSI パッケージのアンインストール
     - `msiexec /x {ProductCode} /qn` コマンド
     - 静音モード対応
   - プロセスの監視と待機
   - 終了コードの取得とエラーハンドリング
   - タイムアウト処理

2. **残留物スキャナー** (`core/scanner.py`)
   - **ファイル・ディレクトリスキャン**
     - Program Files 配下の関連フォルダ
     - AppData (Local, Roaming, ProgramData) の関連フォルダ
     - スタートメニュー、デスクトップのショートカット
     - 一時ファイル

   - **レジストリスキャン**
     - プログラム名での検索
     - 発行元名での検索
     - GUID での検索
     - 壊れた参照の検出

   - **その他の残留物**
     - サービスの検出
     - タスクスケジューラのタスク
     - フォントファイル
     - ドライバファイル

3. **削除機能**
   - 安全な削除確認
   - ファイル削除 (使用中ファイルの検出)
   - レジストリキー削除
   - 削除失敗時のリトライ

4. **CLI コマンド拡張**
   - `uninstall`: プログラムのアンインストール
   - `scan`: 残留物スキャン
   - `clean`: 残留物削除

#### 技術的課題

- 使用中ファイルの削除
- アンインストーラプロセスのハング対応
- MSI と 非MSI アプリケーションの判別

### Phase 3: GUI実装 [予定]

**期間**: 2-3週間
**状態**: 未着手

#### 実装予定

1. **メインウィンドウ** (`gui/main_window.py`)
   - PyQt6 ベースのメインウィンドウ
   - メニューバー
   - ツールバー
   - ステータスバー

2. **プログラム一覧ビュー** (`gui/widgets/program_list.py`)
   - テーブルビュー
   - ソート機能 (名前、サイズ、日付)
   - フィルター機能
   - 検索機能
   - 複数選択 (バッチアンインストール用)
   - アイコン表示

3. **詳細情報パネル**
   - 選択したプログラムの詳細表示
   - プロパティ一覧
   - レジストリキー情報

4. **アンインストールウィザード**
   - 確認ダイアログ
   - 進捗表示
   - ログ表示
   - 残留物スキャン結果
   - 削除確認

5. **ログビューア** (`gui/widgets/log_viewer.py`)
   - リアルタイムログ表示
   - フィルター機能
   - ログファイルのエクスポート

6. **設定画面**
   - バックアップ設定
   - ログ設定
   - スキャン設定

#### UIデザイン

- モダンでシンプルなデザイン
- ダークモード対応
- 日本語と英語のローカライゼーション

### Phase 4: 高度な削除機能 [予定]

**期間**: 2週間
**状態**: 未着手

#### 実装予定

1. **強制削除機能** (`core/force_delete.py`)
   - 破損したアンインストール情報への対応
   - 直接削除 (UninstallString がない場合)
   - プロセス強制終了
   - ファイルロックの解除

2. **バッチアンインストール**
   - 複数プログラムの選択
   - 順次アンインストール
   - エラーハンドリング
   - 進捗レポート

3. **頑固なアプリデータベース** (`database/stubborn_apps.json`)
   - 特殊な削除手順が必要なアプリの情報
   - カスタム削除スクリプト
   - データベースの更新機能

4. **ブラウザ拡張機能管理**
   - Chrome 拡張機能の検出と削除
   - Firefox アドオンの検出と削除
   - Edge 拡張機能の検出と削除

#### データベース構造

```json
{
  "stubborn_apps": [
    {
      "name": "Example App",
      "detection_patterns": ["Example", "ExampleApp"],
      "removal_steps": [
        {
          "type": "stop_process",
          "process_name": "example.exe"
        },
        {
          "type": "delete_service",
          "service_name": "ExampleService"
        },
        {
          "type": "delete_registry",
          "key": "HKLM\\Software\\Example"
        },
        {
          "type": "delete_directory",
          "path": "%ProgramFiles%\\Example"
        }
      ]
    }
  ]
}
```

### Phase 5: インストールモニター [予定]

**期間**: 2-3週間
**状態**: 未着手

#### 実装予定

1. **スナップショット方式** (`core/monitor.py`)
   - インストール前のスナップショット
     - ファイルシステムの状態
     - レジストリの状態
     - サービス一覧
   - インストール後のスナップショット
   - 差分の比較と記録

2. **変更追跡**
   - 新規ファイル・フォルダの検出
   - 変更されたファイルの検出
   - 新規レジストリキーの検出
   - 新規サービスの検出
   - スタートアップエントリの追加

3. **モニターデータの管理**
   - JSON形式での保存
   - アンインストール時のデータ活用
   - モニターデータの一覧表示

4. **GUI統合**
   - モニターの開始/停止ボタン
   - 変更内容のリアルタイム表示
   - モニターデータの確認

#### 技術的課題

- スナップショット取得の高速化
- 大量の変更データの効率的な管理
- システムパフォーマンスへの影響最小化

### Phase 6: 追加機能と最適化 [予定]

**期間**: 2週間
**状態**: 未着手

#### 実装予定

1. **統計とレポート**
   - インストール済みプログラムの統計
   - ディスク使用量の分析
   - アンインストール履歴
   - レポート生成 (HTML, PDF)

2. **パフォーマンス最適化**
   - レジストリスキャンの高速化
   - マルチスレッド処理
   - キャッシング機構
   - メモリ使用量の最適化

3. **ユーザビリティ向上**
   - プログラム評価システム
   - アンインストール推奨機能
   - ディスクスペース解放の提案
   - オンラインヘルプ

4. **セキュリティ強化**
   - ホワイトリスト機能
   - デジタル署名の検証
   - マルウェア検出との統合 (オプション)

---

## 各モジュールの詳細

### core/registry.py [✓ 完了]

**目的**: Windowsレジストリからインストール済みプログラムの情報を取得

#### 主要クラス

```python
@dataclass
class InstalledProgram:
    """インストール済みプログラムの情報"""
    name: str
    version: Optional[str]
    publisher: Optional[str]
    install_date: Optional[str]
    install_location: Optional[str]
    uninstall_string: Optional[str]
    quiet_uninstall_string: Optional[str]
    estimated_size: Optional[int]
    display_icon: Optional[str]
    registry_key: Optional[str]
    is_system_component: bool
    architecture: str  # x64, x86, user

class RegistryReader:
    """レジストリリーダークラス"""
    def get_installed_programs(self, include_updates: bool = False) -> List[InstalledProgram]
    def search_programs(self, query: str) -> List[InstalledProgram]
    def get_program_by_name(self, name: str) -> Optional[InstalledProgram]
```

#### レジストリパス

1. **64bit アプリケーション**
   - `HKEY_LOCAL_MACHINE\Software\Microsoft\Windows\CurrentVersion\Uninstall`

2. **32bit アプリケーション (64bit Windows上)**
   - `HKEY_LOCAL_MACHINE\Software\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall`

3. **ユーザーレベルアプリケーション**
   - `HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Uninstall`

#### 機能

- Windows Updateのフィルタリング
- 重複プログラムの削除
- プログラム情報の正規化
- インストール日のパース (YYYYMMDD形式)

### core/uninstaller.py [Phase 2]

**目的**: アンインストールの実行

#### 主要クラス (予定)

```python
class Uninstaller:
    """アンインストーラークラス"""

    def __init__(self, program: InstalledProgram):
        self.program = program
        self.logger = get_logger()

    def uninstall(self, silent: bool = False) -> bool:
        """アンインストールを実行"""
        pass

    def execute_uninstall_string(self, uninstall_string: str) -> subprocess.CompletedProcess:
        """UninstallStringを実行"""
        pass

    def uninstall_msi(self, product_code: str, silent: bool = False) -> bool:
        """MSIパッケージをアンインストール"""
        pass

    def wait_for_completion(self, process: subprocess.Popen, timeout: int = 300) -> bool:
        """プロセスの完了を待機"""
        pass
```

#### アンインストール方法

1. **UninstallString の実行**
   - レジストリから UninstallString を取得
   - サイレントモードパラメータの追加 (`/S`, `/silent`, `/quiet` など)
   - プロセスの起動と監視

2. **MSI パッケージのアンインストール**
   - ProductCode の抽出
   - `msiexec /x {ProductCode} /qn` コマンドの実行
   - 終了コードの確認

3. **エラーハンドリング**
   - タイムアウト処理
   - プロセスのハング検出
   - エラーログの記録

### core/scanner.py [Phase 2]

**目的**: アンインストール後の残留物をスキャン

#### 主要クラス (予定)

```python
@dataclass
class Leftover:
    """残留物の情報"""
    type: str  # file, directory, registry, service, task
    path: str
    size: Optional[int]
    last_modified: Optional[datetime]

class LeftoverScanner:
    """残留物スキャナークラス"""

    def scan_leftovers(self, program: InstalledProgram) -> List[Leftover]:
        """残留物をスキャン"""
        pass

    def scan_files(self, program_name: str) -> List[Leftover]:
        """ファイル・ディレクトリをスキャン"""
        pass

    def scan_registry(self, program_name: str) -> List[Leftover]:
        """レジストリをスキャン"""
        pass

    def scan_services(self, program_name: str) -> List[Leftover]:
        """サービスをスキャン"""
        pass
```

#### スキャン対象

1. **ファイル・ディレクトリ**
   - `C:\Program Files\` - プログラム本体
   - `C:\Program Files (x86)\` - 32bitプログラム
   - `%AppData%\` - ユーザーデータ
   - `%LocalAppData%\` - ローカルデータ
   - `%ProgramData%\` - 共有データ
   - スタートメニュー
   - デスクトップ
   - クイック起動

2. **レジストリ**
   - `HKLM\Software\[プログラム名]`
   - `HKLM\Software\[発行元]`
   - `HKCU\Software\[プログラム名]`
   - `HKCR\` - ファイル拡張子関連付け
   - スタートアップエントリ

3. **サービス**
   - Windowsサービス一覧
   - プログラム名でのフィルタリング

4. **タスクスケジューラ**
   - スケジュールされたタスク
   - プログラム名でのフィルタリング

### utils/backup.py [✓ 完了]

**目的**: バックアップと復元機能

#### 主要クラス

```python
class BackupManager:
    """バックアップマネージャークラス"""

    def create_restore_point(self, description: str) -> bool:
        """システム復元ポイントを作成"""
        pass

    def backup_registry_key(self, hive: int, key_path: str, backup_name: str) -> Optional[Path]:
        """レジストリキーをバックアップ"""
        pass

    def backup_files(self, file_paths: List[str], backup_name: str) -> Optional[Path]:
        """ファイルをバックアップ"""
        pass

    def restore_registry_backup(self, backup_file: Path) -> bool:
        """レジストリバックアップを復元"""
        pass
```

#### バックアップ形式

1. **システム復元ポイント**
   - Windows標準機能を使用
   - `wmic.exe` コマンド経由

2. **レジストリバックアップ**
   - `.reg` ファイル形式
   - `reg export` コマンド使用

3. **ファイルバックアップ**
   - ZIP形式で圧縮
   - メタデータを JSON で保存

### utils/logger.py [✓ 完了]

**目的**: 詳細なログ記録

#### 主要クラス

```python
class UninstallerLogger:
    """カスタムロガークラス"""

    def __init__(self, name: str, log_dir: Optional[str] = None):
        """ロガーを初期化"""
        pass

    def log_operation_start(self, operation: str, target: str):
        """操作の開始を記録"""
        pass

    def log_operation_end(self, operation: str, success: bool, details: str = ""):
        """操作の終了を記録"""
        pass

    def log_file_deletion(self, file_path: str, success: bool):
        """ファイル削除を記録"""
        pass
```

#### ログフォーマット

```
[2025-11-06 14:30:15] INFO     | uninstaller | アンインストール開始: Adobe Reader DC
[2025-11-06 14:30:16] INFO     | uninstaller | UninstallStringを実行
[2025-11-06 14:30:45] INFO     | uninstaller | プロセス終了: 終了コード 0
[2025-11-06 14:30:46] INFO     | scanner     | 残留物スキャン開始
[2025-11-06 14:30:48] INFO     | scanner     | 検出: 15ファイル, 8レジストリキー
[2025-11-06 14:30:50] INFO     | uninstaller | 削除完了
```

---

## セキュリティとバックアップ

### セキュリティ対策

1. **管理者権限の確認**
   - UAC昇格プロンプト
   - 権限エラーのハンドリング

2. **ホワイトリスト**
   - システムコンポーネントの保護
   - 重要なプログラムの削除警告

3. **削除前の確認**
   - 確認ダイアログ
   - 削除内容のプレビュー

4. **デジタル署名の検証** (Phase 6)
   - プログラムの発行元確認
   - 信頼できるプログラムの識別

### バックアップ戦略

1. **自動バックアップ**
   - アンインストール前にシステム復元ポイントを自動作成
   - レジストリキーの自動バックアップ

2. **バックアップの保持期間**
   - デフォルト: 30日間
   - 設定で変更可能

3. **復元機能**
   - ワンクリックでバックアップから復元
   - 部分復元（レジストリのみ、ファイルのみ）

---

## テスト計画

### 単体テスト

各モジュールの単体テスト:

```python
# tests/test_registry.py
def test_get_installed_programs():
    """インストール済みプログラムの取得テスト"""
    reader = RegistryReader()
    programs = reader.get_installed_programs()
    assert len(programs) > 0
    assert all(isinstance(p, InstalledProgram) for p in programs)

# tests/test_scanner.py
def test_scan_files():
    """ファイルスキャンのテスト"""
    scanner = LeftoverScanner()
    leftovers = scanner.scan_files("TestProgram")
    assert isinstance(leftovers, list)
```

### 統合テスト

実際のアプリケーションでのテスト:

1. **テストアプリケーションのインストール**
2. **アンインストール実行**
3. **残留物スキャン**
4. **残留物削除**
5. **バックアップ確認**

### テスト環境

- **仮想マシン** (VMware / Hyper-V)
  - クリーンなWindows 10/11環境
  - スナップショット機能で復元可能

- **テストプログラム**
  - 軽量なフリーソフト
  - 様々なインストーラ形式 (MSI, NSIS, Inno Setup など)

---

## 配布計画

### パッケージング

1. **PyInstaller で単一EXE化**
   ```bash
   pyinstaller --onefile --windowed --icon=app.ico main.py
   ```

2. **インストーラー作成**
   - Inno Setup を使用
   - スタートメニューへの登録
   - アンインストーラーの登録

3. **デジタル署名** (オプション)
   - コード署名証明書の取得
   - 実行ファイルへの署名

### 配布形式

1. **スタンドアロンEXE**
   - 依存関係を全て含む
   - インストール不要で実行可能

2. **インストーラー**
   - 標準的なWindowsインストーラー
   - レジストリへの登録
   - 自動更新機能

3. **ポータブル版**
   - ZIP形式
   - USBメモリで持ち運び可能

---

## 今後の展望

### Phase 7以降 (将来的な機能)

1. **クラウド連携**
   - プログラムデータベースのクラウド同期
   - アンインストール履歴のバックアップ

2. **AIによる推奨機能**
   - 不要なプログラムの自動検出
   - 削除推奨の提案

3. **プラグインシステム**
   - カスタム削除スクリプトの追加
   - サードパーティ拡張

4. **マルチ言語対応**
   - 日本語、英語、中国語など
   - ローカライゼーションフレームワーク

5. **自動更新機能**
   - 新バージョンの自動チェック
   - ワンクリック更新

---

## 付録

### 参考資料

1. **Windows Registry**
   - [Microsoft Docs: Registry](https://docs.microsoft.com/en-us/windows/win32/sysinfo/registry)

2. **Windows Installer**
   - [Microsoft Docs: Windows Installer](https://docs.microsoft.com/en-us/windows/win32/msi/windows-installer-portal)

3. **PyQt6 Documentation**
   - [PyQt6 Official Documentation](https://www.riverbankcomputing.com/static/Docs/PyQt6/)

4. **Click Documentation**
   - [Click Official Documentation](https://click.palletsprojects.com/)

### 開発環境セットアップ

```bash
# 仮想環境の作成
python -m venv venv

# 仮想環境の有効化 (Windows)
venv\Scripts\activate

# 依存関係のインストール
pip install -r requirements.txt

# 開発モードでインストール
pip install -e .
```

### コーディング規約

- **PEP 8** に準拠
- **Type Hints** を使用
- **Docstrings** を記述 (Google スタイル)
- **Black** でコードフォーマット

---

**文書バージョン**: 1.0
**作成日**: 2025-11-06
**最終更新**: 2025-11-06
**作成者**: Windows Uninstaller Development Team

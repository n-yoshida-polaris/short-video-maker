# Linux での仮想環境 (venv) 構築手順

本プロジェクトは venv を使って開発環境を構築します。
以下は Linux (Ubuntu/Debian 系を想定) での基本的な手順です。

1) 事前準備
    - Python3 がインストールされていることを確認
      ```bash
      python3 --version
      ```
    - 必要であれば venv パッケージをインストール（Ubuntu/Debian）
      ```bash
      sudo apt update
      sudo apt install -y python3-venv
      ```

2) 仮想環境の作成（プロジェクト直下に .venv を作成）
   ```bash
   python3 -m venv .venv
   ```

3) 仮想環境の有効化
   ```bash
   source .venv/bin/activate
   ```
    - 有効化後、プロンプトに `(venv)` が表示されます。

4) 依存関係のインストール
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

5) 動作確認（例）
   ```bash
   python -m svmu.main --sheet "Sheet1" --output ./outputs --limit 5
   ```
    - Excel を使う場合は `.env` で `USE_GOOGLE_SHEETS=false` を設定し、
      ```bash
      python -m svmu.main --excel "./assets/ideas.xlsx" --sheet "Sheet1" --output ./outputs --limit 5
      ```

6) 仮想環境の無効化
   ```bash
   deactivate
   ```

補足:

- `.venv/` は既に `.gitignore` に含まれており、リポジトリにコミットされません。
- 他ディストリビューションでも基本は同様です。`python3-venv` パッケージ名は環境により異なることがあります。

# ShortVideoMakeAndUpload

Excel/Googleスプレッドシートの各行から短尺の縦動画（1080x1920）を自動生成し、ffmpegで背景動画にテキストオーバーレイを合成。

## 特長

- データソースを選択可能: Excel（.xlsx）または Google スプレッドシート
- Pillowでタイトル＋箇条書きの縦型画像（1080x1920）をレンダリング
- ffmpegで背景動画（H.264）にテキスト画像を合成し、背景の音声は維持
- 出力フォルダ・安全なファイル名で保存
- `.env` と YAML による環境変数・設定管理

## 必要環境

- Python 3.10+
- ffmpeg が PATH で利用可能であること
- フォント：日本語の明朝/セリフ系フォント（例：Noto Serif CJK JP）をご用意ください。`.env` の `FONT_PATH` で指定できます。
- フォント色は `.env` または YAML で指定できます（`TITLE_COLOR`, `BULLET_COLOR`）。未指定の場合は白（#FFFFFF）になります。

## クイックスタート

1. 依存関係をインストール:
   ```bash
   pip install -r requirements.txt
   ```
2. `.env.example` を `.env` にコピーして値を編集。
3. `config.yaml.example` を `config.yaml` にコピーして必要に応じて調整。
4. データソースの設定:
    - Excelを使う場合（デフォルト）: `.env` の `USE_GOOGLE_SHEETS=false`、`EXCEL_PATH` と `SHEET_NAME` を設定。
    - Googleスプレッドシートを使う場合: `.env` の `USE_GOOGLE_SHEETS=true` を設定し、以下を用意します。
        - `GSHEET_SPREADSHEET_ID` にスプレッドシートのIDを設定（URLの `/d/` と `/edit` の間の文字列）。
        - Google Cloud でサービスアカウントを作成し、JSON鍵を `./credentials/service_account.json` などに保存。
        - そのサービスアカウントのメールアドレスを対象スプレッドシートに「閲覧者」以上で共有。
        - 必要に応じて `.env` の `GSHEET_SERVICE_ACCOUNT_JSON` でJSONパスを変更できます。
5. シートの列（Excel/Google共通）を用意。既定で想定される列と説明:
    - `id`（文字列/数値）: 行の一意識別子。未入力の場合は行番号で代替します。
    - `title`（文字列）: 動画のタイトル。画像上部にセンタリングして表示します。
    - `bullets`（文字列）: 箇条書き本文。改行は `\n` または `・` 区切りのいずれかでOK。自動折り返し対応。
    - `status`（文字列）: `Ready` で処理対象。完了後は `Done` に更新されます（自動）。
    - `output_filename`（任意; 拡張子なし）: 出力ファイル名のベース（拡張子を除く）。自動生成後に書き込まれます。
    - `output_datetime`（任意; 文字列）: 出力日時。`yyyy/mm/dd hh:mm:ss` 形式のローカル時刻が自動で書き込まれます。
    - `tags`【投稿情報】（任意; CSV 文字列）: 将来拡張用。未使用でも問題ありません。
    - `description`【投稿情報】（任意; 文字列）: 補足説明。未使用でも問題ありません。
    - `issued` 投稿日時

参考: 列は Excel/Google スプレッドシートのどちらでも同一名称で扱われます。既存ブックの書式（列幅・改行など）は保持され、値のみ更新します。

サンプル（MDテーブル形式）:

| id | title            | bullets                             | status | output_filename    | output_datetime     | tags  | description | issue_status |
|---:|:-----------------|:------------------------------------|:-------|:-------------------|:--------------------|:------|:------------|--------------|
|  1 | 老後貧乏を招く 50代の思考   | ・貯蓄よりまず収支見直し\n・固定費の削減から\n・投資は小さく始める | Ready  |                    |                     | 家計,投資 | 家計見直しの基本    |              | 
|  2 | いますぐ始める英語学習3ステップ | ・毎日5分の音読\n・1フレーズ暗記\n・週末に復習          | Done   | 2_いますぐ始める英語学習3ステップ | 2026/01/31 14:20:05 | 学習    | 習慣化のコツ      | 投稿済み         | 

6. 背景動画（mp4）を用意し、`.env` の `BACKGROUND_VIDEO` にパスを設定します。

7. 実行（生成→合成→シート更新）:
    - Excel利用時:
      ```bash
      python -m svmu.main --excel "$EXCEL_PATH" --sheet "Sheet1" --output ./outputs --limit 5
      ```
    - Googleスプレッドシート利用時（`USE_GOOGLE_SHEETS=true` 設定済み）:
      ```bash
      python -m svmu.main --sheet "Sheet1" --output ./outputs --limit 5
      ```

## マルチチャンネル運用（YAML をチャンネルごとに配置）

複数のチャンネル設定を、プロジェクト直下の `channels/` ディレクトリに YAML として置き、まとめて順番に実行できます。

- ディレクトリ: `./channels/`
- ファイル: `*.yaml` または `*.yml`（例: `finance.yaml`, `english.yaml`）
- サンプル: `channels/channel.sample.yaml`

実行方法:

```bash
# 乾燥実行（一覧のみ）
python -m svmu_multi.run --dry-run

# 実行（見つかった YAML を順に実行）
python -m svmu_multi.run

# 1チャンネルあたりの最大処理件数を制限（例: 3件）
python -m svmu_multi.run --limit 3

# channels ディレクトリを変更
python -m svmu_multi.run --channels-dir ./my_channels
```

各チャンネルの YAML は `config.yaml.example` と同じキーを上書きできます。例:

```yaml
USE_GOOGLE_SHEETS: true
GSHEET_SPREADSHEET_ID: "YOUR_SHEET_ID"
SHEET_NAME: シート1
BACKGROUND_VIDEO: ./assets/backgrounds/bg1.mp4
OUTPUT_DIR: ./outputs/finance
TITLE_COLOR: "#000000"  # タイトルの文字色（例）
BULLET_COLOR: "#FFAA00"  # 本文の文字色（例）
DEFAULT_STATUS_READY: Ready
DEFAULT_STATUS_DONE: Done
```

### 定期実行（cron / タスクスケジューラ）

- Linux (cron):
  ```cron
  # 毎時 10分に全チャンネルを実行（venv を使う例）
  10 * * * * cd /path/to/ShortVideoMaker && /path/to/venv/bin/python -m svmu_multi.run --limit 5 >> logs/multi.log 2>&1
  ```

- Windows (タスク スケジューラ):
  - プログラム/スクリプト: `C:\\Path\\To\\python.exe`
  - 引数の追加: `-m svmu_multi.run --limit 5`
  - 開始 (作業) ディレクトリ: `E:\\002__DEV\\projects\\ShortVideoMaker`
  - もしくは PowerShell で手動起動:
    ```powershell
    cd E:\002__DEV\projects\ShortVideoMaker
    python -m svmu_multi.run --limit 5
    ```

注意: 各 YAML は個別に `OUTPUT_DIR` を変えておくと出力が混在しません。

## 補足

- ログ: 標準出力に表示。将来的にファイル/JSONログ対応を検討しています。


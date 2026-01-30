# Linux での仮想環境 (venv) 構築手順

本プロジェクトは venv を使って開発環境を構築します。以下は Linux (Ubuntu/Debian 系を想定) での基本的な手順です。

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
   python -m svmu.main --sheet "Sheet1" --output ./outputs --platform youtube --limit 5
   ```
   - Excel を使う場合は `.env` で `USE_GOOGLE_SHEETS=false` を設定し、
     ```bash
     python -m svmu.main --excel "./data/ideas.xlsx" --sheet "Sheet1" --output ./outputs --platform youtube --limit 5
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
5. シートの列（Excel/Google共通）を用意。既定で想定される列:
    - `id`（文字列/数値）
    - `title`（文字列）
    - `bullets`（文字列; 行区切りは `\n` または `・`）
    - `tags`（任意; CSV 文字列）
    - `description`（任意; 文字列）
    - `status`（文字列; `Ready` で処理対象。処理後は `Done` に更新）
    - `output_filename`（任意; 拡張子なし）
    - `platforms`（任意; CSV: `youtube,tiktok,instagram`）
    - `video_duration_sec`（任意; 整数秒）
    - 互換: `upload_url`, `uploaded_at`（互換維持用。初回成功時に埋まります）

6. 背景動画（mp4）を用意し、`.env` の `BACKGROUND_VIDEO` にパスを設定します。

7. 実行（生成→合成→シート更新）:
    - Excel利用時:
      ```bash
      python -m svmu.main --excel "$EXCEL_PATH" --sheet "Sheet1" --output ./outputs --platform youtube --limit 5
      ```
    - Googleスプレッドシート利用時（`USE_GOOGLE_SHEETS=true` 設定済み）:
      ```bash
      python -m svmu.main --sheet "Sheet1" --output ./outputs --platform youtube --limit 5
      ```

## 補足

- 長さ: `video_duration_sec` が指定されている場合、出力は `min(背景動画の長さ, 指定秒数)` に切り詰められます。ループ再生は行いません。
- TikTok / Instagram: これらのアップローダーは現状スタブです。実装されるまではスキップされます。
- ログ: 標準出力に表示。将来的にファイル/JSONログ対応を検討しています。

## ライセンス

MIT

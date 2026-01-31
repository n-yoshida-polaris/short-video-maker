from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

import yaml
from dotenv import load_dotenv


@dataclass
class AppConfig:
    excel_path: str
    sheet_name: Optional[str]
    background_video: str
    output_dir: str
    font_path: Optional[str]
    ffmpeg_path: Optional[str]
    # Google Sheets
    use_google_sheets: bool
    gsheet_spreadsheet_id: Optional[str]
    gsheet_service_account_json: Optional[str]
    status_ready: str
    status_done: str


def str_to_bool(v: str) -> bool:
    return str(v).strip().lower() in {"1", "true", "yes", "y"}


def load_config(config_yaml_path: Optional[str] = None) -> AppConfig:
    # .env overrides
    load_dotenv(override=True)

    cfg_yaml = {}
    if config_yaml_path and os.path.isfile(config_yaml_path):
        with open(config_yaml_path, "r", encoding="utf-8") as f:
            cfg_yaml = yaml.safe_load(f) or {}

    def get(name: str, default: Optional[str] = None):
        # YAML を優先し、無ければ環境変数、最後にデフォルト
        return os.getenv(name, default) if cfg_yaml.get(name) is None else cfg_yaml.get(name)

    # 設定を返す
    return AppConfig(
        excel_path=get("EXCEL_PATH", "./assets/ideas.xlsx"),
        sheet_name=get("SHEET_NAME", "Sheet1"),
        background_video=get("BACKGROUND_VIDEO", "./assets/background.mp4"),
        output_dir=get("OUTPUT_DIR", "./outputs"),
        font_path=get("FONT_PATH", "./assets/yu-mincho-demibold.ttf"),
        ffmpeg_path=get("FFMPEG_PATH", "./assets/ffmpeg.exe"),
        use_google_sheets=str_to_bool(str(get("USE_GOOGLE_SHEETS", "false"))),
        gsheet_spreadsheet_id=get("GSHEET_SPREADSHEET_ID", None),
        gsheet_service_account_json=get("GSHEET_SERVICE_ACCOUNT_JSON", None),
        status_ready=get("DEFAULT_STATUS_READY", "Ready"),
        status_done=get("DEFAULT_STATUS_DONE", "Done"),
    )

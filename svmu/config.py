from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional, List

import yaml
from dotenv import load_dotenv


@dataclass
class AppConfig:
    excel_path: str
    sheet_name: Optional[str]
    background_video: str
    output_dir: str
    font_path: Optional[str]
    default_platforms: List[str]
    ffmpeg_path: Optional[str]

    # Google Sheets
    use_google_sheets: bool
    gsheet_spreadsheet_id: Optional[str]
    gsheet_service_account_json: Optional[str]

    # YouTube
    yt_client_secrets: Optional[str]
    yt_token_path: Optional[str]
    privacy_status: str
    category_id: str
    made_for_kids: bool

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
        return os.getenv(name, cfg_yaml.get(name, default))

    default_platforms = get("default_platforms", "youtube")
    platforms_list = [p.strip().lower() for p in default_platforms.split(",") if p.strip()]

    return AppConfig(
        excel_path=get("EXCEL_PATH", "./data/ideas.xlsx"),
        sheet_name=get("SHEET_NAME", None),
        background_video=get("BACKGROUND_VIDEO", "./assets/background.mp4"),
        output_dir=get("OUTPUT_DIR", "./outputs"),
        font_path=get("FONT_PATH", None),
        default_platforms=platforms_list,
        ffmpeg_path=get("FFMPEG_PATH", None),
        use_google_sheets=str_to_bool(str(get("USE_GOOGLE_SHEETS", "false"))),
        gsheet_spreadsheet_id=get("GSHEET_SPREADSHEET_ID", None),
        gsheet_service_account_json=get("GSHEET_SERVICE_ACCOUNT_JSON", "./credentials/service_account.json"),
        yt_client_secrets=get("YOUTUBE_CLIENT_SECRETS", "./credentials/client_secrets.json"),
        yt_token_path=get("YOUTUBE_TOKEN_PATH", "./credentials/token.json"),
        privacy_status=get("DEFAULT_PRIVACY_STATUS", "private"),
        category_id=str(get("DEFAULT_CATEGORY_ID", "22")),
        made_for_kids=str_to_bool(str(get("DEFAULT_MADE_FOR_KIDS", "false"))),
        status_ready=get("DEFAULT_STATUS_READY", "Ready"),
        status_done=get("DEFAULT_STATUS_DONE", "Done"),
    )

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional, Tuple

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
    # Font colors (RGBA)
    title_color: Tuple[int, int, int, int]
    bullet_color: Tuple[int, int, int, int]
    # Google Sheets
    use_google_sheets: bool
    gsheet_spreadsheet_id: Optional[str]
    gsheet_service_account_json: Optional[str]
    status_ready: str
    status_done: str


def str_to_bool(v: str) -> bool:
    return str(v).strip().lower() in {"1", "true", "yes", "y"}


def _parse_hex_color(value: Optional[str], default: Tuple[int, int, int, int]) -> Tuple[int, int, int, int]:
    if not value or not isinstance(value, str):
        return default
    s = value.strip()
    if s.startswith('#'):
        s = s[1:]
    # Expand #RGB to #RRGGBB
    if len(s) == 3:
        try:
            r = int(s[0] * 2, 16)
            g = int(s[1] * 2, 16)
            b = int(s[2] * 2, 16)
            return (r, g, b, 255)
        except Exception:
            return default
    # #RRGGBB or #RRGGBBAA
    if len(s) == 6 or len(s) == 8:
        try:
            r = int(s[0:2], 16)
            g = int(s[2:4], 16)
            b = int(s[4:6], 16)
            a = int(s[6:8], 16) if len(s) == 8 else 255
            return (r, g, b, a)
        except Exception:
            return default
    return default


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

    # Colors: default to white
    default_white = (255, 255, 255, 255)
    title_color = _parse_hex_color(get("TITLE_COLOR", None), default_white)
    bullet_color = _parse_hex_color(get("BULLET_COLOR", None), default_white)

    # 設定を返す
    return AppConfig(
        excel_path=get("EXCEL_PATH", "./assets/ideas.xlsx"),
        sheet_name=get("SHEET_NAME", "Sheet1"),
        background_video=get("BACKGROUND_VIDEO", "./assets/background.mp4"),
        output_dir=get("OUTPUT_DIR", "./outputs"),
        font_path=get("FONT_PATH", "./assets/yu-mincho-demibold.ttf"),
        ffmpeg_path=get("FFMPEG_PATH", "./assets/ffmpeg.exe"),
        title_color=title_color,
        bullet_color=bullet_color,
        use_google_sheets=str_to_bool(str(get("USE_GOOGLE_SHEETS", "false"))),
        gsheet_spreadsheet_id=get("GSHEET_SPREADSHEET_ID", None),
        gsheet_service_account_json=get("GSHEET_SERVICE_ACCOUNT_JSON", None),
        status_ready=get("DEFAULT_STATUS_READY", "Ready"),
        status_done=get("DEFAULT_STATUS_DONE", "Done"),
    )

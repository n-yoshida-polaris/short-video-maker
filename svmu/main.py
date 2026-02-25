from __future__ import annotations

import argparse
import os
from datetime import datetime

from svmu.compose_video import compose_with_overlay, ComposeError, append_ending_if_exists
from svmu.config import load_config
from svmu.excel_io import ExcelStore
from svmu.google_sheets_io import GoogleSheetStore
from svmu.render_image import Renderer
from svmu.utils import safe_filename


def ensure_dirs(path: str):
    os.makedirs(path, exist_ok=True)


def process_row(
        cfg,
        idea,
        out_dir: str
) -> tuple[bool, str | None]:
    """
    Returns (success, base_name) where base_name is the file stem used for outputs.
    """
    print(f"\n[INFO] Processing id={idea.id} title={idea.title!r}")

    # 1) Render overlay image
    renderer = Renderer(
        font_path=cfg.font_path,
        title_color=cfg.title_color,
        bullet_color=cfg.bullet_color,
        title_shadow=cfg.title_shadow,
        bullet_shadow=cfg.bullet_shadow,
        shadow_offset=cfg.shadow_offset,
    )
    overlay_img = renderer.render(idea.title, idea.bullets)

    overlays_dir = os.path.join(out_dir, "overlays")
    ensure_dirs(overlays_dir)

    base_name = idea.output_filename or f"{idea.id}_{safe_filename(idea.title)}"
    overlay_path = os.path.join(overlays_dir, base_name + ".png")
    renderer.save_png(overlay_img, overlay_path)
    print(f"[OK] Overlay saved: {overlay_path}")

    # 2) Compose video
    outputs_dir = os.path.join(out_dir, "videos")
    ensure_dirs(outputs_dir)
    video_out = os.path.join(outputs_dir, base_name + ".mp4")

    try:
        print(cfg.background_video, overlay_path, video_out)
        compose_with_overlay(
            background_video=cfg.background_video,
            overlay_png=overlay_path,
            output_path=video_out,
            video_codec="libx264",
            crf=20,
            preset="medium",
            ffmpeg_path=cfg.ffmpeg_path,
        )
    except FileNotFoundError as e:
        print(f"[ERROR] File not exist: {e} {e.filename}")
        return False, None
    except ComposeError as e:
        print(f"[ERROR] Compose failed: {e}")
        return False, None

    print(f"[OK] Video composed: {video_out}")

    # 2.5) Append ending clip if available under APP_ROOT/ending
    try:
        appended = append_ending_if_exists(
            main_video_path=video_out,
            ffmpeg_path=cfg.ffmpeg_path,
            video_codec="libx264",
            crf=20,
            preset="medium",
        )
        if appended:
            print("[OK] Ending clip appended to the video.")
        else:
            print("[INFO] No ending clip found or append skipped.")
    except Exception as e:
        print(f"[WARN] Failed to append ending clip: {e}")

    # 3) Upload step removed: skip uploads and return compose success only
    print("[INFO] Upload step is disabled; only rendering and composition are performed.")
    return True, base_name


def main():
    parser = argparse.ArgumentParser(description="Short Video Make and Upload")
    parser.add_argument("--excel", dest="excel_path", default=None, help="Path to Excel .xlsx")
    parser.add_argument("--sheet", dest="sheet_name", default=None, help="Sheet name")
    parser.add_argument("--output", dest="output_dir", default=None, help="Output directory")
    parser.add_argument("--limit", dest="limit", type=int, default=10, help="Max rows to process")
    parser.add_argument("--config", dest="config_yaml", default=None, help="Optional config.yaml path")

    args = parser.parse_args()

    cfg = load_config(args.config_yaml)

    # CLI overrides
    excel_path = args.excel_path or cfg.excel_path
    sheet_name = args.sheet_name or cfg.sheet_name
    out_dir = args.output_dir or cfg.output_dir

    ensure_dirs(out_dir)

    # Select data store: Google Sheets if enabled, otherwise Excel
    if cfg.use_google_sheets:
        if not cfg.gsheet_spreadsheet_id:
            raise ValueError("USE_GOOGLE_SHEETS is true but GSHEET_SPREADSHEET_ID is not set.")
        store = GoogleSheetStore(
            spreadsheet_id=cfg.gsheet_spreadsheet_id,
            sheet_name=sheet_name,
            service_account_json=cfg.gsheet_service_account_json or "./credentials/service_account.json",
        )
    else:
        store = ExcelStore(excel_path=excel_path, sheet_name=sheet_name)
        print(f"[INFO] Using Excel file: {excel_path} sheet={sheet_name or '(default)'}")

    # 準備中のみ取得
    rows = store.read_ready(status_ready=cfg.status_ready)

    if not rows:
        print("[INFO] No rows with Ready status.")
        return

    processed = 0
    for idea in rows:
        if processed >= args.limit:
            break
        success, base_name = process_row(cfg, idea, out_dir)
        if success:
            # Mark as Done and record filenames and timestamp
            ts = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
            success = store.write_status(
                row_index=idea.idx,
                status_done=cfg.status_done,
                output_filename=base_name,
                output_datetime=ts)
            processed += 1

        if not success:
            print("[WARN] Processing failed; Excel/Sheet not updated.")

    print(f"\n[DONE] Processed {processed} rows (limit={args.limit}).")


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
import os
from datetime import datetime
from typing import Optional

from svmu.compose_video import compose_with_overlay, ComposeError, append_ending_if_exists
from svmu.config import load_config, _parse_hex_color, _parse_offset
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
        bullet_line_spacing=cfg.bullet_line_spacing,
        stroke_width=cfg.stroke_width,
        title_stroke_color=cfg.title_stroke_color,
        bullet_stroke_color=cfg.bullet_stroke_color,
        title_font_weight=cfg.title_font_weight,
        bullet_font_weight=cfg.bullet_font_weight,
        bullet_x_align=cfg.bullet_x_align,
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

    # 2.5) Append ending clip if available
    try:
        appended = append_ending_if_exists(
            main_video_path=video_out,
            ffmpeg_path=cfg.ffmpeg_path,
            video_codec="libx264",
            crf=20,
            preset="medium",
            ending_dir=cfg.ending_video,
        )
        if appended:
            print("[OK] Ending clip appended to the video.")
        else:
            print("[INFO] No ending clip found or append skipped.")
    except Exception as e:
        print(f"[WARN] Failed to append ending clip: {e}")

    return True, base_name


def run(
        config_yaml: Optional[str] = None,
        excel_path: Optional[str] = None,
        sheet_name: Optional[str] = None,
        output_dir: Optional[str] = None,
        limit: int = 10,
        title: Optional[str] = None,
        bullets: Optional[list] = None,
        idea_id: Optional[str] = None,
        output_filename: Optional[str] = None,
        background_video: Optional[str] = None,
        font_path: Optional[str] = None,
        ffmpeg_path: Optional[str] = None,
        ending_video: Optional[str] = None,
        title_color: Optional[str] = None,
        bullet_color: Optional[str] = None,
        title_shadow: Optional[str] = None,
        bullet_shadow: Optional[str] = None,
        shadow_offset: Optional[str] = None,
        bullet_line_spacing: Optional[float] = None,
        stroke_width: Optional[int] = None,
        title_stroke_color: Optional[str] = None,
        bullet_stroke_color: Optional[str] = None,
        title_font_weight: Optional[int] = None,
        bullet_font_weight: Optional[int] = None,
        bullet_x_align: Optional[str] = None,
        use_google_sheets: Optional[bool] = None,
        gsheet_id: Optional[str] = None,
        gsheet_sa_json: Optional[str] = None,
        status_ready: Optional[str] = None,
        status_done: Optional[str] = None,
) -> int:
    """Core processing logic. Returns the number of successfully processed rows."""
    from svmu.excel_io import IdeaRow

    cfg = load_config(config_yaml)

    # Apply CLI overrides (highest priority)
    if background_video is not None:
        cfg.background_video = background_video
    if font_path is not None:
        cfg.font_path = font_path
    if ffmpeg_path is not None:
        cfg.ffmpeg_path = ffmpeg_path
    if ending_video is not None:
        cfg.ending_video = ending_video
    if title_color is not None:
        cfg.title_color = _parse_hex_color(title_color, cfg.title_color)
    if bullet_color is not None:
        cfg.bullet_color = _parse_hex_color(bullet_color, cfg.bullet_color)
    if title_shadow is not None:
        cfg.title_shadow = _parse_hex_color(title_shadow, cfg.title_shadow)
    if bullet_shadow is not None:
        cfg.bullet_shadow = _parse_hex_color(bullet_shadow, cfg.bullet_shadow)
    if shadow_offset is not None:
        cfg.shadow_offset = _parse_offset(shadow_offset, cfg.shadow_offset)
    if bullet_line_spacing is not None:
        cfg.bullet_line_spacing = bullet_line_spacing
    if stroke_width is not None:
        cfg.stroke_width = stroke_width
    if title_stroke_color is not None:
        cfg.title_stroke_color = _parse_hex_color(title_stroke_color, cfg.title_stroke_color)
    if bullet_stroke_color is not None:
        cfg.bullet_stroke_color = _parse_hex_color(bullet_stroke_color, cfg.bullet_stroke_color)
    if title_font_weight is not None:
        cfg.title_font_weight = title_font_weight
    if bullet_font_weight is not None:
        cfg.bullet_font_weight = bullet_font_weight
    if bullet_x_align is not None:
        cfg.bullet_x_align = bullet_x_align
    if use_google_sheets is not None:
        cfg.use_google_sheets = use_google_sheets
    if gsheet_id is not None:
        cfg.gsheet_spreadsheet_id = gsheet_id
    if gsheet_sa_json is not None:
        cfg.gsheet_service_account_json = gsheet_sa_json
    if status_ready is not None:
        cfg.status_ready = status_ready
    if status_done is not None:
        cfg.status_done = status_done

    out_dir = output_dir or cfg.output_dir
    ensure_dirs(out_dir)

    # Direct mode: skip spreadsheet entirely
    if title is not None:
        _id = idea_id or datetime.now().strftime("%Y%m%d%H%M%S")
        bullets_str = "\n".join(bullets) if bullets else ""
        idea = IdeaRow(
            idx=0,
            id=_id,
            title=title,
            bullets=bullets_str,
            tags=None,
            description=None,
            status="Ready",
            output_filename=output_filename,
            output_datetime=None,
        )
        success, base_name = process_row(cfg, idea, out_dir)
        if success:
            print(f"\n[DONE] Video created: {base_name}")
        else:
            print("\n[FAILED] Video creation failed.")
        return 1 if success else 0

    # Spreadsheet mode
    excel_path = excel_path or cfg.excel_path
    sheet_name = sheet_name or cfg.sheet_name

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

    rows = None
    try:
        rows = store.read_ready(status_ready=cfg.status_ready)
    except Exception:
        print(f"[WARN] Couldn't read rows from sheets. :{sheet_name}")

    if not rows:
        print("[INFO] No rows with Ready status.")
        return 0

    processed = 0
    for idea in rows:
        if processed >= limit:
            break
        success, base_name = process_row(cfg, idea, out_dir)
        if success:
            ts = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
            success = store.write_status(
                row_index=idea.idx,
                status_done=cfg.status_done,
                output_filename=base_name,
                output_datetime=ts)
            processed += 1

        if not success:
            print("[WARN] Processing failed; Excel/Sheet not updated.")

    print(f"\n[DONE] Processed {processed} rows (limit={limit}).")
    return processed


def main():
    parser = argparse.ArgumentParser(
        description="Short Video Make and Upload",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Direct mode (no spreadsheet):\n"
            "  python -m svmu.main --title \"タイトル\" --bullet \"項目1\" --bullet \"項目2\"\n\n"
            "Spreadsheet mode:\n"
            "  python -m svmu.main --excel ./assets/ideas.xlsx --limit 5"
        ),
    )

    # --- Direct mode ---
    direct = parser.add_argument_group("ダイレクトモード（スプレッドシート不要）")
    direct.add_argument("--title", dest="title", default=None,
                        help="動画タイトル（指定するとダイレクトモードで起動）")
    direct.add_argument("--bullet", dest="bullets", action="append", default=None, metavar="TEXT",
                        help="箇条書き1行（複数回指定可）")
    direct.add_argument("--id", dest="idea_id", default=None,
                        help="出力ファイル名のプレフィックス（省略時は実行日時）")
    direct.add_argument("--output-filename", dest="output_filename", default=None,
                        help="出力ファイル名（拡張子なし）。指定するとプレフィックス+タイトルより優先される")

    # --- Spreadsheet mode ---
    sheet = parser.add_argument_group("スプレッドシートモード")
    sheet.add_argument("--excel", dest="excel_path", default=None,
                       help="Excel ファイルのパス (.xlsx)")
    sheet.add_argument("--sheet", dest="sheet_name", default=None,
                       help="読み込むシート名")
    sheet.add_argument("--limit", dest="limit", type=int, default=10,
                       help="最大処理件数（デフォルト: 10）")
    sheet.add_argument("--use-google-sheets", dest="use_google_sheets", action="store_true", default=None,
                       help="Google スプレッドシートを使用する")
    sheet.add_argument("--gsheet-id", dest="gsheet_id", default=None,
                       help="Google スプレッドシートの ID")
    sheet.add_argument("--gsheet-sa-json", dest="gsheet_sa_json", default=None,
                       help="サービスアカウント JSON ファイルのパス")
    sheet.add_argument("--status-ready", dest="status_ready", default=None,
                       help="処理対象とみなすステータス値（デフォルト: Ready）")
    sheet.add_argument("--status-done", dest="status_done", default=None,
                       help="処理完了後に書き込むステータス値（デフォルト: Done）")

    # --- Video / output ---
    video = parser.add_argument_group("動画・出力")
    video.add_argument("--output", dest="output_dir", default=None,
                       help="出力ディレクトリ")
    video.add_argument("--background", dest="background_video", default=None,
                       help="背景動画のパス（.mp4 またはディレクトリ）")
    video.add_argument("--ending", dest="ending_video", default=None,
                       help="エンディング動画ディレクトリのパス")
    video.add_argument("--ffmpeg", dest="ffmpeg_path", default=None,
                       help="ffmpeg 実行ファイルのパス")

    # --- Style ---
    style = parser.add_argument_group("スタイル")
    style.add_argument("--font", dest="font_path", default=None,
                       help="フォントファイルのパス（OTF/TTF）")
    style.add_argument("--title-color", dest="title_color", default=None, metavar="COLOR",
                       help="タイトルの文字色（例: #FFFFFF）")
    style.add_argument("--bullet-color", dest="bullet_color", default=None, metavar="COLOR",
                       help="箇条書きの文字色（例: #FFFFFF）")
    style.add_argument("--title-shadow", dest="title_shadow", default=None, metavar="COLOR",
                       help="タイトルの影色（例: #000000B4）")
    style.add_argument("--bullet-shadow", dest="bullet_shadow", default=None, metavar="COLOR",
                       help="箇条書きの影色（例: #000000A0）")
    style.add_argument("--shadow-offset", dest="shadow_offset", default=None, metavar="X,Y",
                       help="影のオフセット（例: 2,2）")
    style.add_argument("--bullet-line-spacing", dest="bullet_line_spacing", type=float, default=None, metavar="N",
                       help="箇条書きの行間倍率（デフォルト: 1.7）")
    style.add_argument("--stroke-width", dest="stroke_width", type=int, default=None, metavar="PX",
                       help="文字の縁取り幅(px)。0で無効（デフォルト: 0）")
    style.add_argument("--title-stroke-color", dest="title_stroke_color", default=None, metavar="COLOR",
                       help="タイトルの縁取り色（例: #000028）")
    style.add_argument("--bullet-stroke-color", dest="bullet_stroke_color", default=None, metavar="COLOR",
                       help="箇条書きの縁取り色（例: #000028）")
    style.add_argument("--title-font-weight", dest="title_font_weight", type=int, default=None, metavar="WGHT",
                       help="タイトルのフォントウェイト（可変フォントのwght軸。例: 700=Bold）")
    style.add_argument("--bullet-font-weight", dest="bullet_font_weight", type=int, default=None, metavar="WGHT",
                       help="箇条書きのフォントウェイト（可変フォントのwght軸。例: 500=Medium）")
    style.add_argument("--bullet-align", dest="bullet_x_align", default=None, choices=["left", "center"],
                       help="箇条書きの横揃え（デフォルト: left）")

    # --- Config ---
    parser.add_argument("--config", dest="config_yaml", default=None,
                        help="追加設定の YAML ファイルパス")

    args = parser.parse_args()

    run(
        config_yaml=args.config_yaml,
        excel_path=args.excel_path,
        sheet_name=args.sheet_name,
        output_dir=args.output_dir,
        limit=args.limit,
        title=args.title,
        bullets=args.bullets,
        idea_id=args.idea_id,
        output_filename=args.output_filename,
        background_video=args.background_video,
        font_path=args.font_path,
        ffmpeg_path=args.ffmpeg_path,
        ending_video=args.ending_video,
        title_color=args.title_color,
        bullet_color=args.bullet_color,
        title_shadow=args.title_shadow,
        bullet_shadow=args.bullet_shadow,
        shadow_offset=args.shadow_offset,
        bullet_line_spacing=args.bullet_line_spacing,
        stroke_width=args.stroke_width,
        title_stroke_color=args.title_stroke_color,
        bullet_stroke_color=args.bullet_stroke_color,
        title_font_weight=args.title_font_weight,
        bullet_font_weight=args.bullet_font_weight,
        bullet_x_align=args.bullet_x_align,
        use_google_sheets=args.use_google_sheets if args.use_google_sheets else None,
        gsheet_id=args.gsheet_id,
        gsheet_sa_json=args.gsheet_sa_json,
        status_ready=args.status_ready,
        status_done=args.status_done,
    )


if __name__ == "__main__":
    main()
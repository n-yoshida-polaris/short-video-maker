from __future__ import annotations

import os
import random
import shutil
import subprocess
from pprint import pprint
from typing import Optional, List


def _project_root() -> str:
    # svmu directory -> project root
    return os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))


def _first_mp4_in(dir_path: str) -> Optional[str]:
    if not os.path.isdir(dir_path):
        return None
    for base, _, files in os.walk(dir_path):
        for fn in sorted(files):
            if fn.lower().endswith(".mp4"):
                return os.path.join(base, fn)
    return None


class ComposeError(Exception):
    pass


def _collect_mp4_files(root: str) -> List[str]:
    files: List[str] = []
    for base, _, filenames in os.walk(root):
        for fn in filenames:
            if fn.lower().endswith(".mp4"):
                files.append(os.path.join(base, fn))
    return files


def _resolve_background_video(path: str) -> str:
    """Return a concrete mp4 file.
    - If path is a file, validate and return it.
    - If path is a directory, pick a random .mp4 under it (recursive).
    """
    if os.path.isdir(path):
        candidates = _collect_mp4_files(path)
        if not candidates:
            raise ComposeError(f"No .mp4 files found under directory: {path}")
        return random.choice(candidates)
    if os.path.isfile(path):
        if not path.lower().endswith(".mp4"):
            raise ComposeError(f"Background video must be an .mp4 file: {path}")
        return path
    raise ComposeError(f"Background path not found: {path}")


def compose_with_overlay(
        background_video: str,
        overlay_png: str,
        output_path: str,
        video_codec: str = "libx264",
        crf: int = 20,
        preset: str = "medium",
        fps: Optional[int] = None,
        ffmpeg_path: Optional[str] = None,
) -> None:
    """
    Compose a vertical 1080x1920 video by scaling/cropping background to fill and overlaying the PNG centered.
    Keeps original background audio. Optionally trims duration (no looping).
    Accepts a file path or a directory for background_video; if a directory, a random .mp4 inside it is chosen.
    """
    # Resolve background video (file or directory)
    bg_file = _resolve_background_video(background_video)

    if not os.path.isfile(overlay_png):
        raise ComposeError(f"Overlay PNG not found: {overlay_png}")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Build filter graph
    vf = (
        "[0:v]scale=w=1080:h=1920:force_original_aspect_ratio=increase,"
        "crop=1080:1920,setsar=1[bg];"
        "[1:v]scale=1080:1920:force_original_aspect_ratio=decrease[ov];"
        "[bg][ov]overlay=(W-w)/2:(H-h)/2[v]"
    )
    exe = ffmpeg_path or "ffmpeg"
    cmd = [
        exe,
        "-y",
        "-i",
        bg_file,
        "-i",
        overlay_png,
        "-filter_complex",
        vf,
        "-map",
        "[v]",
        "-map",
        "0:a?",
        "-c:v",
        video_codec,
        "-preset",
        preset,
        "-crf",
        str(crf),
        "-pix_fmt",
        "yuv420p",
        "-shortest",
    ]

    if fps:
        cmd += ["-r", str(fps)]

    cmd += [output_path]

    try:
        resolved = shutil.which(exe) if exe == "ffmpeg" else exe
        print(resolved)
        pprint(cmd)
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        raise ComposeError(f"ffmpeg failed with code {e.returncode}") from e


def append_ending_if_exists(
        main_video_path: str,
        ffmpeg_path: Optional[str] = None,
        video_codec: str = "libx264",
        crf: int = 20,
        preset: str = "medium",
        ending_dir: Optional[str] = None,
) -> bool:
    """
    Append an ending clip if available.
    - If ending_dir is provided, search that directory (recursive) for the first .mp4.
    - Otherwise, fallback to APP_ROOT/ending.
    Returns True if appended, False if no ending was found or on safe no-op.
    On ffmpeg failure, leaves the original file intact and returns False.
    """
    try:
        if not os.path.isfile(main_video_path):
            return False

        # Resolve ending directory (YAML-configurable) or default to project ./ending
        search_dir = ending_dir if ending_dir else os.path.join(_project_root(), "ending")
        ending_mp4 = _first_mp4_in(search_dir)
        if not ending_mp4:
            # No ending clip -> nothing to do
            return False

        tmp_out = main_video_path + ".tmp_concat.mp4"
        if os.path.exists(tmp_out):
            try:
                os.remove(tmp_out)
            except Exception:
                pass

        exe = ffmpeg_path or "ffmpeg"
        # Concat with re-encode to avoid codec mismatch problems
        filter_graph = (
            "[0:v][0:a][1:v][1:a]concat=n=2:v=1:a=1[v][a]"
        )
        cmd = [
            exe,
            "-y",
            "-i", main_video_path,
            "-i", ending_mp4,
            "-filter_complex", filter_graph,
            "-map", "[v]",
            "-map", "[a]",
            "-c:v", video_codec,
            "-preset", preset,
            "-crf", str(crf),
            "-pix_fmt", "yuv420p",
            "-shortest",
            tmp_out,
        ]

        try:
            resolved = shutil.which(exe) if exe == "ffmpeg" else exe
            print(resolved)
            pprint(cmd)
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError:
            # Keep original video if concat fails
            return False

        # Replace original with concatenated output
        try:
            os.replace(tmp_out, main_video_path)
        except Exception:
            # Cleanup temp if replace failed
            try:
                os.remove(tmp_out)
            except Exception:
                pass
            return False

        print(f"[OK] Ending appended: {ending_mp4}")
        return True
    except Exception as _:
        # Be conservative: do not break the flow
        return False

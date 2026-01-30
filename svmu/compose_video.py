from __future__ import annotations

import os
import random
import shutil
import subprocess
from pprint import pprint
from typing import Optional, List


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
        duration_sec: Optional[int] = None,
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
    if duration_sec and duration_sec > 0:
        cmd += ["-t", str(duration_sec)]

    cmd += [output_path]

    try:
        print("##################################################")
        resolved = shutil.which(exe) if exe == "ffmpeg" else exe
        print(resolved)
        pprint(cmd)
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        raise ComposeError(f"ffmpeg failed with code {e.returncode}") from e

from __future__ import annotations

import os
from typing import Tuple, List, Optional

from PIL import Image, ImageDraw, ImageFont

# 縦動画 縦横
CANVAS_W = 1080
CANVAS_H = 1920

# Youtube や SNS 表示時に隠れるサイドの余白(px)
SIDE_HIDDEN_MARGIN = 50

# タイトル
TITLE_FONT_SIZE = 92
TITLE_LINE_SPACING = 1.3
TITLE_X_ALIGN = "center"  # "center" or "left"
TITLE_X = 90  # タイトル開始位置(左：絶対位置) Used when TITLE_X_ALIGN == "left"
TITLE_Y = 240 # タイトル開始位置(上：絶対位置)
TITLE_COLOR = (255, 255, 255, 255)
TITLE_SHADOW = (0, 0, 0, 180)

# 本文
BULLET_FONT_SIZE = 48
BULLET_LINE_SPACING = 1.7
BULLET_PREFIX = ""
BULLET_X = 90   # 本文開始位置(左：絶対位置)
BULLET_Y = 560  # 本文開始位置(上：絶対位置)
BULLET_COLOR = (255, 255, 255, 255)
BULLET_SHADOW = (0, 0, 0, 160)


# 影設定
SHADOW_OFFSET = (2, 2)

# タイトルと本文の最大幅
MAX_TEXT_W = 900


class Renderer:
    def __init__(self, font_path: Optional[str] = None):
        # Try to load a Mincho/serif font; fall back to default
        self.title_font = self._load_font(font_path, TITLE_FONT_SIZE)
        self.text_font = self._load_font(font_path, BULLET_FONT_SIZE)

    @staticmethod
    def _load_font(font_path: Optional[str], size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        try:
            if font_path and os.path.isfile(font_path):
                return ImageFont.truetype(font_path, size=size)
        except Exception:
            pass
        # Try commonly available fonts on Linux
        for candidate in [
            "/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc",
            "/usr/share/fonts/opentype/noto/NotoSerifCJKjp-Regular.otf",
            "/usr/share/fonts/truetype/noto/NotoSerifCJK-Regular.ttc",
            "/usr/share/fonts/truetype/noto/NotoSerifJP-Regular.otf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
        ]:
            try:
                if os.path.isfile(candidate):
                    return ImageFont.truetype(candidate, size=size)
            except Exception:
                continue
        return ImageFont.load_default()

    @staticmethod
    def _measure(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> Tuple[int, int]:
        # PIL deprecates ImageDraw.textsize; use textbbox for accurate size
        # Returns (width, height)
        try:
            left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
            return right - left, bottom - top
        except Exception:
            # Fallback to font.getsize for older Pillow versions
            try:
                return font.getsize(text)
            except Exception:
                # As a last resort, approximate by length
                return (len(text) * (font.size if hasattr(font, 'size') else 10),
                        font.size if hasattr(font, 'size') else 10)

    def _wrap_text(self, text: str, font: ImageFont.ImageFont, max_width: int, draw: ImageDraw.ImageDraw) -> List[str]:
        # Handle Japanese by measuring by character; break on \n or when width exceeds
        lines: List[str] = []
        for raw_line in text.replace("\r", "").split("\n"):
            if not raw_line:
                lines.append("")
                continue
            current = ""
            for ch in raw_line:
                candidate = current + ch
                w, _ = self._measure(draw, candidate, font)
                if w <= max_width:
                    current = candidate
                else:
                    if current:
                        lines.append(current)
                    current = ch
            if current:
                lines.append(current)
        return lines

    def render(self, title: str, bullets: str) -> Image.Image:
        # Transparent canvas; overlay atop video
        img = Image.new("RGBA", (CANVAS_W, CANVAS_H), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        max_text_w = MAX_TEXT_W

        # Title at fixed position
        title_lines = self._wrap_text(title, self.title_font, max_text_w, draw)
        y = TITLE_Y
        for line in title_lines:
            tw, th = self._measure(draw, line, self.title_font)
            if TITLE_X_ALIGN == "center":
                tx = (CANVAS_W - tw) // 2
            else:
                tx = TITLE_X
            # Shadow
            draw.text((tx + SHADOW_OFFSET[0], y + SHADOW_OFFSET[1]), line, font=self.title_font, fill=TITLE_SHADOW)
            draw.text((tx, y), line, font=self.title_font, fill=TITLE_COLOR)
            y += int(th * TITLE_LINE_SPACING)

        # Bullets center area
        bullet_text = bullets.replace("\r", "").strip()
        if "\n" not in bullet_text and "・" in bullet_text:
            bullet_items = [s.strip() for s in bullet_text.split("・") if s.strip()]
        else:
            bullet_items = [s.strip() for s in bullet_text.split("\n") if s.strip()]

        bullet_lines: List[str] = []
        for item in bullet_items:
            wrapped = self._wrap_text(item, self.text_font, max_text_w, draw)
            if not wrapped:
                continue
            # Prefix first line with bullet mark
            bullet_lines.append(f"{BULLET_PREFIX}{wrapped[0]}")
            for cont in wrapped[1:]:
                bullet_lines.append(f"  {cont}")

        # Bullets at fixed position
        y2 = BULLET_Y
        for line in bullet_lines:
            lw, lh = self._measure(draw, line, self.text_font)
            x = BULLET_X
            # Shadow
            draw.text((x + SHADOW_OFFSET[0], y2 + SHADOW_OFFSET[1]), line, font=self.text_font, fill=BULLET_SHADOW)
            draw.text((x, y2), line, font=self.text_font, fill=BULLET_COLOR)
            y2 += int(lh * BULLET_LINE_SPACING)

        return img

    def save_png(self, img: Image.Image, path: str) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        img.save(path, format="PNG")

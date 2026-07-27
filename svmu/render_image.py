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
BULLET_X_ALIGN = "left"  # "center" or "left"
BULLET_X = 90   # 本文開始位置(左：絶対位置) Used when BULLET_X_ALIGN == "left"
BULLET_Y = 560  # 本文開始位置(上：絶対位置)
BULLET_COLOR = (255, 255, 255, 255)
BULLET_SHADOW = (0, 0, 0, 160)


# 影設定
SHADOW_OFFSET = (2, 2)

# ストローク（縁取り）。STROKE_WIDTH=0 で無効
STROKE_WIDTH = 0
TITLE_STROKE_COLOR = (0, 0, 40, 255)
BULLET_STROKE_COLOR = (0, 0, 40, 255)

# フォントウェイト（可変フォントの wght 軸）。None = フォント既定値のまま
TITLE_FONT_WEIGHT = None
BULLET_FONT_WEIGHT = None

# タイトルと本文の最大幅
MAX_TEXT_W = 900


class Renderer:
    def __init__(self, font_path: Optional[str] = None,
                 title_color: Optional[Tuple[int, int, int, int]] = None,
                 bullet_color: Optional[Tuple[int, int, int, int]] = None,
                 title_shadow: Optional[Tuple[int, int, int, int]] = None,
                 bullet_shadow: Optional[Tuple[int, int, int, int]] = None,
                 shadow_offset: Optional[Tuple[int, int]] = None,
                 bullet_line_spacing: Optional[float] = None,
                 stroke_width: Optional[int] = None,
                 title_stroke_color: Optional[Tuple[int, int, int, int]] = None,
                 bullet_stroke_color: Optional[Tuple[int, int, int, int]] = None,
                 title_font_weight: Optional[int] = None,
                 bullet_font_weight: Optional[int] = None,
                 bullet_x_align: Optional[str] = None):
        # Try to load a Mincho/serif font; fall back to default
        self.title_font = self._load_font(font_path, TITLE_FONT_SIZE,
                                           title_font_weight if title_font_weight is not None else TITLE_FONT_WEIGHT)
        self.text_font = self._load_font(font_path, BULLET_FONT_SIZE,
                                          bullet_font_weight if bullet_font_weight is not None else BULLET_FONT_WEIGHT)
        # Colors
        self.title_color = title_color or TITLE_COLOR
        self.bullet_color = bullet_color or BULLET_COLOR
        # Shadows
        self.title_shadow = title_shadow or TITLE_SHADOW
        self.bullet_shadow = bullet_shadow or BULLET_SHADOW
        self.shadow_offset = shadow_offset or SHADOW_OFFSET
        # Line spacing
        self.bullet_line_spacing = bullet_line_spacing if bullet_line_spacing is not None else BULLET_LINE_SPACING
        # Stroke (outline)
        self.stroke_width = stroke_width if stroke_width is not None else STROKE_WIDTH
        self.title_stroke_color = title_stroke_color or TITLE_STROKE_COLOR
        self.bullet_stroke_color = bullet_stroke_color or BULLET_STROKE_COLOR
        # Alignment
        self.bullet_x_align = bullet_x_align or BULLET_X_ALIGN

    @staticmethod
    def _load_font(font_path: Optional[str], size: int,
                    weight: Optional[int] = None) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        font = None
        try:
            if font_path and os.path.isfile(font_path):
                font = ImageFont.truetype(font_path, size=size)
        except Exception:
            font = None
        if font is None:
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
                        font = ImageFont.truetype(candidate, size=size)
                        break
                except Exception:
                    continue
        if font is None:
            font = ImageFont.load_default()

        if weight is not None:
            try:
                axes = font.get_variation_axes()
                if len(axes) == 1:
                    font.set_variation_by_axes([weight])
                else:
                    values = [ax.get("default") or 400 for ax in axes]
                    for i, ax in enumerate(axes):
                        name = ax.get("name") or b""
                        if b"weight" in name.lower():
                            values[i] = weight
                    font.set_variation_by_axes(values)
            except Exception:
                # Not a variable font, or variation axes unsupported; keep as-is
                pass

        return font

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
            draw.text((tx + self.shadow_offset[0], y + self.shadow_offset[1]), line, font=self.title_font, fill=self.title_shadow)
            draw.text((tx, y), line, font=self.title_font, fill=self.title_color,
                      stroke_width=self.stroke_width, stroke_fill=self.title_stroke_color)
            y += int(th * TITLE_LINE_SPACING)

        # Bullets center area
        bullet_text = bullets.replace("\r", "")
        if "\n" not in bullet_text and "・" in bullet_text:
            # When using '・' delimiter, keep non-empty items only
            bullet_items = [s.strip() for s in bullet_text.split("・") if s.strip()]
        else:
            # Preserve in-between empty lines, but drop trailing empty lines
            # tmp_items = [s.strip() for s in bullet_text.split("\n")]
            tmp_items = [s for s in bullet_text.split("\n")]
            # Remove empty lines at the end only
            while tmp_items and tmp_items[-1] == "":
                tmp_items.pop()
            bullet_items = tmp_items

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
            # If the line is empty, create vertical spacing but don't draw text
            if line == "":
                base_h = getattr(self.text_font, "size", 12)
                y2 += int(base_h * self.bullet_line_spacing)
                continue
            lw, lh = self._measure(draw, line, self.text_font)
            if lh == 0:
                lh = getattr(self.text_font, "size", 12)
            if self.bullet_x_align == "center":
                x = (CANVAS_W - lw) // 2
            else:
                x = BULLET_X
            # Shadow
            draw.text((x + self.shadow_offset[0], y2 + self.shadow_offset[1]), line, font=self.text_font, fill=self.bullet_shadow)
            draw.text((x, y2), line, font=self.text_font, fill=self.bullet_color,
                      stroke_width=self.stroke_width, stroke_fill=self.bullet_stroke_color)
            y2 += int(lh * self.bullet_line_spacing)

        return img

    def save_png(self, img: Image.Image, path: str) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        img.save(path, format="PNG")

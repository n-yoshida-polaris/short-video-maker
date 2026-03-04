from __future__ import annotations

import re
import unicodedata


def safe_filename(name: str, max_len: int = 80, replacement: str = "_") -> str:
    # Normalize and strip control characters
    s = unicodedata.normalize("NFKC", name).strip()
    # Replace slashes and illegal characters
    s = re.sub(r"[\\/:*?\"<>|]", replacement, s)
    s = re.sub(r"\s+", " ", s)
    s = s.strip()
    if len(s) > max_len:
        s = s[:max_len].rstrip()
    # Avoid empty
    return s or "video"

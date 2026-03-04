from __future__ import annotations

from typing import Dict, Any


class TikTokUploader:
    def upload(self, video_path: str, title: str, description: str = "", tags: list[str] | None = None) -> Dict[str, Any]:
        # Placeholder: not implemented yet
        raise NotImplementedError("TikTok upload is not implemented yet.")


class InstagramUploader:
    def upload(self, video_path: str, title: str, description: str = "", tags: list[str] | None = None) -> Dict[str, Any]:
        # Placeholder: not implemented yet
        raise NotImplementedError("Instagram upload is not implemented yet.")

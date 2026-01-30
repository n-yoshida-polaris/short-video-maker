from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

import pandas as pd

DEFAULT_COLUMNS = [
    "id",
    "title",
    "bullets",
    "tags",
    "description",
    "status",
    "output_filename",
    "platforms",
    "video_duration_sec",
    # Legacy (kept for backward compatibility)
    "upload_url",
    "uploaded_at",
]


@dataclass
class IdeaRow:
    idx: int  # DataFrame index
    id: str
    title: str
    bullets: str
    tags: Optional[str]
    description: Optional[str]
    status: str
    output_filename: Optional[str]
    platforms: Optional[str]
    video_duration_sec: Optional[int]


class ExcelStore:
    def __init__(self, excel_path: str, sheet_name: Optional[str] = None):
        self.excel_path = excel_path
        self.sheet_name = sheet_name
        if not os.path.isfile(self.excel_path):
            raise FileNotFoundError(f"Excel not found: {self.excel_path}")

    def read_ready(self, status_ready: str = "Ready") -> List[IdeaRow]:
        df = pd.read_excel(self.excel_path, sheet_name=self.sheet_name)
        # Ensure all columns exist
        for col in DEFAULT_COLUMNS:
            if col not in df.columns:
                df[col] = None
        df = df.fillna("")
        ready_df = df[df["status"].astype(str).str.lower() == status_ready.lower()]
        rows: List[IdeaRow] = []
        for idx, r in ready_df.iterrows():
            rows.append(
                IdeaRow(
                    idx=idx,
                    id=str(r["id"]) if str(r["id"]).strip() != "" else str(idx),
                    title=str(r["title"]).strip(),
                    bullets=str(r["bullets"]).strip(),
                    tags=str(r["tags"]).strip() or None,
                    description=str(r["description"]).strip() or None,
                    status=str(r["status"]).strip(),
                    output_filename=str(r["output_filename"]).strip() or None,
                    platforms=str(r["platforms"]).strip() or None,
                    video_duration_sec=int(r["video_duration_sec"]) if str(
                        r["video_duration_sec"]).strip().isdigit() else None,
                )
            )
        # Keep original df for later writes
        self._df = df
        return rows

    def write_uploaded(
            self,
            row_index: int,
            status_done: str = "Done",
            upload_url: Optional[str] = None,
            uploaded_at: Optional[datetime] = None,
            platform: Optional[str] = None,
    ) -> None:
        if not hasattr(self, "_df"):
            # Lazy-load if not present
            self._df = pd.read_excel(self.excel_path, sheet_name=self.sheet_name)
        df = self._df
        if "status" not in df.columns:
            df["status"] = ""
        # Ensure legacy columns exist for backward compatibility
        if "upload_url" not in df.columns:
            df["upload_url"] = ""
        if "uploaded_at" not in df.columns:
            df["uploaded_at"] = ""

        # Ensure per-platform columns if platform provided
        platform = (platform or "").strip().lower() or None
        if platform in {"youtube", "tiktok", "instagram"}:
            url_col = f"{platform}_upload_url"
            at_col = f"{platform}_uploaded_at"
            if url_col not in df.columns:
                df[url_col] = ""
            if at_col not in df.columns:
                df[at_col] = ""
        else:
            url_col = None
            at_col = None

        # Update status
        df.at[row_index, "status"] = status_done

        # Write URLs and timestamps
        if upload_url:
            if url_col:
                df.at[row_index, url_col] = upload_url
            # Also keep legacy filled for first success (mainly YouTube) for compatibility
            if not str(df.at[row_index, "upload_url"]).strip():
                df.at[row_index, "upload_url"] = upload_url
        if uploaded_at:
            ts = uploaded_at.strftime("%Y-%m-%d %H:%M:%S")
            if at_col:
                df.at[row_index, at_col] = ts
            if not str(df.at[row_index, "uploaded_at"]).strip():
                df.at[row_index, "uploaded_at"] = ts

        # Save back to the same sheet
        if self.sheet_name:
            with pd.ExcelWriter(self.excel_path, engine="openpyxl", mode="a", if_sheet_exists="replace") as writer:
                df.to_excel(writer, sheet_name=self.sheet_name, index=False)
        else:
            df.to_excel(self.excel_path, index=False)

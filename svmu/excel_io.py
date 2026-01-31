from __future__ import annotations

import os
from dataclasses import dataclass
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
    "output_datetime",
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
    output_datetime: Optional[str]


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
                    output_datetime=str(r["output_datetime"]).strip() or None,
                )
            )
        # Keep original df for later writes
        self._df = df
        return rows

    def write_status(self, row_index: int, status_done: str = "Done", output_filename: Optional[str] = None, output_datetime: Optional[str] = None) -> None:
        if not hasattr(self, "_df"):
            # Lazy-load if not present
            self._df = pd.read_excel(self.excel_path, sheet_name=self.sheet_name)
        df = self._df
        # Ensure columns exist
        for col in DEFAULT_COLUMNS:
            if col not in df.columns:
                df[col] = ""

        # Update fields
        df.at[row_index, "status"] = status_done
        if output_filename is not None:
            df.at[row_index, "output_filename"] = output_filename
        if output_datetime is not None:
            df.at[row_index, "output_datetime"] = output_datetime

        # Save back to the same sheet
        if self.sheet_name:
            with pd.ExcelWriter(self.excel_path, engine="openpyxl", mode="a", if_sheet_exists="replace") as writer:
                df.to_excel(writer, sheet_name=self.sheet_name, index=False)
        else:
            df.to_excel(self.excel_path, index=False)

from __future__ import annotations

from typing import List, Optional, Dict

import gspread
import pandas as pd

# Reuse shared schema and dataclass from excel_io to keep one source of truth
from .excel_io import DEFAULT_COLUMNS, IdeaRow


def _lower(s: Optional[str]) -> str:
    return (s or "").strip().lower()


class GoogleSheetStore:
    def __init__(self, spreadsheet_id: str, sheet_name: Optional[str], service_account_json: str):
        if not spreadsheet_id:
            raise ValueError("spreadsheet_id is required for GoogleSheetStore")
        if not service_account_json:
            raise ValueError("service_account_json path is required for GoogleSheetStore")

        self.spreadsheet_id = spreadsheet_id
        self.sheet_name = sheet_name
        self._gc = gspread.service_account(filename=service_account_json)
        self._sh = self._gc.open_by_key(spreadsheet_id)
        self._ws = self._sh.worksheet(sheet_name) if sheet_name else self._sh.sheet1

        self._header: List[str] = []
        self._col_index: Dict[str, int] = {}
        self._df: Optional[pd.DataFrame] = None

    # --- Helpers ---
    def _read_header(self) -> List[str]:
        header = self._ws.row_values(1)
        self._header = header
        self._col_index = {name: idx for idx, name in enumerate(header)}
        return header

    def _ensure_columns(self, needed: List[str]) -> None:
        header = self._read_header()
        changed = False
        for col in needed:
            if col not in header:
                header.append(col)
                changed = True
        if changed:
            # Update header row with new columns
            self._ws.update('1:1', [header])
            self._header = header
            self._col_index = {name: idx for idx, name in enumerate(header)}

    def _col_idx(self, name: str) -> Optional[int]:
        return self._col_index.get(name)

    def _rownum_from_index(self, idx: int) -> int:
        # Sheet rows are 1-based and first row is header
        return int(idx) + 2

    # --- Public API ---
    def read_ready(self, status_ready: str = "Ready") -> List[IdeaRow]:
        # Ensure base columns exist in header (will add if missing)
        self._ensure_columns(DEFAULT_COLUMNS)

        # Read all records
        records = self._ws.get_all_records(numericise_false=True)
        df = pd.DataFrame.from_records(records)
        # Guarantee all default columns exist and fill NAs
        for col in DEFAULT_COLUMNS:
            if col not in df.columns:
                df[col] = ""
        df = df.fillna("")

        # Store for later writes
        self._df = df.copy()

        # Filter ready rows (case-insensitive)
        ready_mask = df["status"].astype(str).str.lower() == status_ready.lower()
        ready_df = df[ready_mask]

        rows: List[IdeaRow] = []
        for idx, r in ready_df.iterrows():
            rows.append(
                IdeaRow(
                    idx=int(idx),
                    id=str(r.get("id", "")).strip() or str(idx),
                    title=str(r.get("title", "")).strip(),
                    bullets=str(r.get("bullets", "")).strip(),
                    tags=str(r.get("tags", "")).strip() or None,
                    description=str(r.get("description", "")).strip() or None,
                    status=str(r.get("status", "")).strip(),
                    output_filename=str(r.get("output_filename", "")).strip() or None,
                    output_datetime=str(r.get("output_datetime", "")).strip() or None,
                )
            )
        # Keep original df for later writes
        self._df = df
        return rows

    def write_status(
            self,
            row_index: int,
            status_done: str = "Done",
            output_filename: Optional[str] = None,
            output_datetime: Optional[str] = None) -> None:
        # Ensure required columns exist
        self._ensure_columns(DEFAULT_COLUMNS)
        # Figure column positions (0-based)
        self._read_header()
        def col_to_a1(col_idx_zero_based: int) -> str:
            col_num = col_idx_zero_based + 1
            letters = ""
            while col_num:
                col_num, remainder = divmod(col_num - 1, 26)
                letters = chr(65 + remainder) + letters
            return letters

        updates: Dict[str, str] = {}
        rownum = self._rownum_from_index(row_index)

        # status
        status_col_idx = self._col_idx("status")
        if status_col_idx is not None:
            updates[f"{col_to_a1(status_col_idx)}{rownum}"] = status_done
        # output_filename
        if output_filename is not None:
            of_col_idx = self._col_idx("output_filename")
            if of_col_idx is not None:
                updates[f"{col_to_a1(of_col_idx)}{rownum}"] = output_filename
        # output_datetime
        if output_datetime is not None:
            od_col_idx = self._col_idx("output_datetime")
            if od_col_idx is not None:
                updates[f"{col_to_a1(od_col_idx)}{rownum}"] = output_datetime

        # Apply updates (simple per-cell updates for compatibility)
        if updates:
            for a1, val in updates.items():
                self._ws.update(a1, val)

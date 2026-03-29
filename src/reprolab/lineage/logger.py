"""Explainable transformation log management and export."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from ..models import CorrectionRecord


class TransformationLogger:
    """Stores and exports correction records for auditing."""

    def __init__(self) -> None:
        self._records: list[CorrectionRecord] = []

    def add(self, records: list[CorrectionRecord]) -> None:
        """Append records to the in-memory transformation log."""
        self._records.extend(records)

    def to_frame(self) -> pd.DataFrame:
        """Return all records as a pandas DataFrame."""
        return pd.DataFrame([r.as_dict() for r in self._records])

    def export_json(self, path: str | Path) -> None:
        """Export records in JSON format."""
        payload = [r.as_dict() for r in self._records]
        Path(path).write_text(
            json.dumps(payload, indent=2, default=str), encoding="utf-8"
        )

    def export_csv(self, path: str | Path) -> None:
        """Export records in CSV format."""
        self.to_frame().to_csv(path, index=False)

"""Deterministic lineage tracking for reproducibility and regeneration."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict

import pandas as pd

from ..models import LineageRecord


class LineageTracker:
    """Tracks versioned deterministic lineage for each pipeline step."""

    def __init__(self) -> None:
        self._history: list[LineageRecord] = []

    def add_step(
        self,
        before_df: pd.DataFrame,
        after_df: pd.DataFrame,
        step_name: str,
        step_version: str,
    ) -> None:
        """Record lineage metadata for one deterministic transformation step."""
        before_hash = self.dataset_hash(before_df)
        after_hash = self.dataset_hash(after_df)
        signature = self._signature(step_name, step_version, before_hash, after_hash)
        self._history.append(
            LineageRecord(
                dataset_hash_before=before_hash,
                dataset_hash_after=after_hash,
                step_name=step_name,
                step_version=step_version,
                timestamp_utc=LineageRecord.now_iso(),
                deterministic_signature=signature,
            )
        )

    def history(self) -> list[dict[str, str]]:
        """Return lineage history as dictionaries."""
        return [asdict(item) for item in self._history]

    @staticmethod
    def dataset_hash(df: pd.DataFrame) -> str:
        """Compute deterministic dataset hash independent of row index."""
        canonical = df.copy()
        canonical = canonical.sort_index(axis=1)
        canonical = canonical.reset_index(drop=True)
        payload = canonical.to_json(
            orient="split", date_format="iso", default_handler=str
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @staticmethod
    def _signature(step: str, version: str, before_hash: str, after_hash: str) -> str:
        content = json.dumps(
            {
                "step": step,
                "version": version,
                "before": before_hash,
                "after": after_hash,
            },
            sort_keys=True,
        )
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

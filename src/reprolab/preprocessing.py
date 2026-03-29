"""Automated preprocessing for biomedical datasets."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from .models import CorrectionRecord

LOGGER = logging.getLogger(__name__)


@dataclass
class PreprocessingConfig:
    """Configuration for deterministic preprocessing."""

    duplicate_subset: list[str] | None = None
    date_columns: tuple[str, ...] = ("event_date", "visit_date", "lab_date")
    unit_columns: tuple[str, ...] = ("glucose_mg_dl",)
    categorical_columns: tuple[str, ...] = ("diagnosis_code", "adverse_event")


class DataPreprocessor:
    """Performs deterministic, explainable preprocessing operations."""

    def __init__(self, config: PreprocessingConfig | None = None) -> None:
        self.config = config or PreprocessingConfig()

    def process(self, df: pd.DataFrame) -> tuple[pd.DataFrame, list[CorrectionRecord]]:
        """Run the full preprocessing routine and return logs."""
        working = df.copy(deep=True)
        corrections: list[CorrectionRecord] = []

        working, dup_logs = self._handle_duplicates(working)
        corrections.extend(dup_logs)

        working, miss_logs = self._handle_missing_values(working)
        corrections.extend(miss_logs)

        working, fmt_logs = self._standardize_formatting(working)
        corrections.extend(fmt_logs)

        LOGGER.info("Preprocessing complete with %d corrections", len(corrections))
        return working, corrections

    def _handle_duplicates(
        self, df: pd.DataFrame
    ) -> tuple[pd.DataFrame, list[CorrectionRecord]]:
        subset = self.config.duplicate_subset
        dup_mask = df.duplicated(subset=subset, keep="first")
        logs: list[CorrectionRecord] = []
        for idx in df.index[dup_mask]:
            logs.append(
                CorrectionRecord(
                    row_index=int(idx),
                    column="__row__",
                    original_value="duplicate",
                    corrected_value="removed",
                    constraint_name="duplicate_detection",
                    rationale="Exact duplicate row removed deterministically.",
                    confidence=1.0,
                )
            )
        cleaned = df.loc[~dup_mask].copy()
        return cleaned, logs

    def _handle_missing_values(
        self, df: pd.DataFrame
    ) -> tuple[pd.DataFrame, list[CorrectionRecord]]:
        logs: list[CorrectionRecord] = []
        for col in df.columns:
            series = df[col]
            missing = series.isna()
            if not missing.any():
                continue

            if pd.api.types.is_numeric_dtype(series):
                replacement = float(series.median()) if series.notna().any() else 0.0
            else:
                mode = series.mode(dropna=True)
                replacement = mode.iloc[0] if not mode.empty else "UNKNOWN"

            for idx in df.index[missing]:
                logs.append(
                    CorrectionRecord(
                        row_index=int(idx),
                        column=col,
                        original_value=None,
                        corrected_value=replacement,
                        constraint_name="missing_value_imputation",
                        rationale="Filled missing value using deterministic column statistic.",
                        confidence=0.85,
                    )
                )
            df.loc[missing, col] = replacement
        return df, logs

    def _standardize_formatting(
        self, df: pd.DataFrame
    ) -> tuple[pd.DataFrame, list[CorrectionRecord]]:
        logs: list[CorrectionRecord] = []

        for col in self.config.date_columns:
            if col not in df.columns:
                continue
            parsed = pd.to_datetime(df[col], errors="coerce", dayfirst=False)
            unresolved = parsed.isna() & df[col].notna()
            if unresolved.any():
                parsed_alt = pd.to_datetime(
                    df.loc[unresolved, col], errors="coerce", dayfirst=True
                )
                parsed.loc[unresolved] = parsed_alt
            for idx, old in df[col].items():
                new = parsed.loc[idx]
                if pd.isna(new) and pd.notna(old):
                    continue
                if pd.notna(new):
                    as_iso = new.date().isoformat()
                    if str(old) != as_iso:
                        logs.append(
                            CorrectionRecord(
                                row_index=int(idx),
                                column=col,
                                original_value=old,
                                corrected_value=as_iso,
                                constraint_name="date_standardization",
                                rationale="Normalized date to ISO-8601 format.",
                                confidence=0.95,
                            )
                        )
                        df.at[idx, col] = as_iso

        for col in self.config.unit_columns:
            if col not in df.columns:
                continue
            for idx, old in df[col].items():
                new = self._to_numeric_mg_dl(old)
                if pd.notna(new) and old != new:
                    logs.append(
                        CorrectionRecord(
                            row_index=int(idx),
                            column=col,
                            original_value=old,
                            corrected_value=new,
                            constraint_name="unit_standardization",
                            rationale="Converted value to canonical mg/dL numeric format.",
                            confidence=0.9,
                        )
                    )
                    df.at[idx, col] = new

        for col in self.config.categorical_columns:
            if col not in df.columns:
                continue
            for idx, old in df[col].items():
                if pd.isna(old):
                    continue
                new = str(old).strip().upper()
                if old != new:
                    logs.append(
                        CorrectionRecord(
                            row_index=int(idx),
                            column=col,
                            original_value=old,
                            corrected_value=new,
                            constraint_name="categorical_code_standardization",
                            rationale="Canonicalized categorical string to uppercase code.",
                            confidence=0.98,
                        )
                    )
                    df.at[idx, col] = new

        return df, logs

    @staticmethod
    def _to_numeric_mg_dl(value: Any) -> float | Any:
        if pd.isna(value):
            return value
        if isinstance(value, (int, float, np.number)):
            return float(value)
        text = str(value)
        match = re.search(r"[-+]?\d*\.?\d+", text)
        if not match:
            return value
        return float(match.group())

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
    numeric_imputation_strategy: str = "median"
    knn_neighbors: int = 3


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
        numeric_frame = df.select_dtypes(include=[np.number]).copy()

        for col in df.columns:
            series = df[col]
            missing = series.isna()
            if not missing.any():
                continue

            if pd.api.types.is_numeric_dtype(series):
                replacements, rationale, confidence = self._numeric_replacements(
                    df, numeric_frame, col
                )
                for idx in df.index[missing]:
                    replacement = float(replacements.loc[idx])
                    logs.append(
                        CorrectionRecord(
                            row_index=int(idx),
                            column=col,
                            original_value=None,
                            corrected_value=replacement,
                            constraint_name="missing_value_imputation",
                            rationale=rationale,
                            confidence=confidence,
                        )
                    )
                    df.at[idx, col] = replacement
                    if col in numeric_frame.columns:
                        numeric_frame.at[idx, col] = replacement
                continue

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

    def _numeric_replacements(
        self, df: pd.DataFrame, numeric_frame: pd.DataFrame, column: str
    ) -> tuple[pd.Series, str, float]:
        series = pd.to_numeric(df[column], errors="coerce")
        median = float(series.median()) if series.notna().any() else 0.0

        if self.config.numeric_imputation_strategy != "knn":
            filled = series.fillna(median)
            return (
                filled,
                "Filled missing numeric value using deterministic column median.",
                0.85,
            )

        filled = self._knn_impute_numeric_column(numeric_frame, column, median)
        return (
            filled,
            "Filled missing numeric value using deterministic row-level KNN imputation with median fallback.",
            0.88,
        )

    def _knn_impute_numeric_column(
        self, numeric_frame: pd.DataFrame, column: str, fallback: float
    ) -> pd.Series:
        series = pd.to_numeric(numeric_frame[column], errors="coerce")
        if series.notna().all():
            return series

        features = numeric_frame.drop(columns=[column], errors="ignore").apply(
            pd.to_numeric, errors="coerce"
        )
        out = series.copy()

        for idx in series.index[series.isna()]:
            neighbor_vals: list[tuple[float, float]] = []
            target_features = features.loc[idx] if not features.empty else pd.Series(dtype=float)

            for other_idx in series.index:
                if other_idx == idx or pd.isna(series.loc[other_idx]):
                    continue
                if features.empty:
                    neighbor_vals.append((0.0, float(series.loc[other_idx])))
                    continue

                candidate = features.loc[other_idx]
                overlap = target_features.notna() & candidate.notna()
                if not overlap.any():
                    continue

                diff = target_features.loc[overlap] - candidate.loc[overlap]
                distance = float(np.sqrt(np.mean(np.square(diff.to_numpy(dtype=float)))))
                neighbor_vals.append((distance, float(series.loc[other_idx])))

            if not neighbor_vals:
                out.loc[idx] = fallback
                continue

            neighbor_vals.sort(key=lambda item: (item[0], item[1]))
            chosen = neighbor_vals[: max(1, self.config.knn_neighbors)]
            weights = np.array([1.0 / (dist + 1e-6) for dist, _ in chosen], dtype=float)
            values = np.array([value for _, value in chosen], dtype=float)
            out.loc[idx] = float(np.average(values, weights=weights))

        return out.fillna(fallback)

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

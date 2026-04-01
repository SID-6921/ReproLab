"""Reproducibility scoring for experiment-level quality assessment."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class ReproducibilityScore:
    """Score breakdown for one experiment dataset."""

    overall: int
    metadata_completeness: float
    reagent_traceability: float
    step_granularity: float

    def as_dict(self) -> dict[str, float | int]:
        return {
            "overall": self.overall,
            "metadata_completeness": self.metadata_completeness,
            "reagent_traceability": self.reagent_traceability,
            "step_granularity": self.step_granularity,
        }


class ReproducibilityScorer:
    """Computes a deterministic 0-100 reproducibility score."""

    metadata_columns: tuple[str, ...] = (
        "patient_id",
        "diagnosis_code",
        "hba1c_pct",
        "glucose_mg_dl",
        "event_date",
        "adverse_event",
    )
    reagent_columns: tuple[str, ...] = (
        "reagent_name",
        "reagent_lot",
        "lot_number",
        "vendor",
        "catalog_number",
    )
    granularity_columns: tuple[str, ...] = (
        "temperature_c",
        "ph",
        "incubation_time_min",
        "incubation_time",
        "event_date",
    )

    def score(self, df: pd.DataFrame, log_df: pd.DataFrame | None = None) -> ReproducibilityScore:
        """Return experiment-level reproducibility score components."""
        metadata = self._metadata_completeness(df)
        traceability = self._reagent_traceability(df)
        granularity = self._step_granularity(df, log_df)

        overall = int(round(100 * (0.45 * metadata + 0.35 * traceability + 0.20 * granularity)))
        overall = max(0, min(100, overall))

        return ReproducibilityScore(
            overall=overall,
            metadata_completeness=round(metadata * 100, 2),
            reagent_traceability=round(traceability * 100, 2),
            step_granularity=round(granularity * 100, 2),
        )

    def _metadata_completeness(self, df: pd.DataFrame) -> float:
        present = [c for c in self.metadata_columns if c in df.columns]
        if not present or df.empty:
            return 0.0
        completeness = float(df[present].notna().mean().mean())
        return max(0.0, min(1.0, completeness))

    def _reagent_traceability(self, df: pd.DataFrame) -> float:
        present = [c for c in self.reagent_columns if c in df.columns]
        if df.empty:
            return 0.0
        if not present:
            return 0.4
        completeness = float(df[present].notna().mean().mean())
        return max(0.0, min(1.0, completeness))

    def _step_granularity(self, df: pd.DataFrame, log_df: pd.DataFrame | None) -> float:
        if df.empty:
            return 0.0

        present_granularity = [c for c in self.granularity_columns if c in df.columns]
        structural = len(present_granularity) / len(self.granularity_columns)

        text_quality = 0.0
        if "protocol_step" in df.columns:
            steps = df["protocol_step"].dropna().astype(str)
            if not steps.empty:
                avg_words = float(steps.map(lambda s: len(s.split())).mean())
                text_quality = min(1.0, avg_words / 15.0)

        audit_signal = 0.0
        if log_df is not None and not log_df.empty and len(df) > 0:
            audit_signal = min(1.0, len(log_df) / max(1, int(len(df) * 0.25)))

        combined = 0.65 * structural + 0.25 * text_quality + 0.10 * audit_signal
        return max(0.0, min(1.0, combined))

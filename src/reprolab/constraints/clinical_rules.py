"""Concrete clinical constraints for diagnosis-linked datasets."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .base import CandidateCorrection, ClinicalConstraint, ConstraintResult


@dataclass
class ICDDeterministicConstraint(ClinicalConstraint):
    """Normalizes and validates ICD diagnosis prefixes deterministically."""

    name: str = "icd_deterministic"
    valid_prefixes: tuple[str, ...] = ("E10", "E11", "T88", "I10")

    def apply(self, df: pd.DataFrame) -> ConstraintResult:
        candidates: list[CandidateCorrection] = []
        if "diagnosis_code" not in df.columns:
            return ConstraintResult(candidates)

        for idx, raw in df["diagnosis_code"].items():
            if pd.isna(raw):
                continue
            val = str(raw).strip().upper()
            if val != raw:
                candidates.append(
                    CandidateCorrection(
                        row_index=int(idx),
                        column="diagnosis_code",
                        proposed_value=val,
                        confidence=0.98,
                        rationale="ICD code canonicalized to uppercase.",
                        constraint_name=self.name,
                    )
                )
            if not val.startswith(self.valid_prefixes):
                candidates.append(
                    CandidateCorrection(
                        row_index=int(idx),
                        column="diagnosis_code",
                        proposed_value="T88",
                        confidence=0.55,
                        rationale="Diagnosis code out of supported ontology scope; mapped to T88.",
                        constraint_name=self.name,
                    )
                )
        return ConstraintResult(candidates)


@dataclass
class DiagnosisBiomarkerConstraint(ClinicalConstraint):
    """Checks cross-variable consistency between diagnosis and HbA1c."""

    name: str = "diagnosis_biomarker_consistency"
    diabetic_codes: tuple[str, ...] = ("E10", "E11")
    hba1c_threshold: float = 6.5

    def apply(self, df: pd.DataFrame) -> ConstraintResult:
        candidates: list[CandidateCorrection] = []
        required = {"diagnosis_code", "hba1c_pct"}
        if not required.issubset(df.columns):
            return ConstraintResult(candidates)

        for idx, row in df.iterrows():
            code = (
                str(row["diagnosis_code"]).upper()
                if pd.notna(row["diagnosis_code"])
                else ""
            )
            hba1c = row["hba1c_pct"]
            if pd.isna(hba1c):
                continue
            is_diabetic = code.startswith(self.diabetic_codes)
            if is_diabetic and float(hba1c) < self.hba1c_threshold:
                candidates.append(
                    CandidateCorrection(
                        row_index=int(idx),
                        column="hba1c_pct",
                        proposed_value=self.hba1c_threshold,
                        confidence=0.7,
                        rationale="Diabetes diagnosis requires HbA1c above clinical threshold.",
                        constraint_name=self.name,
                    )
                )
            elif (not is_diabetic) and float(hba1c) >= self.hba1c_threshold:
                candidates.append(
                    CandidateCorrection(
                        row_index=int(idx),
                        column="diagnosis_code",
                        proposed_value="E11",
                        confidence=0.65,
                        rationale="Elevated HbA1c suggests diabetes-linked diagnosis.",
                        constraint_name=self.name,
                    )
                )
        return ConstraintResult(candidates)


@dataclass
class ProbabilisticBiomarkerAnomalyConstraint(ClinicalConstraint):
    """Flags context-aware biomarker outliers with probabilistic confidence."""

    name: str = "probabilistic_biomarker_anomaly"

    def apply(self, df: pd.DataFrame) -> ConstraintResult:
        candidates: list[CandidateCorrection] = []
        if "glucose_mg_dl" not in df.columns:
            return ConstraintResult(candidates)

        values = pd.to_numeric(df["glucose_mg_dl"], errors="coerce")
        mean = float(values.mean()) if values.notna().any() else 100.0
        std = float(values.std(ddof=0)) if values.notna().any() else 15.0
        std = max(std, 1.0)

        for idx, value in values.items():
            if pd.isna(value):
                continue
            z = abs((float(value) - mean) / std)
            if z <= 3.0:
                continue
            clipped = float(np.clip(value, mean - 3.0 * std, mean + 3.0 * std))
            confidence = float(min(0.95, 0.5 + 0.1 * z))
            candidates.append(
                CandidateCorrection(
                    row_index=int(idx),
                    column="glucose_mg_dl",
                    proposed_value=round(clipped, 2),
                    confidence=confidence,
                    rationale="Value is a context-aware statistical outlier based on z-score.",
                    constraint_name=self.name,
                )
            )
        return ConstraintResult(candidates)


def default_clinical_constraints() -> list[ClinicalConstraint]:
    """Return the default constraint set for diagnosis-linked datasets."""
    return [
        ICDDeterministicConstraint(),
        DiagnosisBiomarkerConstraint(),
        ProbabilisticBiomarkerAnomalyConstraint(),
    ]

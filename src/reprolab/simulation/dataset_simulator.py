"""Synthetic dataset generation with controlled biomedical errors."""

from __future__ import annotations

import numpy as np
import pandas as pd


def simulate_biomed_dataset(
    n: int = 100, seed: int = 42
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Generate a diagnosis-linked dataset with controlled error types."""
    rng = np.random.default_rng(seed)
    ids = [f"P{i:04d}" for i in range(n)]
    diagnosis = rng.choice(["E11", "I10", "T88"], size=n, p=[0.45, 0.35, 0.20])
    hba1c = np.where(
        diagnosis == "E11", rng.normal(7.8, 0.9, size=n), rng.normal(5.6, 0.6, size=n)
    )
    glucose = np.where(
        diagnosis == "E11", rng.normal(170, 35, size=n), rng.normal(98, 18, size=n)
    )

    df = pd.DataFrame(
        {
            "patient_id": ids,
            "diagnosis_code": diagnosis.astype(object),
            "hba1c_pct": np.round(hba1c, 2),
            "glucose_mg_dl": np.round(glucose, 1).astype(object),
            "event_date": pd.date_range("2026-01-01", periods=n, freq="D").strftime(
                "%Y-%m-%d"
            ),
            "adverse_event": rng.choice(["YES", "NO"], size=n, p=[0.1, 0.9]),
        }
    )

    # Inject controlled errors.
    n_missing = max(1, n // 10)
    n_code = max(1, n // 12)
    n_cross = max(1, n // 8)

    missing_idx = rng.choice(df.index, size=n_missing, replace=False)
    df.loc[missing_idx, "glucose_mg_dl"] = None

    code_idx = rng.choice(df.index, size=n_code, replace=False)
    df.loc[code_idx, "diagnosis_code"] = "??"

    cross_idx = rng.choice(df.index, size=n_cross, replace=False)
    df.loc[cross_idx, "hba1c_pct"] = rng.normal(4.9, 0.2, size=n_cross)
    df.loc[cross_idx, "diagnosis_code"] = "E11"

    # Inject duplicate and format issues.
    duplicate_row = df.iloc[[0]].copy()
    duplicate_row.loc[:, "diagnosis_code"] = duplicate_row["diagnosis_code"].str.lower()
    duplicate_row.loc[:, "event_date"] = "01/02/2026"
    duplicate_row.loc[:, "glucose_mg_dl"] = "180 mg/dL"
    df = pd.concat([df, duplicate_row], ignore_index=True)

    error_profile = {
        "missing_values": int(n_missing),
        "coding_errors": int(n_code),
        "cross_variable_violations": int(n_cross),
        "duplicates": 1,
    }
    return df, error_profile

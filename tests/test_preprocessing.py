from __future__ import annotations

import pandas as pd
from reprolab.preprocessing import DataPreprocessor, PreprocessingConfig


def test_preprocessing_handles_duplicates_missing_and_formatting() -> None:
    df = pd.DataFrame(
        {
            "patient_id": ["P1", "P1", "P2"],
            "diagnosis_code": ["e11", "e11", "i10"],
            "hba1c_pct": [8.0, 8.0, 5.6],
            "event_date": ["2026/01/01", "2026/01/01", "01-03-2026"],
            "glucose_mg_dl": ["180 mg/dL", "180 mg/dL", None],
            "adverse_event": ["yes", "yes", "NO"],
        }
    )

    cleaned, logs = DataPreprocessor().process(df)

    assert len(cleaned) == 2
    assert cleaned["diagnosis_code"].str.isupper().all()
    assert cleaned["event_date"].str.match(r"\d{4}-\d{2}-\d{2}").all()
    assert cleaned["glucose_mg_dl"].notna().all()
    assert len(logs) > 0


def test_preprocessing_supports_knn_numeric_imputation() -> None:
    df = pd.DataFrame(
        {
            "patient_id": ["P1", "P2", "P3", "P4"],
            "diagnosis_code": ["e11", "e11", "e11", "i10"],
            "hba1c_pct": [8.0, 8.2, None, 5.5],
            "glucose_mg_dl": [180.0, 182.0, 181.0, 95.0],
            "weight_kg": [82.0, 84.0, 83.0, 60.0],
            "adverse_event": ["yes", "no", "yes", "no"],
        }
    )

    cleaned, logs = DataPreprocessor(
        PreprocessingConfig(numeric_imputation_strategy="knn", knn_neighbors=2)
    ).process(df)

    imputed_value = float(cleaned.loc[2, "hba1c_pct"])
    assert 8.0 <= imputed_value <= 8.2
    assert cleaned["hba1c_pct"].notna().all()
    assert any(
        "KNN imputation" in record.rationale for record in logs if record.column == "hba1c_pct"
    )


def test_preprocessing_benchmark_includes_knn_strategy() -> None:
    from reprolab.simulation.benchmark import run_preprocessing_benchmark

    df = pd.DataFrame(
        {
            "patient_id": ["P1", "P2", "P3"],
            "diagnosis_code": ["e11", "e11", "i10"],
            "hba1c_pct": [8.1, None, 5.4],
            "glucose_mg_dl": [175.0, 176.0, 92.0],
            "adverse_event": ["yes", "no", "no"],
        }
    )

    benchmark = run_preprocessing_benchmark(df)

    assert "reprolab_median" in set(benchmark["strategy"])
    assert "reprolab_knn" in set(benchmark["strategy"])

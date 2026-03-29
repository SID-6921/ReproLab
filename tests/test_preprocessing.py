from __future__ import annotations

import pandas as pd
from reprolab.preprocessing import DataPreprocessor


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

from __future__ import annotations

import pandas as pd
from reprolab.constraints.clinical_rules import default_clinical_constraints
from reprolab.validation.engine import ValidationEngine


def test_validation_engine_corrects_cross_variable_inconsistency() -> None:
    df = pd.DataFrame(
        {
            "patient_id": ["P1", "P2"],
            "diagnosis_code": ["E11", "I10"],
            "hba1c_pct": [5.2, 7.1],
            "glucose_mg_dl": [120, 130],
        }
    )

    engine = ValidationEngine(default_clinical_constraints())
    corrected, logs = engine.validate_and_correct(df)

    assert len(logs) >= 1
    assert float(corrected.loc[0, "hba1c_pct"]) >= 6.5
    assert str(corrected.loc[1, "diagnosis_code"]).startswith("E11")

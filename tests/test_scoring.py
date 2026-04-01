from __future__ import annotations

import pandas as pd
from reprolab.constraints.clinical_rules import default_clinical_constraints
from reprolab.pipeline import ReproLabPipeline
from reprolab.scoring import ReproducibilityScorer


def test_scorer_returns_high_score_for_complete_traceable_input() -> None:
    df = pd.DataFrame(
        {
            "patient_id": ["P1", "P2"],
            "diagnosis_code": ["E11", "I10"],
            "hba1c_pct": [7.2, 5.5],
            "glucose_mg_dl": [170, 98],
            "event_date": ["2026-01-01", "2026-01-02"],
            "adverse_event": ["NO", "YES"],
            "reagent_name": ["Buffer A", "Enzyme B"],
            "reagent_lot": ["LOT-001", "LOT-002"],
            "vendor": ["VendorX", "VendorY"],
            "catalog_number": ["CAT-11", "CAT-12"],
            "temperature_c": [37.0, 25.0],
            "ph": [7.4, 7.1],
            "incubation_time_min": [30, 45],
            "protocol_step": [
                "Mix reagent and incubate at 37C for 30 minutes.",
                "Wash sample and incubate at room temperature for 45 minutes.",
            ],
        }
    )

    score = ReproducibilityScorer().score(df)

    assert score.overall >= 80
    assert score.metadata_completeness == 100.0
    assert score.reagent_traceability == 100.0


def test_pipeline_result_contains_reproducibility_score() -> None:
    df = pd.DataFrame(
        {
            "patient_id": ["P1", "P2"],
            "diagnosis_code": ["E11", "I10"],
            "hba1c_pct": [7.2, 5.5],
            "glucose_mg_dl": [170, 98],
            "event_date": ["2026-01-01", "2026-01-02"],
            "adverse_event": ["NO", "YES"],
        }
    )

    pipeline = ReproLabPipeline(constraints=default_clinical_constraints())
    result = pipeline.run(df)

    assert "overall" in result.reproducibility_score
    assert "metadata_completeness" in result.reproducibility_score
    assert "reagent_traceability" in result.reproducibility_score
    assert "step_granularity" in result.reproducibility_score
    assert 0 <= int(result.reproducibility_score["overall"]) <= 100

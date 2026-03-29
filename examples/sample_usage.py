"""Example usage of ReproLab with sample and simulated datasets."""

from __future__ import annotations

import logging

import pandas as pd
from reprolab.constraints.clinical_rules import default_clinical_constraints
from reprolab.pipeline import ReproLabPipeline
from reprolab.simulation.benchmark import run_preprocessing_benchmark
from reprolab.simulation.dataset_simulator import simulate_biomed_dataset

logging.basicConfig(level=logging.INFO)


def run_sample() -> None:
    raw = pd.DataFrame(
        {
            "patient_id": ["P1", "P1", "P2", "P3"],
            "diagnosis_code": ["e11", "e11", "I10", "??"],
            "hba1c_pct": [8.2, 8.2, 5.9, 7.4],
            "event_date": ["2026/01/10", "2026/01/10", "10-02-2026", "2026-03-05"],
            "glucose_mg_dl": ["180 mg/dL", "180 mg/dL", None, 450],
            "adverse_event": ["yes", "yes", "NO", "no"],
        }
    )

    pipeline = ReproLabPipeline(constraints=default_clinical_constraints())
    result = pipeline.run(raw)

    print("=== Cleaned Data ===")
    print(result.cleaned_data)

    print("\n=== Transformation Log ===")
    print(result.transformation_log)

    print("\n=== Lineage ===")
    for item in result.lineage_history:
        print(item)

    pipeline.export_logs("transformation_log.json", "transformation_log.csv")

    simulated, profile = simulate_biomed_dataset(n=120, seed=12)
    benchmark_df = run_preprocessing_benchmark(simulated)
    print("\n=== Error Profile ===")
    print(profile)
    print("\n=== Benchmark ===")
    print(benchmark_df)


if __name__ == "__main__":
    run_sample()

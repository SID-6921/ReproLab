from __future__ import annotations

from reprolab.simulation.benchmark import run_preprocessing_benchmark
from reprolab.simulation.dataset_simulator import simulate_biomed_dataset


def test_benchmark_outputs_required_metrics() -> None:
    df, _ = simulate_biomed_dataset(n=40, seed=8)
    out = run_preprocessing_benchmark(df)

    required = {
        "strategy",
        "data_integrity_score",
        "error_correction_rate",
        "residual_errors",
        "preprocessing_time_sec",
    }
    assert required.issubset(set(out.columns))
    assert len(out) == 3

# ReproLab

ReproLab is a Python package for reproducible biomedical data preprocessing with clinically constrained validation, explainable correction logging, and deterministic lineage tracking.

This README is written as an operator guide so someone can clone the repository and run it immediately.

## What ReproLab Does

ReproLab combines six capabilities:

1. Automated preprocessing
- Duplicate detection and deterministic removal
- Missing-value handling with deterministic imputations
- Standardization of date, unit, and categorical formats

2. Clinically constrained validation engine
- Deterministic ICD-like ontology checks
- Cross-variable checks (example: diagnosis and HbA1c consistency)
- Probabilistic context-aware anomaly correction
- Confidence-scored correction proposals
- Deterministic conflict resolution between competing rules

3. Explainable transformation logging
- Original value vs corrected value
- Constraint/rule applied
- Rationale text
- Confidence score
- Export to JSON and CSV

4. Reproducibility-preserving lineage
- Hash of dataset before and after each step
- Versioned step metadata
- Deterministic signatures to support regeneration

5. Modular extensibility
- Reusable constraint interface
- Plug-in clinical rules per dataset/domain

6. Testing and benchmarking
- Synthetic dataset generator with controlled errors
- Comparison vs manual and generic preprocessing baselines
- Metrics: integrity score, correction rate, residual errors, runtime

## Requirements

- Python 3.10+
- pip

## Quick Start

1. Clone and enter the repository:

```bash
git clone https://github.com/SID-6921/ReproLab.git
cd ReproLab
```

2. Install package and dev dependencies:

```bash
pip install -e .[dev]
```

3. Run tests:

```bash
python -m pytest
```

4. Run the sample workflow:

```bash
python examples/sample_usage.py
```

The sample script in [examples/sample_usage.py](examples/sample_usage.py) prints:
- cleaned dataset
- transformation log
- lineage history
- simulated error profile
- benchmark table

It also exports:
- transformation_log.json
- transformation_log.csv

## Minimal Usage

```python
import pandas as pd
from reprolab.pipeline import ReproLabPipeline
from reprolab.constraints.clinical_rules import default_clinical_constraints

raw = pd.DataFrame(
  {
    "patient_id": ["P1", "P1", "P2"],
    "diagnosis_code": ["e11", "E11", "T88"],
    "hba1c_pct": [8.2, 8.2, 4.1],
    "event_date": ["2026/01/10", "2026-01-10", "10-02-2026"],
    "glucose_mg_dl": ["180 mg/dL", None, "95"],
    "adverse_event": ["yes", "yes", "NO"],
  }
)

pipeline = ReproLabPipeline(constraints=default_clinical_constraints())
result = pipeline.run(raw)

cleaned = result.cleaned_data
logs = result.transformation_log
lineage = result.lineage_history

pipeline.export_logs("transformation_log.json", "transformation_log.csv")
```

## Input Data Contract

Expected columns for the default clinical rule set:

- patient_id
- diagnosis_code
- hba1c_pct
- glucose_mg_dl
- event_date
- adverse_event

If columns are missing, applicable rules are skipped safely.

## Output Artifacts

Pipeline output object contains:

- cleaned_data (pandas DataFrame)
- transformation_log (pandas DataFrame)
- lineage_history (list of dictionaries)

Each transformation log entry includes:

- row_index
- column
- original_value
- corrected_value
- constraint_name
- rationale
- confidence

## Benchmarking and Simulation

Use simulation utilities to create controlled-error datasets and benchmark strategies:

```python
from reprolab.simulation.dataset_simulator import simulate_biomed_dataset
from reprolab.simulation.benchmark import run_preprocessing_benchmark

df, error_profile = simulate_biomed_dataset(n=120, seed=12)
benchmark = run_preprocessing_benchmark(df)
```

Benchmark output includes:

- strategy
- data_integrity_score
- error_correction_rate
- residual_errors
- preprocessing_time_sec

## Preliminary Data Package (Grant Support)

Generate grant-aligned preliminary outputs with:

```bash
python examples/generate_preliminary_data.py
```

This writes files to [outputs/preliminary_data](outputs/preliminary_data), including:

- [outputs/preliminary_data/preliminary_report.md](outputs/preliminary_data/preliminary_report.md)
- [outputs/preliminary_data/preliminary_metrics.csv](outputs/preliminary_data/preliminary_metrics.csv)
- [outputs/preliminary_data/transformation_log.csv](outputs/preliminary_data/transformation_log.csv)

The package is designed to directly support Specific Aims with evidence for:

- missingness/inconsistency reduction
- overall data quality improvement
- estimated cleaning time savings
- downstream summary-statistic stability after preprocessing

## Extending Constraints

To add your own rules, implement the base clinical constraint interface in [src/reprolab/constraints/base.py](src/reprolab/constraints/base.py) and pass custom constraints to the pipeline constructor.

Reference implementations:

- [src/reprolab/constraints/clinical_rules.py](src/reprolab/constraints/clinical_rules.py)

## Project Structure

- [src/reprolab/pipeline.py](src/reprolab/pipeline.py): orchestration entry point
- [src/reprolab/preprocessing.py](src/reprolab/preprocessing.py): deterministic preprocessing
- [src/reprolab/validation/engine.py](src/reprolab/validation/engine.py): correction proposal resolution
- [src/reprolab/lineage/logger.py](src/reprolab/lineage/logger.py): explainable log storage/export
- [src/reprolab/lineage/tracker.py](src/reprolab/lineage/tracker.py): reproducibility lineage metadata
- [src/reprolab/simulation/dataset_simulator.py](src/reprolab/simulation/dataset_simulator.py): controlled error injection
- [src/reprolab/simulation/benchmark.py](src/reprolab/simulation/benchmark.py): strategy comparison metrics
- [tests](tests): automated tests

## Troubleshooting

1. Import errors after cloning
- Re-run: pip install -e .[dev]

2. Tests not discovered
- Run from repository root and execute: python -m pytest

3. Different outputs across runs
- Ensure same input data and same simulator seed

## Reproducible Environments

For stricter environment reproducibility, install pinned dependencies from [requirements-lock.txt](requirements-lock.txt):

```bash
python -m pip install -r requirements-lock.txt
python -m pip install -e .
```

## Contributing

Contribution workflow and PR checklist are documented in [CONTRIBUTING.md](CONTRIBUTING.md).

## License

This repository uses a proprietary all-rights-reserved license.

Reuse, copying, modification, or distribution is not permitted without written permission from the copyright holder.

See [LICENSE](LICENSE).

## Citation

If permission is granted for use, citation is required.

Use metadata from [CITATION.cff](CITATION.cff).

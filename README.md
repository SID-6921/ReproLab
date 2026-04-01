# ReproLab

ReproLab is a Python package for reproducible biomedical data preprocessing with:

- deterministic preprocessing
- clinically constrained validation
- explainable transformation logging
- deterministic lineage tracking

This guide is implementation-focused so a new contributor can set up, run, extend, and validate the project quickly.

## Table of Contents

- [What It Does](#what-it-does)
- [Requirements](#requirements)
- [Quick Start](#quick-start)
- [Implementation Workflow](#implementation-workflow)
- [Minimal Usage](#minimal-usage)
- [Input Contract](#input-contract)
- [Output Contract](#output-contract)
- [Benchmarking and Simulation](#benchmarking-and-simulation)
- [Extending Constraints](#extending-constraints)
- [Project Structure](#project-structure)
- [Troubleshooting](#troubleshooting)
- [Reproducible Environments](#reproducible-environments)
- [Contributing](#contributing)
- [License](#license)
- [Citation](#citation)

## What It Does

ReproLab combines six capabilities:

1. Automated preprocessing
- Duplicate detection and deterministic removal
- Missing-value handling with deterministic imputations
- Standardization of date, unit, and categorical formats

2. Clinically constrained validation engine
- Deterministic ICD-like ontology checks
- Cross-variable checks (diagnosis and HbA1c consistency)
- Probabilistic context-aware anomaly correction
- Confidence-scored correction proposals
- Deterministic conflict resolution for competing rules

3. Explainable transformation logging
- Original value and corrected value
- Constraint/rule applied
- Rationale
- Confidence
- JSON and CSV export

4. Reproducibility-preserving lineage
- Hash before and after each step
- Versioned step metadata
- Deterministic signatures for regeneration

5. Modular extensibility
- Reusable constraint interface
- Plug-in clinical rules per dataset/domain

6. Testing and benchmarking
- Synthetic error injection
- Comparison with manual and generic baselines
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

2. Install dependencies:

```bash
python -m pip install -e .[dev]
```

3. Run tests:

```bash
python -m pytest
```

4. Run sample workflow:

```bash
python examples/sample_usage.py
```

The sample in [examples/sample_usage.py](examples/sample_usage.py) prints:

- cleaned dataset
- transformation log
- lineage history
- simulated error profile
- benchmark table

It also exports:

- transformation_log.json
- transformation_log.csv

## Implementation Workflow

Use this when implementing or changing behavior in ReproLab:

1. Create a branch from `main`
2. Implement focused changes in `src/reprolab`
3. Add or update tests in `tests`
4. Run local validation:

```bash
python -m pytest
```

5. Run sample usage for sanity checks:

```bash
python examples/sample_usage.py
```

6. Open a pull request with clear notes on behavior changes

## Minimal Usage

```python
import pandas as pd
from reprolab.constraints.clinical_rules import default_clinical_constraints
from reprolab.pipeline import ReproLabPipeline

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

## Input Contract

Expected columns for the default clinical constraints:

- patient_id
- diagnosis_code
- hba1c_pct
- glucose_mg_dl
- event_date
- adverse_event

If some columns are missing, relevant rules are skipped safely.

## Output Contract

`PipelineResult` includes:

- `cleaned_data` (`pandas.DataFrame`)
- `transformation_log` (`pandas.DataFrame`)
- `lineage_history` (`list[dict[str, str]]`)
- `reproducibility_score` (`dict[str, float | int]`)

`reproducibility_score` includes:

- `overall` (`0-100`)
- `metadata_completeness` (`0-100`)
- `reagent_traceability` (`0-100`)
- `step_granularity` (`0-100`)

Each transformation-log record includes:

- `row_index`
- `column`
- `original_value`
- `corrected_value`
- `constraint_name`
- `rationale`
- `confidence`

## Benchmarking and Simulation

Use simulation utilities to generate controlled-error datasets and benchmark strategies:

```python
from reprolab.simulation.benchmark import run_preprocessing_benchmark
from reprolab.simulation.dataset_simulator import simulate_biomed_dataset

df, error_profile = simulate_biomed_dataset(n=120, seed=12)
benchmark_df = run_preprocessing_benchmark(df)
```

Benchmark output columns:

- strategy
- data_integrity_score
- error_correction_rate
- residual_errors
- preprocessing_time_sec

### Preliminary Data Package

Generate grant-aligned outputs:

```bash
python examples/generate_preliminary_data.py
```

This writes to [outputs/preliminary_data](outputs/preliminary_data), including:

- [outputs/preliminary_data/preliminary_report.md](outputs/preliminary_data/preliminary_report.md)
- [outputs/preliminary_data/preliminary_metrics.csv](outputs/preliminary_data/preliminary_metrics.csv)
- [outputs/preliminary_data/transformation_log.csv](outputs/preliminary_data/transformation_log.csv)
- [docs/preliminary_results_specific_aims.md](docs/preliminary_results_specific_aims.md)

## Extending Constraints

To add custom rules:

1. Implement a new constraint using the interface in [src/reprolab/constraints/base.py](src/reprolab/constraints/base.py)
2. Return `CandidateCorrection` entries from `apply(...)`
3. Pass your constraint list to `ReproLabPipeline(...)`

Reference examples:

- [src/reprolab/constraints/clinical_rules.py](src/reprolab/constraints/clinical_rules.py)

## Project Structure

- [src/reprolab/pipeline.py](src/reprolab/pipeline.py): Orchestration entry point
- [src/reprolab/preprocessing.py](src/reprolab/preprocessing.py): Deterministic preprocessing
- [src/reprolab/validation/engine.py](src/reprolab/validation/engine.py): Constraint execution and conflict resolution
- [src/reprolab/lineage/logger.py](src/reprolab/lineage/logger.py): Transformation log storage/export
- [src/reprolab/lineage/tracker.py](src/reprolab/lineage/tracker.py): Deterministic lineage metadata
- [src/reprolab/simulation/dataset_simulator.py](src/reprolab/simulation/dataset_simulator.py): Controlled error injection
- [src/reprolab/simulation/benchmark.py](src/reprolab/simulation/benchmark.py): Strategy benchmark metrics
- [tests](tests): Automated tests

## Troubleshooting

1. Import errors after cloning
- Run: `python -m pip install -e .[dev]`

2. Tests not discovered
- Run tests from repository root with: `python -m pytest`

3. Different outputs across runs
- Keep input data and simulator seed consistent

## Reproducible Environments

For stricter reproducibility, use pinned dependencies from [requirements-lock.txt](requirements-lock.txt):

```bash
python -m pip install -r requirements-lock.txt
python -m pip install -e .
```

## Contributing

Contribution workflow and PR checklist: [CONTRIBUTING.md](CONTRIBUTING.md)

## License

This repository uses a proprietary all-rights-reserved license.

Reuse, copying, modification, or distribution is not permitted without written permission from the copyright holder.

See [LICENSE](LICENSE).

## Citation

If permission is granted for use, citation is required.

Use metadata from [CITATION.cff](CITATION.cff).

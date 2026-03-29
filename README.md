# ReproLab

ReproLab is a Python package for reproducible biomedical preprocessing with clinically-constrained validation, explainable transformation logs, and deterministic lineage tracking.

## Features

- Automated preprocessing (duplicates, missing values, date/unit/category formatting)
- Clinical validation engine
  - Deterministic ontology constraints (example ICD family checks)
  - Cross-variable constraints (diagnosis-biomarker consistency)
  - Probabilistic anomaly detection
  - Confidence-scored corrections and conflict resolution
- Explainable transformation logging with JSON/CSV export
- Deterministic lineage metadata for exact regeneration
- Simulation and benchmark framework for controlled error injection

## Installation

```bash
pip install -e .
```

## Quick Example

```python
from reprolab.pipeline import ReproLabPipeline
from reprolab.constraints.clinical_rules import default_clinical_constraints
import pandas as pd

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

print(result.cleaned_data)
print(result.transformation_log.head())
```

See [examples/sample_usage.py](examples/sample_usage.py) for a fuller workflow including benchmark simulation.

"""Generate grant-aligned preliminary data for ReproLab.

This script creates a clinical-style base dataset, injects realistic noise,
runs ReproLab preprocessing, and outputs quality/stability/time metrics.
"""

from __future__ import annotations

import time
from pathlib import Path

import numpy as np
import pandas as pd
from reprolab.constraints.clinical_rules import default_clinical_constraints
from reprolab.pipeline import ReproLabPipeline

OUTPUT_DIR = Path("results/preliminary")


def make_clean_dataset(n: int = 600, seed: int = 11) -> pd.DataFrame:
    """Create a clean, clinical-style diagnosis-linked dataset."""
    rng = np.random.default_rng(seed)
    diagnosis = rng.choice(["E11", "I10", "T88"], size=n, p=[0.45, 0.40, 0.15])
    hba1c = np.where(
        diagnosis == "E11", rng.normal(7.9, 0.8, size=n), rng.normal(5.5, 0.5, size=n)
    )
    glucose = np.where(
        diagnosis == "E11", rng.normal(172, 28, size=n), rng.normal(99, 16, size=n)
    )

    df = pd.DataFrame(
        {
            "patient_id": [f"PT{i:05d}" for i in range(n)],
            "diagnosis_code": diagnosis,
            "hba1c_pct": np.round(hba1c, 2),
            "glucose_mg_dl": np.round(glucose, 1),
            "event_date": pd.date_range("2025-01-01", periods=n, freq="D").strftime(
                "%Y-%m-%d"
            ),
            "adverse_event": rng.choice(["YES", "NO"], size=n, p=[0.12, 0.88]),
        }
    )
    return df


def inject_noise(clean_df: pd.DataFrame, seed: int = 12) -> pd.DataFrame:
    """Inject controlled missingness, coding errors, format drift, and duplicates."""
    rng = np.random.default_rng(seed)
    noisy = clean_df.copy(deep=True)
    noisy["glucose_mg_dl"] = noisy["glucose_mg_dl"].astype(object)

    n = len(noisy)
    miss_idx = rng.choice(noisy.index, size=max(1, int(0.12 * n)), replace=False)
    code_idx = rng.choice(noisy.index, size=max(1, int(0.10 * n)), replace=False)
    date_idx = rng.choice(noisy.index, size=max(1, int(0.15 * n)), replace=False)
    unit_idx = rng.choice(noisy.index, size=max(1, int(0.16 * n)), replace=False)
    cross_idx = rng.choice(noisy.index, size=max(1, int(0.08 * n)), replace=False)

    noisy.loc[miss_idx, "glucose_mg_dl"] = None
    noisy.loc[code_idx, "diagnosis_code"] = "??"
    noisy.loc[date_idx, "event_date"] = pd.to_datetime(
        noisy.loc[date_idx, "event_date"]
    ).dt.strftime("%d-%m-%Y")
    noisy.loc[unit_idx, "glucose_mg_dl"] = (
        noisy.loc[unit_idx, "glucose_mg_dl"].astype(str) + " mg/dL"
    )
    noisy.loc[cross_idx, "diagnosis_code"] = "E11"
    noisy.loc[cross_idx, "hba1c_pct"] = np.round(
        rng.normal(5.0, 0.2, size=len(cross_idx)), 2
    )

    # Add lowercase/categorical drift.
    cat_idx = rng.choice(noisy.index, size=max(1, int(0.12 * n)), replace=False)
    noisy.loc[cat_idx, "adverse_event"] = noisy.loc[
        cat_idx, "adverse_event"
    ].str.lower()

    # Add duplicate rows.
    duplicate_rows = noisy.sample(n=max(1, int(0.05 * n)), random_state=seed)
    noisy = pd.concat([noisy, duplicate_rows], ignore_index=True)
    return noisy


def count_inconsistencies(df: pd.DataFrame) -> int:
    """Count format and clinical consistency issues in a dataset."""
    inconsistencies = 0

    if "diagnosis_code" in df.columns:
        diag = df["diagnosis_code"].astype(str)
        inconsistencies += int(
            (~diag.str.upper().str.startswith(("E10", "E11", "I10", "T88"))).sum()
        )

    if "event_date" in df.columns:
        parsed = pd.to_datetime(df["event_date"], errors="coerce")
        inconsistencies += int(parsed.isna().sum())

    if "glucose_mg_dl" in df.columns:
        numeric_glucose = pd.to_numeric(df["glucose_mg_dl"], errors="coerce")
        non_missing_original = df["glucose_mg_dl"].notna()
        inconsistencies += int((numeric_glucose.isna() & non_missing_original).sum())

    if {"diagnosis_code", "hba1c_pct"}.issubset(df.columns):
        diabetic = (
            df["diagnosis_code"].astype(str).str.upper().str.startswith(("E10", "E11"))
        )
        low_hba1c = pd.to_numeric(df["hba1c_pct"], errors="coerce") < 6.5
        inconsistencies += int((diabetic & low_hba1c).sum())

    return inconsistencies


def quality_score(df: pd.DataFrame) -> float:
    """Compute a simple quality score in [0, 1]. Higher is better."""
    missing_ratio = float(df.isna().mean().mean())
    inconsistency_penalty = count_inconsistencies(df) / max(1, len(df))
    score = max(0.0, 1.0 - missing_ratio - 0.4 * inconsistency_penalty)
    return round(score, 4)


def bootstrap_stability(df: pd.DataFrame, seed: int = 99, rounds: int = 250) -> float:
    """Measure stability using SD of bootstrapped diabetic mean glucose."""
    rng = np.random.default_rng(seed)
    work = df.copy()
    work["diagnosis_code"] = work["diagnosis_code"].astype(str).str.upper()
    work["glucose_mg_dl"] = pd.to_numeric(work["glucose_mg_dl"], errors="coerce")

    diabetic = work[work["diagnosis_code"].str.startswith(("E10", "E11"))]
    diabetic = diabetic.dropna(subset=["glucose_mg_dl"])
    if diabetic.empty:
        return float("nan")

    means: list[float] = []
    for _ in range(rounds):
        sample_idx = rng.choice(
            diabetic.index.to_numpy(), size=len(diabetic), replace=True
        )
        means.append(float(diabetic.loc[sample_idx, "glucose_mg_dl"].mean()))
    return float(np.std(means, ddof=1))


def manual_clean_baseline(df: pd.DataFrame) -> pd.DataFrame:
    """Simple manual-style deterministic baseline for comparison."""
    out = df.drop_duplicates().copy()

    if "event_date" in out.columns:
        parsed = pd.to_datetime(out["event_date"], errors="coerce")
        unresolved = parsed.isna() & out["event_date"].notna()
        if unresolved.any():
            parsed_alt = pd.to_datetime(
                out.loc[unresolved, "event_date"], errors="coerce", dayfirst=True
            )
            parsed.loc[unresolved] = parsed_alt
        out["event_date"] = parsed.dt.strftime("%Y-%m-%d")

    if "glucose_mg_dl" in out.columns:
        out["glucose_mg_dl"] = pd.to_numeric(
            out["glucose_mg_dl"].astype(str).str.extract(r"([-+]?\d*\.?\d+)")[0],
            errors="coerce",
        )

    for col in out.columns:
        if out[col].isna().any():
            if pd.api.types.is_numeric_dtype(out[col]):
                out[col] = out[col].fillna(out[col].median())
            else:
                mode = out[col].mode(dropna=True)
                out[col] = out[col].fillna(
                    mode.iloc[0] if not mode.empty else "UNKNOWN"
                )

    if "diagnosis_code" in out.columns:
        out["diagnosis_code"] = out["diagnosis_code"].astype(str).str.upper()
    if "adverse_event" in out.columns:
        out["adverse_event"] = out["adverse_event"].astype(str).str.upper()
    return out


def build_preliminary_outputs() -> None:
    """Create all preliminary-data artifacts and summary report."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    clean = make_clean_dataset()
    noisy = inject_noise(clean)

    t0 = time.perf_counter()
    manual = manual_clean_baseline(noisy)
    manual_time = time.perf_counter() - t0

    pipeline = ReproLabPipeline(constraints=default_clinical_constraints())
    t1 = time.perf_counter()
    result = pipeline.run(noisy)
    reprolab_time = time.perf_counter() - t1
    reprolab = result.cleaned_data

    missing_before = float(noisy.isna().mean().mean())
    missing_after = float(reprolab.isna().mean().mean())

    incons_before = count_inconsistencies(noisy)
    incons_after = count_inconsistencies(reprolab)

    quality_before = quality_score(noisy)
    quality_after = quality_score(reprolab)

    stability_before = bootstrap_stability(noisy)
    stability_after = bootstrap_stability(reprolab)

    estimated_manual_seconds = max(1.0, incons_before * 20.0)
    time_savings_pct = max(
        0.0,
        100.0 * (estimated_manual_seconds - reprolab_time) / estimated_manual_seconds,
    )

    summary = pd.DataFrame(
        [
            {
                "metric": "missing_ratio_before",
                "value": round(missing_before, 4),
            },
            {
                "metric": "missing_ratio_after",
                "value": round(missing_after, 4),
            },
            {
                "metric": "inconsistencies_before",
                "value": incons_before,
            },
            {
                "metric": "inconsistencies_after",
                "value": incons_after,
            },
            {
                "metric": "quality_score_before",
                "value": quality_before,
            },
            {
                "metric": "quality_score_after",
                "value": quality_after,
            },
            {
                "metric": "bootstrap_sd_mean_glucose_before",
                "value": round(stability_before, 4),
            },
            {
                "metric": "bootstrap_sd_mean_glucose_after",
                "value": round(stability_after, 4),
            },
            {
                "metric": "manual_runtime_seconds",
                "value": round(manual_time, 4),
            },
            {
                "metric": "reprolab_runtime_seconds",
                "value": round(reprolab_time, 4),
            },
            {
                "metric": "estimated_manual_effort_seconds",
                "value": round(estimated_manual_seconds, 2),
            },
            {
                "metric": "estimated_time_savings_percent",
                "value": round(time_savings_pct, 2),
            },
        ]
    )

    noisy.to_csv(OUTPUT_DIR / "dataset_noisy.csv", index=False)
    manual.to_csv(OUTPUT_DIR / "dataset_manual_clean.csv", index=False)
    reprolab.to_csv(OUTPUT_DIR / "dataset_reprolab_clean.csv", index=False)
    result.transformation_log.to_csv(OUTPUT_DIR / "transformation_log.csv", index=False)
    pd.DataFrame(result.lineage_history).to_csv(
        OUTPUT_DIR / "lineage_history.csv", index=False
    )
    summary.to_csv(OUTPUT_DIR / "preliminary_metrics.csv", index=False)

    report = f"""# ReproLab Preliminary Data Summary

Generated: {pd.Timestamp.now(tz="UTC").isoformat()}

## Study Setup

- Base dataset rows: {len(clean)}
- Noisy dataset rows (with duplicates): {len(noisy)}
- Pipeline: ReproLab default clinical constraints

## Results Supporting Specific Aims

1. Reduction in missing data and inconsistencies
- Missing ratio before: {missing_before:.4f}
- Missing ratio after: {missing_after:.4f}
- Inconsistencies before: {incons_before}
- Inconsistencies after: {incons_after}

2. Improvement in overall dataset quality
- Quality score before: {quality_before:.4f}
- Quality score after: {quality_after:.4f}

3. Estimated time savings vs manual cleaning
- Manual script runtime (baseline): {manual_time:.4f} s
- ReproLab runtime: {reprolab_time:.4f} s
- Estimated manual effort (20 sec per inconsistency): {estimated_manual_seconds:.2f} s
- Estimated savings using ReproLab: {time_savings_pct:.2f}%

4. Downstream analysis stability example
- Bootstrap SD of diabetic mean glucose before: {stability_before:.4f}
- Bootstrap SD of diabetic mean glucose after: {stability_after:.4f}
- Lower SD indicates more stable summary statistics after preprocessing.

## Output Files

- dataset_noisy.csv
- dataset_manual_clean.csv
- dataset_reprolab_clean.csv
- transformation_log.csv
- lineage_history.csv
- preliminary_metrics.csv
"""
    (OUTPUT_DIR / "preliminary_report.md").write_text(report, encoding="utf-8")


if __name__ == "__main__":
    build_preliminary_outputs()

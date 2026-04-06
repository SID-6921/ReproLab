# Utility Proof Summary (Expanded Follow-Up)

## Goal

Evaluate whether ReproLab does more than separate strong datasets from weak ones by testing whether preprocessing choices improve robustness under controlled corruption.

## Method

- Script: `scripts/geo_utility_proof.py`
- Data:
  - GSE32707: stronger ARDS cohort
  - GSE3037: weaker paired LPS/control cohort
- Runs: 4 per scenario
- Scenarios:
  - `mixed_noise`: 3% missing + 10% gaussian noise + 1% outliers
  - `high_missingness`: 25% missing only
  - `structured_batch_noise`: missingness + gaussian noise + outliers + synthetic batch shift + block missingness
  - `extreme_corruption`: higher missingness, noise, outliers, larger batch shift, larger block missingness
- Preprocessing methods:
  - `baseline`
  - `minimal_imputation`
  - `knn_imputation`
  - `variance_stabilizing`
  - `quantile_normalization`
  - `combat_like`
- Metrics:
  - Spearman correlation of log2FC vs clean reference
  - Jaccard overlap of significant genes
  - Pathway top-set Jaccard overlap
  - Pathway score Spearman correlation
  - Signal-to-noise ratio before and after preprocessing

## Main Findings

1. Quality separation remains strong.
- GSE32707 still carries a large reproducible reference signal.
- GSE3037 remains weaker and more fragile under strict inference.

2. KNN imputation is the strongest overall method.
- On GSE32707 under `high_missingness`, KNN increased gene-level Jaccard from `0.511` to `0.781`.
- On GSE32707 under `extreme_corruption`, KNN increased gene-level Jaccard from `0.151` to `0.711`.
- On `structured_batch_noise`, KNN also gave the best balance of gene-level and pathway-level stability.

3. Higher SNR alone is not enough.
- `variance_stabilizing` often produced the largest SNR gains, but it also damaged DEG overlap and biological fidelity.
- `combat_like` correction was not stable enough to use as a default preprocessing step.

4. Practical interpretation.
- ReproLab now has a stronger utility claim than before: it is both a reproducible quality gate and a useful robustness evaluation framework.
- The current best-supported preprocessing upgrade is KNN imputation, not generic normalization by default.

## Evidence Files

- `results/benchmarks/utility_proof_results.json`
- `results/robustness/` (all per-run outputs)
- `docs/ReproLab_feedback_followup_summary_2026-04-06.docx`

## Decision

- Keep KNN imputation as the most promising preprocessing direction.
- Keep pathway-level consistency metrics in the benchmark because they catch failures that SNR alone misses.
- Position current system as a reproducibility, quality-control, and robustness-evaluation framework with a defensible utility story under corruption.

# Utility Proof Summary (GSE32707 vs GSE3037)

## Goal

Evaluate whether our processing logic improves robustness versus a baseline when data are corrupted.

## Method

- Script: scripts/geo_utility_proof.py
- Data: GSE32707 (strong cohort), GSE3037 (weak paired cohort)
- Runs: 10 per scenario
- Scenarios:
  - mixed_noise: 3% missing + 10% gaussian noise + 1% outliers
  - high_missingness: 25% missing only
- Metrics:
  - Spearman correlation of log2FC vs clean reference
  - Jaccard overlap of significant genes
  - Absolute difference in significant-gene count vs reference

## Main findings

1. Quality-separation result still holds strongly.
- GSE32707 retains large corrected signal in strict analysis.
- GSE3037 remains low-confidence under FDR and mainly raw-p-value driven.

2. Current cleaning step (median imputation only) did **not** outperform baseline in this stress test.
- In both scenarios, cleaned path was similar or slightly worse on stability metrics.

3. Practical interpretation:
- Our current value is strongest as a **reproducible quality gate** and conservative statistical filter.
- The "data cleaning improves DEG stability" claim is **not yet supported** by this stress test.

## Evidence files

- utility_proof_results.json
- analysis_outputs/GSE32707_mixed_noise_baseline_runs_runs.csv
- analysis_outputs/GSE32707_mixed_noise_cleaned_runs_runs.csv
- analysis_outputs/GSE32707_high_missingness_baseline_runs_runs.csv
- analysis_outputs/GSE32707_high_missingness_cleaned_runs_runs.csv
- analysis_outputs/GSE3037_mixed_noise_baseline_runs_runs.csv
- analysis_outputs/GSE3037_mixed_noise_cleaned_runs_runs.csv
- analysis_outputs/GSE3037_high_missingness_baseline_runs_runs.csv
- analysis_outputs/GSE3037_high_missingness_cleaned_runs_runs.csv

## Decision

- Keep current benchmark outputs for transparency.
- Position current system as: reproducibility and quality-control framework.
- Next technical step: implement and validate a stronger normalization/denoising module before claiming cleaning lift.

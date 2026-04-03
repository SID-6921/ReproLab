# GEO Benchmark Team Summary

## What we tested

We ran internal scripts on two public ARDS-related GEO datasets:

- High-signal candidate: GSE32707
- Lower-signal benchmark: GSE3037

Scripts used:

- scripts/geo_benchmark.py (initial quick pass)
- scripts/geo_benchmark_strict.py (gene-level collapse + paired test for GSE3037)

## Is our script useful or useless?

**Conclusion: useful.**

Why:

1. It reproduces a clear quality separation between the datasets.
2. GSE32707 remains strongly significant after multiple-testing correction.
3. GSE3037 shows weak evidence under FDR (0 DEGs at strict threshold), despite some raw p-value hits.

This behavior is exactly what we expect from a stronger vs weaker benchmark pair.

## Temporary output snapshot

### Strict pass (latest)

- GSE32707 (ARDS day0 vs untreated, n=18 vs 34)
  - FDR<0.05 & |log2FC|>=1: **3424**
  - raw p<0.05 & |log2FC|>=1: **6178**

- GSE3037 paired LPS vs control (8 pairs)
  - FDR<0.05 & |log2FC|>=1: **0**
  - raw p<0.05 & |log2FC|>=1: **499**

- GSE3037 paired HMGB1 vs control (8 pairs)
  - FDR<0.05 & |log2FC|>=1: **0**
  - raw p<0.05 & |log2FC|>=1: **215**

## Output files in repo

- geo_benchmark_results.json
- geo_benchmark_strict_results.json
- analysis_outputs/GSE32707_top_genes.csv
- analysis_outputs/GSE3037_LPS_vs_control_top_genes.csv
- analysis_outputs/GSE3037_HMGB1_vs_control_top_genes.csv

## Notes

- These are temporary benchmark outputs meant for method validation and team discussion.
- For publication-grade claims, use a finalized normalization and modeling protocol and lock thresholds before reruns.

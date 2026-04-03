# ReproLab Preliminary Data Summary

Generated: 2026-03-29T14:43:23.341252+00:00

## Study Setup

- Base dataset rows: 600
- Noisy dataset rows (with duplicates): 630
- Pipeline: ReproLab default clinical constraints

## Results Supporting Specific Aims

1. Reduction in missing data and inconsistencies
- Missing ratio before: 0.0177
- Missing ratio after: 0.0000
- Inconsistencies before: 315
- Inconsistencies after: 72

2. Improvement in overall dataset quality
- Quality score before: 0.7823
- Quality score after: 0.9520

3. Estimated time savings vs manual cleaning
- Manual script runtime (baseline): 0.0059 s
- ReproLab runtime: 0.0398 s
- Estimated manual effort (20 sec per inconsistency): 6300.00 s
- Estimated savings using ReproLab: 100.00%

4. Downstream analysis stability example
- Bootstrap SD of diabetic mean glucose before: 2.5583
- Bootstrap SD of diabetic mean glucose after: 2.1544
- Lower SD indicates more stable summary statistics after preprocessing.

## Output Files

- dataset_noisy.csv
- dataset_manual_clean.csv
- dataset_reprolab_clean.csv
- transformation_log.csv
- lineage_history.csv
- preliminary_metrics.csv

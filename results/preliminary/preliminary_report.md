# ReproLab Preliminary Data Summary

Generated: 2026-05-18T22:17:18.520159+00:00

## Study Setup

- Real-world cohort dataset rows (MIMIC-IV extract): 546038
- Pipeline: ReproLab default clinical constraints

## Results Supporting Specific Aims

1. Reduction in missing data and inconsistencies
- Missing ratio before: 0.1184
- Missing ratio after: 0.0000
- Inconsistencies before: 881049
- Inconsistencies after: 479440

2. Improvement in overall dataset quality
- Quality score before: 0.2362
- Quality score after: 0.6488

3. Estimated time savings vs manual cleaning
- Manual script runtime (baseline): 1.0092 s
- ReproLab runtime: 42.5065 s
- Estimated manual effort (20 sec per inconsistency): 17620980.00 s
- Estimated savings using ReproLab: 100.00%

4. Downstream analysis stability example
- Bootstrap SD of diabetic mean glucose before: 7.2643
- Bootstrap SD of diabetic mean glucose after: 0.1909
- Lower SD indicates more stable summary statistics after preprocessing.

## Output Files

- dataset_noisy.csv
- dataset_manual_clean.csv
- dataset_reprolab_clean.csv
- transformation_log.csv
- lineage_history.csv
- preliminary_metrics.csv

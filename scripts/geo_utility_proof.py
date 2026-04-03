import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from geo_benchmark_strict import (
    GEOparse,
    classify_gse3037_and_patient,
    classify_gse32707,
    collapse_probes_to_genes,
    paired_test,
    two_group_test,
)


def preprocess_matrix(expr: pd.DataFrame) -> pd.DataFrame:
    arr = expr.to_numpy(dtype=float).copy()

    # Median imputation per gene.
    med = np.nanmedian(arr, axis=1)
    row_idx, col_idx = np.where(np.isnan(arr))
    if len(row_idx):
        arr[row_idx, col_idx] = med[row_idx]

    # Keep values unchanged after imputation to avoid distorting fold-change ranking.
    return pd.DataFrame(arr, index=expr.index, columns=expr.columns)


def corrupt_matrix(
    expr: pd.DataFrame,
    rng: np.random.Generator,
    missing_rate: float,
    gaussian_noise_rate: float,
    outlier_rate: float,
) -> pd.DataFrame:
    arr = expr.to_numpy(dtype=float).copy()
    n_genes, n_samples = arr.shape

    # Missingness injection.
    miss_mask = rng.random(arr.shape) < missing_rate
    arr[miss_mask] = np.nan

    # Add moderate gaussian noise to random values.
    noise_mask = rng.random(arr.shape) < gaussian_noise_rate
    arr[noise_mask] = arr[noise_mask] + rng.normal(0.0, 0.5, size=noise_mask.sum())

    # Inject sparse extreme outliers.
    out_mask = rng.random(arr.shape) < outlier_rate
    signs = rng.choice([-1.0, 1.0], size=out_mask.sum())
    arr[out_mask] = arr[out_mask] + signs * rng.uniform(3.0, 6.0, size=out_mask.sum())

    return pd.DataFrame(arr, index=expr.index, columns=expr.columns)


def jaccard(a: set, b: set) -> float:
    if not a and not b:
        return 1.0
    union = a | b
    if not union:
        return 1.0
    return len(a & b) / len(union)


def metric_from_result(ref_df: pd.DataFrame, test_df: pd.DataFrame, sig_col: str) -> dict:
    ref_map = ref_df.set_index("gene")
    tst_map = test_df.set_index("gene")
    common = ref_map.index.intersection(tst_map.index)

    r = ref_map.loc[common, "log2fc"].to_numpy(dtype=float)
    t = tst_map.loc[common, "log2fc"].to_numpy(dtype=float)
    corr = spearmanr(r, t, nan_policy="omit").correlation
    if np.isnan(corr):
        corr = 0.0

    ref_sig = set(ref_map.index[ref_map[sig_col]].tolist())
    tst_sig = set(tst_map.index[tst_map[sig_col]].tolist())

    return {
        "spearman_log2fc": float(corr),
        "jaccard_significant": float(jaccard(ref_sig, tst_sig)),
        "ref_sig_count": int(len(ref_sig)),
        "test_sig_count": int(len(tst_sig)),
        "abs_sig_count_delta": int(abs(len(ref_sig) - len(tst_sig))),
    }


def prepare_gse32707(cache_dir: Path):
    gse = GEOparse.get_GEO(geo="GSE32707", destdir=str(cache_dir), silent=True)
    expr = gse.pivot_samples("VALUE")
    gpl = list(gse.gpls.values())[0].table
    expr_gene = collapse_probes_to_genes(expr, gpl, symbol_col="Symbol")

    rows = []
    for gsm_id, gsm in gse.gsms.items():
        title = gsm.metadata.get("title", [""])[0]
        src = gsm.metadata.get("source_name_ch1", [""])[0]
        chars = " | ".join(gsm.metadata.get("characteristics_ch1", []))
        grp, day = classify_gse32707(" ".join([title, src, chars]))
        rows.append({"gsm": gsm_id, "group": grp, "day": day})
    meta = pd.DataFrame(rows)

    a = [c for c in meta[(meta["group"] == "ards") & (meta["day"] == "day0")]["gsm"].tolist() if c in expr_gene.columns]
    b = [c for c in meta[(meta["group"] == "control")]["gsm"].tolist() if c in expr_gene.columns]
    return expr_gene, a, b


def prepare_gse3037(cache_dir: Path):
    gse = GEOparse.get_GEO(geo="GSE3037", destdir=str(cache_dir), silent=True)
    expr = gse.pivot_samples("VALUE")
    gpl = list(gse.gpls.values())[0].table
    expr_gene = collapse_probes_to_genes(expr, gpl, symbol_col="Gene Symbol")

    rows = []
    for gsm_id, gsm in gse.gsms.items():
        title = gsm.metadata.get("title", [""])[0]
        src = gsm.metadata.get("source_name_ch1", [""])[0]
        grp, pid = classify_gse3037_and_patient(" ".join([title, src]))
        rows.append({"gsm": gsm_id, "group": grp, "patient": pid})
    meta = pd.DataFrame(rows)

    def matched(group_name):
        t = meta[meta["group"] == group_name][["patient", "gsm"]].dropna()
        c = meta[meta["group"] == "control"][["patient", "gsm"]].dropna()
        m = t.merge(c, on="patient", suffixes=("_treated", "_control"))
        tr = [x for x in m["gsm_treated"].tolist() if x in expr_gene.columns]
        ct = [x for x in m["gsm_control"].tolist() if x in expr_gene.columns]
        return tr, ct

    lps_t, lps_c = matched("lps")
    return expr_gene, lps_t, lps_c


def aggregate_metrics(rows):
    return {
        "mean_spearman_log2fc": float(np.mean([r["spearman_log2fc"] for r in rows])),
        "mean_jaccard_significant": float(np.mean([r["jaccard_significant"] for r in rows])),
        "mean_abs_sig_count_delta": float(np.mean([r["abs_sig_count_delta"] for r in rows])),
        "mean_test_sig_count": float(np.mean([r["test_sig_count"] for r in rows])),
    }


def main():
    cache_dir = Path(".geo_cache")
    cache_dir.mkdir(exist_ok=True)
    out_dir = Path("results/robustness")
    out_dir.mkdir(parents=True, exist_ok=True)

    rng = np.random.default_rng(42)
    n_runs = 10
    scenarios = {
        "mixed_noise": {
            "missing_rate": 0.03,
            "gaussian_noise_rate": 0.10,
            "outlier_rate": 0.01,
        },
        "high_missingness": {
            "missing_rate": 0.25,
            "gaussian_noise_rate": 0.00,
            "outlier_rate": 0.00,
        },
    }

    # References on clean data
    expr1, g1_a, g1_b = prepare_gse32707(cache_dir)
    ref1 = two_group_test(expr1, g1_a, g1_b)

    expr2, g2_t, g2_c = prepare_gse3037(cache_dir)
    ref2 = paired_test(expr2, g2_t, g2_c)

    results = {
        "experiment": {
            "n_runs": n_runs,
            "scenarios": scenarios,
        },
        "GSE32707_reference_sig_count_fdr": int(ref1["sig_adj_lfc"].sum()),
        "GSE3037_reference_sig_count_raw": int(ref2["sig_raw_lfc"].sum()),
        "scenario_results": {},
    }

    per_run_tables = {}

    for scenario_name, params in scenarios.items():
        g1_base_rows = []
        g1_clean_rows = []
        g2_base_rows = []
        g2_clean_rows = []

        for _ in range(n_runs):
            corr1 = corrupt_matrix(expr1, rng, **params)
            base1 = two_group_test(corr1, g1_a, g1_b)
            clean1 = two_group_test(preprocess_matrix(corr1), g1_a, g1_b)
            g1_base_rows.append(metric_from_result(ref1, base1, "sig_adj_lfc"))
            g1_clean_rows.append(metric_from_result(ref1, clean1, "sig_adj_lfc"))

            corr2 = corrupt_matrix(expr2, rng, **params)
            base2 = paired_test(corr2, g2_t, g2_c)
            clean2 = paired_test(preprocess_matrix(corr2), g2_t, g2_c)
            g2_base_rows.append(metric_from_result(ref2, base2, "sig_raw_lfc"))
            g2_clean_rows.append(metric_from_result(ref2, clean2, "sig_raw_lfc"))

        results["scenario_results"][scenario_name] = {
            "GSE32707": {
                "baseline": aggregate_metrics(g1_base_rows),
                "cleaned": aggregate_metrics(g1_clean_rows),
            },
            "GSE3037": {
                "baseline": aggregate_metrics(g2_base_rows),
                "cleaned": aggregate_metrics(g2_clean_rows),
            },
        }

        per_run_tables[f"GSE32707_{scenario_name}_baseline"] = pd.DataFrame(g1_base_rows)
        per_run_tables[f"GSE32707_{scenario_name}_cleaned"] = pd.DataFrame(g1_clean_rows)
        per_run_tables[f"GSE3037_{scenario_name}_baseline"] = pd.DataFrame(g2_base_rows)
        per_run_tables[f"GSE3037_{scenario_name}_cleaned"] = pd.DataFrame(g2_clean_rows)

    out_json = Path("results/benchmarks/utility_proof_results.json")
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(results, indent=2), encoding="utf-8")

    # Save per-run metrics for auditability.
    for name, df in per_run_tables.items():
        df.to_csv(out_dir / f"{name}_runs.csv", index=False)

    print(json.dumps(results, indent=2))
    print(f"Saved utility results to: {out_json.resolve()}")


if __name__ == "__main__":
    main()

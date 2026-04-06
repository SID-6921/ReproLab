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


CANONICAL_PATHWAYS = {
    "inflammatory_response": {
        "IL1B",
        "IL6",
        "TNF",
        "CXCL8",
        "NFKB1",
        "NFKBIA",
        "CCL2",
        "STAT3",
        "PTGS2",
        "CXCL10",
    },
    "interferon_signaling": {
        "IFIT1",
        "IFIT3",
        "ISG15",
        "MX1",
        "OAS1",
        "OAS2",
        "STAT1",
        "IRF7",
        "IFI44",
        "IFI27",
    },
    "innate_immune_activation": {
        "TLR2",
        "TLR4",
        "MYD88",
        "TRAF6",
        "RELA",
        "IRAK1",
        "MAPK14",
        "JUN",
        "FOS",
        "CD14",
    },
    "stress_response": {
        "HMOX1",
        "SOD2",
        "CAT",
        "GPX1",
        "HSP90AA1",
        "DNAJB1",
        "DDIT3",
        "ATF4",
        "XBP1",
        "HSPB1",
    },
}


def row_median_impute(expr: pd.DataFrame) -> pd.DataFrame:
    arr = expr.to_numpy(dtype=float).copy()
    med = np.nanmedian(arr, axis=1)
    row_idx, col_idx = np.where(np.isnan(arr))
    if len(row_idx):
        arr[row_idx, col_idx] = med[row_idx]
    arr[np.isnan(arr)] = 0.0
    return pd.DataFrame(arr, index=expr.index, columns=expr.columns)


def signal_to_noise_ratio(expr: pd.DataFrame) -> float:
    arr = expr.to_numpy(dtype=float)
    snrs = []
    for row in arr:
        valid = row[~np.isnan(row)]
        if len(valid) > 1:
            std_val = np.std(valid)
            if std_val > 0:
                snrs.append(np.abs(np.mean(valid)) / std_val)
    return float(np.mean(snrs)) if snrs else 0.0


def quantile_normalize(expr: pd.DataFrame) -> pd.DataFrame:
    # Quantile normalization requires no missing values.
    arr = row_median_impute(expr).to_numpy(dtype=float)
    sorted_vals = np.sort(arr, axis=0)
    mean_sorted = np.mean(sorted_vals, axis=1)

    out = np.empty_like(arr)
    for j in range(arr.shape[1]):
        order = np.argsort(arr[:, j])
        out[order, j] = mean_sorted

    return pd.DataFrame(out, index=expr.index, columns=expr.columns)


def knn_impute(expr: pd.DataFrame, k: int = 5) -> pd.DataFrame:
    arr_raw = expr.to_numpy(dtype=float)
    if not np.isnan(arr_raw).any():
        return expr.copy()

    # Distance matrix built from row-median-filled matrix.
    arr_fill = row_median_impute(expr).to_numpy(dtype=float)
    sample_vectors = arr_fill.T
    dists = np.sqrt(((sample_vectors[:, None, :] - sample_vectors[None, :, :]) ** 2).mean(axis=2))

    out = arr_raw.copy()
    row_medians = np.nanmedian(arr_raw, axis=1)

    for sample_idx in range(out.shape[1]):
        missing_rows = np.where(np.isnan(out[:, sample_idx]))[0]
        if len(missing_rows) == 0:
            continue

        neighbors = np.argsort(dists[sample_idx])
        neighbors = neighbors[neighbors != sample_idx]

        for gene_idx in missing_rows:
            chosen = []
            for n in neighbors:
                val = arr_raw[gene_idx, n]
                if not np.isnan(val):
                    chosen.append((n, dists[sample_idx, n]))
                if len(chosen) >= k:
                    break

            if not chosen:
                out[gene_idx, sample_idx] = row_medians[gene_idx] if not np.isnan(row_medians[gene_idx]) else 0.0
                continue

            vals = np.array([arr_raw[gene_idx, n] for n, _ in chosen], dtype=float)
            ws = np.array([1.0 / (dist + 1e-6) for _, dist in chosen], dtype=float)
            out[gene_idx, sample_idx] = float(np.sum(vals * ws) / np.sum(ws))

    out[np.isnan(out)] = 0.0
    return pd.DataFrame(out, index=expr.index, columns=expr.columns)


def variance_stabilize(expr: pd.DataFrame) -> pd.DataFrame:
    # Simple VSN-like transform: shift to positive then log2.
    arr = row_median_impute(expr).to_numpy(dtype=float)
    min_val = float(np.min(arr))
    shifted = arr - min_val + 1.0
    vsn = np.log2(shifted)
    return pd.DataFrame(vsn, index=expr.index, columns=expr.columns)


def combat_like_correction(expr: pd.DataFrame, batch_labels: np.ndarray) -> pd.DataFrame:
    # Location-scale batch correction with known synthetic batch labels.
    arr = row_median_impute(expr).to_numpy(dtype=float)
    corrected = arr.copy()
    eps = 1e-6

    global_mean = np.mean(arr, axis=1, keepdims=True)
    global_std = np.std(arr, axis=1, keepdims=True)

    for b in np.unique(batch_labels):
        idx = np.where(batch_labels == b)[0]
        if len(idx) < 2:
            continue
        batch = arr[:, idx]
        b_mean = np.mean(batch, axis=1, keepdims=True)
        b_std = np.std(batch, axis=1, keepdims=True)
        corrected[:, idx] = ((batch - b_mean) / (b_std + eps)) * (global_std + eps) + global_mean

    return pd.DataFrame(corrected, index=expr.index, columns=expr.columns)


def corrupt_matrix(
    expr: pd.DataFrame,
    rng: np.random.Generator,
    missing_rate: float,
    gaussian_noise_rate: float,
    outlier_rate: float,
    batch_shift: float = 0.0,
    block_missing_rate: float = 0.0,
) -> tuple[pd.DataFrame, np.ndarray]:
    arr = expr.to_numpy(dtype=float).copy()
    n_genes, n_samples = arr.shape

    # Synthetic batch labels for correction experiments.
    batch_labels = np.zeros(n_samples, dtype=int)
    batch_labels[n_samples // 2 :] = 1

    miss_mask = rng.random(arr.shape) < missing_rate
    arr[miss_mask] = np.nan

    noise_mask = rng.random(arr.shape) < gaussian_noise_rate
    arr[noise_mask] = arr[noise_mask] + rng.normal(0.0, 0.5, size=noise_mask.sum())

    out_mask = rng.random(arr.shape) < outlier_rate
    signs = rng.choice([-1.0, 1.0], size=out_mask.sum())
    arr[out_mask] = arr[out_mask] + signs * rng.uniform(3.0, 6.0, size=out_mask.sum())

    # Structured block missingness.
    if block_missing_rate > 0:
        g_block = max(1, int(n_genes * block_missing_rate))
        s_block = max(1, int(n_samples * block_missing_rate))
        g_start = int(rng.integers(0, max(1, n_genes - g_block + 1)))
        s_start = int(rng.integers(0, max(1, n_samples - s_block + 1)))
        arr[g_start : g_start + g_block, s_start : s_start + s_block] = np.nan

    # Structured batch shift on a subset of genes in batch 1.
    if batch_shift > 0:
        batch1 = np.where(batch_labels == 1)[0]
        affected = rng.choice(n_genes, size=max(1, int(0.2 * n_genes)), replace=False)
        arr[np.ix_(affected, batch1)] = arr[np.ix_(affected, batch1)] + batch_shift

    return pd.DataFrame(arr, index=expr.index, columns=expr.columns), batch_labels


def jaccard(a: set, b: set) -> float:
    if not a and not b:
        return 1.0
    union = a | b
    if not union:
        return 1.0
    return len(a & b) / len(union)


def build_pathways_from_reference(ref_df: pd.DataFrame, all_genes: set[str]) -> dict[str, set[str]]:
    pathways = {}

    # Keep canonical pathways that overlap with this dataset.
    for name, genes in CANONICAL_PATHWAYS.items():
        overlap = set(g for g in genes if g in all_genes)
        if len(overlap) >= 3:
            pathways[name] = overlap

    # Add data-driven pathways from strongest reference signal if canonical overlap is low.
    ranked = ref_df.sort_values("log2fc", key=lambda s: np.abs(s), ascending=False)["gene"].tolist()
    block_size = 80
    for i in range(0, min(len(ranked), 800), block_size):
        block = set(ranked[i : i + block_size])
        if len(block) >= 20:
            pathways[f"data_driven_block_{i // block_size + 1}"] = block

    return pathways


def pathway_scores(deg_df: pd.DataFrame, pathways: dict[str, set[str]]) -> dict[str, float]:
    m = deg_df.set_index("gene")
    scores = {}
    for name, genes in pathways.items():
        overlap = [g for g in genes if g in m.index]
        if len(overlap) < 3:
            scores[name] = 0.0
            continue
        vals = np.abs(m.loc[overlap, "log2fc"].to_numpy(dtype=float))
        scores[name] = float(np.mean(vals) * np.sqrt(len(overlap)))
    return scores


def metric_from_result(
    ref_df: pd.DataFrame,
    test_df: pd.DataFrame,
    sig_col: str,
    pathways: dict[str, set[str]],
    snr_before: float | None = None,
    snr_after: float | None = None,
) -> dict:
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

    ref_ps = pathway_scores(ref_df, pathways)
    tst_ps = pathway_scores(test_df, pathways)
    top_k = min(5, len(pathways)) if pathways else 0
    if top_k > 0:
        ref_top = {k for k, _ in sorted(ref_ps.items(), key=lambda x: x[1], reverse=True)[:top_k]}
        tst_top = {k for k, _ in sorted(tst_ps.items(), key=lambda x: x[1], reverse=True)[:top_k]}
        p_jacc = jaccard(ref_top, tst_top)
        keys = list(ref_ps.keys())
        p_corr = spearmanr([ref_ps[k] for k in keys], [tst_ps[k] for k in keys], nan_policy="omit").correlation
        if np.isnan(p_corr):
            p_corr = 0.0
    else:
        p_jacc = 0.0
        p_corr = 0.0

    out = {
        "spearman_log2fc": float(corr),
        "jaccard_significant": float(jaccard(ref_sig, tst_sig)),
        "pathway_top_jaccard": float(p_jacc),
        "pathway_score_spearman": float(p_corr),
        "ref_sig_count": int(len(ref_sig)),
        "test_sig_count": int(len(tst_sig)),
        "abs_sig_count_delta": int(abs(len(ref_sig) - len(tst_sig))),
    }

    if snr_before is not None:
        out["snr_before"] = float(snr_before)
    if snr_after is not None:
        out["snr_after"] = float(snr_after)

    return out


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


def aggregate_metrics(rows: list[dict]) -> dict:
    agg = {
        "mean_spearman_log2fc": float(np.mean([r["spearman_log2fc"] for r in rows])),
        "mean_jaccard_significant": float(np.mean([r["jaccard_significant"] for r in rows])),
        "mean_pathway_top_jaccard": float(np.mean([r["pathway_top_jaccard"] for r in rows])),
        "mean_pathway_score_spearman": float(np.mean([r["pathway_score_spearman"] for r in rows])),
        "mean_abs_sig_count_delta": float(np.mean([r["abs_sig_count_delta"] for r in rows])),
        "mean_test_sig_count": float(np.mean([r["test_sig_count"] for r in rows])),
    }

    if any("snr_before" in r for r in rows):
        agg["mean_snr_before"] = float(np.mean([r["snr_before"] for r in rows if "snr_before" in r]))
    if any("snr_after" in r for r in rows):
        agg["mean_snr_after"] = float(np.mean([r["snr_after"] for r in rows if "snr_after" in r]))
        if "mean_snr_before" in agg and agg["mean_snr_before"] > 0:
            agg["snr_improvement_ratio"] = float(agg["mean_snr_after"] / agg["mean_snr_before"])

    return agg


def run_method(name: str, expr: pd.DataFrame, batch_labels: np.ndarray | None) -> pd.DataFrame:
    if name == "baseline":
        return expr
    if name == "minimal_imputation":
        return row_median_impute(expr)
    if name == "knn_imputation":
        return knn_impute(expr)
    if name == "variance_stabilizing":
        return variance_stabilize(expr)
    if name == "quantile_normalization":
        return quantile_normalize(expr)
    if name == "combat_like":
        if batch_labels is None:
            return row_median_impute(expr)
        return combat_like_correction(expr, batch_labels)
    raise ValueError(f"Unknown method: {name}")


def main():
    cache_dir = Path(".geo_cache")
    cache_dir.mkdir(exist_ok=True)
    out_dir = Path("results/robustness")
    out_dir.mkdir(parents=True, exist_ok=True)

    rng = np.random.default_rng(42)
    n_runs = 4
    scenarios = {
        "mixed_noise": {
            "missing_rate": 0.03,
            "gaussian_noise_rate": 0.10,
            "outlier_rate": 0.01,
            "batch_shift": 0.0,
            "block_missing_rate": 0.0,
        },
        "high_missingness": {
            "missing_rate": 0.25,
            "gaussian_noise_rate": 0.00,
            "outlier_rate": 0.00,
            "batch_shift": 0.0,
            "block_missing_rate": 0.0,
        },
        "structured_batch_noise": {
            "missing_rate": 0.10,
            "gaussian_noise_rate": 0.15,
            "outlier_rate": 0.02,
            "batch_shift": 1.5,
            "block_missing_rate": 0.08,
        },
        "extreme_corruption": {
            "missing_rate": 0.35,
            "gaussian_noise_rate": 0.20,
            "outlier_rate": 0.03,
            "batch_shift": 2.0,
            "block_missing_rate": 0.15,
        },
    }

    methods = [
        "baseline",
        "minimal_imputation",
        "knn_imputation",
        "variance_stabilizing",
        "quantile_normalization",
        "combat_like",
    ]

    expr1, g1_a, g1_b = prepare_gse32707(cache_dir)
    ref1 = two_group_test(expr1, g1_a, g1_b)
    pathways1 = build_pathways_from_reference(ref1, set(expr1.index.astype(str)))

    expr2, g2_t, g2_c = prepare_gse3037(cache_dir)
    ref2 = paired_test(expr2, g2_t, g2_c)
    pathways2 = build_pathways_from_reference(ref2, set(expr2.index.astype(str)))

    results = {
        "experiment": {
            "n_runs": n_runs,
            "scenarios": scenarios,
            "preprocessing_methods": methods,
            "pathway_count_GSE32707": len(pathways1),
            "pathway_count_GSE3037": len(pathways2),
        },
        "GSE32707_reference_sig_count_fdr": int(ref1["sig_adj_lfc"].sum()),
        "GSE3037_reference_sig_count_raw": int(ref2["sig_raw_lfc"].sum()),
        "scenario_results": {},
    }

    per_run_tables = {}

    for scenario_name, params in scenarios.items():
        by_method_1 = {m: [] for m in methods}
        by_method_2 = {m: [] for m in methods}

        for _ in range(n_runs):
            corr1, batch1 = corrupt_matrix(expr1, rng, **params)
            corr2, batch2 = corrupt_matrix(expr2, rng, **params)
            snr1_before = signal_to_noise_ratio(corr1)
            snr2_before = signal_to_noise_ratio(corr2)

            for m in methods:
                p1 = run_method(m, corr1, batch1)
                p2 = run_method(m, corr2, batch2)

                d1 = two_group_test(p1, g1_a, g1_b)
                d2 = paired_test(p2, g2_t, g2_c)

                by_method_1[m].append(
                    metric_from_result(
                        ref1,
                        d1,
                        "sig_adj_lfc",
                        pathways1,
                        snr_before=snr1_before,
                        snr_after=signal_to_noise_ratio(p1),
                    )
                )
                by_method_2[m].append(
                    metric_from_result(
                        ref2,
                        d2,
                        "sig_raw_lfc",
                        pathways2,
                        snr_before=snr2_before,
                        snr_after=signal_to_noise_ratio(p2),
                    )
                )

        results["scenario_results"][scenario_name] = {
            "GSE32707": {m: aggregate_metrics(rows) for m, rows in by_method_1.items()},
            "GSE3037": {m: aggregate_metrics(rows) for m, rows in by_method_2.items()},
        }

        for m, rows in by_method_1.items():
            per_run_tables[f"GSE32707_{scenario_name}_{m}"] = pd.DataFrame(rows)
        for m, rows in by_method_2.items():
            per_run_tables[f"GSE3037_{scenario_name}_{m}"] = pd.DataFrame(rows)

    out_json = Path("results/benchmarks/utility_proof_results.json")
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(results, indent=2), encoding="utf-8")

    for name, df in per_run_tables.items():
        df.to_csv(out_dir / f"{name}_runs.csv", index=False)

    print(json.dumps(results, indent=2))
    print(f"Saved utility results to: {out_json.resolve()}")


if __name__ == "__main__":
    main()

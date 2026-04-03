import json
import re
from pathlib import Path

import GEOparse
import numpy as np
import pandas as pd
from scipy.stats import ttest_1samp, ttest_ind
from statsmodels.stats.multitest import multipletests


def _split_symbols(raw: str):
    if raw is None:
        return []
    txt = str(raw).strip()
    if not txt or txt in {"---", "NA", "nan"}:
        return []
    parts = re.split(r"\s*///\s*|\s*;\s*|\s*,\s*", txt)
    out = []
    for p in parts:
        p2 = p.strip().upper()
        if p2 and p2 not in {"---", "NA", "N/A", "NULL"}:
            out.append(p2)
    return out


def collapse_probes_to_genes(expr: pd.DataFrame, gpl_table: pd.DataFrame, symbol_col: str):
    ann = gpl_table[["ID", symbol_col]].copy()
    ann.columns = ["probe_id", "symbol_raw"]
    ann = ann[ann["probe_id"].isin(expr.index)].copy()
    ann["symbols"] = ann["symbol_raw"].apply(_split_symbols)
    ann = ann.explode("symbols")
    ann = ann.dropna(subset=["symbols"])
    ann = ann.rename(columns={"symbols": "gene"})

    expr2 = expr.copy()
    expr2["probe_id"] = expr2.index
    merged = ann.merge(expr2, on="probe_id", how="inner")

    sample_cols = [c for c in expr.columns]
    merged["probe_var"] = merged[sample_cols].var(axis=1, ddof=1)

    idx = merged.groupby("gene")["probe_var"].idxmax()
    best = merged.loc[idx, ["gene", *sample_cols]].copy()
    best = best.set_index("gene").sort_index()
    return best


def classify_gse32707(text: str):
    t = (text or "").lower()
    day = "day0" if ("day 0" in t or "day0" in t) else ("day7" if ("day 7" in t or "day7" in t) else None)
    if "ards" in t:
        grp = "ards"
    elif "untreated" in t or "without sepsis" in t:
        grp = "control"
    elif "sirs" in t:
        grp = "sirs"
    elif "sepsis" in t:
        grp = "sepsis"
    else:
        grp = None
    return grp, day


def classify_gse3037_and_patient(text: str):
    t = (text or "").lower()
    patient_match = re.search(r"patient\s*(\d+)", t)
    patient = patient_match.group(1).zfill(2) if patient_match else None
    if "hmgb1" in t:
        group = "hmgb1"
    elif "lps" in t:
        group = "lps"
    elif "control" in t:
        group = "control"
    else:
        group = None
    return group, patient


def two_group_test(expr: pd.DataFrame, group_a_cols, group_b_cols, lfc_threshold=1.0):
    a = expr[group_a_cols].to_numpy(dtype=float)
    b = expr[group_b_cols].to_numpy(dtype=float)

    mean_a = np.nanmean(a, axis=1)
    mean_b = np.nanmean(b, axis=1)
    log2fc = mean_a - mean_b
    pvals = ttest_ind(a, b, axis=1, equal_var=False, nan_policy="omit").pvalue
    pvals = np.nan_to_num(pvals, nan=1.0, posinf=1.0, neginf=1.0)
    adj = multipletests(pvals, method="fdr_bh")[1]

    df = pd.DataFrame({"gene": expr.index, "log2fc": log2fc, "pvalue": pvals, "adj_pvalue": adj})
    df["sig_adj_lfc"] = (df["adj_pvalue"] < 0.05) & (df["log2fc"].abs() >= lfc_threshold)
    df["sig_raw_lfc"] = (df["pvalue"] < 0.05) & (df["log2fc"].abs() >= lfc_threshold)
    return df


def paired_test(expr: pd.DataFrame, treated_cols, control_cols, lfc_threshold=1.0):
    tr = expr[treated_cols].to_numpy(dtype=float)
    ct = expr[control_cols].to_numpy(dtype=float)
    diff = tr - ct
    mean_diff = np.nanmean(diff, axis=1)

    pvals = ttest_1samp(diff, popmean=0.0, axis=1, nan_policy="omit").pvalue
    pvals = np.nan_to_num(pvals, nan=1.0, posinf=1.0, neginf=1.0)
    adj = multipletests(pvals, method="fdr_bh")[1]

    df = pd.DataFrame({"gene": expr.index, "log2fc": mean_diff, "pvalue": pvals, "adj_pvalue": adj})
    df["sig_adj_lfc"] = (df["adj_pvalue"] < 0.05) & (df["log2fc"].abs() >= lfc_threshold)
    df["sig_raw_lfc"] = (df["pvalue"] < 0.05) & (df["log2fc"].abs() >= lfc_threshold)
    return df


def summarize(df: pd.DataFrame):
    return {
        "deg_adj_p_lt_0_05_lfc_ge_1": int(df["sig_adj_lfc"].sum()),
        "deg_raw_p_lt_0_05_lfc_ge_1": int(df["sig_raw_lfc"].sum()),
    }


def save_top(df: pd.DataFrame, out_csv: Path, n=25):
    d = df.sort_values(["adj_pvalue", "pvalue"]).head(n).copy()
    d.to_csv(out_csv, index=False)


def main():
    out_dir = Path("analysis_outputs")
    out_dir.mkdir(exist_ok=True)
    cache_dir = Path(".geo_cache")
    cache_dir.mkdir(exist_ok=True)

    results = {}

    # GSE32707 strict (gene-collapsed)
    gse1 = GEOparse.get_GEO(geo="GSE32707", destdir=str(cache_dir), silent=True)
    expr1 = gse1.pivot_samples("VALUE")
    gpl1 = list(gse1.gpls.values())[0].table
    expr1_gene = collapse_probes_to_genes(expr1, gpl1, symbol_col="Symbol")

    meta_rows1 = []
    for gsm_id, gsm in gse1.gsms.items():
        title = gsm.metadata.get("title", [""])[0]
        src = gsm.metadata.get("source_name_ch1", [""])[0]
        chars = " | ".join(gsm.metadata.get("characteristics_ch1", []))
        text = " ".join([title, src, chars])
        grp, day = classify_gse32707(text)
        meta_rows1.append({"gsm": gsm_id, "group": grp, "day": day})
    meta1 = pd.DataFrame(meta_rows1)

    ards_cols = meta1[(meta1["group"] == "ards") & (meta1["day"] == "day0")]["gsm"].tolist()
    control_cols = meta1[(meta1["group"] == "control")]["gsm"].tolist()
    ards_cols = [c for c in ards_cols if c in expr1_gene.columns]
    control_cols = [c for c in control_cols if c in expr1_gene.columns]

    d1 = two_group_test(expr1_gene, ards_cols, control_cols)
    save_top(d1, out_dir / "GSE32707_top_genes.csv")

    results["GSE32707_strict"] = {
        "geo_samples_total": int(len(gse1.gsms)),
        "gene_level_shape": [int(expr1_gene.shape[0]), int(expr1_gene.shape[1])],
        "contrast": {
            "name": "ARDS_day0_vs_all_untreated_controls",
            "n_ards": len(ards_cols),
            "n_control": len(control_cols),
            **summarize(d1),
        },
        "top_genes_file": str((out_dir / "GSE32707_top_genes.csv").as_posix()),
    }

    # GSE3037 strict (gene-collapsed + paired)
    gse2 = GEOparse.get_GEO(geo="GSE3037", destdir=str(cache_dir), silent=True)
    expr2 = gse2.pivot_samples("VALUE")
    gpl2 = list(gse2.gpls.values())[0].table
    expr2_gene = collapse_probes_to_genes(expr2, gpl2, symbol_col="Gene Symbol")

    meta_rows2 = []
    for gsm_id, gsm in gse2.gsms.items():
        title = gsm.metadata.get("title", [""])[0]
        src = gsm.metadata.get("source_name_ch1", [""])[0]
        text = " ".join([title, src])
        grp, pid = classify_gse3037_and_patient(text)
        meta_rows2.append({"gsm": gsm_id, "group": grp, "patient": pid})
    meta2 = pd.DataFrame(meta_rows2)

    def matched_cols(group_name):
        t = meta2[meta2["group"] == group_name][["patient", "gsm"]].dropna()
        c = meta2[meta2["group"] == "control"][ ["patient", "gsm"] ].dropna()
        m = t.merge(c, on="patient", suffixes=("_treated", "_control"))
        tr = [x for x in m["gsm_treated"].tolist() if x in expr2_gene.columns]
        ct = [x for x in m["gsm_control"].tolist() if x in expr2_gene.columns]
        return m["patient"].tolist(), tr, ct

    p_lps, lps_t, lps_c = matched_cols("lps")
    p_hm, hm_t, hm_c = matched_cols("hmgb1")

    d2_lps = paired_test(expr2_gene, lps_t, lps_c)
    d2_hm = paired_test(expr2_gene, hm_t, hm_c)

    save_top(d2_lps, out_dir / "GSE3037_LPS_vs_control_top_genes.csv")
    save_top(d2_hm, out_dir / "GSE3037_HMGB1_vs_control_top_genes.csv")

    results["GSE3037_strict"] = {
        "geo_samples_total": int(len(gse2.gsms)),
        "gene_level_shape": [int(expr2_gene.shape[0]), int(expr2_gene.shape[1])],
        "paired_contrasts": {
            "LPS_vs_control": {
                "paired_patients": p_lps,
                "n_pairs": len(p_lps),
                **summarize(d2_lps),
            },
            "HMGB1_vs_control": {
                "paired_patients": p_hm,
                "n_pairs": len(p_hm),
                **summarize(d2_hm),
            },
        },
        "top_genes_files": [
            str((out_dir / "GSE3037_LPS_vs_control_top_genes.csv").as_posix()),
            str((out_dir / "GSE3037_HMGB1_vs_control_top_genes.csv").as_posix()),
        ],
    }

    out_json = Path("geo_benchmark_strict_results.json")
    out_json.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(json.dumps(results, indent=2))
    print(f"Saved strict results to: {out_json.resolve()}")


if __name__ == "__main__":
    main()

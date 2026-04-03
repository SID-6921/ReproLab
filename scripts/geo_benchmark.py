import json
from pathlib import Path

import GEOparse
import numpy as np
import pandas as pd
from scipy.stats import ttest_ind
from statsmodels.stats.multitest import multipletests


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


def classify_gse3037(text: str):
    t = (text or "").lower()
    if "hmgb1" in t:
        return "hmgb1"
    if "lps" in t:
        return "lps"
    if "control" in t:
        return "control"
    return None


def run_deg(expr: pd.DataFrame, group_a_cols, group_b_cols, lfc_threshold=1.0):
    a = expr[group_a_cols].to_numpy(dtype=float)
    b = expr[group_b_cols].to_numpy(dtype=float)

    mean_a = np.nanmean(a, axis=1)
    mean_b = np.nanmean(b, axis=1)
    log2fc = mean_a - mean_b

    pvals = ttest_ind(a, b, axis=1, equal_var=False, nan_policy="omit").pvalue
    pvals = np.nan_to_num(pvals, nan=1.0, posinf=1.0, neginf=1.0)
    adj = multipletests(pvals, method="fdr_bh")[1]

    deg_adj = int(np.sum((adj < 0.05) & (np.abs(log2fc) >= lfc_threshold)))
    deg_raw = int(np.sum((pvals < 0.05) & (np.abs(log2fc) >= lfc_threshold)))
    return {
        "deg_adj_p_lt_0_05_lfc_ge_1": deg_adj,
        "deg_raw_p_lt_0_05_lfc_ge_1": deg_raw,
    }


def main():
    results = {}
    cache_dir = Path(".geo_cache")
    cache_dir.mkdir(exist_ok=True)

    gse1 = GEOparse.get_GEO(geo="GSE32707", destdir=str(cache_dir), silent=True)
    expr1 = gse1.pivot_samples("VALUE")

    meta_rows1 = []
    for gsm_id, gsm in gse1.gsms.items():
        title = gsm.metadata.get("title", [""])[0]
        src = gsm.metadata.get("source_name_ch1", [""])[0]
        chars = " | ".join(gsm.metadata.get("characteristics_ch1", []))
        text = " ".join([title, src, chars])
        grp, day = classify_gse32707(text)
        meta_rows1.append({"gsm": gsm_id, "group": grp, "day": day, "text": text})
    meta1 = pd.DataFrame(meta_rows1)

    sel1 = meta1[(meta1["day"] == "day0") & (meta1["group"].isin(["ards", "control"]))]
    a_cols1 = sel1[sel1["group"] == "ards"]["gsm"].tolist()
    b_cols1 = sel1[sel1["group"] == "control"]["gsm"].tolist()
    # Some untreated samples in this GEO series do not expose explicit day labels;
    # use all untreated controls as fallback so ARDS day 0 can still be contrasted.
    if not b_cols1:
        b_cols1 = meta1[meta1["group"] == "control"]["gsm"].tolist()
    common1_a = [c for c in a_cols1 if c in expr1.columns]
    common1_b = [c for c in b_cols1 if c in expr1.columns]

    deg1 = run_deg(expr1, common1_a, common1_b) if (len(common1_a) >= 3 and len(common1_b) >= 3) else {"error": "insufficient labeled samples"}

    counts1 = meta1.groupby(["group", "day"], dropna=False).size().to_dict()
    counts1_str = {f"{k[0]}|{k[1]}": int(v) for k, v in counts1.items()}

    results["GSE32707"] = {
        "geo_samples_total": int(len(gse1.gsms)),
        "expr_shape": [int(expr1.shape[0]), int(expr1.shape[1])],
        "missing_rate": float(np.isnan(expr1.to_numpy(dtype=float)).mean()),
        "labeled_group_counts": counts1_str,
        "contrast": {
            "name": "ARDS_day0_vs_untreated_day0",
            "n_ards": len(common1_a),
            "n_control": len(common1_b),
            **deg1,
        },
    }

    gse2 = GEOparse.get_GEO(geo="GSE3037", destdir=str(cache_dir), silent=True)
    expr2 = gse2.pivot_samples("VALUE")

    meta_rows2 = []
    for gsm_id, gsm in gse2.gsms.items():
        title = gsm.metadata.get("title", [""])[0]
        src = gsm.metadata.get("source_name_ch1", [""])[0]
        chars = " | ".join(gsm.metadata.get("characteristics_ch1", []))
        text = " ".join([title, src, chars])
        grp = classify_gse3037(text)
        meta_rows2.append({"gsm": gsm_id, "group": grp, "text": text})
    meta2 = pd.DataFrame(meta_rows2)

    ctrl_cols = [c for c in meta2[meta2["group"] == "control"]["gsm"].tolist() if c in expr2.columns]
    lps_cols = [c for c in meta2[meta2["group"] == "lps"]["gsm"].tolist() if c in expr2.columns]
    hmgb1_cols = [c for c in meta2[meta2["group"] == "hmgb1"]["gsm"].tolist() if c in expr2.columns]

    deg2_lps = run_deg(expr2, lps_cols, ctrl_cols) if (len(lps_cols) >= 3 and len(ctrl_cols) >= 3) else {"error": "insufficient labeled samples"}
    deg2_hmgb1 = run_deg(expr2, hmgb1_cols, ctrl_cols) if (len(hmgb1_cols) >= 3 and len(ctrl_cols) >= 3) else {"error": "insufficient labeled samples"}

    counts2 = meta2.groupby(["group"], dropna=False).size().to_dict()
    counts2_str = {str(k): int(v) for k, v in counts2.items()}

    results["GSE3037"] = {
        "geo_samples_total": int(len(gse2.gsms)),
        "expr_shape": [int(expr2.shape[0]), int(expr2.shape[1])],
        "missing_rate": float(np.isnan(expr2.to_numpy(dtype=float)).mean()),
        "labeled_group_counts": counts2_str,
        "contrasts": {
            "LPS_vs_control": {"n_lps": len(lps_cols), "n_control": len(ctrl_cols), **deg2_lps},
            "HMGB1_vs_control": {"n_hmgb1": len(hmgb1_cols), "n_control": len(ctrl_cols), **deg2_hmgb1},
        },
    }

    out_path = Path("results/benchmarks/geo_benchmark_results.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(json.dumps(results, indent=2))
    print(f"Saved results to: {out_path.resolve()}")


if __name__ == "__main__":
    main()

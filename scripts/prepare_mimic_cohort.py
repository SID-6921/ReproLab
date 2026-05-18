"""Script to extract and flatten a cohort from raw MIMIC-IV CSVs for ReproLab testing.
Leaves all data 'dirty' (nulls, string-numbers, weird dates) to test ReproLab's validation.
"""

import os
from pathlib import Path

import pandas as pd

# --- CONFIGURATION ---
# Change this to the folder where you extracted the MIMIC-IV CSV files
MIMIC_DIR = Path("mimic/hosp")
OUTPUT_CSV = Path("data/mimic_cohort_raw.csv")

# Standard MIMIC-IV item IDs for Glucose and HbA1c
GLUCOSE_ITEMIDS = [50809, 50931]
HBA1C_ITEMIDS = [50868]
TARGET_ITEMIDS = set(GLUCOSE_ITEMIDS + HBA1C_ITEMIDS)


def main():
    if not MIMIC_DIR.exists():
        print(f"Error: Could not find MIMIC directory at {MIMIC_DIR}")
        return

    os.makedirs(OUTPUT_CSV.parent, exist_ok=True)

    print("1. Loading Admissions (event_date)...")
    admissions = pd.read_csv(
        MIMIC_DIR / "admissions.csv", usecols=["subject_id", "hadm_id", "admittime"]
    )

    print("2. Loading Primary Diagnoses (diagnosis_code)...")
    diagnoses = pd.read_csv(
        MIMIC_DIR / "diagnoses_icd.csv", usecols=["subject_id", "hadm_id", "seq_num", "icd_code"]
    )
    # Keep only the primary diagnosis for each admission to keep the table flat
    diagnoses = diagnoses[diagnoses["seq_num"] == 1].drop(columns=["seq_num"])

    print("3. Extracting target labs from labevents.csv (chunked to save RAM)...")
    lab_chunks = []
    chunk_size = 1_000_000

    # We grab 'value' instead of 'valuenum' so we capture dirty text data (e.g. ">600", "ERROR")
    lab_reader = pd.read_csv(
        MIMIC_DIR / "labevents.csv",
        usecols=["subject_id", "hadm_id", "itemid", "value"],
        chunksize=chunk_size,
    )

    for i, chunk in enumerate(lab_reader):
        # Filter down to just Glucose and HbA1c item IDs
        filtered = chunk[chunk["itemid"].isin(TARGET_ITEMIDS)]
        lab_chunks.append(filtered)
        if i % 10 == 0:
            print(f"   ...processed {i * chunk_size} lab event rows")

    labs_filtered = pd.concat(lab_chunks, ignore_index=True)

    print("4. Pivoting labs to columns...")
    # Map item IDs to our target column names
    labs_filtered["test_name"] = labs_filtered["itemid"].apply(
        lambda x: "glucose_mg_dl" if x in GLUCOSE_ITEMIDS else "hba1c_pct"
    )

    # If a patient had multiple glucose tests in one admission, take the first one
    # to flatten the dataset. Drop duplicates so pivot works cleanly.
    labs_filtered = labs_filtered.drop_duplicates(
        subset=["subject_id", "hadm_id", "test_name"], keep="first"
    )

    # Pivot so 'glucose_mg_dl' and 'hba1c_pct' become columns
    labs_pivoted = labs_filtered.pivot(
        index=["subject_id", "hadm_id"], columns="test_name", values="value"
    ).reset_index()

    print("5. Merging all tables into a single flat cohort...")
    # Base it off the admissions table
    cohort = admissions.merge(diagnoses, on=["subject_id", "hadm_id"], how="left")
    cohort = cohort.merge(labs_pivoted, on=["subject_id", "hadm_id"], how="left")

    print("6. Renaming columns for ReproLab...")
    cohort = cohort.rename(
        columns={
            "subject_id": "patient_id",
            "icd_code": "diagnosis_code",
            "admittime": "event_date",
        }
    )

    # Add a mock adverse_event column (since MIMIC doesn't explicitly flag this in a single column)
    # We'll just randomly assign YES/NO so the ReproLab pipeline has something to process
    import numpy as np

    rng = np.random.default_rng(42)
    cohort["adverse_event"] = rng.choice(["yes", "NO", "No", "YES", None], size=len(cohort))

    # Drop hadm_id as it's not needed by ReproLab
    cohort = cohort.drop(columns=["hadm_id"])

    print(f"7. Saving {len(cohort)} rows to {OUTPUT_CSV}...")
    cohort.to_csv(OUTPUT_CSV, index=False)

    print("\nData extraction complete! Preview:")
    print(cohort.head())


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Append new STAR mapping QC rows to an existing mapping QC table."""
import argparse
from pathlib import Path
import pandas as pd

ASSIGNED_COL = "proportion_of_reads_assigned_to_annotated_genes_percent"
BASE_COLS = ["sample", "total_reads", "mapped_reads", "mapping_rate", "uniquely_mapped_reads", "unique_mapping_rate"]


def die(msg):
    raise SystemExit(f"ERROR: {msg}")


def main():
    ap = argparse.ArgumentParser(description="Merge existing and new mapping QC TSV files. Existing rows are kept when sample IDs overlap.")
    ap.add_argument("--existing", required=True, type=Path, help="Existing mapping QC TSV. May contain assigned-gene proportion column.")
    ap.add_argument("--new", required=True, type=Path, help="New mapping QC TSV generated from STAR logs.")
    ap.add_argument("--out", required=True, type=Path, help="Output merged TSV without assigned-gene proportion column.")
    ap.add_argument("--report", required=True, type=Path, help="Text report path.")
    args = ap.parse_args()

    old = pd.read_csv(args.existing, sep="\t", dtype=str)
    new = pd.read_csv(args.new, sep="\t", dtype=str)
    for name, df in [("existing", old), ("new", new)]:
        missing = [c for c in BASE_COLS if c not in df.columns]
        if missing:
            die(f"{name} mapping QC is missing columns: {missing}")

    old_base = old[BASE_COLS].copy()
    new_base = new[BASE_COLS].copy()
    if old_base["sample"].duplicated().any():
        d = old_base.loc[old_base["sample"].duplicated(), "sample"].head(20).tolist()
        die("Existing mapping QC contains duplicated sample IDs: " + ", ".join(d))
    if new_base["sample"].duplicated().any():
        d = new_base.loc[new_base["sample"].duplicated(), "sample"].head(20).tolist()
        die("New mapping QC contains duplicated sample IDs: " + ", ".join(d))

    existing_samples = set(old_base["sample"].astype(str))
    append = new_base.loc[~new_base["sample"].astype(str).isin(existing_samples)].copy()
    skipped = new_base.loc[new_base["sample"].astype(str).isin(existing_samples), "sample"].tolist()
    out = pd.concat([old_base, append], ignore_index=True)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.out, sep="\t", index=False)
    report = (
        f"existing_samples\t{len(old_base)}\n"
        f"new_rows_input\t{len(new_base)}\n"
        f"new_rows_appended\t{len(append)}\n"
        f"new_rows_skipped_as_duplicates\t{len(skipped)}\n"
        f"final_samples\t{len(out)}\n"
        f"skipped_duplicate_samples\t{','.join(skipped[:100])}\n"
    )
    args.report.write_text(report, encoding="utf-8")
    print(report, end="")


if __name__ == "__main__":
    main()

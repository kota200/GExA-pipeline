#!/usr/bin/env python3
"""Validate that updated GExA count/TPM/mapping files are mutually consistent."""
import argparse
import csv
import json
import sys
from pathlib import Path
import pandas as pd

csv.field_size_limit(sys.maxsize)

REQUIRED_MAPPING_COLS = [
    "sample",
    "total_reads",
    "mapped_reads",
    "mapping_rate",
    "uniquely_mapped_reads",
    "unique_mapping_rate",
    "proportion_of_reads_assigned_to_annotated_genes_percent",
]


def die(msg):
    raise SystemExit(f"ERROR: {msg}")


def read_header(path: Path):
    with path.open("r", newline="", encoding="utf-8-sig", errors="replace") as f:
        reader = csv.reader(f)
        header = next(reader, None)
    if not header:
        die(f"CSV has no header: {path}")
    return header


def detect_sra_col(header):
    for c in ("SRA", "SRR"):
        if c in header:
            return c
    lower = {h.lower(): h for h in header}
    for c in ("sra", "srr"):
        if c in lower:
            return lower[c]
    die(f"Could not find SRA/SRR column. Header starts with: {header[:12]}")


def read_ids(path: Path):
    header = read_header(path)
    sra_col = detect_sra_col(header)
    ids = []
    with path.open("r", newline="", encoding="utf-8-sig", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            sid = (row.get(sra_col) or "").strip()
            if sid:
                ids.append(sid)
    return header, sra_col, ids


def main():
    ap = argparse.ArgumentParser(description="Validate updated GExA count/TPM matrices and mapping QC table.")
    ap.add_argument("--count", required=True, type=Path, help="Final count matrix CSV.")
    ap.add_argument("--tpm", required=True, type=Path, help="Final TPM matrix CSV.")
    ap.add_argument("--mapping-qc", required=True, type=Path, help="Final mapping QC TSV.")
    ap.add_argument("--metadata-cols", type=int, default=10, help="Number of left-side metadata columns. Default: 10.")
    ap.add_argument("--report", required=True, type=Path, help="Output JSON validation report.")
    args = ap.parse_args()

    count_header, count_col, count_ids = read_ids(args.count)
    tpm_header, tpm_col, tpm_ids = read_ids(args.tpm)
    if count_header[:args.metadata_cols] != tpm_header[:args.metadata_cols]:
        die("Count and TPM metadata-column headers differ")
    if count_header[args.metadata_cols:] != tpm_header[args.metadata_cols:]:
        die("Count and TPM gene-column headers differ")
    if count_ids != tpm_ids:
        die("Count and TPM sample orders differ")
    if len(count_ids) != len(set(count_ids)):
        die("Final matrix contains duplicated SRA/SRR IDs")

    mapping = pd.read_csv(args.mapping_qc, sep="\t", dtype=str)
    missing_cols = [c for c in REQUIRED_MAPPING_COLS if c not in mapping.columns]
    if missing_cols:
        die("Mapping QC is missing required columns: " + ", ".join(missing_cols))
    mapping_ids = mapping["sample"].astype(str).tolist()
    if mapping_ids != tpm_ids:
        die("Mapping QC sample order differs from final TPM/count matrices")
    pct = pd.to_numeric(mapping["proportion_of_reads_assigned_to_annotated_genes_percent"], errors="raise")
    if (pct > 100.000001).any():
        bad = mapping.loc[pct > 100.000001, "sample"].head(20).tolist()
        die("Assigned-gene proportion exceeds 100% for: " + ", ".join(bad))
    if (pct < -0.000001).any():
        bad = mapping.loc[pct < -0.000001, "sample"].head(20).tolist()
        die("Assigned-gene proportion is negative for: " + ", ".join(bad))

    report = {
        "status": "PASS",
        "samples": len(tpm_ids),
        "metadata_columns": args.metadata_cols,
        "gene_columns": len(tpm_header) - args.metadata_cols,
        "count_sra_column": count_col,
        "tpm_sra_column": tpm_col,
        "mapping_qc_columns": list(mapping.columns),
        "assigned_gene_percent_min": float(pct.min()) if len(pct) else None,
        "assigned_gene_percent_median": float(pct.median()) if len(pct) else None,
        "assigned_gene_percent_max": float(pct.max()) if len(pct) else None,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

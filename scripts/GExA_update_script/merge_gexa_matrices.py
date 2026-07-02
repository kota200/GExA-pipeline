#!/usr/bin/env python3
"""Safely append newly processed samples to an existing GExA count/TPM matrix."""
import argparse
import csv
import json
import sys
from pathlib import Path

csv.field_size_limit(sys.maxsize)


def die(msg: str) -> None:
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


def read_existing_ids(path: Path, sra_col: str):
    ids = []
    seen = set()
    dup = []
    with path.open("r", newline="", encoding="utf-8-sig", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            sid = (row.get(sra_col) or "").strip()
            if not sid:
                continue
            if sid in seen:
                dup.append(sid)
            seen.add(sid)
            ids.append(sid)
    return ids, seen, dup


def write_matrix(existing: Path, new: Path, out: Path, report: Path, matrix_type: str, metadata_cols: int, allow_new_genes: bool):
    fill = "0" if matrix_type == "count" else "0.0"
    existing_header = read_header(existing)
    new_header = read_header(new)
    if len(existing_header) <= metadata_cols:
        die(f"Existing matrix has <= metadata columns ({metadata_cols}); no gene columns: {existing}")
    if len(new_header) <= metadata_cols:
        die(f"New matrix has <= metadata columns ({metadata_cols}); no gene columns: {new}")

    existing_meta = existing_header[:metadata_cols]
    new_meta = new_header[:metadata_cols]
    if existing_meta != new_meta:
        die(
            "Metadata columns differ between existing and new matrices.\n"
            f"existing: {existing_meta}\nnew:      {new_meta}"
        )
    sra_col = detect_sra_col(existing_header)
    if sra_col not in new_header:
        die(f"New matrix does not contain accession column {sra_col}: {new}")

    existing_genes = existing_header[metadata_cols:]
    new_genes = new_header[metadata_cols:]
    existing_gene_set = set(existing_genes)
    new_gene_set = set(new_genes)
    missing_in_new = [g for g in existing_genes if g not in new_gene_set]
    extra_in_new = [g for g in new_genes if g not in existing_gene_set]

    if allow_new_genes:
        output_genes = existing_genes + [g for g in new_genes if g not in existing_gene_set]
    else:
        output_genes = existing_genes
    output_header = existing_meta + output_genes

    existing_ids, existing_seen, existing_dups = read_existing_ids(existing, sra_col)
    if existing_dups:
        die("Existing matrix contains duplicated accessions in SRA/SRR column: " + ", ".join(existing_dups[:20]))

    out.parent.mkdir(parents=True, exist_ok=True)
    skipped_new_dups = []
    appended = 0
    existing_written = 0

    with out.open("w", newline="", encoding="utf-8") as fout:
        writer = csv.DictWriter(fout, fieldnames=output_header, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()

        with existing.open("r", newline="", encoding="utf-8-sig", errors="replace") as fin:
            reader = csv.DictReader(fin)
            for row in reader:
                if allow_new_genes:
                    for g in output_genes:
                        if g not in row:
                            row[g] = fill
                writer.writerow({k: row.get(k, fill if k in output_genes else "NA") for k in output_header})
                existing_written += 1

        seen_all = set(existing_seen)
        with new.open("r", newline="", encoding="utf-8-sig", errors="replace") as fin:
            reader = csv.DictReader(fin)
            for row in reader:
                sid = (row.get(sra_col) or "").strip()
                if not sid:
                    continue
                if sid in seen_all:
                    skipped_new_dups.append(sid)
                    continue
                outrow = {}
                for c in existing_meta:
                    outrow[c] = row.get(c, "NA") or "NA"
                for g in output_genes:
                    outrow[g] = row.get(g, fill)
                    if outrow[g] in (None, ""):
                        outrow[g] = fill
                writer.writerow(outrow)
                seen_all.add(sid)
                appended += 1

    rep = {
        "matrix_type": matrix_type,
        "existing_file": str(existing),
        "new_file": str(new),
        "output_file": str(out),
        "metadata_columns": existing_meta,
        "gene_columns_existing": len(existing_genes),
        "gene_columns_new": len(new_genes),
        "genes_missing_in_new_filled_with_zero": len(missing_in_new),
        "genes_extra_in_new": len(extra_in_new),
        "extra_new_genes_policy": "appended" if allow_new_genes else "excluded",
        "existing_samples": existing_written,
        "new_samples_appended": appended,
        "new_samples_skipped_as_duplicates": len(skipped_new_dups),
        "new_duplicate_accessions": skipped_new_dups[:100],
        "final_samples": existing_written + appended,
        "missing_genes_preview": missing_in_new[:50],
        "extra_new_genes_preview": extra_in_new[:50],
    }
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(rep, indent=2), encoding="utf-8")
    print(json.dumps(rep, indent=2))


def main():
    ap = argparse.ArgumentParser(description="Append a new count/TPM matrix to an existing GExA matrix while preserving existing gene-column order.")
    ap.add_argument("--existing", required=True, type=Path, help="Existing full GExA matrix CSV.")
    ap.add_argument("--new", required=True, type=Path, help="New sample matrix CSV generated by mapping_script.sh.")
    ap.add_argument("--out", required=True, type=Path, help="Merged output CSV. Existing input is never overwritten.")
    ap.add_argument("--report", required=True, type=Path, help="JSON report path.")
    ap.add_argument("--matrix-type", required=True, choices=["count", "tpm"], help="Controls fill value for missing genes: count=0, tpm=0.0.")
    ap.add_argument("--metadata-cols", type=int, default=10, help="Number of left-side metadata columns. Default: 10.")
    ap.add_argument("--allow-new-genes", action="store_true", help="Append genes present only in the new matrix. Default: exclude them and warn in the report.")
    args = ap.parse_args()

    for p in [args.existing, args.new]:
        if not p.is_file():
            die(f"Input file not found: {p}")
    write_matrix(args.existing, args.new, args.out, args.report, args.matrix_type, args.metadata_cols, args.allow_new_genes)


if __name__ == "__main__":
    main()

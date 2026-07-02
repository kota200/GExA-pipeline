#!/usr/bin/env python3
"""Create a CSV whose accession column is named SRA, for legacy scripts that require SRA exactly."""
import argparse
import csv
import sys
from pathlib import Path

csv.field_size_limit(sys.maxsize)


def main():
    ap = argparse.ArgumentParser(description="Ensure a matrix CSV has an accession column named SRA. If the input already has SRA, the output is a byte-for-byte copy; if it has SRR, only the header is renamed to SRA.")
    ap.add_argument("--input", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    args = ap.parse_args()
    with args.input.open("r", newline="", encoding="utf-8-sig", errors="replace") as fin:
        reader = csv.reader(fin)
        header = next(reader, None)
        if not header:
            raise SystemExit(f"ERROR: CSV has no header: {args.input}")
        if "SRA" not in header:
            if "SRR" in header:
                header = ["SRA" if h == "SRR" else h for h in header]
            else:
                lower = {h.lower(): i for i, h in enumerate(header)}
                if "sra" in lower:
                    header[lower["sra"]] = "SRA"
                elif "srr" in lower:
                    header[lower["srr"]] = "SRA"
                else:
                    raise SystemExit("ERROR: input CSV must contain SRA or SRR column")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("w", newline="", encoding="utf-8") as fout:
            writer = csv.writer(fout, lineterminator="\n")
            writer.writerow(header)
            for row in reader:
                writer.writerow(row)
    print(f"Wrote: {args.output}")


if __name__ == "__main__":
    main()

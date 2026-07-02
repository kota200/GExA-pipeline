#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  blastp_annot.sh <target_species_proteins.fa> <output_prefix>

Environment overrides:
  DATA_DIR                 Directory containing Arab/rice BLAST DBs and annotation TSVs.
                           Default: ./data, or ../data relative to this script.
  PYTHON                   Python executable. Default: python3.
  BLAST_THREADS            blastp thread count. Default: 12.
  BLAST_MAX_TARGET_SEQS    max_target_seqs for blastp. Default: 5.
USAGE
}

if [[ ${1:-} == "-h" || ${1:-} == "--help" ]]; then
  usage
  exit 0
fi

input=${1:?Missing target species protein FASTA}
out=${2:?Missing output prefix}

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
PYTHON=${PYTHON:-python3}
THREADS=${BLAST_THREADS:-12}
MAX_TARGET_SEQS=${BLAST_MAX_TARGET_SEQS:-5}

if [[ -z "${DATA_DIR:-}" ]]; then
  if [[ -d data ]]; then
    DATA_DIR="data"
  elif [[ -d "$SCRIPT_DIR/../data" ]]; then
    DATA_DIR="$SCRIPT_DIR/../data"
  else
    DATA_DIR="data"
  fi
fi

require_file() {
  local path="$1"
  local label="$2"
  if [[ ! -f "$path" ]]; then
    echo "ERROR: $label not found: $path" >&2
    exit 1
  fi
}

extract_best_annotation() {
  local source="$1"
  local dest="$2"
  local mode="$3"

  awk -F'\t' -v OFS='\t' -v mode="$mode" '
    function trim(x) {
      gsub(/\r$/, "", x)
      gsub(/^[[:space:]]+|[[:space:]]+$/, "", x)
      return x
    }
    function missing(x) {
      x = trim(x)
      return x == "" || x == "NA" || x == "na" || x == "N/A"
    }
    {
      if (mode == "arabidopsis") {
        # BLAST has 13 columns. Arab appended columns:
        # 14=short name, 15=summary/description, 16=TAIR functional description,
        # 17=aliases, 18=GO.
        ann = $16
        if (missing(ann)) ann = $15
        if (missing(ann)) ann = $14
        if (missing(ann)) ann = $17
      } else {
        # BLAST has 13 columns. Rice appended columns from build_Os_annotation.py:
        # 14=RGAP functional annotation, 20=protein name, 23=Oryzabase explanation,
        # 15/17=symbol/name, 27=GO.
        ann = $14
        if (missing(ann)) ann = $20
        if (missing(ann)) ann = $23
        if (missing(ann)) ann = $15
        if (missing(ann)) ann = $17
        if (missing(ann)) ann = $27
      }
      if (missing(ann)) ann = "NA"
      print $1, trim(ann)
    }
  ' "$source" > "$dest"
}

require_file "$input" "target species protein FASTA"
require_file "$DATA_DIR/Arab_proteins.fasta" "Arabidopsis protein BLAST database FASTA"
require_file "$DATA_DIR/Os_proteins.fasta" "rice protein BLAST database FASTA"
require_file "$DATA_DIR/Arab_gene_annotation_list.tsv" "Arabidopsis annotation TSV"
require_file "$DATA_DIR/Os_gene_annotation_list.tsv" "rice annotation TSV"
require_file "$SCRIPT_DIR/blast_append_annotation.py" "blast_append_annotation.py"
require_file "$SCRIPT_DIR/merge_annot.sh" "merge_annot.sh"
require_file "$SCRIPT_DIR/drop_dot.sh" "drop_dot.sh"

at_blast="${out}_proteins_At_proteins_blastp_out.txt"
os_blast="${out}_proteins_Os_proteins_blastp_out.txt"
at_appended="${out}_At_proteins_blastp.txt"
os_appended="${out}_Os_proteins_blastp.txt"
at_annot="${out}_At_annot.txt"
os_annot="${out}_Os_annot.txt"
merged_tmp="${out}_annot.tmp"

blastp -db "$DATA_DIR/Arab_proteins.fasta" \
  -evalue 1e-20 \
  -outfmt "6 qseqid qlen qstart qend sseqid slen sstart send pident bitscore mismatch gapopen evalue" \
  -query "$input" \
  -num_threads "$THREADS" \
  -max_target_seqs "$MAX_TARGET_SEQS" \
  > "$at_blast"

blastp -db "$DATA_DIR/Os_proteins.fasta" \
  -evalue 1e-20 \
  -outfmt "6 qseqid qlen qstart qend sseqid slen sstart send pident bitscore mismatch gapopen evalue" \
  -query "$input" \
  -num_threads "$THREADS" \
  -max_target_seqs "$MAX_TARGET_SEQS" \
  > "$os_blast"

"$PYTHON" "$SCRIPT_DIR/blast_append_annotation.py" \
  --blast "$at_blast" \
  --anno "$DATA_DIR/Arab_gene_annotation_list.tsv" \
  --out "$at_appended"

"$PYTHON" "$SCRIPT_DIR/blast_append_annotation.py" \
  --blast "$os_blast" \
  --anno "$DATA_DIR/Os_gene_annotation_list.tsv" \
  --out "$os_appended"

extract_best_annotation "$at_appended" "$at_annot" "arabidopsis"
extract_best_annotation "$os_appended" "$os_annot" "rice"

"$SCRIPT_DIR/merge_annot.sh" --arab "$at_annot" --rice "$os_annot" --output "$merged_tmp"
"$SCRIPT_DIR/drop_dot.sh" "$merged_tmp" "${out}_annot.txt"

rm -f "$merged_tmp" "$at_blast" "$os_blast" "$at_appended" "$os_appended" "$at_annot" "$os_annot"

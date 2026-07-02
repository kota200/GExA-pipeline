# Automated GExA updates

Use `scripts/GExA_update_script/update_gexa.sh` to refresh an existing GExA database without remapping samples that are already present.

## What the updater does

1. Searches NCBI SRA with `API_RNA-seq.py`.
2. Compares the returned accessions with the existing count matrix, TPM matrix, and mapping-QC table.
3. Maps only new samples with `mapping_script.sh`.
4. Merges new count/TPM rows into the existing matrices.
5. Builds and merges STAR mapping QC.
6. Adds the proportion of reads assigned to annotated genes.
7. Runs `check_sample.sh` and the selected species-specific metadata standardizer.
8. Validates final count/TPM/mapping-QC consistency.
9. Regenerates static shard files for the web UI.

Original input files are not overwritten in place. Refreshed files are written under `--outdir`, and logs/reports are written under `--workdir` and `--outdir/reports`.

## Required inputs

- `--species`: one or more SRA search names
- `--prefix`: existing GExA prefix such as `PM_Tift`
- `--count`: existing count matrix CSV
- `--tpm`: existing TPM matrix CSV
- `--mapping-qc`: existing STAR mapping QC TSV
- `--star-index`: STAR genome index
- `--gff`: GFF3 annotation used by featureCounts
- `--workdir`: update working directory
- `--outdir`: final update output directory
- `--standardize-script`: metadata standardization script in `scripts/`

## Recommended workflow

Run a dry run first:

```bash
bash scripts/GExA_update_script/update_gexa.sh \
  --species "pearl millet" "Cenchrus americanus" "Pennisetum glaucum" \
  --prefix PM_Tift \
  --count Pearl_millet_count_data_cv_Tift.csv \
  --tpm Pearl_millet_TPM_data_cv_Tift.csv \
  --mapping-qc PM_Tift_STAR_mapping_w_assigned.tsv \
  --star-index /path/to/STAR_index \
  --gff /path/to/annotation.gff3 \
  --workdir gexa_update_work \
  --outdir gexa_update_result \
  --standardize-script standardize_metadata_pearl_millet.py \
  --dry-run
```

If the new-sample count looks correct, run without `--dry-run`:

```bash
bash scripts/GExA_update_script/update_gexa.sh \
  --species "pearl millet" "Cenchrus americanus" "Pennisetum glaucum" \
  --prefix PM_Tift \
  --count Pearl_millet_count_data_cv_Tift.csv \
  --tpm Pearl_millet_TPM_data_cv_Tift.csv \
  --mapping-qc PM_Tift_STAR_mapping_w_assigned.tsv \
  --star-index /path/to/STAR_index \
  --gff /path/to/annotation.gff3 \
  --workdir gexa_update_work \
  --outdir gexa_update_result \
  --standardize-script standardize_metadata_pearl_millet.py
```

## Species-specific standardizers

The repository includes:

- `standardize_metadata_barley.py`
- `standardize_metadata_finger_millet.py`
- `standardize_metadata_foxtail_millet.py`
- `standardize_metadata_pearl_millet.py`
- `standardize_metadata_proso_millet.py`
- `standardize_metadata_rice.py`
- `standardize_metadata_sorghum.py`

Use the standardizer that matches the database being updated. For a new species, copy the closest script and adapt the metadata replacement rules.

## Publishing updated files

After a successful update, publish:

- final matrices: `gexa_update_result/*standardized.csv`
- final mapping QC: `gexa_update_result/*mapping*.tsv`
- static web files: `gexa_update_result/out_sharded/`

For an existing web page, usually replace only:

- `meta.tsv`
- `gene_index.tsv`
- `manifest.json`
- `shards/`

Keep the existing HTML and `<prefix>_annot.txt` unless the title/reference labels changed or the gene set changed.

## Annotation note

Arabidopsis and rice annotation scripts remain part of the main pipeline:

- `scripts/blastp_annot.sh`
- `scripts/blast_append_annotation.py`
- `scripts/merge_annot.sh`
- `scripts/build_os_data.sh`
- `scripts/build_Os_annotation.py`

The automated updater keeps the existing gene order by default, so annotation files usually do not need to change. If you use `--allow-new-genes`, rerun `blastp_annot.sh` so annotation search stays complete.

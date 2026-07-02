# GExA pipeline for constructing and updating RNA sequencing (RNA-seq) databases

## What this pipeline does

This pipeline turns public RNA-seq SRA runs into an interactive web database:

1. Search SRA by organism name(s)
2. Download FASTQ and map reads (STAR)
3. Count reads per gene (featureCounts) and compute TPM
4. Clean metadata spellings and filter obvious low-quality samples
5. Add gene annotations via BLASTP (Arabidopsis + rice)
6. Generate an HTML front-end from a template
7. Shard the large TPM matrix for fast web loading

It also includes an automated update workflow for existing GExA databases. The update workflow detects new SRA runs, maps only the new samples, merges them into the current matrices, refreshes QC, validates the result, and regenerates static shard files for the web page.

## Typical use cases

- Create a web portal for a species/cultivar.
- Rebuild or refresh the database periodically with new SRA runs.
- Generate standardized matrices for downstream analysis.
- Keep a deployed GExA site current without remapping all existing samples.

## Minimum required inputs

- `--species`: organism/scientific names used for NCBI SRA query
- `--star-index`: STAR genomeDir (pre-built)
- `--gff`: GFF3 annotation (gene features must have `ID=`)
- `--proteins`: protein FASTA (headers must match gene IDs)

## Quick start: build a new database

```bash
./run_pipeline.sh \
  --species "Setaria italica" \
  --species "foxtail millet" \
  --prefix SI_Yugu1 \
  --star-index /path/to/star_index \
  --gff /path/to/genes.gff3 \
  --proteins /path/to/target_species_proteins.fa \
  --title-prefix "Foxtail Millet" \
  --ref-label "Yugu1" \
  --outdir out/SI_Yugu1
```

After completion, upload:

- `out/SI_Yugu1/site/`

to your web server (static hosting is enough).

## Quick start: update an existing GExA database

Always start with `--dry-run` to confirm which SRA accessions will be added:

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

Run the same command without `--dry-run` to map new samples and create refreshed outputs. The updater writes new files to `--outdir`; it does not overwrite the original count, TPM, or mapping-QC inputs in place.

## Outputs

### New-build `results/`

- `<prefix>_TPM_matrix.csv` - raw TPM matrix (sample x gene)
- `<prefix>_TPM_matrix.cleaned.csv` - metadata standardized
- `<prefix>_TPM_matrix.cleaned.filtered.csv` - low-quality samples removed
- `<prefix>_count_matrix.csv` - count matrix
- `<prefix>_metadata.tsv` - metadata log (from BioSample/SRA)

### New-build `site/`

- `<prefix>.html` - interactive UI
- `<prefix>_annot.txt` - gene annotations for UI
- `meta.tsv`, `gene_index.tsv`, `manifest.json`, `shards/` - sharded matrix files

### Update `outdir/`

- `*.updated.csv` - merged count/TPM matrices before final standardization
- `*.standardized.csv` - final standardized count/TPM matrices
- `*mapping*.tsv` - refreshed mapping QC
- `out_sharded/` - refreshed static files for the deployed site
- `reports/` - merge, filtering, and validation reports

## Common pitfalls

### 1) GFF3 `ID=` mismatch

`featureCounts` is run with `-t gene -g ID`. Your GFF3 gene features must look like:

```text
chr1  ...  gene  ...  ID=GENE12345;...
```

If your gene IDs are stored under a different key (e.g. `gene_id`), edit `mapping_script.sh` accordingly.

### 2) BLAST resources missing

`blastp_annot.sh` expects `./data/Arab_proteins.fasta`, `./data/Os_proteins.fasta`, and annotation TSVs. Create protein BLAST DBs with `makeblastdb`, or use `scripts/build_os_data.sh` to build the rice RGAP7/Oryzabase resources.

### 3) Download/mapping failures

Some SRR runs may fail to download or map. `mapping_script.sh` records failures to `Download_failed_list.txt`, and the automated updater also writes `failed_samples.tsv` under the update work directory.

### 4) Gene set changes during an update

The updater keeps the existing gene list/order by default. If you explicitly use `--allow-new-genes`, rerun `blastp_annot.sh` afterward so Arabidopsis/rice annotation search in the HTML remains complete.

## Recommended publication practice

- Keep your metadata normalization rules as a TSV mapping file and version-control it.
- Record software versions and reference genome/annotation versions.
- Avoid committing large reference files unless licenses allow it.
- Use the automated updater's `--dry-run` before scheduled or periodic GExA refreshes.

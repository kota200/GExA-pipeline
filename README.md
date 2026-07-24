# Building GExA-style plant expression atlases from public RNA-seq datasets

This repository contains a reproducible pipeline that:

1. searches NCBI SRA for RNA-seq/transcriptome runs,
2. downloads FASTQs, maps reads with STAR, counts with featureCounts,
3. builds TPM/count matrices,
4. standardizes metadata and filters obviously bad samples,
5. annotates genes via BLASTP against Arabidopsis and rice,
6. generates an interactive HTML page from a template,
7. preprocesses a large matrix into sharded binary files for fast web loading, and
8. updates an existing GExA database automatically when new public SRA runs become available.

## What you need

### Required inputs

- **Organism name(s)** for NCBI SRA search (repeatable `--species`).
- **STAR genome index** (built in advance, `--star-index`).
- **GFF3 annotation** (`--gff`) where gene features have `ID=...` (used by featureCounts `-g ID`).
- **Target species protein FASTA** (`--proteins`) whose headers match the gene IDs you want to annotate.
- **HTML template** (`scripts/Template.html`) and parameters to customize it.

### Software dependencies

The mapping step downloads and processes RNA-seq data, so you need common bioinformatics tools:

- `aria2c`, `wget`
- `fasterq-dump` (SRA-Toolkit)
- `fastp`
- `STAR`
- `samtools`
- `featureCounts` (Subread)
- `blastp` (BLAST+)

Python 3 + modules:

- `pandas`
- `bs4` (BeautifulSoup)

> Tip: consider using conda/mamba and recording exact versions for reproducibility.

## Execution environment (assumptions)

### Supported platforms

- **Linux (x86_64)** is required.
- **WSL2 (Ubuntu/Debian on Windows)** should work (treated as Linux), but Windows-native execution is **not supported**.
- macOS is not officially supported/tested.

### Shell / filesystem assumptions

- `bash` (recommended: bash 4+)
- Standard GNU userland tools: `grep`, `sed`, `awk`, `cut`, `sort`, `paste`, `gzip`, etc.
- A large, writable working directory is required (SRA FASTQs can be very large).
  - **WSL note**: for performance, prefer working under the Linux filesystem (e.g. `/home/...`) rather than `/mnt/c/...`.

### Additional external tools used by scripts

In addition to the tools listed above, some scripts may call:

- SRA Toolkit: `prefetch`, `fasterq-dump`
- NCBI Entrez Direct (recommended): `efetch`, `xtract`
- Decompression helper (optional): `pbzip2` (otherwise `bzip2`)

### Resource requirements (rule of thumb)

- **Disk**: can exceed **tens to hundreds of GB** depending on the number of samples.
- **RAM**: mainly depends on STAR index size (small plant genomes may fit in 8-16 GB; large genomes can require more).
- **CPU**: STAR/featureCounts/fasterq-dump can use multiple threads (some thread counts are currently fixed in scripts).

### Network / rate limits

- Requires outbound HTTPS access to NCBI/SRA and (optionally) DDBJ endpoints.
- Heavy use of NCBI e-utils may be throttled; for quick tests, consider `--max-samples` or the updater's `--dry-run`.

### Viewing the generated website (IMPORTANT)

The generated `out/<prefix>/site/` directory is a **static website** that loads `manifest.json`, `meta.tsv`,
`gene_index.tsv`, and `shards/*` via browser requests. For local testing, open it via **HTTP** (not `file://`).

```bash
cd out/<prefix>/site
python3 -m http.server 8000
# open: http://127.0.0.1:8000/<prefix>.html
```

## Repository layout

```text
.
├── run_pipeline.sh                    # main entrypoint for a new atlas
├── scripts/                           # core scripts
│   ├── GExA_update_script/            # automated updater for existing GExA atlases
│   ├── build_os_data.sh               # rice RGAP7/Oryzabase download + BLAST DB builder
│   ├── build_Os_annotation.py         # rice annotation table builder
│   ├── blastp_annot.sh                # Arabidopsis/rice BLASTP annotation
│   └── standardize_metadata_*.py      # species-specific metadata cleanup scripts
├── data/                              # Arabidopsis annotation resources
└── docs/wiki/                         # GitHub Wiki / Help draft pages
```

## Quick start

1) Build STAR index (example):

If possible, prepare a GTF-format annotation file and use it when generating the STAR index.

```bash
STAR --runThreadN 24 \
  --runMode genomeGenerate \
  --genomeDir /path/to/star_index \
  --genomeFastaFiles genome.fa \
  --sjdbGTFfile genes.gtf
```

2) Prepare BLAST databases for Arabidopsis/rice.

- Arabidopsis datasets: TAIR10
  Data were obtained from TAIR (Phoenix Bioinformatics) Public_Data_Releases and are licensed under CC BY 4.0.
  We have reformatted files for this pipeline.
  Source: TAIR Public_Data_Releases (download date: 2024-10-01) (Berardini et al., 2015, https://doi.org/10.1002/dvg.22877).
  Source URL: https://www.arabidopsis.org/download_files/Genes/TAIR10_genome_release/
  License: CC BY 4.0.
- Rice datasets: RGAP 7, from the Rice Genome Annotation Project (RGAP, Kawahara et al., 2013; https://doi.org/10.1186/1939-8433-6-4)
  and Oryzabase (Kurata and Yamazaki, 2006; https://doi.org/10.1104/pp.105.063008).
  Source URLs:
  - RGAP7 download page: https://rice.uga.edu/download_osa1r7.shtml
  - RGAP7 all-model proteins: https://rice.uga.edu/osa1r7_download/osa1_r7.all_models.pep.fa.gz
  - RGAP7 functional annotation: https://rice.uga.edu/osa1r7_download/osa1_r7.all_models.functional_annotation.txt.gz
  - RGAP7 GOSlim annotation: https://rice.uga.edu/osa1r7_download/osa1_r7.all_models.GOSlim.txt.gz
  - Oryzabase English gene list: https://shigen.nig.ac.jp/rice/oryzabase/gene/download?classtag=GENE_EN_LIST

For the rice datasets, download/build the protein BLAST DBs and annotation files with:

```bash
# Recommended: build rice (RGAP7 + Oryzabase) reference files automatically.
# This will download the required files and create:
#   - data/Os_proteins.fasta (+ BLAST DB files)
#   - data/Os_gene_annotation_list.tsv
bash scripts/build_os_data.sh --data-dir data --threads 8
```

`blastp_annot.sh` expects the following files under `./data/` (repository root):

- `data/Arab_proteins.fasta` and its BLAST DB files (`.pin/.psq/.phr` etc)
- `data/Os_proteins.fasta` and its BLAST DB files
- `data/Arab_gene_annotation_list.tsv`
- `data/Os_gene_annotation_list.tsv`

### Example of use

```bash
./run_pipeline.sh \
  --species "Cenchrus americanus" \
  --species "Pearl millet" \
  --prefix PM_Tift \
  --star-index /path/to/star_index \
  --gff /path/to/genes.gff3 \
  --proteins /path/to/target_species_proteins.fa \
  --title-prefix "Pearl Millet" \
  --ref-label "Tift" \
  --outdir out/PM_Tift
```

Outputs:

- `out/PM_Tift/results/` - CSV matrices + metadata TSV
- `out/PM_Tift/site/` - **upload this directory to your web server**
  - `PM_Tift.html`
  - `PM_Tift_annot.txt`
  - `meta.tsv`, `gene_index.tsv`, `manifest.json`, `shards/`

## Automated updates for existing GExA databases

Use `scripts/GExA_update_script/update_gexa.sh` when a GExA database already has count/TPM matrices and mapping-QC files. The updater searches SRA again, detects only new accessions, maps those new samples, merges them into the existing matrices, refreshes mapping QC, applies metadata standardization, validates consistency, and regenerates shard files for the web database.

The updater writes new files to `--outdir` and backs up the original input files under the update work/output folders. It does not overwrite the original count, TPM, or mapping-QC files in place.

Start with a dry run:

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

Then run without `--dry-run` to perform mapping and merge:

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

Species-specific metadata standardizers currently included:

- `standardize_metadata_barley.py`
- `standardize_metadata_finger_millet.py`
- `standardize_metadata_foxtail_millet.py`
- `standardize_metadata_pearl_millet.py`
- `standardize_metadata_proso_millet.py`
- `standardize_metadata_rice.py`
- `standardize_metadata_sorghum.py`

After a successful update, publish the refreshed database files from:

- `gexa_update_result/*standardized.csv` for final matrices
- `gexa_update_result/*mapping*.tsv` for mapping QC
- `gexa_update_result/out_sharded/` for static web files

If you use `--allow-new-genes` and new gene columns are added, rerun the Arabidopsis/rice annotation workflow (`blastp_annot.sh`) so the HTML annotation search remains complete.

## Customizing metadata normalization

To fix spelling/formatting variation, you can pass mapping rules to `standardize_metadata.py`:

- TSV mapping file (repeatable): `--map-tsv replacements.tsv`

```tsv
# column	from	to
tissue	Leaves	Leaf
tissue	ROOTS	Root
treatment	25.0 degrees	25 deg C
treatment	42 Degree	42 deg C
```

- Inline rules (repeatable): `--replace 'tissue:Leaves=leaf'`

## Partial runs / resume

- Start from a later step:

```bash
./run_pipeline.sh ... --from clean
```

- Stop early:

```bash
./run_pipeline.sh ... --to html
```

- Use your own SRR list (skip NCBI search):

```bash
./run_pipeline.sh ... --srr-list path/to/tmp_list
```

- Test with only first N samples:

```bash
./run_pipeline.sh ... --max-samples 20
```

## Notes / caveats

- **Large downloads:** SRA datasets can be huge. Always check disk quota.
- **NCBI rate limits:** heavy use of eutils may be throttled.
- The mapping and BLAST scripts currently use fixed thread counts internally.
  If you want to tune performance, edit:
  - `scripts/mapping_script.sh` (STAR/featureCounts/fasterq-dump)
  - `scripts/blastp_annot.sh` (blastp)
- The automated updater refreshes expression matrices and static shard files. Arabidopsis/rice gene annotations are preserved and should be regenerated only when the gene set changes.

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.

# How to publish or refresh the web database

## 1) Build the site folder for a new database

Run the full pipeline. The final site folder is:

- `out/<prefix>/site/`

It contains:

- `<prefix>.html`
- `<prefix>_annot.txt`
- `meta.tsv`, `gene_index.tsv`, `manifest.json`
- `shards/` (binary shard files)

## 2) Or refresh an existing database automatically

For an existing GExA database, run the automated updater:

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

The updater writes refreshed static files to:

- `gexa_update_result/out_sharded/`

Use those files to replace the deployed `meta.tsv`, `gene_index.tsv`, `manifest.json`, and `shards/`. Keep the existing HTML and annotation file unless the title, reference label, or gene set changed.

## 3) Upload to your server

Upload the entire new-build `site/` directory, or replace the refreshed files from `out_sharded/`, to a static hosting location.

Examples:

- GitHub Pages (for small/medium datasets)
- Nginx/Apache static directory
- Any object storage with static hosting

## 4) Confirm in a browser

Open:

- `<prefix>.html`

If you see network errors, confirm that the relative files exist next to the HTML:

- `meta.tsv`
- `gene_index.tsv`
- `manifest.json`
- `shards/`
- `<prefix>_annot.txt`

## 5) Optional: custom domain + caching

Large shard downloads benefit from caching.

- Enable gzip/brotli for `meta.tsv`, `gene_index.tsv`, `manifest.json`
- Configure long cache headers for `shards/*.bin`
- After an automated update, purge CDN/browser cache for `manifest.json` so users load the refreshed shard manifest.

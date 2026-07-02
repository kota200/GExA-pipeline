# GExA automated update scripts

`update_gexa.sh` refreshes an existing GExA database by adding only new public SRA runs.

From the repository root, start with:

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

Remove `--dry-run` after confirming the new sample list. The wrapper automatically uses the parent `scripts/` directory for core pipeline scripts when it is run from this location.

Main outputs:

- `*.updated.csv`: merged count/TPM matrices before final standardization
- `*.standardized.csv`: final standardized count/TPM matrices
- `*mapping*.tsv`: refreshed mapping QC
- `out_sharded/`: refreshed static files for the web UI
- `reports/`: merge, filter, and validation reports

Arabidopsis/rice annotation scripts stay in the main `scripts/` directory. Rerun `blastp_annot.sh` only when the gene set changes, such as when using `--allow-new-genes`.

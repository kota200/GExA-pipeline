#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path

import pandas as pd


def read_lib_type(path: str) -> pd.DataFrame:
    lib = pd.read_csv(path, sep='\t', header=None, names=['sample', 'library_type'], dtype=str)
    lib['sample'] = lib['sample'].str.strip()
    lib['library_type'] = lib['library_type'].str.strip().str.upper()
    lib = lib.dropna(subset=['sample', 'library_type'])

    # OS_lib_type.txt can contain duplicated SRA IDs. Allow duplicates only if the type is identical.
    conflicts = lib.groupby('sample')['library_type'].nunique()
    conflicts = conflicts[conflicts > 1]
    if not conflicts.empty:
        raise ValueError(
            'Conflicting library types found for: ' + ', '.join(conflicts.index[:20])
        )
    return lib.drop_duplicates('sample')


def main() -> None:
    ap = argparse.ArgumentParser(
        description=(
            'Add the percent/proportion of reads assigned to annotated genes to a STAR mapping TSV. '
            'For PAIRED libraries, the summed featureCounts counts are divided by 2 because this '
            'pipeline used featureCounts -p without --countReadPairs, while STAR Log.final.out '
            'counts a paired-end fragment/read pair as one input read.'
        )
    )
    ap.add_argument('--counts', required=True, help='count_matrix.csv: rows=samples, columns=metadata + genes')
    ap.add_argument('--mapping', required=True, help='rice_STAR_mapping.tsv from STAR Log.final.out summary')
    ap.add_argument('--lib-type', required=True, help='OS_lib_type.txt: column 1=SRA ID, column 2=SINGLE/PAIRED')
    ap.add_argument('--out', required=True, help='output TSV path')
    ap.add_argument('--metadata-cols', type=int, default=10,
                    help='Number of non-gene metadata columns at the left side of count matrix. Default: 10')
    ap.add_argument('--digits', type=int, default=2, help='Decimal digits for the percent column. Default: 2')
    args = ap.parse_args()

    counts = pd.read_csv(args.counts, low_memory=False)
    mapping = pd.read_csv(args.mapping, sep='\t')
    lib = read_lib_type(args.lib_type)

    if 'SRA' not in counts.columns:
        raise ValueError('count matrix must contain an SRA column')
    if 'sample' not in mapping.columns or 'total_reads' not in mapping.columns:
        raise ValueError('mapping TSV must contain sample and total_reads columns')
    if counts.shape[1] <= args.metadata_cols:
        raise ValueError('metadata-cols is too large; no gene count columns remain')

    gene_cols = list(counts.columns[args.metadata_cols:])
    # Convert gene columns to numeric. Non-numeric entries become 0 only if they are empty/NA.
    gene_counts = counts[gene_cols].apply(pd.to_numeric, errors='coerce')
    bad = gene_counts.isna().sum().sum()
    if bad:
        raise ValueError(f'Non-numeric values detected in gene count columns: {bad} cells')

    assigned = pd.DataFrame({
        'sample': counts['SRA'].astype(str),
        'assigned_to_annotated_genes_raw_count_sum': gene_counts.sum(axis=1),
    })

    out = mapping.merge(assigned, on='sample', how='left', validate='one_to_one')
    out = out.merge(lib, on='sample', how='left', validate='many_to_one')

    missing_counts = out.loc[out['assigned_to_annotated_genes_raw_count_sum'].isna(), 'sample'].tolist()
    missing_lib = out.loc[out['library_type'].isna(), 'sample'].tolist()
    if missing_counts:
        raise ValueError('Samples missing from count matrix: ' + ', '.join(missing_counts[:20]))
    if missing_lib:
        raise ValueError('Samples missing from lib-type file: ' + ', '.join(missing_lib[:20]))

    total_reads = pd.to_numeric(out['total_reads'], errors='raise')
    lib_type = out['library_type'].str.upper()
    # For SINGLE: count sum / total_reads. For PAIRED: count sum / (2 * total_reads).
    denominator = total_reads.where(lib_type != 'PAIRED', total_reads * 2)
    pct = out['assigned_to_annotated_genes_raw_count_sum'] / denominator * 100

    if (pct > 100.000001).any():
        bad_rows = out.loc[pct > 100.000001, ['sample', 'total_reads', 'assigned_to_annotated_genes_raw_count_sum', 'library_type']]
        raise ValueError(
            'Calculated proportions exceeded 100%. Check whether paired-end counts are read-level or fragment-level.\n'
            + bad_rows.head(20).to_string(index=False)
        )

    out['proportion_of_reads_assigned_to_annotated_genes_percent'] = pct.round(args.digits)

    # User requested only one added rightmost column, so do not keep internal helper columns.
    original_cols = list(mapping.columns)
    final_cols = original_cols + ['proportion_of_reads_assigned_to_annotated_genes_percent']
    out[final_cols].to_csv(args.out, sep='\t', index=False)

    print(f'Wrote: {args.out}', file=sys.stderr)
    print(f'Samples: {len(out)}', file=sys.stderr)
    print(f'Gene columns summed: {len(gene_cols)}', file=sys.stderr)
    print(f'Min/median/max assigned percent: {pct.min():.2f} / {pct.median():.2f} / {pct.max():.2f}', file=sys.stderr)


if __name__ == '__main__':
    main()

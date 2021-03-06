README-SnakeQUANT
================

## Overview

SnakeQUANT is a quantification pipeline to generate scRNA-seq gene
expression data for scEiaD. This is run previous to `SnakePOP` and `SnakeSCEIAD`. SnakeQUANT does the following:

  - Builds kallisto quantification indices for human, mouse, and macaque
    originating data
  - Generates both exonic and intronic gene quantification for
    RNA-velocity calculations. This is only run for 10x Droplet-based
    scRNA-seq
  - Generates transcript level quantification for well based scRNA-seq
  - For macaque data, quantifies data gainst both macaque and human
    indices and picks best(highest) expresion values for the two
  - Generate statistics like % mitochondiral gene expression for QC
  - The `pipeline_data/clean_quant/all_species_full_sparse_matrix.Rdata` removes cells which have > 10% mito gene expression (relative to full transcriptome quant)

## Output
```
pipeline_data/clean_quant/all_species_full_sparse_matrix.Rdata
pipeline_data/clean_quant/all_species_full_sparse_unspliced_matrix.Rdata
pipeline_data/cell_info/all_cell_info.tsv
pipeline_data/clean_quant/mito_counts.tsv
```



## Setup

SnakeQUANT requires a tab-separated sample metadata that contains the
following columns:

  - sample\_accession: an ID for each individual sample in scEiaD
  - run\_accession: names of the 1 or more fastq.gz files that make up a
    sample
  - library\_layout: PAIRED / SINGLE
  - organism: species
  - Platform: Sequencing technology(10x, SmartSEQ etc)
  - UMI: YES / NO

Example sample metadata files are in the `data/` folder

Before the pipeline is run, make sure the relevant paths in
`config.yaml` are changed:

  - `fastq_path`: absolute path to directory with run-level fastqs
  - `quant_path`: absolute path to where *sample-level* quantification
    files are stored

# Pipeline step

## Reference file generation

  - rule `make_sample_name_prefixes`: makes .txt file with all distinct
    prefixes used to grep for samples later on in the pipeline. Prefixes
    are the beginning character letters(no numbers) for a sample name ie
    SRS, E-MTAB.(`references/samplename_patterns.txt`)
  - rule `download_annotation`: get GTF based transcript annotation for
    each species from differnet sources. Links are hardcoding in ATM.
    files are stored in `reference/gtf`
  - rule `make_mitochondiral_gene_lists`: makes a list of mitchondrial
    genes for each species. files are stored in `references/mito_genes/`

## Generation of quantification indices

rule `get_velocity_files` does quite a bit, all within the script
`src/get_velocity_annotation.R` For Each species, 4 quantificaiton
indices are made for differnet technologies: 10xv2, 10xv3, DropSeq and
well(1 for all well techs). The reason separate indices are needed for
the droplet tech is that generation of intron transcript sequnences is
highly dependent on the read length which varies by technologies. For
well based samples, initally both exonic and intronic transcript
sequences are generated, but a python script
`src/remove_entry_from_fasta.py` is called within the Rscript to remove
intronic sequences to reduce index size.

## Quantification

Sample level quantification is written to the location specified by
`quant_path` in `config.yaml`( currently
`/data/OGVFB_BG/new_quant_sciad`). The sample level quant output is
structured like this
`{quant_path}/quant/{sample_accession}/{technology}/{reference}`. Only
macaque samples have multiple values for reference(human, macaque).

rule `kallisto_quant` handles well based quant and geneated transcript
level gene expression

### Droplet based quantification

All quant is handled by `bustool`. A local installation of bustools is
required. path to bustools binary must specfied as `bustools_path` in
`config.yaml`. Quantification happens in the rule
`bustools_whitelist_correct_count`. For 10x data, barcode whitelists
were manually downloaded from
<https://github.com/BUStools/getting_started/releases> . For DropSeq
techonology a single whitelist is created by running `bustools
whitelist` on all DropSeq samples and then merged to a single file (rule
`make_dropseq_whitelists`). Couple notes about rule
`bustools_whitelist_correct_count` - in the `bustools capture` step, it
looks like the target transcript ids for spliced and unspliced are
backwards, but they are not. - Previoulsy we were also running `bustools
correct`. I had to drop this because it can create duplicate barcodes
within the same sample, which really messes up the intronic quant.

## Processing of Quant output

### rule `create_sparse_matrix`

This rule creates a study level sparse matrix for droplet based
technologies, and pulls in quant files generated by
`bustools_whitelist_correct_count` stored in `{quant_path}/...` These
are written to `pipeline_data/clean_quant/{study_accession}`. This rule
performs several QC steps: - remove cells with less than 200 read -
remove cells with more than 3000 reads - remove cells with %
mitochondrial gene expression \> 10% (this requires the mitochondrial
gene lists generated earlier) The rule outputs both exonic and intronic
quant, as well as a `stats.tsv` file. `stats.tsv` records how many cells
are lost from QC.

### rule `merge_nonUMI_quant_by_organism`

Takes sample level well-based quant and outputs organism level gene and
transcript quantifcation. These are stored in
`{quant_path}/quant/{organism}`

## Species level merging of Droplet and Well data(rule `combine_well_and_umi`)

  - Merges droplet and well quant to the species level for both exonic
    and intronic quant and writes to
    `pipeline_data/clean_quant/{organism}`
  - creates study-barcode id for each cell
  - outputs a `cell_info` file to `pipeline_data/cell_info/` that maps
    id to metadata.

## Merging all quant together

Handled by `src/blend_macaque_merge_across_reference.R`. Outputs clean,
species level quant to `pipeline_data/clean_quant/{species}` and single
pan-species quant to `pipeline_data/clean_quant`.(two files, for exonic
and intronic quant.)

### Macaque blending

Macaque data quantified against human and macaque references are
compared; for each gene where the human quant is both greater than the
macaque quant, the human quant is added to the final macaque quant. Only
human genes with expression about the 20th percentile of macaque gene
expression(~ 9 reads) can be conisdered for this.

### Mito stats

The script `src/mito_stats.R` generates information about sample-level %
mitochondrial gene expression; for droplet, it reads in existing
`stats.tsv` files from `create_sparse_matrix`. For well data, each
sample is read in(this takes time and memory), and % mitochonrial
expression is calculated

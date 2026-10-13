# Ornaments

Ornaments extends kallisto with variant-aware pseudoalignment of RNA-seq reads
and allele-specific expression estimates at heterozygous loci. It provides
commands for converting genomic variants, preparing a personalized
transcriptome, building an index, and quantifying expression.

The method is described in [Adduri and Kim, *Ornaments for efficient
allele-specific expression estimation with bias correction*, AJHG (2024)](https://www.sciencedirect.com/science/article/pii/S0002929724002210).

## Install with Pixi

Use Pixi 0.80.0 or newer. From a local copy of this repository:

```bash
pixi install
pixi run ornaments --help
```

Pixi installs the Python package and compiles its bundled native engine. All
build dependencies come from conda-forge/bioconda or PyPI; HTSlib is included in
the repository. The manifest targets Linux x86-64 and macOS x86-64/ARM64, with
Python 3.11. The package supports Python >=3.10. HDF5 is optional and disabled
by default. macOS source builds require Apple's command line SDK to be
installed beforehand; Linux build tools and sysroots are supplied by Conda.

For a restricted environment, **configure internal mirror URLs before running
`pixi install`**. See [airgapped installation](docs/airgapped-installation.md)
for strict mirror configuration, lockfiles, source and wheel deployment, and
fully offline operation. No separate ornaments channel is needed.

Run commands with `pixi run ornaments`, or enter `pixi shell` and use
`ornaments` directly. Every workflow command has `--help`.

## Complete example workflow

The included `examples/` files are sufficient to run all stages. Put generated
outputs in a new working directory:

```bash
mkdir -p work

# 1. Convert genomic coordinates to transcript coordinates.
pixi run ornaments convert \
  -v examples/truncated_chr1.vcf.gz \
  -g examples/truncated_v36.annotation.gtf \
  -t examples/truncated_transcriptome.fasta \
  -o work/converted.vcf -c work/conversion.tsv

# 2. Merge input files and select samples (also useful for one input file).
printf '%s\n' work/converted.vcf > work/vcfs.txt
pixi run ornaments merge -i work/vcfs.txt -s HG00405 -o work/merged.vcf

# 3. Sort by transcript name and numeric variant position.
pixi run ornaments sort -i work/merged.vcf -o work/sorted.vcf

# 4. Construct the ornament personalized transcriptome.
pixi run ornaments personalize \
  -f examples/truncated_transcriptome.fasta -v work/sorted.vcf \
  -t ornament -o work/HG00405.ornament.fa -s HG00405 -k 31

# 5. Build an index using the same k as personalization.
pixi run ornaments index \
  -i work/HG00405.ornament.index -k 31 work/HG00405.ornament.fa

# 6. Quantify paired reads.
pixi run ornaments quant \
  -i work/HG00405.ornament.index -o work/paired \
  --vcf work/sorted.vcf --sample HG00405 \
  examples/HG00405_1.fastq examples/HG00405_2.fastq
```

For single reads, supply the fragment length mean and standard deviation:

```bash
pixi run ornaments quant \
  -i work/HG00405.ornament.index -o work/single \
  --vcf work/sorted.vcf --sample HG00405 --single -l 150 -s 25 \
  examples/HG00405.fastq
```

Quantification writes `allele_counts.txt` (expected allele-specific counts),
`tpms.txt` (transcript TPM estimates), and `thetas.txt` (transcript probability
estimates) into the output directory. Reference transcriptome inputs without
ornaments use the underlying kallisto behavior.

## Command details

| Command | Inputs | Outputs |
| --- | --- | --- |
| `convert` | gzipped genomic VCF, annotation GTF, reference FASTA | transcriptomic VCF and coordinate conversion map |
| `merge` | text file listing VCF paths; sample name or sample-name file | merged VCF with selected sample columns |
| `sort` | transcriptomic VCF | stable sorted VCF |
| `personalize` | reference FASTA, transcriptomic VCF, samples, mode | personalized FASTA; coordinates in diploid mode |
| `index` | personalized FASTA, k | native index |
| `quant` | index, sorted transcriptomic VCF, sample, FASTQ reads | expression and allele counts |

Use compatible reference FASTA and GTF releases. `convert --no-prepend-chr`
disables adding `chr` when matching annotation chromosome names. Conversion
reports inconsistent reference alleles; a compatible reference and annotation
should yield zero inconsistencies.

`merge -i` lists one input path per line, relative to the working directory.
Blank lines are ignored. `-s` accepts a single sample name or a file listing
sample names in the desired output order; an empty sample file selects all
samples from the first input. Every input must contain every selected sample.
Merging retains **all variant records**, including homozygous alternatives
needed by personalization, and preserves VCF metadata, INFO, FORMAT, and sample
fields. It concatenates records rather than combining duplicate loci or
recalculating cohort-level INFO annotations. Sort after merging chromosome files.

`sort` uses temporary sorted runs to bound memory and file descriptors. It
retains headers and stable order for equal transcript/position keys. Use
`--temp-dir DIRECTORY` to place temporary files on suitable storage or
`--chunk-size RECORDS` to tune memory use. Merge and sort accept plain or
`.gz` VCF inputs and outputs and replace outputs only after successful writes.
Transcript-start edge deletions use the converter’s special nonpositive
positions and remain intact through merging and sorting. Do not use the same
file for input and output.

`personalize -s` accepts comma-separated sample names or `ALL`. k must be odd
and between 3 and 31; the default is 31. Always use the same k for personalization
and indexing. Variants must use transcript coordinates; retain phased genotypes
for diploid construction.

For a diploid FASTA with `_L` and `_R` transcript alleles, select one sample and
provide the **coordinates output** path with `-c`:

```bash
pixi run ornaments personalize \
  -f examples/truncated_transcriptome.fasta -v work/sorted.vcf \
  -t diploid -o work/HG00405.diploid.fa -s HG00405 \
  -c work/HG00405.diploid.coords
```

This coordinates file is produced by diploid generation; it is separate from
the genomic-to-transcriptomic conversion map. Quantification accepts plain and
gzipped transcriptomic VCFs and validates that the requested sample is present.

## Existing command compatibility

These installed helper names retain their short and long argument flags:

- `convert_genomic_vcf_to_transcriptomic_vcf`
- `merge_transcriptome_vcfs`
- `create_personalized_transcriptome`
- `sort_transcriptome_vcf` (new)

The root `.py` scripts remain usable from a checkout with installed Python
dependencies. The unified CLI also forwards the original native `version`,
`cite`, `inspect`, `bus`, `quant-only`, `pseudo`, and `h5dump` commands.
`ornaments-native` exposes the complete original native interface.

**`ornaments merge` now merges VCFs.** Use `ornaments-native merge` for the
original native abundance merge operation. Native commands retain their
existing flags and exit status. Optional HDF5 commands require a build with
HDF5 support enabled.

## Build and verify

```bash
pixi run test
pixi run example-workflow
pixi run build-package
```

After changing local source, use `pixi reinstall ornaments` to rebuild the
installed package before testing.

The example check runs conversion, merge, sorting, ornament and diploid
construction, indexing, and paired and single quantification against real
bundled data. Packaging produces a platform wheel and a source distribution in
`dist/`. See the installation guide for compatible wheel runtime environments.

A standalone native build remains available with installed compiler,
compression libraries, CMake, make, and autoconf 2.69:

```bash
cmake -S . -B build
cmake --build build
cmake --install build --prefix /path/to/install
```

This installs the original native binary and requires the Python package
separately for preparation subcommands. The HTSlib build uses a writable copy
under the build directory; it performs no downloads.

## Reference data

Reference transcriptomes and matching annotations are available from
[GENCODE](https://www.gencodegenes.org/human/). Phased genomic variants may be
obtained from [1000 Genomes](http://ftp.1000genomes.ebi.ac.uk/vol1/ftp/data_collections/1000G_2504_high_coverage/working/20201028_3202_phased/).
Download and transfer data separately when working in a restricted environment.

Ornaments builds on kallisto; credit for kallisto belongs to its original
authors. See `LICENSE`, `LICENSE.txt`, and the included HTSlib license.

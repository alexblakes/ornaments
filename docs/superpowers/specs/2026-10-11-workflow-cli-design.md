# Ornaments workflow CLI and mirror-only installation

## Intent and acceptance criteria

Provide an independently runnable command for each step of the workflow already
documented in this repository. A transferred source checkout must be installable
with Pixi inside a network restricted environment whose only package sources are
mirrors of conda-forge, bioconda, and PyPI. Reference data and reads are supplied
locally; commands never download them.

The user approved the unified CLI and local Python package approach on
2026-10-11. Linux x86-64 is the primary deployment target. Include macOS x86-64
and ARM64 in the environment where dependency availability permits. Windows is
outside this change's scope.

Success means an installed `ornaments` command exposes all six stages, retains
the existing helper executable names, and includes its native index and
quantification engine. The included example data must pass conversion, merging,
sorting, ornament generation, indexing, and paired and single read
quantification. Diploid generation must also produce FASTA and its coordinate
output. Installation must not require the abhinadduri channel, defaults,
GitHub, GNU download servers, or a separate Pixi build-backend channel.

## Architecture

Use a Python console entry point named `ornaments` as the public dispatcher.
Package the existing Python algorithms as importable modules, with thin command
adapters and lazy scientific-library imports so top-level help is lightweight.
Keep the existing root scripts as compatibility entry points using the same
argument parsing and implementation as the installed helpers.

Compile the existing C++ engine and install it inside the Python package under
a private executable name. The dispatcher locates it relative to its installed
package, avoiding PATH recursion and dependence on a source checkout. Index and
quantification delegate to the engine without invoking a shell; propagate its
exit status and output. Retain a direct `ornaments-native` entry point for the
original native interface, including native commands that are not part of the
six-stage workflow.

The native engine already has a `merge` command for quantification outputs.
The new public `ornaments merge` means transcriptomic VCF merging. Document
`ornaments-native merge` as the route to the original native operation. Other
non-conflicting native commands remain available through dispatcher forwarding.

## Command contracts and data flow

1. `ornaments convert -v GENOMIC.vcf.gz -g ANNOTATION.gtf -t REFERENCE.fa
   -o TRANSCRIPTOMIC.vcf -c COORDINATES.tsv`: reuse the coordinate conversion
   implementation, including `--no-prepend-chr`. Retain existing short and long
   flags.
2. `ornaments merge -i FILE_LIST -s SAMPLE_OR_SAMPLE_FILE -o MERGED.vcf`:
   retain the existing input-list and sample selection interface. Validate
   sample presence in every input and preserve the selected sample order,
   VCF metadata, and genotype field semantics. Retain all records by default,
   matching the current executed behavior. Correct the README's claim that
   this filters only heterozygous sites: homozygous alternative variants are
   needed by personalization. Do not introduce a new biological filtering
   policy as part of adding a CLI.
3. `ornaments sort -i INPUT.vcf -o SORTED.vcf`: add the missing command;
   preserve header lines and record fields, sort by transcript name and numeric
   position, and preserve input order for identical keys. Use bounded memory
   with temporary sorted chunks and a merge so chromosome-scale inputs do
   not require retaining every record in RAM. Support a configurable temporary
   directory. Reject malformed records with their input line number.
4. `ornaments personalize -f REFERENCE.fa -v SORTED.vcf -t ornament|diploid
   -o PERSONALIZED.fa -s SAMPLES [-c COORDINATES] [-k K]`: reuse the current
   algorithms and flags. Resolve `ALL` from the VCF header before invoking the
   algorithm; validate samples and require a single sample plus the coordinates
   output path for diploid mode. The coordinates argument here is an output,
   not the conversion map from stage 1. Preserve the existing default k of 31.
5. `ornaments index -i INDEX [-k K] PERSONALIZED.fa`: retain the native syntax
   and behavior. Personalization and indexing must use the same k value.
6. `ornaments quant -i INDEX -o DIRECTORY --vcf SORTED.vcf --sample SAMPLE
   READ1.fastq READ2.fastq`: retain all existing native quantification flags.
   Single read mode uses `--single -l MEAN -s SD READ.fastq`.

Each stage has command help. Missing arguments and invalid user input produce
a clear error and nonzero exit code. Do not turn algorithm failures into
successful exits. Avoid overwriting an input path with its own output. Preserve
existing scientific computation except for compatibility and input handling
defects necessary to make these documented paths work.

Install the legacy helper command names
`convert_genomic_vcf_to_transcriptomic_vcf`, `merge_transcriptome_vcfs`, and
`create_personalized_transcriptome` with their current flags. Add a standalone
`sort_transcriptome_vcf` alias for symmetry. Examples use the unified interface.

## Packaging and build

Add a PEP 517 `pyproject.toml` using scikit-build-core to build a platform wheel
containing the Python package and private native executable. Declare Python
3.10 or newer and explicit scientific dependencies, including NumPy,
Biopython, pandas, and gtfparse. Adapt the GTF reader to the supported pandas
return representation rather than relying on an obsolete Python 3.6 stack.

Modernize the CMake configuration sufficiently for current CMake and reliable
dependency ordering. Build the committed HTSlib sources locally, retaining the
vendored API used by this engine. Obtain compilers, CMake, make, autoconf,
compression libraries, and Python build requirements from the mirrors. Keep
HDF5 optional and disabled by default, matching the current CMake behavior.
The build must not contain dependency fetches. Include all required Python,
C++, and vendored build sources in the source distribution.

Provide a Pixi manifest with dependencies from conda-forge and bioconda and a
local path PyPI dependency for this project. Include tasks for CLI use and
packaging. Use PyPI only for packages or build requirements unavailable or
deliberately sourced there; no direct Git or remote source dependencies.

Document two distribution routes: install from a transferred source checkout,
or install a platform wheel built for the target environment and staged on an
internal PyPI index. The source route is required and includes compiler tools;
the wheel route can omit build tools but still requires compatible runtime
libraries from the Conda mirrors. Do not claim arbitrary host-built wheels are
portable across operating systems or incompatible library versions.

## Mirror operation

Provide a site configuration example mapping conda-forge and bioconda to
internal mirror URLs and setting the PyPI simple index URL. Mirror hostnames
are deployment-specific and must be supplied by the operator. Document how
to use this configuration before solving or installing and how to generate a
lockfile within the restricted environment. Explain the difference between
mirror-accessible installation and fully offline installation from an already
populated cache.

Show a strict installation route with explicit internal channel and PyPI URLs
and no public fallback. A public lockfile is not evidence of a mirror-only
installation; regenerate or correctly remap it for the target site. Do not
embed credentials. Record the Pixi version used for local validation and the
configuration mechanisms supported by that version.

## Documentation

Update the README with Pixi installation first, a concise six-step example,
legacy aliases, native command compatibility, output paths, matching k values,
and diploid coordinates requirements. Add an airgapped installation guide and
a deployable configuration example. Clearly distinguish commands implemented
and verified locally from installation exercised against real site mirrors.

## Verification and limits

Use focused checks of CLI argument dispatch and failure propagation, VCF
sorting and metadata/sample preservation, and personalization argument
validation. Exercise the real bundled examples through every stage, including
paired and single quantification and diploid output. Install a built wheel
outside the source tree and verify that package discovery and native engine
location do not depend on the working directory.

Inspect build and dependency configuration for public downloads. Site mirror
URLs and a Linux execution environment are not supplied in this session; do
not claim a real site installation or Linux run unless one is actually
available. Report the tested platform and any unresolved checks explicitly.

## Scope boundaries

No workflow scheduler, automatic dataset downloads, new expression model,
container deployment, package publication, or unrelated algorithm refactor.
The commands provide the composable end-to-end interface requested by the
user; orchestration can be added separately if requested.

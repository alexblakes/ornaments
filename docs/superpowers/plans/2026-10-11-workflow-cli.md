# Workflow CLI and Mirror Installation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Install a complete six-stage Ornaments CLI from local source using Pixi and internal Conda/PyPI mirrors.

**Architecture:** A Python dispatcher invokes importable preparation algorithms and a packaged private C++ engine. A scikit-build-core wheel combines these components; Pixi supplies build tools and runtime dependencies. Keep legacy helper entry points and make the original native interface accessible separately.

**Tech Stack:** Python >=3.10, argparse, NumPy, Biopython, pandas, gtfparse, C++14, CMake, vendored HTSlib, scikit-build-core, Pixi, pytest.

**Spec:** `docs/superpowers/specs/2026-10-11-workflow-cli-design.md`

## Global Constraints

- Linux x86-64 is the primary deployment target.
- Include macOS x86-64 and ARM64 in the environment where dependency availability permits.
- Declare Python 3.10 or newer.
- The build must not contain dependency fetches.
- Keep HDF5 optional and disabled by default, matching the current CMake behavior.
- Installation must not require the abhinadduri channel, defaults, GitHub, GNU download servers, or a separate Pixi build-backend channel.
- Reference data and reads are supplied locally; commands never download them.
- Preserve existing scientific computation except for compatibility and input handling defects necessary to make these documented paths work.
- Retain all records by default, matching the current executed behavior.
- Personalization and indexing must use the same k value.
- A public lockfile is not evidence of a mirror-only installation; regenerate or correctly remap it for the target site.
- Do not embed credentials.
- No workflow scheduler, automatic dataset downloads, new expression model, container deployment, package publication, or unrelated algorithm refactor.

## Review Focus

- A path containing spaces must reach the native executable as one argument; Task 1 tests argument forwarding.
- Multiple VCFs can place samples in different column orders; Task 2 tests ordered sample projection and FORMAT preservation.
- Empty VCF bodies and identical sort keys must retain headers and stable ordering; Task 2 tests both, including chunk boundaries.
- `ALL`, absent samples, and diploid coordinates requirements must yield deterministic outcomes rather than silent success; Task 3 tests these cases.
- An installed wheel executed outside its source tree must find its bundled engine and retain legacy helpers; Tasks 4 and 5 exercise this explicitly.

## File Structure

- `python/ornaments/__init__.py`: package identity and version.
- `python/ornaments/__main__.py`: `python -m ornaments` entry point.
- `python/ornaments/cli.py`: command discovery, dispatch, error reporting, legacy adapter entry points.
- `python/ornaments/native.py`: private executable location and subprocess dispatch.
- `python/ornaments/convert.py`: existing coordinate conversion algorithm and argument parser.
- `python/ornaments/personalize.py`: existing personalization algorithm and parser.
- `python/ornaments/vcf.py`: text opening, VCF header parsing, and selected sample validation shared by preparation commands.
- `python/ornaments/merge.py`: VCF merging and sample projection.
- `python/ornaments/sort.py`: bounded-memory stable VCF sorting.
- Existing root Python scripts: compatibility wrappers importing packaged implementations.
- `pyproject.toml`: wheel build, Python metadata, dependency constraints, and console entry points.
- `pixi.toml`: environment dependencies, local package installation, and CLI/build/check tasks.
- `CMakeLists.txt`, `src/CMakeLists.txt`: modern CMake, isolated vendored HTSlib build, native installation destination.
- `build.sh`, `meta.yaml`: align existing Conda build route with supported dependencies and public commands.
- `.gitignore`: generated environments, build artifacts, and Python caches.
- `tests/test_cli.py`, `tests/test_vcf.py`, `tests/test_personalize.py`: focused regression checks.
- `tests/run_example_workflow.py`: subprocess integration check using included real data.
- `docs/airgapped-installation.md`, `config/pixi-mirrors.example.toml`: installation instructions and site configuration example.
- `README.md`: supported installation and six-stage workflow.

### Task 1: Public dispatcher and native compatibility

**Files:** Create package identity, module entry point, `cli.py`, `native.py`, and `tests/test_cli.py`.

**Interfaces:**
- Produce `cli.main(argv: list[str] | None = None) -> int`.
- Produce `native.run(argv: list[str]) -> int` and `native.main() -> int` for `ornaments-native`.
- Native binary path is `Path(__file__).parent / "_bin" / "ornaments"`.
- Preparation modules expose `cli(argv: list[str] | None = None) -> int`; dispatcher imports them only when selected.

- [ ] **Step 1: Add failing tests for help, forwarding, and native errors.**

```python
def test_top_level_help(capsys):
    from ornaments.cli import main
    assert main(["--help"]) == 0
    help_text = capsys.readouterr().out
    assert all(name in help_text for name in
               ["convert", "merge", "sort", "personalize", "index", "quant"])

def test_native_arguments_and_status(monkeypatch):
    from ornaments import native
    from ornaments.cli import main
    received = []
    monkeypatch.setattr(native, "run", lambda args: received.append(args) or 7)
    assert main(["index", "-i", "path with spaces/index", "input.fa"]) == 7
    assert received == [["index", "-i", "path with spaces/index", "input.fa"]]
```

Add a test asserting `ornaments-native merge` forwards native `merge`, while public
`merge` invokes the Python adapter. Assert missing engine reports its expected
path and a nonzero status.

- [ ] **Step 2: Run `PYTHONPATH=python python -m pytest tests/test_cli.py -q`; expect import failures before scaffolding.**
- [ ] **Step 3: Implement lazy dispatch, help, and private executable lookup.**

```python
def run(argv: list[str]) -> int:
    import subprocess
    from pathlib import Path
    executable = Path(__file__).parent / "_bin" / "ornaments"
    if not executable.is_file():
        raise FileNotFoundError(f"Native engine is missing: {executable}; reinstall Ornaments")
    return subprocess.run([str(executable), *argv], check=False).returncode
```

Use an explicit map from preparation command names to importable modules.
Handle user input exceptions at the CLI boundary with stderr and nonzero
status; propagate native status. Keep unrecognized command handling clear and
list supported commands. Forward existing non-conflicting native commands.

- [ ] **Step 4: Run focused dispatcher tests and confirm help does not import scientific libraries.**
- [ ] **Step 5: Commit the dispatcher and tests with `feat: add unified workflow dispatcher`.**

### Task 2: Conversion, merging, and sorting

**Files:** Move conversion implementation into `python/ornaments/convert.py`; create `vcf.py`, `merge.py`, `sort.py`, `tests/test_vcf.py`; replace conversion/merge root scripts with wrappers.

**Interfaces:**
- `vcf.open_text(path: str | Path, mode: str = "rt")` opens plain text or `.gz` input.
- `vcf.read_samples(path: str | Path) -> list[str]` reads the `#CHROM` header and rejects missing/duplicate sample headers.
- `merge.merge_vcfs(paths: list[str], output: str, samples: list[str]) -> None` preserves all records and selected sample fields.
- `sort.sort_vcf(input_path: str, output_path: str, *, temp_dir: str | None = None, chunk_size: int = 100000) -> None` sorts stably by `(transcript, numeric_position, original_ordinal)`.
- Each command implements `cli(argv=None) -> int`; conversion retains its existing `main(...)` scientific signature.

- [ ] **Step 1: Add regression fixtures with actual VCF headers and FORMAT fields.**

```python
def test_sort_across_chunks_preserves_ties(tmp_path):
    from ornaments.sort import sort_vcf
    source = tmp_path / "in.vcf"
    target = tmp_path / "out.vcf"
    header = "##fileformat=VCFv4.2\n#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\n"
    rows = ["txB\t2\ta\tA\tG\t.\t.\t.\n", "txA\t10\tb\tA\tG\t.\t.\t.\n", "txA\t2\tc\tA\tG\t.\t.\t.\n", "txA\t2\td\tA\tG\t.\t.\t.\n"]
    source.write_text(header + "".join(rows))
    sort_vcf(str(source), str(target), chunk_size=1)
    assert target.read_text() == header + "".join(rows[i] for i in [2, 3, 1, 0])
```

Add a merge fixture with first header `A,B`, second header `B,A`, requested
samples `A,B`, and FORMAT `GT:DP`; assert the two records preserve genotype
and depth values in requested order. Retain metadata from inputs without
duplicating identical lines. Test empty body, missing samples, blank input-list
lines, gzipped input, invalid numeric POS with line number, and same input/output
path rejection. Preserve INFO and FORMAT rather than dropping fields silently.

- [ ] **Step 2: Run `PYTHONPATH=python python -m pytest tests/test_vcf.py -q`; expect missing module failures.**
- [ ] **Step 3: Implement VCF preparation and expose conversion as a callable adapter.**

```python
# Conversion's CLI adapter preserves existing flag names.
def cli(argv=None):
    args = parse_arguments(argv)
    main(args.genome_vcf_file, args.gtf_file, args.transcriptome,
         args.output, args.coordinate_output, not args.no_prepend_chr)
    return 0
```

Change conversion's `parse_arguments` to accept `argv=None`. Request pandas
output explicitly with the chosen supported gtfparse API and test the real
annotation file during Task 5. Merge metadata before writing `#CHROM`; reject
conflicting definitions for the same metadata identifier if they cannot be
preserved faithfully. Use per-input sample indexes and retain whole sample
fields. Sorting uses `TemporaryDirectory`, sorted chunks and `heapq.merge`;
clean intermediate files on errors. Reject input/output aliases before opening
outputs. Keep filenames with spaces intact and validate minimum VCF columns.

- [ ] **Step 4: Run preparation tests and conversion help through both unified and legacy interfaces.**
- [ ] **Step 5: Commit with `feat: expose conversion merge and stable VCF sorting`.**

### Task 3: Personalization and legacy adapters

**Files:** Move existing personalization code into `python/ornaments/personalize.py`; create `tests/test_personalize.py`; modify root personalization wrapper and `cli.py` legacy adapters.

**Interfaces:** Preserve `personalize.main(tfasta, tvcf, output_type, output_file, samples, coordinates, k)`; `personalize.cli(argv=None) -> int` validates inputs first. Reuse `vcf.read_samples` from Task 2.

- [ ] **Step 1: Add failing tests that mock the scientific operation, exercising real parsing and validation.**

```python
def test_all_resolves_header_samples(monkeypatch, tmp_path):
    from ornaments import personalize
    vcf = tmp_path / "variants.vcf"
    vcf.write_text("#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tA\tB\n")
    fasta = tmp_path / "ref.fa"
    fasta.write_text(">tx\nACGT\n")
    calls = []
    monkeypatch.setattr(personalize, "main", lambda *args: calls.append(args))
    assert personalize.cli(["-f", str(fasta), "-v", str(vcf), "-t", "ornament",
                            "-o", str(tmp_path / "out.fa"), "-s", "ALL"]) == 0
    assert calls[0][4] == "A,B"
```

Test absent samples and diploid without `-c` produce nonzero CLI exits without
creating output, diploid with multiple selected samples fails, and valid
diploid coordinates reach the scientific function. Check invalid k: it must be
positive, odd, and within the native engine's supported limit read from
`src/Kmer.hpp`. Check input/output aliases, including coordinates output.

- [ ] **Step 2: Run `PYTHONPATH=python python -m pytest tests/test_personalize.py -q`; expect failing import or validation.**
- [ ] **Step 3: Implement header resolution and validation before scientific execution.**

```python
available = read_samples(args.transcriptome_vcf)
selected = available if args.samples.strip() == "ALL" else [s.strip() for s in args.samples.split(",")]
missing = [s for s in selected if s not in available]
if missing:
    parser.error("Samples absent from VCF: " + ", ".join(missing))
if args.output_type == "diploid" and (len(selected) != 1 or not args.coordinates):
    parser.error("Diploid output requires one sample and -c coordinates output")
```

Ensure the scientific function cannot silently succeed after validation errors;
remove its obsolete argv-dependent help branch. Fix the direct `ALL` path if
needed so both Python callers and CLI adapters have coherent sample behavior.
Keep all three root script help/argument contracts, and expose installed
legacy helpers through console entry points. Make root wrappers import the
source package explicitly when run from an uninstalled checkout.

- [ ] **Step 4: Run focused personalization tests and legacy help checks.**
- [ ] **Step 5: Commit with `feat: add validated personalization commands`.**

### Task 4: Local wheel build and Pixi mirror installation

**Files:** Create `pyproject.toml`, `pixi.toml`, mirror example and installation guide; modify CMake files, `build.sh`, `meta.yaml`, `.gitignore`; extend dispatcher tests for an installed layout.

**Interfaces:** Wheel contains `ornaments/_bin/ornaments` and all Python modules. Public scripts are `ornaments`, `ornaments-native`, `convert_genomic_vcf_to_transcriptomic_vcf`, `merge_transcriptome_vcfs`, `create_personalized_transcriptome`, and `sort_transcriptome_vcf`.

- [ ] **Step 1: Add installed-layout tests and inspect current Pixi/gtfparse/build backend primary documentation before fixing version ranges.**

```python
def test_native_uses_packaged_location(monkeypatch, tmp_path):
    from ornaments import native
    import subprocess
    package = tmp_path / "ornaments"
    engine = package / "_bin" / "ornaments"
    engine.parent.mkdir(parents=True)
    engine.touch()
    monkeypatch.setattr(native, "__file__", str(package / "native.py"))
    received = []
    monkeypatch.setattr(subprocess, "run", lambda args, **kw:
                        received.append((args, kw)) or subprocess.CompletedProcess(args, 0))
    assert native.run(["version"]) == 0
    assert received[0][0] == [str(engine), "version"]
    assert received[0][1].get("shell", False) is False
```

- [ ] **Step 2: Define the local build and entry points.**

```toml
[build-system]
requires = ["scikit-build-core>=0.10,<1"]
build-backend = "scikit_build_core.build"

[project]
name = "ornaments"
version = "1.1.0"
requires-python = ">=3.10"
dependencies = ["numpy>=1.24,<3", "biopython>=1.81,<2", "pandas>=2,<3", "gtfparse>=2.5,<3"]

[project.scripts]
ornaments = "ornaments.cli:main"
ornaments-native = "ornaments.native:main"
convert_genomic_vcf_to_transcriptomic_vcf = "ornaments.cli:convert_main"
merge_transcriptome_vcfs = "ornaments.cli:merge_main"
create_personalized_transcriptome = "ornaments.cli:personalize_main"
sort_transcriptome_vcf = "ornaments.cli:sort_main"

[tool.scikit-build]
wheel.packages = ["python/ornaments"]
```

Confirm declared ranges against real dependency compatibility, especially
gtfparse/pandas/NumPy; adjust constraints based on resolver/build evidence.
Include license metadata and source distribution files. Configure CMake's
install path via a packaging-specific variable so ordinary CMake still
installs the native engine to `bin`.

- [ ] **Step 3: Modernize local CMake without changing native algorithm code.**

Use CMake >=3.18, `Threads::Threads`, and explicit compression library discovery.
Copy vendored HTSlib into the CMake binary directory before building; its
autoconf source mutation must not dirty the checkout or modify a read-only
source tree. Use explicit `add_dependencies(kallisto_core htslib)` and declared
static-library byproducts. Configure HTSlib with the existing disabled optional
compression/network features. Preserve native dependencies on zlib, bzip2 and
lzma as required by the existing engine. Use generator-independent native
make for HTSlib, not Ninja. Include all vendored sources in sdist.

- [ ] **Step 4: Define Pixi environment and tasks.**

```toml
[workspace]
name = "ornaments"
channels = ["conda-forge", "bioconda"]
platforms = ["linux-64", "osx-64", "osx-arm64"]

[pypi-dependencies]
ornaments = { path = "." }

[tasks]
ornaments = "ornaments"
```

Add Python 3.11, CMake, Ninja, make, autoconf, compiler metapackages,
compression development libraries, compatible scientific libraries,
scikit-build-core, build, pip, and pytest. Use platform-specific compiler
dependencies when necessary. Confirm Pixi's documented method for disabling
build isolation for the local package when using environment-supplied build
requirements; avoid redundant uncapped public dependency resolution. Add
build and focused-check tasks. Update legacy Conda recipe/build script to
install the same package and aliases with local source and declared build
requirements; remove Python 3.6 pins and outside-channel assumptions.

- [ ] **Step 5: Write site configuration and explicit mirror installation instructions.**

Verify the current Pixi config schema before writing
`config/pixi-mirrors.example.toml`. Show conda-forge/bioconda mappings and
PyPI index configuration; explain manifest versus site config precedence.
Provide a strict alternate manifest configuration with explicit internal
channel URLs plus `[pypi-options] index-url`, never `extra-index-urls` pointing
to public servers. Document transferring source, installing Pixi beforehand,
solving inside the site, handling lockfile URLs and caches, and staging a wheel
for a matching platform. Keep credential placeholders out of URLs.

- [ ] **Step 6: Run `pixi install`, focused tests, `pixi run python -m build`, and inspect wheel and sdist inventories.**
Expected: wheel contains executable and modules; sdist contains HTSlib and C++
sources. Inspect dependency links of the built engine and document runtime
libraries. Sandbox-related network failures require the normal escalation
route. A package resolution or build failure is a defect to fix, not grounds
for substituting a mock build.
- [ ] **Step 7: Commit with `build: package workflow CLI for Pixi mirror environments`.**

### Task 5: Real workflow, installation checks, and documentation

**Files:** Create `tests/run_example_workflow.py`; update README and installation guide.

**Interfaces:** Integration script invokes installed commands using
`subprocess.run(..., check=True)`, reads examples relative to an explicit source
root, and writes all products to a temporary directory. It accepts a CLI path
so the same check can exercise Pixi and a separately installed wheel.

- [ ] **Step 1: Add the real example workflow with assertions on outputs.**

```python
def invoke(executable, *args):
    import subprocess
    subprocess.run([str(executable), *map(str, args)], check=True)

# All output paths below are under an isolated temporary directory.
invoke(cli, "convert", "-v", examples / "truncated_chr1.vcf.gz",
       "-g", examples / "truncated_v36.annotation.gtf",
       "-t", examples / "truncated_transcriptome.fasta",
       "-o", converted, "-c", conversion_map)
invoke(cli, "merge", "-i", file_list, "-s", "HG00405", "-o", merged)
invoke(cli, "sort", "-i", merged, "-o", sorted_vcf)
invoke(cli, "personalize", "-f", examples / "truncated_transcriptome.fasta",
       "-v", sorted_vcf, "-t", "ornament", "-o", fasta, "-s", "HG00405")
invoke(cli, "index", "-i", index, fasta)
invoke(cli, "quant", "-i", index, "-o", paired, "--vcf", sorted_vcf,
       "--sample", "HG00405", examples / "HG00405_1.fastq", examples / "HG00405_2.fastq")
invoke(cli, "quant", "-i", index, "-o", single, "--vcf", sorted_vcf,
       "--sample", "HG00405", "--single", "-l", "150", "-s", "25",
       examples / "HG00405.fastq")
invoke(cli, "personalize", "-f", examples / "truncated_transcriptome.fasta",
       "-v", sorted_vcf, "-t", "diploid", "-o", diploid, "-s", "HG00405",
       "-c", diploid_coordinates)
```

Write `file_list` with the generated converted path. Assert sorted record
order, VCF sample header, nonempty FASTA/index, diploid `_L`/`_R` sequences,
coordinate output, and native quantification products `allele_counts.txt`,
`tpms.txt`, `thetas.txt`. Check parseable nonnegative quantification values;
use shipped expected examples for deterministic scientific comparisons where
their provenance matches the tested command. Do not invent expression values.

- [ ] **Step 2: Run the complete integration script in Pixi, then repair only failures necessary for the approved workflow.**
Expected: all real stages finish with zero status and usable outputs. Include
an output directory containing spaces. If an algorithm failure arises, use
the debugging skill before fixing it and pin any discovered regression with a
focused check.

- [ ] **Step 3: Install the built wheel into a temporary environment and exercise it outside the repository.**
Use the Pixi Python to create a temporary environment with access to supplied
runtime libraries, install the wheel with `pip --no-deps --no-index`, change
working directory to a temporary path, run the example integration script
with that environment's absolute CLI path, and run all legacy `--help`
commands. This checks artifact completeness independently of source imports;
it does not claim a dependency-free wheel.

- [ ] **Step 4: Replace obsolete README installation guidance and add the exact six-step example.**
Show source Pixi installation and link the mirror guide. Explain public/native
merge semantics, selected sample behavior, sorting, k consistency, diploid
coordinates output, optional HDF5, legacy entry points and platform scope.
Keep examples consistent with actual filenames produced by integration.

- [ ] **Step 5: Run focused tests and integration once after final edits; inspect Git diff and configuration for download dependencies.**
Record Pixi version, tested platform, package build and actual integration
results. Report untested Linux and site mirror deployment if unavailable.
Review the completed branch according to the chosen execution skill, fix
findings, and repeat only checks affected by fixes.
- [ ] **Step 6: Commit with `docs: document and verify the complete installed workflow`.**

## Execution Handoff

Recommend native execution because the five tasks share command and packaging
interfaces and the complete example workflow supplies direct integration
evidence. The user must review this plan and choose native or subagent-driven
execution before product implementation begins.

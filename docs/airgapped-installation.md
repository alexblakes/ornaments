# Installing in the GERE from Conda channels

All third-party dependencies come from conda-forge and bioconda, including
`gtfparse`. No PyPI index, Conda/PyPI name mapping, or scikit-build backend is
needed. Pip installs only the local Ornaments source or wheel, with downloads
and dependency resolution disabled.

## Precompiled Linux bundle (no compiler in the GERE)

The **Build GERE wheel bundle** GitHub Actions workflow builds a Linux x86-64,
Python 3.11 wheel. After the branch has been pushed, run the workflow from
GitHub's Actions tab on that branch, or create a `v*` tag to trigger it. Download
the `ornaments-linux-64-python311` artifact ZIP from the completed run and
transfer it into the GERE. This is a separate download from GitHub's **Code →
Download ZIP** source archive. The workflow must finish before a precompiled
bundle is available; the source archive alone still requires compilation.

Extract the artifact ZIP. It contains a runtime `pixi.toml`, an `artifacts/`
directory containing the wheel, this guide, and a mirror configuration example.
Configure the Conda channels as described below, then run from that directory:

```bash
pixi install
pixi run install-wheel
pixi run ornaments --help
```

This route needs neither setuptools nor CMake, compilers, make, autoconf, or
scikit-build. Pip unpacks the precompiled wheel; all runtime dependencies are
installed through Conda. The bundle targets Linux x86-64 with Python 3.11;
it cannot be used on macOS or ARM64. It still requires compatible Linux/glibc
and Conda C++ runtime libraries. Validate it on the target host before running
an analysis. The Linux workflow has to be run on GitHub; a locally built macOS
wheel cannot substitute for its output.

## Configure internal channels before installing

Use Pixi 0.80.0 or newer. In the applicable `pixi.toml`, replace the existing
workspace `channels` with your site's actual mirror URLs:

```toml
[workspace]
# Retain the other workspace settings from the manifest.
channels = ["https://packages.example.internal/conda-forge",
            "https://packages.example.internal/bioconda"]
```

Alternatively, if your mirrors preserve upstream URL layouts, copy
`config/pixi-mirrors.example.toml` to `.pixi/config.toml` and edit its URLs.
Keep TLS verification enabled and use the site's trusted CA configuration.
Store authentication outside tracked files.

The mirrors must contain packages matching the manifest's constraints.
`gtfparse>=2.5,<3` is supplied by Bioconda, including its transitive dependencies.
A missing package must be supplied through the site's Conda mirror.

If a lockfile from another site was transferred, move it aside before solving
against your internal URLs:

```bash
# Only if a lockfile from another site is present:
mv pixi.lock pixi.lock.previous-site
```

Keep the resulting site-specific `pixi.lock` for subsequent
`pixi install --locked` calls. Review channel and artifact URLs in the lockfile.
With mirror mappings, logical URLs may retain upstream URLs, so keep the
mirror configuration with the deployment.

## Build from the GitHub source ZIP

Transfer and extract the whole source repository, including `ext/htslib`.
No Git checkout or native dependency source download is required. The source
manifest supports Linux x86-64 and macOS x86-64/ARM64. If your mirrors contain
only Linux packages, reduce its workspace `platforms` to `["linux-64"]` before
solving. macOS source builds require Apple's command line SDK beforehand.

```bash
pixi install
pixi run install-package
pixi run ornaments --help
```

The first command installs the Conda dependencies. The second builds the
native engine with CMake and installs the Python package with setuptools:

```bash
python -m pip install . --no-deps --no-build-isolation --no-index
```

All build tools are already supplied by the Conda environment. The committed
HTSlib sources compile in a writable build directory without downloading
anything. HDF5 is disabled by default. Repeat `pixi run install-package` after
changing source files. `pixi install` alone installs dependencies and does not
install Ornaments.

For manually pasting the new packaging files into an existing RE checkout,
create the blank files first:

```bash
touch setup.py MANIFEST.in
```

## Build and transfer a wheel yourself

On a compatible Linux build host with access to the Conda channels:

```bash
pixi install
pixi run build-package
```

This creates a platform wheel and source distribution in `dist/`. Transfer
exactly one matching wheel into `artifacts/` alongside a copy of
`deploy/pixi.toml` named `pixi.toml`, and use the precompiled installation steps
above. Keep compatible Conda native runtime dependencies: the wheel contains
the engine, but does not bundle its compression or C++ shared libraries.
The source distribution includes the build sources, manifests, and licenses.

## Fully offline operation

Reachable internal mirrors allow resolution and installation. A machine with
no network at all needs a site lockfile and every Conda artifact in Pixi's
cache beforehand, plus the transferred Ornaments wheel or sources.
`pixi install --offline --locked` can only reuse packages already cached.
No PyPI artifacts are needed.

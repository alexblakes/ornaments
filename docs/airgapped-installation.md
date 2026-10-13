# Installing through internal mirrors

Transfer this repository (including `ext/htslib`) or its source distribution
into the environment. Install Pixi 0.80.0 or newer through your site's software
distribution process. The manifest in `pyproject.toml` targets Linux x86-64 and
macOS x86-64/ARM64. Reference data is supplied locally.

## Configure before installing

Replace the existing workspace channels, name mappings, and backend channels
in `pyproject.toml` with internal URLs:

```toml
[tool.pixi.workspace]
# Retain platforms, requires-pixi, and preview = ["pixi-build"].
channels = ["https://packages.example.internal/conda-forge",
            "https://packages.example.internal/bioconda"]

[tool.pixi.workspace.conda-pypi-map]
"https://packages.example.internal/conda-forge" = { mapping-mode = "replace", mapping = { python-build = "build" } }
"https://packages.example.internal/bioconda" = { mapping-mode = "replace" }

[tool.pixi.package.build]
backend = { name = "pixi-build-cmake", version = "0.*", channels = ["https://packages.example.internal/conda-forge"] }
```

Use your site's actual URLs. Edit existing TOML tables rather than adding
duplicate tables. Both workspace and backend channels must use mirrors: the
backend is resolved separately. The Conda mirror must contain
`pixi-build-cmake` and its dependencies in addition to compilers, sysroots,
Python, and runtime dependencies. No separate backend channel is needed.

Alternatively, if the mirrors preserve upstream URL layouts, copy
`config/pixi-mirrors.example.toml` to `.pixi/config.toml` and edit its URLs.
Mapping mode `replace` suppresses external Conda/PyPI name-map downloads.
The source package and workspace use Conda dependencies, including gtfparse;
no PyPI index is needed for this route. The Python CLI is installed by pip
with dependencies and build isolation disabled and `--no-index`; the native
engine is built by CMake. HTSlib is built from its committed sources in a
private writable copy without downloads. HDF5 is optional and off by default.

Pixi documents mirror behavior in its [configuration reference](https://pixi.prefix.dev/latest/reference/pixi_configuration/).
Keep TLS verification enabled and configure your site's trusted CA if needed.
Store authentication outside tracked files using Pixi's credential mechanisms.
macOS builds require Apple's command line SDK to be installed beforehand.

## Solve and install inside the site

A checkout ships without a public lockfile. Move an existing lockfile aside
before solving against different mirror URLs:

```bash
# Only if a lockfile from another site is present:
mv pixi.lock pixi.lock.previous-site

pixi install
pixi run ornaments --help
pixi run test
pixi run example-workflow
```

Pixi solves all declared platforms. If your mirrors contain only the target
platform, reduce `[tool.pixi.workspace] platforms` to `["linux-64"]` (or the
macOS platform) before installation. Preserve the resulting site-specific
`pixi.lock`; subsequent installs can use `pixi install --locked`. Review its
artifact URLs and keep `.pixi/config.toml` alongside the deployment if using
mirror mappings. A missing artifact should be added to the mirror.

## Build once and distribute a Conda package

```bash
pixi build --output-dir dist
```

Upload the resulting `.conda` artifact to an internal channel. Consumers can
then add that channel alongside the internal conda-forge and bioconda mirrors
and run `pixi add ornaments`. Binary package consumers do not need the build
backend or compilers. Build separately for each target platform; the current
package definition uses Python 3.11. A local source package can also be added
with `pixi add ornaments --path /path/to/ornaments` after enabling the
`pixi-build` preview in the consuming workspace.

## Build once and stage a wheel

`pixi run build-package` still produces a platform wheel and source distribution
under `dist/`. Stage the wheel on the site's PyPI index or transfer it directly.
Wheels require compatible Conda compression and C++ runtime libraries and are
tied to their OS, architecture, and Python environment layout.

For a wheel deployment, remove `[tool.pixi.package]` and all its subtables,
remove `ornaments` from `[tool.pixi.dependencies]`, and remove source build
tools while retaining Python and runtime dependencies. Add:

```toml
[tool.pixi.pypi-dependencies]
ornaments = { path = "artifacts/ornaments-1.1.0-cp311-cp311-linux_x86_64.whl" }
```

Use the actual wheel filename. Retain zlib, bzip2, and xz, plus `libcxx` on
macOS or compatible `libstdcxx-ng` and `libgcc-ng` on Linux. Then `pixi install`
installs the wheel without invoking a compiler. If resolving additional PyPI
packages, set the internal index with `[tool.pixi.pypi-options] index-url` and
ensure wheel links also point to internal hosts.

## Fully offline operation

An environment with reachable internal mirrors can resolve new packages. A
machine with no network needs a site lockfile and all required artifacts in
Pixi's cache beforehand, or a transferred complete environment.
`pixi install --offline --locked` only reuses artifacts already cached. Source
builds also need the cached backend and build dependencies.

The Pixi package has been built and installed on macOS ARM64. Linux and macOS
x86-64 are declared targets; execute builds on those hosts before deploying
binary artifacts. Installation against actual site mirrors requires local
validation.

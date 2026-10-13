# Installing through internal mirrors

Transfer this repository (including `ext/htslib`) or its source distribution
into the environment. Install Pixi 0.80.0 or newer on the target machine through
your site's software distribution process. The primary target is Linux x86-64;
the manifest also supports macOS x86-64 and ARM64. Reference data is supplied
locally. No Git checkout, GNU source download, or separate Pixi backend channel
is needed during installation.

## Configure before installing

The recommended route uses explicit internal URLs in `pixi.toml`. Replace the
workspace channels, replace the name-mapping table with the following entries,
and add the internal PyPI index to the existing `[pypi-options]` table:

```toml
[workspace]
# Retain name, version, platforms, and requires-pixi from the existing manifest.
channels = ["https://packages.example.internal/conda-forge",
            "https://packages.example.internal/bioconda"]

[workspace.conda-pypi-map]
"https://packages.example.internal/conda-forge" = { mapping-mode = "replace", same-name-heuristic = true, mapping = { python-build = "build" } }
"https://packages.example.internal/bioconda" = { mapping-mode = "replace", same-name-heuristic = true }

[pypi-options]
index-url = "https://packages.example.internal/pypi/simple"
no-build-isolation = ["ornaments"]
```

Use your actual URLs, including any required path prefixes. Edit existing
TOML tables rather than adding duplicate tables. Do not add public channels or
`extra-index-urls`. The internal PyPI index must serve local wheel/sdist links,
not links to public `files.pythonhosted.org`. Mapping mode `replace` prevents
Pixi fetching the external Conda/PyPI name map. The explicit map also ensures
that Conda's `python-build` satisfies PyPI's `build` package.

Alternatively, if your site mirrors preserve upstream URL layouts, copy
`config/pixi-mirrors.example.toml` to `.pixi/config.toml` and edit every URL.
The two PyPI mirror entries are needed to redirect both index lookups and
artifact downloads. The manifest's name mappings already suppress external
mapping downloads for the canonical channels. A `[pypi-config] index-url` in
site configuration alone does **not** change an existing workspace's index:
set `[pypi-options] index-url` in the manifest instead.

Pixi documents these behaviors in its [configuration reference](https://pixi.prefix.dev/latest/reference/pixi_configuration/)
and [manifest reference](https://pixi.prefix.dev/latest/reference/pixi_manifest/).
Project `.pixi/config.toml` overrides lower-priority site settings; the
manifest's explicit channel/index choices define resolution inputs. Keep TLS
verification enabled and use your site's trusted CA configuration when needed.
Store authentication through Pixi's supported credential mechanisms, outside
tracked files.

## Solve and install inside the site

The manifest supplies compilers, CMake, Ninja, make, autoconf 2.69, compression
libraries, Python 3.11, scientific dependencies, and scikit-build-core. The
committed HTSlib sources build in a temporary writable directory. HDF5 is
optional and off by default. The local package uses the environment's build
requirements without build isolation, so its build performs no downloads.

A new checkout ships without a public lockfile. If a lockfile is transferred
from another site, move it aside before solving against your internal URLs:

```bash
# Only if a lockfile from another site is present:
mv pixi.lock pixi.lock.previous-site

pixi install
pixi run ornaments --help
pixi run test
pixi run example-workflow
```

Pixi solves all declared platforms. If your mirrors contain only the target
platform, reduce `[workspace] platforms` to `["linux-64"]` (or the deployed
macOS platform) before installation. Preserve the resulting site-specific
`pixi.lock`; subsequent installs can use `pixi install --locked`. Review its
channel and artifact URLs to confirm they point to the site's mirrors. With
mirror mappings, logical lock URLs may retain canonical upstream URLs, so keep
`.pixi/config.toml` with the deployment and verify mappings cover every host.

Mirrors must contain the versions matching the manifest constraints, including
compiler/sysroot packages. PyPI supplies gtfparse and any transitive requirements
not satisfied by the Conda environment. A missing artifact should be added to
the mirror rather than opening a public fallback.

## Build once and stage a wheel

For repeated deployments on the same compatible platform, build in the target
Conda environment:

```bash
pixi run build-package
```

This creates a platform wheel and source distribution under `dist/`. Stage the
wheel on the site's PyPI index or transfer it directly. A wheel is tied to its
OS, architecture, compatible libc/macOS baseline, Python environment layout,
and native compression/C++ runtime libraries. It is not a standalone binary
bundle: retain compatible Conda runtime dependencies. Wheels built on macOS
cannot run on Linux.

For a wheel-only deployment, keep Python and scientific/native runtime
requirements in the manifest, remove source build tools and the
`no-build-isolation` entry for ornaments, and replace the local path dependency
with the wheel path (relative to the manifest):

```toml
[pypi-dependencies]
gtfparse = ">=2.5,<3"
ornaments = { path = "artifacts/ornaments-1.1.0-cp311-cp311-linux_x86_64.whl" }
```

Use the actual generated filename. For macOS retain `libcxx`. For Linux retain `libstdcxx-ng` and
`libgcc-ng` at versions compatible with the build, along with zlib, bzip2, and
xz; macOS uses the platform C++ runtime. Keep site name mappings and index
configuration. Then `pixi install` installs the wheel without invoking a
compiler. A source distribution can instead be unpacked and installed through
the same source route; it includes the manifest and vendored HTSlib.

## Fully offline operation

An environment with reachable internal mirrors can resolve and install new
packages. A machine with no network at all needs the site lockfile and all
required Conda and PyPI artifacts in Pixi's cache ahead of time (or a transferred
complete environment). `pixi install --offline --locked` can only reuse artifacts
already available locally; mirrors alone do not populate a disconnected host.

## Validation record

Verified with Pixi 0.80.0 on macOS ARM64: all three manifest platforms resolve,
36 focused tests pass, and the complete bundled workflow passes, including
paired and single quantification, diploid generation, VCF paths containing
spaces, gzip VCFs, and transcript-start deletions. The wheel and source
distribution include the private engine, Python commands, vendored HTSlib
sources, and required licenses. The built wheel also passes the complete
workflow and every legacy helper help command in a separate runtime-only Pixi
environment outside the source checkout. The wheel is tagged for macOS 26 ARM64; use a
wheel built for your deployment platform instead.

The macOS build links system zlib/bzip2/lzma and the Conda C++ runtime. Linux
execution and installation against actual site mirrors have not been tested
in this session; the environment resolves for Linux but requires validation
on the target host.

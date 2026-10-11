#!/usr/bin/env bash
set -euo pipefail
# Build exclusively from local sources and preinstalled Conda build dependencies.
"${PYTHON}" -m pip install . --no-deps --no-build-isolation --no-index -vv

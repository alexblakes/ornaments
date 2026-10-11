#!/usr/bin/env python3
"""Compatibility entry point; prefer ornaments personalize."""
from pathlib import Path
import sys

if (Path(__file__).parent / "python" / "ornaments").is_dir():
    sys.path.insert(0, str(Path(__file__).parent / "python"))
from ornaments.cli import personalize_main

if __name__ == "__main__":
    raise SystemExit(personalize_main())

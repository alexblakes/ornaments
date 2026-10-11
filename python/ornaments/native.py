"""Invoke the engine shipped alongside the Python package."""
from pathlib import Path
import subprocess
import sys


def run(argv: list[str]) -> int:
    executable = Path(__file__).parent / "_bin" / "ornaments"
    if not executable.is_file():
        raise FileNotFoundError(f"Native engine is missing: {executable}; reinstall Ornaments")
    return subprocess.run([str(executable), *argv], check=False).returncode


def main() -> int:
    try:
        return run(sys.argv[1:])
    except OSError as error:
        print(f"ornaments-native: {error}", file=sys.stderr)
        return 1

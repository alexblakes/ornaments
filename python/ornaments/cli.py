"""Public CLI and backward-compatible helper entry points."""
import importlib
import sys
from . import __version__, native

PREPARATION = {name: f"ornaments.{name}" for name in ("convert", "merge", "sort", "personalize")}
NATIVE = {"index", "quant", "version", "cite", "inspect", "bus", "quant-only", "pseudo", "h5dump"}
HELP = """Usage: ornaments <command> [arguments]

Workflow commands:
  convert       Convert genomic variants to transcript coordinates
  merge         Merge transcriptomic VCFs for selected samples
  sort          Sort transcriptomic variants by transcript and position
  personalize   Generate an ornament or diploid transcriptome
  index         Build a native transcriptome index
  quant         Quantify expression and allele-specific read counts

Run ornaments <command> --help for command arguments.
Other native commands: version, cite, inspect, bus, quant-only, pseudo, h5dump.
Use ornaments-native merge for the original native abundance merge operation.
"""


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in {"-h", "--help", "help"}:
        print(HELP)
        return 0
    if args[0] == "--version":
        print(f"ornaments {__version__}")
        return 0
    command, rest = args[0], args[1:]
    try:
        if command in PREPARATION:
            return importlib.import_module(PREPARATION[command]).cli(rest)
        if command in NATIVE:
            # The original engine uses a command with no arguments to print help.
            return native.run([command] if rest in (["--help"], ["-h"]) else args)
        print(f"ornaments: unknown command {command!r}; use --help", file=sys.stderr)
        return 2
    except (OSError, ValueError) as error:
        print(f"ornaments {command}: {error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130


def convert_main() -> int:
    return main(["convert", *sys.argv[1:]])


def merge_main() -> int:
    return main(["merge", *sys.argv[1:]])


def sort_main() -> int:
    return main(["sort", *sys.argv[1:]])


def personalize_main() -> int:
    return main(["personalize", *sys.argv[1:]])

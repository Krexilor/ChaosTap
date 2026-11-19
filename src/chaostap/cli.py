# LIBRARIES ----------------------------------------------------------------------------------------------------------------------------------------|
import argparse
from collections.abc import Sequence

# PROJECT IMPORTS ----------------------------------------------------------------------------------------------------------------------------------|
from chaostap import __version__

# COMMAND LINE -------------------------------------------------------------------------------------------------------------------------------------|
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog = "chaostap",
        description = "Async network fault-injection and chaos proxy."
    )
    parser.add_argument("--version", action = "version", version = f"%(prog)s {__version__}")

    return parser

def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    parser.parse_args(argv)
    parser.print_help()

    return 0

from __future__ import annotations

import argparse
import sys
from importlib import metadata
from typing import Sequence

__version__ = metadata.version("hgtd_tools")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="hgtd-tools",
        description="Tools for the HGTD production database.",
    )
    p.add_argument("--version", action="version", version=f"hgtd-tools {__version__}")

    sub = p.add_subparsers(dest="command")

    # gui (default)
    gui = sub.add_parser("gui", help="Launch the graphical interface (default).")

    # check
    check = sub.add_parser(
        "check", help="Verify ProdDB API connectivity and tool version."
    )

    return p


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    # default to `gui` when the user just types `hgtd-tools`
    if argv is None:
        argv = sys.argv[1:]
    if not argv or argv[0] not in {"gui", "check", "-h", "--help", "--version"}:
        argv = ["gui", *argv]
    args = parser.parse_args(argv)

    if args.command == "gui":
        from hgtd_tools.app.gui import run_gui

        run_gui()
        return 0

    if args.command == "check":
        import hgtd_tools.api as api
        import hgtd_tools.util as util

        try:
            upstream, txt = api.get_version()
        except Exception as e:
            print(f"[ERROR] Could not reach version endpoint: {e}", file=sys.stderr)
            return 2
        print(f"hgtd-tools local version: {__version__}")
        print(f"hgtd-tools upstream version: {upstream} ({txt})")
        try:
            util.get_manufacturers()
            print("ProdDB API: OK")
            return 0
        except Exception as e:
            print(f"[ERROR] ProdDB API unreachable: {e}", file=sys.stderr)
            return 2

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

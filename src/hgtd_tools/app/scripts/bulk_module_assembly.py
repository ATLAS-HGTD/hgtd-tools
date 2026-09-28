# reorder-python-imports: skip-file
"""
Bulk module assembly.

a) Validate hierarchical part rules per parent_serial_number for
module assembly. Static analysis of csv file only, no requests.
b) Validate what is in the DB (GET) for each parent, and for each child.
c) For allowed new relations, execute POST.
d) For disallowed new relations, warn/report, let user take action (DELETE/POST).

Rules:
  0. A given HY/MF child can only be connected to one parent.
  1. Per parent: exactly one Module_flex, at empty position.
  2. Per parent: exactly two Hybrids, with positions {HV, LV} (order irrelevant).

Usage:
    python bulk_module_assembly.py -i module_children.csv
"""
from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict


REQUIRED_COLUMNS = (
    "parent_kind_of_part",
    "parent_serial_number",
    "child_kind_of_part",
    "child_serial_number",
    "position",
)


# ---------- I/O ----------


def load_hierarchy(csv_path: str) -> list[dict[str, str]]:
    """Read the CSV, normalise 'position' (empty/whitespace -> ''), check schema."""
    with open(csv_path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames is None:
            raise ValueError("CSV is empty or has no header row.")

        missing = [c for c in REQUIRED_COLUMNS if c not in reader.fieldnames]
        if missing:
            raise ValueError(f"CSV is missing required column(s): {missing}")

        rows = []
        for row in reader:
            rows.append(
                {
                    "parent_kind_of_part": (
                        row.get("parent_kind_of_part") or ""
                    ).strip(),
                    "parent_serial_number": (
                        row.get("parent_serial_number") or ""
                    ).strip(),
                    "child_kind_of_part": (row.get("child_kind_of_part") or "").strip(),
                    "child_serial_number": (
                        row.get("child_serial_number") or ""
                    ).strip(),
                    "position": (row.get("position") or "").strip(),
                }
            )

    if not rows:
        raise ValueError("CSV has a header but no data rows.")
    return rows


# ---------- Validation ----------


def validate(rows: list[dict[str, str]]) -> dict[str, list[str]]:
    """Return {parent_serial_number: [violation_messages]} for offenders only."""
    violations: dict[str, list[str]] = defaultdict(list)

    _check_global_uniqueness(rows, violations)

    by_parent: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_parent[row["parent_serial_number"]].append(row)

    for parent_sn in sorted(by_parent):
        group = by_parent[parent_sn]
        _check_module_flex(parent_sn, group, violations)
        _check_hybrids(parent_sn, group, violations)

    return {sn: msgs for sn, msgs in violations.items() if msgs}


def _check_global_uniqueness(
    rows: list[dict[str, str]], out: dict[str, list[str]]
) -> None:
    """Rule 0: every child_serial_number must be globally unique across all kinds."""
    first_seen: dict[str, dict[str, str]] = {}  # serial -> first row seen
    duplicates: dict[str, list[dict[str, str]]] = defaultdict(list)

    for row in rows:
        sn = row["child_serial_number"]
        if not sn:
            continue  # skip empty serials (noise, handled elsewhere if at all)
        if sn in first_seen:
            duplicates[sn].append(row)
        else:
            first_seen[sn] = row

    for sn, dup_rows in sorted(duplicates.items()):
        # Collect every parent this serial appears under (first sighting + dups).
        all_rows = [first_seen[sn]] + dup_rows
        parents = sorted({r["parent_serial_number"] for r in all_rows})
        kinds = sorted({r["child_kind_of_part"] for r in all_rows})
        msg = (
            f"duplicate child serial {sn} (kinds: {', '.join(kinds)}) "
            f"under parent(s): {', '.join(parents)}; "
            f"allowed: appears at most once."
        )
        for parent_sn in parents:
            out[parent_sn].append(msg)


def _check_module_flex(
    parent_sn: str, group: list[dict[str, str]], out: dict[str, list[str]]
) -> None:
    """Rule 1: exactly one Module_flex, at empty position."""
    flexes = [r for r in group if r["child_kind_of_part"] == "Module_flex"]
    n = len(flexes)

    if n == 0:
        out[parent_sn].append(
            "no Module_flex child; required: exactly 1 at empty position."
        )
    elif n > 1:
        sns = ", ".join(sorted(r["child_serial_number"] for r in flexes))
        out[parent_sn].append(
            f"{n} Module_flex children (serial numbers: {sns}); "
            f"required: exactly 1 at empty position."
        )
    else:  # n == 1
        if flexes[0]["position"] != "":
            out[parent_sn].append(
                f"single Module_flex child at position '{flexes[0]['position']}'; "
                f"required: empty position."
            )


def _check_hybrids(
    parent_sn: str, group: list[dict[str, str]], out: dict[str, list[str]]
) -> None:
    """Rule 2: exactly two Hybrids, with positions {HV, LV} (order irrelevant)."""
    hybrids = [r for r in group if r["child_kind_of_part"] == "Hybrid"]
    n = len(hybrids)

    if n < 2:
        sns = ", ".join(sorted(r["child_serial_number"] for r in hybrids)) or "<none>"
        out[parent_sn].append(
            f"{n} Hybrid children (serial numbers: {sns}); "
            f"required: exactly 2, at positions 'HV' and 'LV'."
        )
        return

    if n > 2:
        sns = ", ".join(sorted(r["child_serial_number"] for r in hybrids))
        out[parent_sn].append(
            f"{n} Hybrid children (serial numbers: {sns}); "
            f"required: exactly 2, at positions 'HV' and 'LV'."
        )
        return

    # n == 2: multiset of positions must be exactly {HV, LV}; row order is free.
    positions = [r["position"] for r in hybrids]
    if set(positions) != {"HV", "LV"}:
        out[parent_sn].append(
            f"two Hybrid children at positions {positions}; "
            f"required: 'HV' and 'LV'."
        )
    # n == 2 with positions == {"HV", "LV"} -> OK


# ---------- Reporting ----------


def report(violations: dict[str, list[str]], quiet: bool = False) -> int:
    """Print a summary. Returns 0 on success, 1 on failure (CI-friendly)."""
    if not violations:
        if not quiet:
            print("OK: every parent_serial_number satisfies the hierarchy rules.")
        return 0

    print(f"FAIL: {len(violations)} parent_serial_number(s) violate the rules:")
    for parent_sn, msgs in violations.items():
        for m in msgs:
            print(f"  - {parent_sn}: {m}")
    return 1


# ---------- CLI ----------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bulk_module_assembly",
        description=(
            "Validate a parent/child part hierarchy CSV against the Module_flex "
            "and Hybrid position rules."
        ),
    )
    parser.add_argument(
        "-i",
        "--input",
        dest="input_csv",
        help="explicit path to the input CSV",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="suppress the 'OK' message on success; always print on failure",
    )
    parser.add_argument(
        "--encoding",
        default="utf-8",
        help="file encoding (default: utf-8)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    csv_path = args.input_csv
    try:
        rows = load_hierarchy(csv_path)
    except (OSError, ValueError) as exc:
        print(f"ERROR: could not read '{csv_path}': {exc}", file=sys.stderr)
        return 2
    return report(validate(rows), quiet=args.quiet)


if __name__ == "__main__":
    sys.exit(main())

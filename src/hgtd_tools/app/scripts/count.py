#!/usr/bin/env python3
"""Count parts in the HGTD production database.

Queries ``util.get_relevant_parts`` for one (or all) Kind(s) of Part, narrows
the list with ``util.select_parts`` (the same filters the reporting CLIs use)
and reports how many parts are left, split into valid / invalid / fake SN
categories.

With ``--validate`` every part with a valid SN is additionally run through
``relation_validation``, so the output contains the same two numbers as the
nightly validation report: "valid SN" and "valid & correctly connected"
(plus "valid & new, not yet connected to a Hybrid" for sensors).

Kinds of Part come from ``data.all_cats``; the shortnames accepted by
``--location-shortname`` / ``--manu-shortname`` come from
``data.relevant_location_IDs_by_shortname`` and
``data.relevant_manufacturer_IDs_by_shortname``; ``--sites monitored`` uses the
per-mode site lists from ``data`` (``ML_sites_to_monitor`` etc.).

Examples
--------
    hgtd-count Module
    hgtd-count Module --validate --group-by manufacturer
    hgtd-count "Detector Unit" --sites monitored --validate
    hgtd-count Hybrid --sn-includes-any "20WHY 20WHM" --list valid
    hgtd-count ASIC --version-includes-any "ALTIROC A"
    hgtd-count ASIC --version-includes-any "ALTIROC A" --version-includes-any ALTIROCA
    hgtd-count --cats public --format md -o overview.md
"""

from __future__ import annotations

import csv
import io
import json
import sys
from argparse import ArgumentParser
from pathlib import Path

from hgtd_tools import data, parts_query
from hgtd_tools.parts_query import (
    CAT_SETS,
    LIST_TARGETS,
    VALIDATABLE,
    VALIDATION_CATEGORY,
    build_groups,
    build_listing,
    counts_for,
    display_filters,
)

RENDERERS = {}


# === Rendering


def _show_conn(rows):
    return any(r.get("validated") for r in rows)


def _show_new(rows):
    return any(r.get("sensor_mode") for r in rows)


def _header(rows):
    head = ["kind", "loaded", "filtered", "valid", "invalid", "fake"]
    if _show_conn(rows):
        head += ["connected", "not connected"]
    if _show_new(rows):
        head.append("new (no HY)")
    return head


def _table_cells(rows):
    """Header and body cells for a set of rows, guaranteed to match in width."""
    show_conn = any(r.get("validated") for r in rows)
    show_new = any(r.get("sensor_mode") for r in rows)

    header = ["kind", "loaded", "filtered", "valid", "invalid", "fake"]
    if show_conn:
        header += ["connected", "not connected"]
    if show_new:
        header.append("new (no HY)")

    cells = []
    for row in rows:
        if row.get("error"):
            cells.append([row["kind"], "ERR"] + ["-"] * (len(header) - 2))
            continue
        c = row["counts"]
        line = [row["kind"], row["loaded"], c["total"], c["valid"], c["invalid"], c["fake"]]
        if show_conn:
            line += [c["valid_connected"], c["valid_failed"]] if row["validated"] else ["-", "-"]
        if show_new:
            line.append(c["valid_new"] if row["sensor_mode"] else "-")
        cells.append(line)
    return header, cells


def _row_cells(row):
    if row.get("error"):
        return [row["kind"], "ERR"] + ["-"] * (len(_header([row])) - 2)
    c = row["counts"]
    cells = [row["kind"], row["loaded"], c["total"], c["valid"], c["invalid"], c["fake"]]
    if row["validated"]:
        cells += [c["valid_connected"], c["valid_failed"]]
    else:
        cells += ["-", "-"]
    cells.append(c["valid_new"] if row["sensor_mode"] else "-")
    return cells


def _trim(header, cells, keep=6):
    """Drop trailing columns that are '-' in every row."""
    width = len(cells[0]) if cells else len(header)
    while width > keep and all(r[width - 1] == "-" for r in cells):
        width -= 1
        cells = [r[:width] for r in cells]
    return header[:width], cells


def _group_table(report):
    """Header and cells for the per-group table.

    Groups are counted *after* filtering, so they have no "loaded" column. The
    dicts from build_groups carry no per-row flags either, so the shape of the
    table (which optional columns exist) is taken from the single main row.
    """
    row = report["rows"][0]

    header = ["group", "filtered", "valid", "invalid", "fake"]
    if row["validated"]:
        header += ["connected", "not connected"]
    if row["sensor_mode"]:
        header.append("new (no HY)")

    cells = []
    for g in report["groups"]:
        c = g["counts"]
        line = [g["group"], c["total"], c["valid"], c["invalid"], c["fake"]]
        if row["validated"]:
            line += [c["valid_connected"], c["valid_failed"]]
        if row["sensor_mode"]:
            line.append(c["valid_new"])
        cells.append(line)

    return _trim(header, cells, keep=5)


def _table(header, cells):
    widths = [max(len(str(r[i])) for r in [header] + cells) for i in range(len(header))]
    out = ["  ".join(str(v).ljust(w) for v, w in zip(header, widths)).rstrip()]
    out.append("  ".join("-" * w for w in widths))
    for row in cells:
        out.append("  ".join(str(v).ljust(w) for v, w in zip(row, widths)).rstrip())
    return out


def _context_lines(report):
    lines = []
    if report["sites"]:
        lines.append("Sites: " + ", ".join(report["sites"]))
    if report["filters"]:
        lines.append("Filters: " + ", ".join(f"{k}={v}" for k, v in report["filters"].items()))
    return lines


def _listing_lines(entries, title):
    if not entries:
        return []
    lines = ["", f"{title} ({len(entries)}):"]
    for e in entries:
        line = f"  {e['kind']}: {e['serial_number']} (part_id {e['part_id']})"
        if e.get("reasons"):
            line += " — " + "; ".join(e["reasons"])
        lines.append(line)
    return lines


def render_text(report):
    header, cells = _trim(*_table_cells(report["rows"]))
    lines = _context_lines(report)
    if lines:
        lines.append("")
    lines += _table(header, cells)

    if report["groups"]:
        g_header, g_cells = _group_table(report)
        lines.append("")
        lines += _table(g_header, g_cells)

    if report["listing"]:
        lines += _listing_lines(report["listing"], f"{report['list_target']} parts")
    return "\n".join(lines)


def render_md(report):
    rows = report["rows"]
    header, cells = _trim(_header(rows), [_row_cells(r) for r in rows])
    lines = ["# HGTD parts count", ""]
    for line in _context_lines(report):
        lines.append(line.replace("Filters: ", "Filters: "))
    if len(lines) > 2:
        lines.append("")

    lines.append("| " + " | ".join(header) + " |")
    lines.append("|" + "|".join(["---"] * len(header)) + "|")
    for row in cells:
        lines.append("| " + " | ".join(str(v) for v in row) + " |")

    if report["groups"]:
        g_header, g_cells = _group_table(report)
        lines.append("")
        lines.append("| " + " | ".join(g_header) + " |")
        lines.append("|" + "|".join(["---"] * len(g_header)) + "|")
        for cells in g_cells:
            lines.append("| " + " | ".join(str(v) for v in cells) + " |")

    if report["listing"]:
        lines += _listing_lines(report["listing"], f"{report['list_target']} parts")
    return "\n".join(lines)


def render_csv(report):
    header, cells = _trim(*_table_cells(report["rows"]))
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(header)
    writer.writerows(cells)
    return buf.getvalue().rstrip("\n")


def render_json(report):
    return json.dumps(report, indent=2)


RENDERERS.update({"text": render_text, "md": render_md, "csv": render_csv, "json": render_json})


# === CLI


def _add_filter_arguments(parser):
    parser.add_argument(
        "--location-shortname",
        default=None,
        metavar="NAME",
        choices=sorted(data.relevant_location_IDs_by_shortname),
    )
    parser.add_argument("--location-name", default=None, metavar="NAME")
    parser.add_argument("--location-id", default=None, metavar="ID")
    parser.add_argument(
        "--manu-shortname",
        default=None,
        metavar="NAME",
        choices=sorted(data.relevant_manufacturer_IDs_by_shortname),
    )
    parser.add_argument("--manu-name", default=None, metavar="NAME")
    parser.add_argument("--manu-id", default=None, metavar="ID")
    parser.add_argument(
        "--sites",
        default=None,
        metavar="LIST",
        help="Restrict to these manufacturer shortnames "
        "(comma-separated), or 'monitored' for the site list "
        "data.py defines for this kind's validation mode.",
    )
    parser.add_argument(
        "--sn-includes",
        default=None,
        metavar="TEXT",
        help="Keep parts whose SN contains TEXT (substring).",
    )
    parser.add_argument(
        "--sn-includes-any",
        default=None,
        metavar="TEXT",
        help="Keep parts whose SN contains any of these whitespace-separated substrings.",
    )
    parser.add_argument(
        "--sn-chars-9-10",
        dest="sn_chars_9_10",
        default=None,
        metavar="N",
        help="Keep parts whose SN characters 10-11 equal N.",
    )
    parser.add_argument(
        "--version-includes-any",
        action="append",
        default=None,
        metavar="TEXT",
        help="Keep parts whose 'version' contains any of these substrings. "
        "Repeat the flag for alternatives containing spaces, e.g. "
        "--version-includes-any 'ALTIROC A'. Values are taken "
        "verbatim: no whitespace or comma splitting.",
    )
    parser.add_argument(
        "--name-label-includes",
        default=None,
        metavar="TEXT",
        help="Case-insensitive substring filter on name_label.",
    )
    parser.add_argument(
        "--name-label-excludes",
        default=None,
        metavar="TEXT",
        help="Case-insensitive negative substring filter on name_label.",
    )
    parser.add_argument(
        "--no-parents-of-kind",
        default=None,
        metavar="KOP",
        help="Keep only parts without a parent of this Kind of Part (1 request per part).",
    )
    parser.add_argument(
        "--has-parents-of-kind",
        default=None,
        metavar="KOP",
        help="Keep only parts with a parent of this Kind of Part (1 request per part).",
    )
    parser.add_argument(
        "--no-children-of-kind",
        default=None,
        metavar="KOP",
        help="Keep only parts without a child of this Kind of Part (1 request per part).",
    )
    parser.add_argument(
        "--has-children-of-kind",
        default=None,
        metavar="KOP",
        help="Keep only parts with a child of this Kind of Part (1 request per part).",
    )


def build_parser():
    parser = ArgumentParser(
        prog="hgtd-count",
        description="Count parts in the HGTD production DB, optionally with relation "
        "validation. Without a Kind of Part all of data.all_cats is counted.",
    )
    parser.add_argument(
        "kind_of_part",
        nargs="?",
        default=None,
        help="Kind of Part from data.all_cats (e.g. 'Module', 'Hybrid', 'Sensor', "
        "'Detector Unit') or a validation mode alias ('Module Loading', "
        "'Module Assembly', 'Hybridization', 'Sensor_Parents'). "
        "Omit to count every kind in --cats.",
    )
    parser.add_argument(
        "--cats",
        choices=tuple(CAT_SETS),
        default="all",
        help="Which set of kinds to count when no Kind of Part is "
        "given (data.all_cats / data.public_cats / data.test_cats). "
        "Default: %(default)s",
    )
    _add_filter_arguments(parser)
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Also run relation validation on every valid part and report "
        "'valid & correctly connected'. The mode is derived from the "
        "Kind of Part; kinds without a mode are counted only.",
    )
    parser.add_argument(
        "--use-local",
        dest="use_local",
        action="store_true",
        help="For 'Slot', read the cached JSON from assets instead of the API.",
    )
    parser.add_argument(
        "--dev",
        type=int,
        default=None,
        metavar="N",
        help="Developer mode: only look at the first N parts after filtering.",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=4,
        metavar="N",
        help="Threads for the per-part API calls (Default: %(default)s)",
    )
    parser.add_argument(
        "--group-by",
        choices=("none", "manufacturer", "location"),
        default="none",
        help="Per-group breakdown (single Kind of Part only). Default: %(default)s",
    )
    parser.add_argument(
        "--list",
        dest="list_target",
        choices=LIST_TARGETS,
        default=None,
        help="Also list the SNs of the given category (single Kind of Part only).",
    )
    parser.add_argument(
        "--format",
        choices=tuple(RENDERERS),
        default=None,
        help="Output format (Default: inferred from --output suffix, else text)",
    )
    parser.add_argument(
        "--output",
        "-o",
        default=None,
        metavar="PATH",
        help="Write the report to this file instead of stdout.",
    )
    parser.add_argument(
        "--quiet", action="store_true", help="Suppress the info messages on stderr."
    )
    return parser


def build_filters(args):
    """Keyword arguments for util.select_parts (None values are no-ops)."""
    return {
        "location_shortname": args.location_shortname,
        "location_name": args.location_name,
        "location_id": args.location_id,
        "manu_shortname": args.manu_shortname,
        "manu_name": args.manu_name,
        "manu_id": args.manu_id,
        "sn_does_include": args.sn_includes,
        "sn_does_include_any": args.sn_includes_any,
        "sn_chars_9_to_10_eq": args.sn_chars_9_10,
        "version_does_include_any": args.version_includes_any,
        "name_label_does_include": args.name_label_includes,
        "name_label_does_not_include": args.name_label_excludes,
        "no_parents_ofKind": args.no_parents_of_kind,
        "no_children_ofKind": args.no_children_of_kind,
        "has_parents_ofKind": args.has_parents_of_kind,
        "has_children_ofKind": args.has_children_of_kind,
    }


def resolve_kinds(parser, value, cats):
    """Turn the positional argument (or --cats) into the list of kinds to count."""
    if value is None:
        missing = [c for c in CAT_SETS[cats] if c not in data.KoPID_from_partKoPName]
        if missing:
            parser.error(f"data.py lists kinds without a KoP ID: {', '.join(missing)}")
        return list(CAT_SETS[cats])
    if value in VALIDATION_CATEGORY:
        return [VALIDATION_CATEGORY[value]]
    if value not in data.KoPID_from_partKoPName:
        parser.error(
            f"unknown Kind of Part '{value}'. Valid: "
            + ", ".join(sorted(data.KoPID_from_partKoPName))
            + "; or a validation mode alias: "
            + ", ".join(sorted(VALIDATION_CATEGORY))
        )
    return [value]


def infer_format(args):
    if args.format:
        return args.format
    if args.output:
        suffix = Path(args.output).suffix.lower().lstrip(".")
        if suffix in RENDERERS:
            return suffix
    return "text"


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    kinds = resolve_kinds(parser, args.kind_of_part, args.cats)
    single = len(kinds) == 1

    if not single and args.group_by != "none":
        parser.error("--group-by needs a single Kind of Part")
    if not single and args.list_target:
        parser.error("--list needs a single Kind of Part")
    if not single and args.use_local:
        parser.error("--use-local needs a single Kind of Part")
    if args.sites and args.sites.strip().lower() in ("monitored", "default") and not single:
        parser.error("--sites monitored needs a single Kind of Part")
    if args.sites and args.sites.strip().lower() in ("monitored", "default"):
        if not single:
            parser.error("--sites monitored needs a single Kind of Part")
        if kinds[0] not in VALIDATABLE:
            parser.error(
                f"--sites monitored needs a Kind of Part with a validation mode "
                f"({', '.join(sorted(VALIDATABLE))}); '{kinds[0]}' has none. "
                "List the shortnames explicitly instead."
            )
    if args.validate and not single and not any(k in VALIDATABLE for k in kinds):
        parser.error(
            "--validate needs at least one Kind of Part with a relation validation: "
            + ", ".join(sorted(VALIDATABLE))
        )

    info = (lambda msg: None) if args.quiet else (lambda msg: print(msg, file=sys.stderr))
    filters = build_filters(args)

    rows, sites = [], None
    for kind in kinds:
        try:
            row = parts_query.summarize(
                kind,
                filters=filters,
                sites=args.sites,
                dev=args.dev,
                validate=args.validate,
                max_workers=args.max_workers,
                use_local=args.use_local,
                info=info,
            )
        except ValueError as exc:  # e.g. --sites monitored on a non-validatable kind
            parser.error(str(exc))
        except parts_query.API_ERRORS as exc:
            info(f"[error] {kind}: {exc}")
            row = {
                "kind": kind,
                "validation_mode": None,
                "validated": False,
                "sensor_mode": False,
                "loaded": 0,
                "sites": None,
                "counts": counts_for([], [], [], []),
                "parts": [],
                "valid": [],
                "invalid": [],
                "fake": [],
                "raw": {},
                "outcomes": {},
                "error": str(exc),
            }
        sites = sites or row.get("sites")
        rows.append(row)

    groups, listing = [], []
    if single:
        row = rows[0]
        if args.group_by != "none":
            groups = build_groups(
                row["parts"],
                row["valid"],
                row["invalid"],
                row["fake"],
                row["outcomes"],
                args.group_by,
                row["validated"],
            )
        if args.list_target:
            listing = build_listing(args.list_target, row)

    report = {
        "cats": args.cats if args.kind_of_part is None else None,
        "sites": sites,
        "filters": display_filters(filters),
        "rows": rows,
        "groups": groups,
        "list_target": args.list_target,
        "listing": listing,
    }

    text = RENDERERS[infer_format(args)](report)
    if args.output:
        path = Path(args.output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text + "\n", encoding="utf-8")
        print(f"Wrote {path}", file=sys.stderr)
    else:
        print(text)

    return 0 if not any(r.get("error") for r in rows) else 1


if __name__ == "__main__":
    sys.exit(main())

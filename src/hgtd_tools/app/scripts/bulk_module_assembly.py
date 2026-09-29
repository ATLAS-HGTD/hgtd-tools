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

DB rules (layered on top of the static rules):
  DB-Rule 0: every child (Hybrid or Module_flex) has zero existing parents.
  DB-Rule 1: every parent (Module) has zero existing Module_flex children
             (CSV adds exactly 1).
  DB-Rule 2: every parent (Module) has zero existing Hybrid children
             (CSV adds exactly 2).

CSV input is forgiving: kind names are canonicalised at load time, so
'Module_flex', 'module flex', 'Module-Flex' etc. all map to 'Module Flex'.

Upload is per-row: each allowed CSV row becomes its own POST. Rows whose
child already has a parent in the DB are skipped (and reported) rather
than blocking the run; rows whose parent is already fully wired also
produce diagnostics but the other (still-unwired) parents still upload.

Usage:
    python bulk_module_assembly.py -i module_children.csv -u <username>
    python bulk_module_assembly.py -i module_children.csv -u <username> \\
        --allow-malformed-sn            # static SN check is a warning only;
                                        # DB existence is still required.
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict

import requests

from hgtd_tools import api, util

REQUIRED_COLUMNS = (
    "parent_kind_of_part",
    "parent_serial_number",
    "child_kind_of_part",
    "child_serial_number",
    "position",
)


# ---------- I/O ----------


def _normalise_kind(kind: str) -> str:
    """Map user-typed kind names to the canonical DB kind names.

    Accepts any case, underscore or hyphen or space between tokens, e.g.
    'Module_flex', 'module flex', 'Module-Flex', 'MODULE_FLEX' all map
    to the canonical 'Module Flex'. Unknown kinds are returned stripped.
    """
    k = (kind or "").strip()
    if k.lower().replace("_", " ").replace("-", " ") == "module flex":
        return "Module Flex"
    return k


def load_hierarchy(csv_path: str) -> list[dict[str, str]]:
    """Read the CSV, normalise 'position' (empty/whitespace -> '') and
    canonicalise kind names (e.g. 'Module_flex' -> 'Module Flex'), check schema."""
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
                    "parent_kind_of_part": _normalise_kind(row.get("parent_kind_of_part")),
                    "parent_serial_number": (row.get("parent_serial_number") or "").strip(),
                    "child_kind_of_part": _normalise_kind(row.get("child_kind_of_part")),
                    "child_serial_number": (row.get("child_serial_number") or "").strip(),
                    "position": (row.get("position") or "").strip(),
                }
            )

    if not rows:
        raise ValueError("CSV has a header but no data rows.")
    return rows


# ---------- Missing-SN collection (DB existence check) ----------


def collect_missing_serials(
    rows: list[dict[str, str]],
    sn_to_module_id: dict[str, int],
    sn_to_flex_id: dict[str, int],
    sn_to_hybrid_id: dict[str, int],
) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """
    Return (missing_parents, missing_children), each a list of (serial, kind).

    A serial is "missing" if it appears in the CSV but is absent from the DB
    lookup tables. The CSV-existence pre-flight (SN format) is independent.
    """
    sn_to_id_by_kind = {
        "Module Flex": sn_to_flex_id,
        "Hybrid": sn_to_hybrid_id,
    }

    missing_parents: list[tuple[str, str]] = []
    missing_children: list[tuple[str, str]] = []

    seen_parent: set[str] = set()
    seen_child: set[tuple[str, str]] = set()

    for row in rows:
        pn, pk = row["parent_serial_number"], row["parent_kind_of_part"]
        cn, ck = row["child_serial_number"], row["child_kind_of_part"]

        if pn and pn not in seen_parent:
            seen_parent.add(pn)
            if sn_to_module_id.get(pn) is None:
                missing_parents.append((pn, pk or "<unspecified>"))

        if cn and (ck, cn) not in seen_child:
            seen_child.add((ck, cn))
            if ck in sn_to_id_by_kind and sn_to_id_by_kind[ck].get(cn) is None:
                missing_children.append((cn, ck))

    missing_parents.sort()
    missing_children.sort()
    return missing_parents, missing_children


# ---------- Static validation (offline) ----------


def validate(
    rows: list[dict[str, str]],
    allow_malformed_sn: bool = False,
) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    """
    Return (violations, sn_warnings).

    `violations` is the parent-keyed dict of rule violations that block the
    upload. `sn_warnings` carries SN-format issues: when
    `allow_malformed_sn` is True they go into `sn_warnings` instead of
    `violations`, so a malformed but DB-known SN can still proceed.
    """
    violations: dict[str, list[str]] = defaultdict(list)
    sn_warnings: dict[str, list[str]] = defaultdict(list)

    _check_global_uniqueness(rows, violations)

    sink = sn_warnings if allow_malformed_sn else violations
    _check_serials_valid(rows, sink)

    by_parent: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_parent[row["parent_serial_number"]].append(row)

    for parent_sn in sorted(by_parent):
        group = by_parent[parent_sn]
        _check_module_flex(parent_sn, group, violations)
        _check_hybrids(parent_sn, group, violations)

    return (
        {sn: msgs for sn, msgs in violations.items() if msgs},
        {sn: msgs for sn, msgs in sn_warnings.items() if msgs},
    )


def _check_global_uniqueness(rows: list[dict[str, str]], out: dict[str, list[str]]) -> None:
    """Rule 0 (offline): every child_serial_number must be globally unique."""
    first_seen: dict[str, dict[str, str]] = {}
    duplicates: dict[str, list[dict[str, str]]] = defaultdict(list)

    for row in rows:
        sn = row["child_serial_number"]
        if not sn:
            continue
        if sn in first_seen:
            duplicates[sn].append(row)
        else:
            first_seen[sn] = row

    for sn, dup_rows in sorted(duplicates.items()):
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


def _check_serials_valid(rows: list[dict[str, str]], out: dict[str, list[str]]) -> None:
    """
    SN pre-flight: every parent and child serial must satisfy the ATLAS
    convention. Messages are appended to `out` (which is either `violations`
    or `sn_warnings` depending on the CLI flag). Duplicate (role, sn) pairs
    are reported once per parent.
    """
    seen: dict[str, set[tuple[str, str]]] = defaultdict(set)
    for row in rows:
        parent_sn = row["parent_serial_number"]
        for role, sn in (
            ("parent", row["parent_serial_number"]),
            ("child", row["child_serial_number"]),
        ):
            key = (role, sn)
            if key in seen[parent_sn]:
                continue
            seen[parent_sn].add(key)
            if not sn:
                out[parent_sn].append(f"{role} serial number is empty.")
                continue
            ok, reason = util.check_SN_valid(sn)
            if not ok:
                out[parent_sn].append(f"{role} serial {sn} fails ATLAS SN validation: {reason}")


def _check_module_flex(
    parent_sn: str, group: list[dict[str, str]], out: dict[str, list[str]]
) -> None:
    """Rule 1: exactly one Module_flex, at empty position."""
    flexes = [r for r in group if r["child_kind_of_part"] == "Module Flex"]
    n = len(flexes)

    if n == 0:
        out[parent_sn].append("no Module_flex child; required: exactly 1 at empty position.")
    elif n > 1:
        sns = ", ".join(sorted(r["child_serial_number"] for r in flexes))
        out[parent_sn].append(
            f"{n} Module_flex children (serial numbers: {sns}); "
            f"required: exactly 1 at empty position."
        )
    else:
        if flexes[0]["position"] != "":
            out[parent_sn].append(
                f"single Module_flex child at position '{flexes[0]['position']}'; "
                f"required: empty position."
            )


def _check_hybrids(parent_sn: str, group: list[dict[str, str]], out: dict[str, list[str]]) -> None:
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

    positions = [r["position"] for r in hybrids]
    if set(positions) != {"HV", "LV"}:
        out[parent_sn].append(
            f"two Hybrid children at positions {positions}; required: 'HV' and 'LV'."
        )


# ---------- DB validation ----------


def validate_against_db(
    rows: list[dict[str, str]],
    missing_parents: list[tuple[str, str]],
    missing_children: list[tuple[str, str]],
) -> tuple[dict[str, list[str]], set[tuple[str, str]]]:
    """
    Return (parent_keyed_violations, blocked_children).

    `blocked_children` is the set of (kind, sn) pairs that already have a
    parent in the DB. These rows are skipped (not failed) at upload time;
    their parent SNs still appear in `violations` for diagnostic purposes.
    """
    violations: dict[str, list[str]] = defaultdict(list)

    modules, _ = util.get_relevant_parts("Module")
    flexes, _ = util.get_relevant_parts("Module Flex")
    hybrids, _ = util.get_relevant_parts("Hybrid")

    sn_to_module_id = {p["serial_number"]: p["part_id"] for p in modules}
    sn_to_flex_id = {p["serial_number"]: p["part_id"] for p in flexes}
    sn_to_hybrid_id = {p["serial_number"]: p["part_id"] for p in hybrids}

    missing_parent_sns = {sn for sn, _ in missing_parents}
    missing_child_sns = {(ck, cn) for cn, ck in missing_children}

    by_parent: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_parent[row["parent_serial_number"]].append(row)

    eligible_parents: list[tuple[str, int]] = []
    for parent_sn, group in by_parent.items():
        kind = group[0]["parent_kind_of_part"]
        if kind != "Module":
            violations[parent_sn].append(
                f"parent_kind_of_part '{kind}' for {parent_sn} is not 'Module'."
            )
            continue

        if parent_sn in missing_parent_sns:
            continue

        parent_id = sn_to_module_id.get(parent_sn)
        if parent_id is None:
            violations[parent_sn].append(f"parent serial {parent_sn} not found in DB as a Module.")
            continue
        eligible_parents.append((parent_sn, parent_id))

    parent_messages: dict[str, list[str]] = _db_check_parents_parallel(eligible_parents)
    child_messages, blocked_children = _db_check_children_parallel(
        rows, sn_to_flex_id, sn_to_hybrid_id, missing_child_sns
    )

    for parent_sn, msgs in parent_messages.items():
        violations[parent_sn].extend(msgs)
    for parent_sn, msgs in child_messages.items():
        violations[parent_sn].extend(msgs)

    return (
        {sn: msgs for sn, msgs in violations.items() if msgs},
        blocked_children,
    )


def _db_check_parents_parallel(
    eligible_parents: list[tuple[str, int]],
) -> dict[str, list[str]]:
    """DB-Rules 1 & 2: each Module parent has zero pre-existing children of those kinds."""

    def fn(payload: tuple[str, int]) -> tuple[bool, tuple[str, list[str]]]:
        parent_sn, parent_id = payload
        msgs: list[str] = []
        existing_flexes, _ = util.get_children(parent_id, ofKind="Module Flex")
        existing_hybrids, _ = util.get_children(parent_id, ofKind="Hybrid")

        if existing_flexes:
            sns = ", ".join(sorted(str(c["part"]["serial_number"]) for c in existing_flexes))
            msgs.append(
                f"parent {parent_sn} already has Module_flex child(ren) in DB "
                f"({sns}); CSV adds 1 more, exceeding 'exactly 1 Module_flex'."
            )

        if existing_hybrids:
            sns = ", ".join(sorted(str(c["part"]["serial_number"]) for c in existing_hybrids))
            msgs.append(
                f"parent {parent_sn} already has Hybrid child(ren) in DB "
                f"({sns}); CSV adds 2 more, exceeding 'exactly 2 Hybrids'."
            )

        return (not msgs, (parent_sn, msgs))

    _, rejected = util.parallel_partition(eligible_parents, fn, max_workers=4)
    out: dict[str, list[str]] = {}
    for parent_sn, msgs in rejected:
        out[parent_sn] = msgs
    return out


def _db_check_children_parallel(
    rows: list[dict[str, str]],
    sn_to_flex_id: dict[str, int],
    sn_to_hybrid_id: dict[str, int],
    missing_child_sns: set[tuple[str, str]],
) -> tuple[dict[str, list[str]], set[tuple[str, str]]]:
    """
    DB-Rule 0: every Hybrid/Module_flex child has zero existing parents.

    Returns (parent_keyed_messages, blocked_children). `blocked_children` is
    the set of (kind, sn) pairs that already have a parent in the DB; these
    rows are reported as 'already connected' but excluded from the upload,
    so other (still-unwired) parents can still proceed.
    """
    sn_to_id_by_kind = {
        "Module Flex": sn_to_flex_id,
        "Hybrid": sn_to_hybrid_id,
    }

    seen: dict[tuple[str, str], str] = {}
    for row in rows:
        kind = row["child_kind_of_part"]
        sn = row["child_serial_number"]
        seen.setdefault((kind, sn), row["parent_serial_number"])

    payloads: list[dict[str, object]] = []
    for (kind, sn), parent_sn in seen.items():
        if kind not in sn_to_id_by_kind:
            continue
        if (kind, sn) in missing_child_sns:
            continue
        payloads.append(
            {
                "part_id": sn_to_id_by_kind[kind].get(sn),
                "kind": kind,
                "child_sn": sn,
                "parent_sn": parent_sn,
            }
        )

    def fn(payload: dict[str, object]) -> tuple[bool, tuple[str, str, str]]:
        if payload["part_id"] is None:
            return False, (
                str(payload["parent_sn"]),
                "",
                f"child serial {payload['child_sn']} (kind {payload['kind']}) not found in DB.",
            )
        existing, _ = util.get_parents(payload["part_id"], onlyNonDeleted=True)
        if existing:
            p_sns = ", ".join(sorted(str(p["part_parent"]["serial_number"]) for p in existing))
            return False, (
                str(payload["parent_sn"]),
                f"{payload['kind']}|{payload['child_sn']}",
                f"child {payload['child_sn']} ({payload['kind']}) already "
                f"connected to parent(s) in DB ({p_sns}); "
                f"required: no existing parent.",
            )
        return True, ("", "", "")

    _, rejected = util.parallel_partition(payloads, fn, max_workers=4)
    out: dict[str, list[str]] = defaultdict(list)
    blocked_children: set[tuple[str, str]] = set()
    for parent_sn, blocked_key, msg in rejected:
        if blocked_key:
            kind, sn = blocked_key.split("|", 1)
            blocked_children.add((kind, sn))
        if msg:
            out[parent_sn].append(msg)
    return dict(out), blocked_children


# ---------- Upload ----------


def select_allowed_rows(
    rows: list[dict[str, str]],
    merged_violations: dict[str, list[str]],
    missing_parents: list[tuple[str, str]],
    missing_children: list[tuple[str, str]],
    blocked_children: set[tuple[str, str]] | None = None,
) -> list[dict[str, str]]:
    """
    Filter the CSV down to rows whose parent and child are both still
    available for a new POST. Rows whose child already has a parent in
    the DB (blocked_children) are skipped, not failed.
    """
    bad_parents = set(merged_violations.keys()) | {sn for sn, _ in missing_parents}
    bad_children = {(ck, cn) for cn, ck in missing_children}
    if blocked_children:
        bad_children |= blocked_children

    return [
        r
        for r in rows
        if r["parent_serial_number"] not in bad_parents
        and (r["child_kind_of_part"], r["child_serial_number"]) not in bad_children
    ]


def build_part_tree_payload(
    par_part_id: int,
    chi_part_id: int,
    position: str,
    user: str,
) -> dict:
    """One-row part_tree payload (a single dict, not wrapped in a list)."""
    return {
        "position": position,
        "is_record_deleted": "F",
        "part": chi_part_id,
        "part_parent": par_part_id,
        "record_insertion_user": user,
    }


def upload_relations(
    allowed_rows: list[dict[str, str]],
    sn_to_module_id: dict[str, int],
    sn_to_flex_id: dict[str, int],
    sn_to_hybrid_id: dict[str, int],
    user: str,
    access_token: str,
    dryrun: bool = False,
) -> dict[str, str]:
    """
    POST one /partstreelist payload per allowed CSV row.

    Each row becomes a single-entry payload; the response is keyed by a
    composite identifier 'parent_sn -> (kind, child_sn, position)' so a
    caller can tell exactly which row succeeded or failed.
    """
    sn_to_id_by_kind = {
        "Module Flex": sn_to_flex_id,
        "Hybrid": sn_to_hybrid_id,
    }

    responses: dict[str, str] = {}
    # Iterate in a deterministic order so logs and reports are reproducible.
    for row in sorted(
        allowed_rows,
        key=lambda r: (
            r["parent_serial_number"],
            r["child_kind_of_part"],
            r["child_serial_number"],
        ),
    ):
        parent_id = sn_to_module_id.get(row["parent_serial_number"])
        if parent_id is None:
            continue
        kind = row["child_kind_of_part"]
        child_id = sn_to_id_by_kind[kind].get(row["child_serial_number"])
        if child_id is None:
            continue

        payload = build_part_tree_payload(parent_id, child_id, row["position"], user)
        key = f"{row['parent_serial_number']} -> ({kind}, {row['child_serial_number']}, '{row['position']}')"
        responses[key] = api.post_information(
            "/partstreelist",
            payload,
            dryrun=dryrun,
            existing_token=access_token,
        )
    return responses


# ---------- Reporting ----------


def report(
    violations: dict[str, list[str]],
    sn_warnings: dict[str, list[str]],
    missing_parents: list[tuple[str, str]],
    missing_children: list[tuple[str, str]],
    upload_responses: dict[str, str] | None = None,
    blocked_children: set[tuple[str, str]] | None = None,
    quiet: bool = False,
) -> int:
    """Print a summary. Returns 0 on success, 1 on failure (CI-friendly)."""
    if missing_parents or missing_children:
        if missing_parents:
            print(
                f"NOTE: {len(missing_parents)} parent serial(s) in the CSV "
                f"were not found in the DB; related rows are blocked:"
            )
            for sn, kind in missing_parents:
                print(f"  - {sn} (kind: {kind})")
        if missing_children:
            print(
                f"NOTE: {len(missing_children)} child serial(s) in the CSV "
                f"were not found in the DB; related rows are blocked:"
            )
            for sn, kind in missing_children:
                print(f"  - {sn} (kind: {kind})")

    if sn_warnings:
        print(
            f"WARN: {len(sn_warnings)} parent_serial_number(s) or their children "
            "have malformed SNs but the corresponding parts exist in the DB; "
            "proceeding because you set allow-malformed-sn:"
        )
        for parent_sn, msgs in sn_warnings.items():
            for m in sorted(msgs):
                print(f"  - {parent_sn}: {m}")

    if blocked_children and not quiet:
        print(
            f"NOTE: {len(blocked_children)} child serial(s) already have a "
            f"parent in the DB and were skipped (not re-uploaded):"
        )
        for kind, sn in sorted(blocked_children):
            print(f"  - ({kind}, {sn})")

    # Always report upload results *before* the pass/fail decision, so
    # partial successes (some parents violated, others uploaded cleanly)
    # are visible alongside the FAIL diagnostics.
    if upload_responses and not quiet:
        if violations:
            print(
                f"OK: {len(upload_responses)} allowed row(s) were uploaded "
                f"(partial success; {len(violations)} parent_serial_number(s) "
                f"still have violations outlined below in FAIL block):"
            )
        else:
            print(f"OK: every allowed row was uploaded ({len(upload_responses)} row(s)):")
        for key, resp in upload_responses.items():
            if resp is None:
                body = "(dry-run, no POST issued)"
            elif str(resp) == "201, Created":
                body = "Successfully created relation"
            else:
                body = str(resp)
            print(f"  - {key}: {body}")

    if not violations:
        if missing_parents or missing_children:
            print("FAIL: rows associated with the missing serials above are blocked from upload.")
            return 1
        if not quiet and not upload_responses:
            print("OK: every parent_serial_number satisfies the hierarchy rules (offline + DB).")
        return 0

    print(f"FAIL: {len(violations)} parent_serial_number(s) violate the rules:")
    for parent_sn, msgs in violations.items():
        for m in msgs:
            print(f"  - {parent_sn}: {m}")
    print(
        "Correct mistakes in input csv file and/or interactively change existing relations in hgtd-tools gui"
    )
    return 1


# ---------- CLI ----------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bulk_module_assembly",
        description=(
            "Validate a parent/child part hierarchy CSV against the Module_flex "
            "and Hybrid position rules, both offline and against the DB, and "
            "POST the allowed relations. Per-row partial success is supported: "
            "rows whose child already has a parent in the DB are skipped (and "
            "reported) so other (still-unwired) parents can still proceed."
        ),
    )
    parser.add_argument(
        "-i",
        "--input",
        dest="input_csv",
        required=True,
        help="explicit path to the input CSV",
    )
    parser.add_argument(
        "-u",
        "--user-name",
        dest="userName",
        required=True,
        help="Your CERN user name.",
    )
    parser.add_argument(
        "--local-folder",
        dest="localFolder",
        default=None,
        help=(
            "Path to the folder that will hold temporary DB data for uploading, "
            "including a token for the user. If not given, hgtd-tools uses "
            "~/.hgtd_tools/local_info (creating it if needed), falling back to "
            "./local_info in the current working directory."
        ),
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
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="validate and build payloads but do not POST to the DB",
    )
    parser.add_argument(
        "--skip-upload",
        action="store_true",
        help="validate only; never POST even if all checks pass",
    )
    parser.add_argument(
        "--allow-malformed-sn",
        action="store_true",
        help=(
            "treat ATLAS SN-format failures as warnings (not blockers) when "
            "the part is registered in the DB; DB existence is still required."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    username, local_folder = args.userName, args.localFolder
    csv_path = args.input_csv

    if local_folder is not None:
        api.set_local_folder(local_folder)
    local_folder = api.resolve_local_folder()
    api.user_auth_cli(username, local_folder)
    access_token = api.get_access_token()

    try:
        rows = load_hierarchy(csv_path)
    except (OSError, ValueError) as exc:
        print(f"ERROR: could not read '{csv_path}': {exc}", file=sys.stderr)
        return 2

    # 1) Internally consistent CSV (rules 0, 1, 2 + SN pre-flight).
    offline_violations, sn_warnings = validate(rows, allow_malformed_sn=args.allow_malformed_sn)

    # 2) Resolve all SN -> part_id once; reuse for missing-SN detection + DB rules.
    try:
        modules, _ = util.get_relevant_parts("Module")
        flexes, _ = util.get_relevant_parts("Module Flex")
        hybrids, _ = util.get_relevant_parts("Hybrid")
    except (
        requests.exceptions.HTTPError,
        requests.exceptions.ConnectionError,
        requests.exceptions.Timeout,
        requests.exceptions.RequestException,
        RuntimeError,
        ValueError,
    ) as exc:
        print(f"ERROR: DB lookup failed: {exc}", file=sys.stderr)
        return 3

    sn_to_module_id = {p["serial_number"]: p["part_id"] for p in modules}
    sn_to_flex_id = {p["serial_number"]: p["part_id"] for p in flexes}
    sn_to_hybrid_id = {p["serial_number"]: p["part_id"] for p in hybrids}

    # 3) Missing-SN pre-flight: serials in CSV but absent from DB.
    missing_parents, missing_children = collect_missing_serials(
        rows, sn_to_module_id, sn_to_flex_id, sn_to_hybrid_id
    )

    # 4) DB-Rules 0, 1, 2 (skips missing SNs). blocked_children captures
    #    rows that are already wired in the DB and must be skipped at
    #    upload time but should not block other (still-unwired) parents.
    db_violations, blocked_children = validate_against_db(rows, missing_parents, missing_children)

    # 5) Merge: offline + DB.
    merged: dict[str, list[str]] = defaultdict(list)
    for sn, msgs in offline_violations.items():
        merged[sn].extend(msgs)
    for sn, msgs in db_violations.items():
        merged[sn].extend(msgs)

    violations = {sn: msgs for sn, msgs in merged.items() if msgs}

    # 6) Determine whether to upload. Upload runs whenever at least one row
    #    survives the per-row filter (clean parent, clean child, child not
    #    already wired). The presence of violations elsewhere in the CSV is
    #    still reported but does NOT block the surviving rows.
    has_blockers = bool(missing_parents) or bool(missing_children)

    upload_responses: dict[str, str] | None = None
    if not has_blockers and not args.skip_upload:
        allowed_rows = select_allowed_rows(
            rows,
            violations,
            missing_parents,
            missing_children,
            blocked_children=blocked_children,
        )
        if allowed_rows:
            try:
                upload_responses = upload_relations(
                    allowed_rows,
                    sn_to_module_id,
                    sn_to_flex_id,
                    sn_to_hybrid_id,
                    username,
                    access_token,
                    dryrun=args.dry_run,
                )
            except (
                requests.exceptions.HTTPError,
                requests.exceptions.ConnectionError,
                requests.exceptions.Timeout,
                requests.exceptions.RequestException,
                RuntimeError,
            ) as exc:
                print(f"ERROR: upload failed: {exc}", file=sys.stderr)
                return 4

    return report(
        violations,
        sn_warnings,
        missing_parents,
        missing_children,
        upload_responses=upload_responses,
        blocked_children=blocked_children,
        quiet=args.quiet,
    )


if __name__ == "__main__":
    sys.exit(main())

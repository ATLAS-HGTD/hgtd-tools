"""
Bulk module assembly.

a) Validate hierarchical part rules per parent_serial_number for
module assembly. Static analysis of csv file only, no requests.
b) Validate what is in the DB (GET) for each parent, and for each child.
c) For allowed new relations, execute POST.
d) For disallowed new relations, warn/report, let user take action.

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

Usage:
    python bulk_module_assembly.py -i module_children.csv -u <username>
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


# ---------- Missing-SN collection (DB existence check) ----------


def collect_missing_serials(
    rows: list[dict[str, str]],
    sn_to_module_id: dict[str, int],
    sn_to_flex_id: dict[str, int],
    sn_to_hybrid_id: dict[str, int],
) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """
    Return (missing_parents, missing_children), each a list of (serial, kind).

    A serial is "missing" if it is well-formed (SN pre-flight) and appears
    in the CSV but is absent from the DB lookup tables. Missing parents and
    missing children both block the corresponding upload rows.
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


def validate(rows: list[dict[str, str]]) -> dict[str, list[str]]:
    """Return {parent_serial_number: [violation_messages]} for offenders only."""
    violations: dict[str, list[str]] = defaultdict(list)

    _check_global_uniqueness(rows, violations)
    _check_serials_valid(rows, violations)

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
    """SN pre-flight: every parent and child serial must satisfy the ATLAS convention."""
    for row in rows:
        for role, sn in (
            ("parent", row["parent_serial_number"]),
            ("child", row["child_serial_number"]),
        ):
            if not sn:
                out[row["parent_serial_number"]].append(
                    f"{role} serial number is empty."
                )
                continue
            ok, reason = util.check_SN_valid(sn)
            if not ok:
                out[row["parent_serial_number"]].append(
                    f"{role} serial {sn} fails ATLAS SN validation: {reason}"
                )


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
    else:
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
) -> dict[str, list[str]]:
    """Return {parent_serial_number: [violation_messages]} for offenders only."""
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
            violations[parent_sn].append(
                f"parent serial {parent_sn} not found in DB as a Module."
            )
            continue
        eligible_parents.append((parent_sn, parent_id))

    parent_messages: dict[str, list[str]] = _db_check_parents_parallel(eligible_parents)
    child_messages: dict[str, list[str]] = _db_check_children_parallel(
        rows, sn_to_flex_id, sn_to_hybrid_id, missing_child_sns
    )

    for parent_sn, msgs in parent_messages.items():
        violations[parent_sn].extend(msgs)
    for parent_sn, msgs in child_messages.items():
        violations[parent_sn].extend(msgs)

    return {sn: msgs for sn, msgs in violations.items() if msgs}


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
            sns = ", ".join(
                sorted(str(c["part"]["serial_number"]) for c in existing_flexes)
            )
            msgs.append(
                f"parent {parent_sn} already has Module_flex child(ren) in DB "
                f"({sns}); CSV adds 1 more, exceeding 'exactly 1 Module_flex'."
            )

        if existing_hybrids:
            sns = ", ".join(
                sorted(str(c["part"]["serial_number"]) for c in existing_hybrids)
            )
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
) -> dict[str, list[str]]:
    """DB-Rule 0: every Hybrid/Module_flex child has zero existing parents."""

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

    def fn(payload: dict[str, object]) -> tuple[bool, tuple[str, str]]:
        if payload["part_id"] is None:
            return False, (
                str(payload["parent_sn"]),
                (
                    f"child serial {payload['child_sn']} "
                    f"(kind {payload['kind']}) not found in DB."
                ),
            )
        existing, _ = util.get_parents(payload["part_id"], onlyNonDeleted=True)
        if existing:
            p_sns = ", ".join(
                sorted(str(p["part_parent"]["serial_number"]) for p in existing)
            )
            return False, (
                str(payload["parent_sn"]),
                (
                    f"child {payload['child_sn']} ({payload['kind']}) already "
                    f"connected to parent(s) in DB ({p_sns}); "
                    f"required: no existing parent."
                ),
            )
        return True, ("", "")

    _, rejected = util.parallel_partition(payloads, fn, max_workers=4)
    out: dict[str, list[str]] = defaultdict(list)
    for parent_sn, msg in rejected:
        if msg:
            out[parent_sn].append(msg)
    return dict(out)


# ---------- Upload ----------


def select_allowed_rows(
    rows: list[dict[str, str]],
    merged_violations: dict[str, list[str]],
    missing_parents: list[tuple[str, str]],
    missing_children: list[tuple[str, str]],
) -> list[dict[str, str]]:
    """Filter the CSV down to rows whose parent SN is clean."""
    bad_parents = set(merged_violations.keys()) | {sn for sn, _ in missing_parents}
    bad_children = {(ck, cn) for cn, ck in missing_children}

    return [
        r
        for r in rows
        if r["parent_serial_number"] not in bad_parents
        and (r["child_kind_of_part"], r["child_serial_number"]) not in bad_children
    ]


def build_part_tree_entry(
    par_part_id: int,
    chi_part_id: int,
    position: str,
    user: str,
) -> dict:
    """
    Build a single part_tree entry matching the production DB schema:

        {
            "position": pos,
            "is_record_deleted": "F",
            "part": chi_partID,
            "part_parent": par_partID,
            "record_insertion_user": self.user,
        }
    """
    return {
        "position": position,
        "is_record_deleted": "F",
        "part": chi_part_id,
        "part_parent": par_part_id,
        "record_insertion_user": user,
    }


def build_part_tree_payload_for_parent(
    parent_sn: str,
    parent_id: int,
    children: list[tuple[int, str]],
    user: str,
) -> list[dict]:
    """
    Build the list of part_tree entries for one parent, POSTed as one body
    to `/partstreelist`.
    """
    return [
        build_part_tree_entry(parent_id, child_id, position, user)
        for child_id, position in children
    ]


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
    Group `allowed_rows` by parent and POST one payload per parent.

    Each payload is a list of part_tree entries (one per child), matching
    the production DB schema for `POST /partstreelist`.
    """
    sn_to_id_by_kind = {
        "Module Flex": sn_to_flex_id,
        "Hybrid": sn_to_hybrid_id,
    }

    by_parent: dict[str, list[tuple[int, str]]] = defaultdict(list)
    for row in allowed_rows:
        parent_id = sn_to_module_id.get(row["parent_serial_number"])
        if parent_id is None:
            continue
        kind = row["child_kind_of_part"]
        child_id = sn_to_id_by_kind[kind].get(row["child_serial_number"])
        if child_id is None:
            continue
        by_parent[row["parent_serial_number"]].append((child_id, row["position"]))

    responses: dict[str, str] = {}
    for parent_sn in sorted(by_parent):
        parent_id = sn_to_module_id[parent_sn]
        payload = build_part_tree_payload_for_parent(
            parent_sn, parent_id, by_parent[parent_sn], user
        )
        responses[parent_sn] = api.post_information(
            "/partstreelist",
            payload,
            dryrun=dryrun,
            existing_token=access_token,
        )
    return responses


# ---------- Reporting ----------


def report(
    violations: dict[str, list[str]],
    missing_parents: list[tuple[str, str]],
    missing_children: list[tuple[str, str]],
    upload_responses: dict[str, str] | None = None,
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

    if not violations:
        if missing_parents or missing_children:
            print(
                "FAIL: rows associated with the missing serials above are "
                "blocked from upload."
            )
            return 1
        if upload_responses and not quiet:
            print(
                f"OK: every parent_serial_number satisfies the hierarchy "
                f"rules; uploaded {len(upload_responses)} parent tree(s):"
            )
            for parent_sn, resp in upload_responses.items():
                print(f"  - {parent_sn}: {resp}")
        elif not quiet:
            print(
                "OK: every parent_serial_number satisfies the hierarchy rules "
                "(offline + DB)."
            )
        return 0

    print(f"FAIL: {len(violations)} parent_serial_number(s) violate the rules:")
    for parent_sn, msgs in violations.items():
        for m in msgs:
            print(f"  - {parent_sn}: {m}")
    print(
        "Please correct your input csv or modify the existing relations interactively (hgtd-tools gui)."
    )
    return 1


# ---------- CLI ----------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bulk_module_assembly",
        description=(
            "Validate a parent/child part hierarchy CSV against the Module_flex "
            "and Hybrid position rules, both offline and against the DB, and "
            "POST the allowed relations."
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

    offline_violations = validate(rows)

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

    missing_parents, missing_children = collect_missing_serials(
        rows, sn_to_module_id, sn_to_flex_id, sn_to_hybrid_id
    )

    db_violations = validate_against_db(rows, missing_parents, missing_children)

    merged: dict[str, list[str]] = defaultdict(list)
    for sn, msgs in offline_violations.items():
        merged[sn].extend(msgs)
    for sn, msgs in db_violations.items():
        merged[sn].extend(msgs)

    violations = {sn: msgs for sn, msgs in merged.items() if msgs}

    has_blockers = bool(violations) or bool(missing_parents) or bool(missing_children)

    upload_responses: dict[str, str] | None = None
    if not has_blockers and not args.skip_upload:
        allowed_rows = select_allowed_rows(
            rows, violations, missing_parents, missing_children
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
        missing_parents,
        missing_children,
        upload_responses=upload_responses,
        quiet=args.quiet,
    )


if __name__ == "__main__":
    sys.exit(main())

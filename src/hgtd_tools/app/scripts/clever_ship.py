#!/usr/bin/env python3
"""Prepare or send an HGTD shipment for one or more part subtrees.

Each root can be given as a part_id or as a serial number plus the kind of part
it belongs to; several roots may be combined, comma-separated, and are
deduplicated (a part reachable from two roots is shipped once).

By default the shipment contains each root itself plus every recursive child.
Pass --no-children to ship only the roots, and --without-parent to leave the
roots off while keeping their descendants.

Each shipment item's comment is taken automatically from the part's
comment_description; it is never typed by hand. Parts whose record lacks the
field are completed from /part/{id}/ unless --no-fetch-part-comments is given.

The shipment is POSTed to the ProdDB unless --dry-run is passed, in which case
the payload is printed and nothing is written. A shipment cannot be created as
Received — use receive-shipment for that, which is what moves the parts.

Examples:
    # dry run, default scope: root + all descendants
    clever-ship 28833 -u anstein --from ihep --to ijclab --company dhl --dry-run
    clever-ship 28816 -u anstein --from mainz --to test --company ups --dry-run

    # two roots, comma-separated, descendants only
    clever-ship 28833,28834 -u anstein --without-parent \\
        --from cern --to ihep --company dhl --list --dry-run

    # several serial numbers of the same kind
    clever-ship --sn 20WMO...01,20WMO...02 --kind Module -u anstein \\
        --from ihep --to ijclab --company dhl --dry-run

    # single part, nothing else
    clever-ship 28833 -u anstein --no-children --from mainz --to test \\
        --company ups --dry-run

    # actually POST it
    clever-ship 28833,28834 -u anstein --from ihep --to ijclab --company dhl \\
        --tracking-number trkDHL08193 --date 2026-11-07

Exit codes: 0 success, 1 runtime/API failure, 2 bad usage.
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from hgtd_tools import api, data, util

AUTO_TRACKING_PREFIX = "auto"


def _split_csv(text):
    """'a, b,,c' -> ['a', 'b', 'c'] — tolerates spaces and stray commas."""
    return [tok.strip() for tok in str(text).split(",") if tok.strip()]


def _parse_part_ids(values, parser):
    """Flatten nargs='*' positional values, each possibly comma-separated."""
    ids = []
    for chunk in values:
        for tok in _split_csv(chunk):
            try:
                ids.append(int(tok))
            except ValueError:
                parser.error(
                    f"invalid part_id '{tok}' (expected comma-separated integers, e.g. 28833,28834)"
                )
    return ids


def _parse_sns(value, parser):
    """Split --sn into a list of serial numbers; [] when the flag is absent."""
    if value is None:
        return []
    sns = _split_csv(value)
    if not sns:
        parser.error("--sn was given but contains no serial numbers")
    return sns


def build_parser():
    p = argparse.ArgumentParser(
        prog="clever-ship",
        description="Prepare or send an HGTD shipment for a part tree.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__.split("Examples:", 1)[1].strip(),
    )

    root = p.add_argument_group("root selection")
    root.add_argument(
        "roots",
        nargs="*",
        default=[],
        metavar="PART_ID[,PART_ID...]",
        help="root part_id(s), comma-separated (e.g. 28833,28834); may be combined with --sn",
    )
    root.add_argument(
        "--sn",
        default=None,
        metavar="SN[,SN...]",
        help="root serial number(s), comma-separated (e.g. 20WMO...01,20WMO...02); requires --kind",
    )
    root.add_argument(
        "--kind",
        default=None,
        metavar="KoP",
        help='kind of part the --sn roots belong to (e.g. "Detector"); '
        "applies to every SN and is used only to resolve the part_ids",
    )

    scope = p.add_argument_group("shipment scope")
    scope.add_argument(
        "--no-children",
        dest="children",
        action="store_false",
        help="ship only the part itself, without its recursive children "
        "(default: include all children)",
    )
    scope.add_argument(
        "--without-parent",
        dest="include_root",
        action="store_false",
        help="leave the root part off the shipment and only ship its "
        "descendants (default: include the root)",
    )
    scope.add_argument(
        "--child-kind",
        default="all",
        metavar="KoP",
        help="only follow children of this kind (default: all — unrelated to --kind)",
    )
    scope.add_argument(
        "--max-depth",
        type=int,
        default=None,
        metavar="N",
        help="stop N levels below the root (default: unlimited)",
    )

    ship = p.add_argument_group("shipment fields")
    ship.add_argument(
        "--from",
        dest="from_location",
        required=True,
        metavar="LOC",
        help="origin: shortname (ihep, ijclab, cern, ...), location_id or location_name",
    )
    ship.add_argument(
        "--to",
        dest="to_location",
        required=True,
        metavar="LOC",
        help="destination: shortname, location_id or location_name",
    )
    ship.add_argument(
        "--company",
        required=True,
        metavar="COMPANY",
        help="shipment company: company_id or name (dhl, ups)",
    )
    ship.add_argument(
        "--tracking-number",
        default=None,
        metavar="TEXT",
        help="tracking number; generated if omitted. Must be "
        "unique: util.create_shipment reads the record back "
        "by this value.",
    )
    ship.add_argument(
        "--date",
        dest="shipment_date",
        default=None,
        metavar="YYYY-MM-DD",
        help="shipment date (default: today)",
    )
    ship.add_argument(
        "--status",
        default="Created",
        choices=data.SHIPMENT_STATUSES,
        help="shipment status at creation: Created, Shipped or Cancel "
        "(Received is refused — use receive-shipment, which is what "
        "moves the parts to the destination).",
    )
    ship.add_argument("--edh-link", default=None, metavar="URL", help="EDH link")
    ship.add_argument(
        "--no-fetch-part-comments",
        dest="fetch_part_comments",
        action="store_false",
        help="do not fetch /part/{id}/ for parts whose record lacks "
        "comment_description; their items get an empty comment "
        "(default: fetch)",
    )
    ship.add_argument("--from-contact", default=None, metavar="NAME")
    ship.add_argument("--from-contact-email", default=None, metavar="EMAIL")
    ship.add_argument("--to-contact", default=None, metavar="NAME")
    ship.add_argument("--to-contact-email", default=None, metavar="EMAIL")

    out = p.add_argument_group("output")
    out.add_argument(
        "--list",
        dest="list_parts",
        action="store_true",
        help="list the parts that would be shipped (to stderr)",
    )
    out.add_argument(
        "--list-file",
        default=None,
        metavar="PATH",
        help="write the part list to PATH (SN and part_id per line)",
    )
    out.add_argument(
        "--payload-file", default=None, metavar="PATH", help="write the JSON payload to PATH"
    )
    out.add_argument(
        "--dry-run",
        action="store_true",
        help="do everything except the POST: print the payload and "
        "exit (default: POST the shipment)",
    )
    p.add_argument("--quiet", action="store_true", help="suppress the summary on stderr")

    auth = p.add_argument_group("authentication")
    auth.add_argument(
        "-u",
        "--user-name",
        dest="user_name",
        required=True,
        help="Your CERN user name (used for authentication).",
    )
    auth.add_argument(
        "--local-folder",
        dest="local_folder",
        default=None,
        help="Path holding temporary DB data and the cached token. "
        "Default: ~/.hgtd_tools/local_info, falling back to "
        "./local_info in the current working directory.",
    )
    return p


# --- resolution helpers


def _resolve_location(value):
    """Location dict for a shortname, a location_id, or a location_name.

    Shortnames come from data.relevant_location_IDs_by_shortname (ihep,
    ijclab, cern, ...) and are matched case-insensitively, so "IHEP" and
    "ihep" are the same. Numeric values are treated as location_ids, anything
    else as an exact location_name.
    """
    text = str(value).strip()
    if not text:
        raise RuntimeError("empty location given")

    shortnames = data.relevant_location_IDs_by_shortname
    cache = {}

    def _locations():
        if "all" not in cache:
            cache["all"], _ = util.get_locations()
        return cache["all"]

    def _by_id(loc_id):
        for loc in _locations():
            if int(loc["location_id"]) == int(loc_id):
                return loc
        return None

    key = text.lower()

    # 1. shortname
    if key in shortnames:
        loc = _by_id(shortnames[key])
        if loc is None:
            raise RuntimeError(
                f"shortname '{value}' maps to location_id "
                f"{shortnames[key]}, which the ProdDB does not return"
            )
        return loc

    # 2. numeric id
    if text.isdigit():
        loc = _by_id(int(text))
        if loc is None:
            raise RuntimeError(f"no location with location_id {text}")
        return loc

    # 3. exact name, case-insensitive
    matches = [loc for loc in _locations() if str(loc.get("location_name", "")).lower() == key]
    if len(matches) == 1:
        return matches[0]
    if not matches:
        known = ", ".join(sorted(shortnames))
        raise RuntimeError(
            f"no location '{value}'; known shortnames: {known} "
            "(a location_id or exact location_name also works)"
        )
    raise RuntimeError(
        f"location '{value}' is ambiguous: ids {[int(m['location_id']) for m in matches]}"
    )


def _resolve_company(value, allow_offline_fallback=True):
    """Company id for a company_id or a name (case-insensitive).

    Companies come from the ProdDB via util.get_shipment_companies()
    (/shipmentcomany — the route is misspelled server-side). If that request
    fails, data.SHIPMENT_COMPANIES is used as a documented fallback and a
    warning is printed, so an endpoint problem degrades instead of aborting.
    """
    text = str(value).strip()

    pairs = None
    source = "ProdDB"
    getter = getattr(util, "get_shipment_companies", None)
    if getter is not None:
        try:
            companies, _ = getter()
            pairs = [
                (int(c["company_id"]), str(c.get("name", "")))
                for c in companies
                if str(c.get("is_record_deleted", "F")) == "F"
            ]
        except Exception as e:
            if not allow_offline_fallback:
                raise
            print(
                f"warning: could not fetch shipment companies ({e}); "
                "falling back to data.SHIPMENT_COMPANIES",
                file=sys.stderr,
            )
    if pairs is None:
        pairs = list(data.SHIPMENT_COMPANIES.items())
        source = "data.SHIPMENT_COMPANIES"

    if text.isdigit():
        cid = int(text)
        if cid in {c for c, _ in pairs}:
            return cid
        available = ", ".join(f"{n} ({i})" for i, n in pairs)
        raise RuntimeError(f"unknown company_id {cid} (source: {source}); available: {available}")

    matches = [(cid, name) for cid, name in pairs if name.lower() == text.lower()]
    if len(matches) == 1:
        return matches[0][0]
    if not matches:
        available = ", ".join(f"{name} ({cid})" for cid, name in pairs)
        raise RuntimeError(
            f"no shipment company named '{value}' (source: {source}); available: {available}"
        )
    raise RuntimeError(f"company name '{value}' is ambiguous: ids {[cid for cid, _ in matches]}")


def _auto_tracking_number():
    """Unique tracking number, e.g. auto-20261108-212447-837356.

    Microsecond suffix: create_shipment reads the record back by this value,
    so two runs in the same second must not collide.
    """
    return f"{AUTO_TRACKING_PREFIX}-{datetime.now():%Y%m%d-%H%M%S-%f}"


def _scope_label(args):
    """Short human label for the shipment scope, used in the summary."""
    if not args.children:
        return "part only"
    if args.include_root:
        return "part + all descendants"
    return "descendants only"


def _resolve_roots(args):
    """Part ids for all requested roots, deduplicated, order preserved."""
    ids = [int(r) for r in args.roots]
    for sn in args.sn:
        try:
            pid = util.resolve_part_id_by_sn(sn, args.kind)
        except Exception as e:
            raise RuntimeError(f"{sn} ({args.kind}): {type(e).__name__}: {e}") from e
        if pid is None:
            raise RuntimeError(f"could not resolve serial number '{sn}' ({args.kind}) to a part_id")
        if not args.quiet:
            print(f"resolved {sn} ({args.kind}) -> part_id {pid}", file=sys.stderr)
        ids.append(int(pid))

    seen, unique = set(), []
    for pid in ids:
        if pid in seen:
            print(f"warning: part_id {pid} given more than once; using it once", file=sys.stderr)
            continue
        seen.add(pid)
        unique.append(pid)
    return unique


def _gather_parts(args, root_ids):
    """Parts to ship across all roots, deduplicated by part_id.

    Returns (parts, per_root_counts, skipped_duplicates). Overlapping roots
    (one root contained in another's subtree) are the common source of
    duplicates; the part is shipped once.
    """
    collected, seen = [], set()
    per_root = {}
    skipped = 0

    for root_id in root_ids:
        if not args.children:
            batch = [util.get_info_of_part_id(root_id)[0]]
        else:
            batch = util.get_recursive_children(
                root_id,
                ofKind=args.child_kind,
                max_depth=args.max_depth,
                include_parent=args.include_root,
            )
        kept = 0
        for p in batch:
            pid = int(p["part_id"])
            if pid in seen:
                skipped += 1
                continue
            seen.add(pid)
            collected.append(p)
            kept += 1
        per_root[root_id] = kept

    return collected, per_root, skipped


def _format_parts(parts):
    """One 'SN<TAB>part_id N' line per part, for --list/--list-file."""
    return [f"{p.get('serial_number') or '?'}\tpart_id {p['part_id']}" for p in parts]


def _write_lines(path, lines):
    """Write lines to path as UTF-8, creating parent directories."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _check_date(parser, value, flag):
    """Reject a value that is not YYYY-MM-DD, naming the flag in the error."""
    if value is None:
        return
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        parser.error(f"{flag} must be YYYY-MM-DD")


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.status == "Received":
        parser.error(
            "a shipment cannot be created as Received; create it as "
            "Created/Shipped and use receive-shipment to receive it "
            "(that is what moves the parts and sets the reception date)"
        )
    args.roots = _parse_part_ids(args.roots, parser)
    args.sn = _parse_sns(args.sn, parser)

    # --- root selection
    if not args.roots and not args.sn:
        parser.error("give at least one PART_ID, or --sn together with --kind")
    if args.sn and not args.kind:
        parser.error("--sn requires --kind (which parts table to search)")
    if not args.sn and args.kind is not None:
        parser.error("--kind only resolves --sn; use --child-kind for the traversal")

    # --- scope sanity
    if not args.children and not args.include_root:
        parser.error("--no-children together with --without-parent selects nothing")
    if not args.children and (args.child_kind != "all" or args.max_depth is not None):
        parser.error(
            "--child-kind/--max-depth need children; drop --no-children or the traversal options"
        )

    for opt, value in (("--kind", args.kind), ("--child-kind", args.child_kind)):
        if value is not None and value != "all" and value not in data.KoPID_from_partKoPName:
            parser.error(
                f"unknown kind of part '{value}' for {opt}; choose from: "
                f"all, {', '.join(sorted(data.KoPID_from_partKoPName))}"
            )
    if args.max_depth is not None and args.max_depth < 0:
        parser.error("--max-depth must be >= 0")

    _check_date(parser, args.shipment_date, "--date")

    shipment_date = args.shipment_date or datetime.now().strftime("%Y-%m-%d")

    # --- authenticate before the first API request
    if args.local_folder is not None:
        api.set_local_folder(args.local_folder)
    try:
        api.user_auth_cli(args.user_name, api.resolve_local_folder())
        access_token = api.get_access_token()
    except Exception as e:
        print(f"error: authentication failed: {type(e).__name__}: {e}", file=sys.stderr)
        return 1
    if not args.quiet:
        print(f"authenticated as {args.user_name}", file=sys.stderr)

    # --- resolve roots
    try:
        root_ids = _resolve_roots(args)
    except Exception as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    if not root_ids:
        print("error: no roots resolved; nothing to ship", file=sys.stderr)
        return 1

    # --- gather parts
    try:
        parts, per_root, skipped = _gather_parts(args, root_ids)
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"error: {type(e).__name__}: {e}", file=sys.stderr)
        return 1

    if not parts:
        print(
            f"error: no parts selected ({_scope_label(args)}); nothing to ship",
            file=sys.stderr,
        )
        return 1

    # --- resolve location / company
    try:
        from_location = _resolve_location(args.from_location)
        to_location = _resolve_location(args.to_location)
        company_id = _resolve_company(args.company)
    except Exception as e:
        print(f"error: {type(e).__name__}: {e}", file=sys.stderr)
        return 1

    if int(from_location["location_id"]) == int(to_location["location_id"]):
        print("warning: origin and destination are the same location", file=sys.stderr)

    tracking_number = args.tracking_number or _auto_tracking_number()

    if args.fetch_part_comments:
        try:
            util.backfill_part_comments(parts)
        except Exception as e:
            print(f"error: could not fetch part comments: {type(e).__name__}: {e}", file=sys.stderr)
            return 1

    payload = util.build_shipment_payload(
        from_location=from_location,
        to_location=to_location,
        company=company_id,
        items=[dict(p, part_id=p["part_id"], serial_number=p.get("serial_number")) for p in parts],
        tracking_number=tracking_number,
        status=args.status,
        shipment_date=shipment_date,
        edh_link=args.edh_link,
        from_contact=args.from_contact,
        from_contact_email=args.from_contact_email,
        to_contact=args.to_contact,
        to_contact_email=args.to_contact_email,
        record_insertion_user=args.user_name,
    )
    # --- listings
    if args.list_parts or args.list_file:
        lines = _format_parts(parts)
        if args.list_parts:
            print("\n".join(lines), file=sys.stderr)
        if args.list_file:
            _write_lines(args.list_file, lines)

    if args.payload_file:
        _write_lines(
            args.payload_file,
            json.dumps(payload, indent=2, ensure_ascii=False).split("\n"),
        )

    # --- summary
    if not args.quiet:
        n_empty = sum(1 for p in parts if not util.part_comment(p))
        if n_empty:
            print(
                f"note: {n_empty} part(s) have no comment_description; "
                "their shipment items get an empty comment",
                file=sys.stderr,
            )
        mode = "DRY RUN" if args.dry_run else "POSTING"
        roots_desc = ", ".join(str(r) for r in root_ids)
        print(
            f"[{mode}] {len(parts)} part(s) [{_scope_label(args)}] from "
            f"{len(root_ids)} root(s) ({roots_desc})",
            file=sys.stderr,
        )
        if len(root_ids) > 1:
            detail = ", ".join(f"{rid}:{n}" for rid, n in per_root.items())
            print(f"  per root (before dedupe): {detail}", file=sys.stderr)
        if skipped:
            print(
                f"  {skipped} duplicate part(s) skipped "
                "(overlapping roots or shared sub-assemblies)",
                file=sys.stderr,
            )
        print(
            f"  {from_location.get('location_name')} -> "
            f"{to_location.get('location_name')}, "
            f"company {company_id}, tracking {tracking_number}, "
            f"status {args.status}, date {shipment_date}",
            file=sys.stderr,
        )

    # --- dry run or POST
    if args.dry_run:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        print("dry run: nothing sent", file=sys.stderr)
        return 0

    if not args.tracking_number and not args.quiet:
        print(f"note: generated tracking number '{tracking_number}'", file=sys.stderr)

    try:
        created, responseText = util.create_shipment(payload, access_token=access_token)
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"error: {type(e).__name__}: {e}", file=sys.stderr)
        return 1

    if not args.quiet:
        print(
            f"created shipment_id {created.get('shipment_id')} "
            f"with {len(parts)} item(s)  [API response: {responseText}]\n"
            " - note this down "
            "and let your contact person on the receiving end know "
            f"the shipment_id {created.get('shipment_id')} for later lookup "
            "and for marking as Received",
            file=sys.stderr,
        )

    if args.status == "Shipped":
        print("note: status Shipped — parts were NOT moved", file=sys.stderr)
    elif args.status == "Cancel":
        print("note: shipment created already canceled", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())

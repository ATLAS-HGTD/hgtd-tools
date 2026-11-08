#!/usr/bin/env python3
"""Find HGTD shipments and mark the selected ones as Received.

Setting the status to "Received" is what moves every part in a shipment to the
shipment's destination location, and it is the only operation that does so.
Creating a shipment already marked Received leaves the parts where they are;
clever-ship refuses that combination and points here instead.

Two ways in:
  * exact identifiers -- shipment_id(s) and/or --tracking-number(s). These are
    acted on directly, with no listing and no search filters applied.
  * search filters -- --search, --status, --company, --date, --open-only.
    All matching shipments are printed and you pick the ones to receive.

--reception-date records when the parts arrived (reception_date). It is
optional; when omitted, the field keeps whatever value it already has.

Examples:
    # exact ids, comma-separated
    receive-shipment 1241,1242 -u yourUsername --dry-run

    # exact tracking numbers, with the arrival date
    receive-shipment --tracking-number trkDHL08193,trkDHL08194 \\
        -u yourUsername --reception-date 2026-11-08

    # search, inspect, then select
    receive-shipment --search DHL --status Created -u yourUsername
    receive-shipment --company dhl --date 2026-11 --open-only -u yourUsername

Exit codes: 0 success, 1 runtime/API failure, 2 bad usage.
"""

import argparse
import json
import sys
from datetime import datetime

from hgtd_tools import api, data, util


def _split_csv(text):
    """Split a comma-separated argument, tolerating spaces and empty tokens."""
    return [tok.strip() for tok in str(text).split(",") if tok.strip()]


def build_parser():
    p = argparse.ArgumentParser(
        prog="receive-shipment",
        description="Find HGTD shipments and mark selected ones as Received.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__.split("Examples:", 1)[1].strip(),
    )

    exact = p.add_argument_group("exact identifiers (skip the listing)")
    exact.add_argument(
        "shipment_ids",
        nargs="*",
        default=[],
        metavar="ID[,ID...]",
        help="shipment_id(s), comma-separated (e.g. 1241,1242)",
    )
    exact.add_argument(
        "--tracking-number",
        default=None,
        metavar="TRK[,TRK...]",
        help="tracking number(s), comma-separated. Requires one GET of all "
        "shipments to resolve them to ids.",
    )

    find = p.add_argument_group("search filters (list, then select)")
    find.add_argument(
        "--search",
        default=None,
        metavar="TEXT",
        help="substring match against shipment_id, tracking number and EDH link (case-insensitive)",
    )
    find.add_argument(
        "--status",
        default=None,
        metavar="STATUS",
        help="filter by status: " + ", ".join(data.SHIPMENT_STATUSES),
    )
    find.add_argument(
        "--company",
        default=None,
        metavar="TEXT",
        help="filter by company name or company_id (substring, case-insensitive)",
    )
    find.add_argument(
        "--date",
        default=None,
        metavar="YYYY[-MM[-DD]]",
        help="filter by shipment date prefix, e.g. 2026, 2026-11, 2026-11-07",
    )
    find.add_argument(
        "--open-only",
        action="store_true",
        help="only " + ", ".join(data.OPEN_SHIPMENT_STATUSES) + " shipments (recommended)",
    )
    find.add_argument(
        "--include-deleted",
        dest="only_non_deleted",
        action="store_false",
        help="include soft-deleted shipment records in the listing",
    )
    find.add_argument(
        "--limit",
        type=int,
        default=200,
        metavar="N",
        help="show at most N matches (default: 200)",
    )

    act = p.add_argument_group("action")
    act.add_argument(
        "--yes",
        action="store_true",
        help="do not ask for confirmation when identifiers were given explicitly",
    )
    act.add_argument(
        "--force",
        action="store_true",
        help="also PUT shipments that are already Received or Canceled",
    )
    act.add_argument(
        "--dry-run",
        action="store_true",
        help="print what would be PUT without sending it",
    )
    act.add_argument(
        "--reception-date",
        default=None,
        metavar="YYYY-MM-DD",
        help="date the parts arrived, sent as reception_date "
        "(e.g. 2026-11-08). Default: not sent, the field keeps its "
        "current value.",
    )
    act.add_argument("--quiet", action="store_true", help="suppress the summary on stderr")

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


# --- matching


def _company_label(shipment):
    company = shipment.get("company") or {}
    return f"{company.get('name', '?')} ({company.get('company_id', '?')})"


def _location_name(shipment, key):
    return ((shipment.get(key) or {}).get("location_name")) or "?"


def _matches(shipment, args):
    """True if the shipment passes every given filter."""
    if args.status:
        if str(shipment.get("status", "")).lower() != args.status.lower():
            return False
    if args.open_only:
        if shipment.get("status") not in data.OPEN_SHIPMENT_STATUSES:
            return False
    if args.company:
        needle = args.company.lower()
        company = shipment.get("company") or {}
        haystacks = [
            str(company.get("name", "")).lower(),
            str(company.get("company_id", "")).lower(),
        ]
        if not any(needle in h for h in haystacks):
            return False
    if args.date:
        if not str(shipment.get("shipment_date") or "").startswith(args.date):
            return False
    if args.search:
        needle = args.search.lower()
        haystacks = [
            str(shipment.get("shipment_id", "")).lower(),
            str(shipment.get("tracking_number", "")).lower(),
            str(shipment.get("edh_link", "")).lower(),
        ]
        if not any(needle in h for h in haystacks):
            return False
    return True


def _search(args):
    """All shipments passing the filters, newest shipment_date first.

    Uses include_children=False: the item list is not needed for selection
    and can be large.
    """
    shipments, _ = util.get_shipments(include_children=False, onlyNonDeleted=args.only_non_deleted)
    hits = [s for s in shipments if _matches(s, args)]
    hits.sort(
        key=lambda s: (
            str(s.get("shipment_date") or ""),
            int(s.get("shipment_id") or 0),
        ),
        reverse=True,
    )
    return hits


# --- display / selection


def _print_table(hits, limit):
    """Print matches as a fixed-width table, truncated to `limit` rows.

    Columns are capped at 28 characters so long EDH links do not blow up the
    layout; over-long cells end in an ellipsis.
    """
    rows = [
        (
            str(s.get("shipment_id")),
            str(s.get("tracking_number") or ""),
            str(s.get("status") or ""),
            str(s.get("shipment_date") or "")[:10],
            _company_label(s),
            f"{_location_name(s, 'from_location')} -> {_location_name(s, 'to_location')}",
            str(s.get("edh_link") or ""),
        )
        for s in hits
    ]
    headers = ("ID", "TRACKING", "STATUS", "DATE", "COMPANY", "ROUTE", "EDH")
    widths = [
        max(len(headers[i]), max((len(r[i]) for r in rows), default=0)) for i in range(len(headers))
    ]
    widths = [min(w, 28) for w in widths]

    def fmt(cells):
        return "  ".join(
            (c[: widths[i] - 1] + "…" if len(c) > widths[i] else c).ljust(widths[i])
            for i, c in enumerate(cells)
        ).rstrip()

    print(fmt(headers))
    print(fmt(tuple("-" * w for w in widths)))
    for row in rows[:limit]:
        print(fmt(row))
    if len(rows) > limit:
        print(f"... {len(rows) - limit} more (use --limit)")


def _prompt_selection(hits):
    """Ask for shipment_ids to act on. Returns a list, or [] to abort."""
    if not sys.stdin.isatty():
        raise RuntimeError(
            "no interactive terminal to select from; pass shipment_ids "
            "or --tracking-number explicitly"
        )
    print(
        "\nselect shipment_id(s), comma-separated — 'all' for every match, empty to abort:",
        file=sys.stderr,
    )
    try:
        answer = input("> ").strip()
    except (EOFError, KeyboardInterrupt):
        print("aborted", file=sys.stderr)
        return []
    if not answer:
        return []
    if answer.lower() == "all":
        return [int(s["shipment_id"]) for s in hits]
    tokens = _split_csv(answer)
    by_id = {int(s["shipment_id"]): s for s in hits}
    chosen = []
    for tok in tokens:
        try:
            sid = int(tok)
        except ValueError:
            raise RuntimeError(f"'{tok}' is not a shipment_id")
        if sid not in by_id:
            raise RuntimeError(f"shipment_id {sid} is not among the matches")
        if sid not in chosen:
            chosen.append(sid)
    return chosen


def _confirm(shipments, dry_run, reception_date=None):
    """Ask for a y/N before the PUTs. Returns True to proceed.

    Always True in --dry-run or without a TTY, so cron runs do not block.
    """
    if dry_run or not sys.stdin.isatty():
        return True
    suffix = f"  reception_date={reception_date}" if reception_date else ""
    print(f"\nabout to PUT status=Received{suffix} for:", file=sys.stderr)
    for s in shipments:
        print(
            f"  {s.get('shipment_id')}  {s.get('tracking_number')}  "
            f"{_location_name(s, 'to_location')}",
            file=sys.stderr,
        )
    try:
        answer = input("proceed? [y/N] ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        return False
    return answer in ("y", "yes")


# --- main


def _resolve_targets(args):
    """Shipments to act on, plus whether they came from a listing."""
    if args.shipment_ids or args.tracking_number:
        targets, missing = [], []
        ids = []
        for chunk in args.shipment_ids:
            for tok in _split_csv(chunk):
                try:
                    ids.append(int(tok))
                except ValueError:
                    raise RuntimeError(f"'{tok}' is not a shipment_id")
        for sid in ids:
            targets.append(util.get_shipment(sid)[0])
        if args.tracking_number:
            listed, _ = util.get_shipments(
                include_children=False,
                onlyNonDeleted=args.only_non_deleted,
            )
            index = {}
            for s in listed:
                index.setdefault(str(s.get("tracking_number")), []).append(s)
            for trk in _split_csv(args.tracking_number):
                found = index.get(trk, [])
                if len(found) == 1:
                    targets.append(found[0])
                elif not found:
                    missing.append(trk)
                else:
                    raise RuntimeError(
                        f"tracking number '{trk}' is not unique: "
                        f"shipment_ids "
                        f"{[s.get('shipment_id') for s in found]}"
                    )
        if missing:
            raise RuntimeError("no shipment with tracking number(s): " + ", ".join(missing))
        # dedupe, preserve order
        seen, unique = set(), []
        for s in targets:
            sid = int(s["shipment_id"])
            if sid not in seen:
                seen.add(sid)
                unique.append(s)
        return unique, False

    hits = _search(args)
    if not hits:
        raise RuntimeError("no shipments match the given filters")
    _print_table(hits, args.limit)
    selected = _prompt_selection(hits)
    if not selected:
        return [], True
    by_id = {int(s["shipment_id"]): s for s in hits}
    return [by_id[sid] for sid in selected], True


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.status and args.status not in data.SHIPMENT_STATUSES:
        parser.error(
            f"unknown status '{args.status}'; choose from: {', '.join(data.SHIPMENT_STATUSES)}"
        )
    if args.limit < 1:
        parser.error("--limit must be >= 1")
    if not (
        args.shipment_ids
        or args.tracking_number
        or args.search
        or args.status
        or args.company
        or args.date
        or args.open_only
    ):
        parser.error(
            "give shipment_id(s), --tracking-number, or at least one filter "
            "(--search/--status/--company/--date/--open-only)"
        )
    if args.reception_date is not None:
        try:
            datetime.strptime(args.reception_date, "%Y-%m-%d")
        except ValueError:
            parser.error("--reception-date must be YYYY-MM-DD")

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

    try:
        targets, from_listing = _resolve_targets(args)
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"error: {type(e).__name__}: {e}", file=sys.stderr)
        return 1

    if not targets:
        print("nothing selected", file=sys.stderr)
        return 0

    actionable = []
    for shipment in targets:
        sid = shipment.get("shipment_id")
        status = shipment.get("status")
        if status == "Received" and not args.force:
            print(
                f"shipment {sid} is already Received; skipping (use --force to PUT anyway)",
                file=sys.stderr,
            )
            continue
        if status == "Cancel" and not args.force:
            print(
                f"warning: shipment {sid} is Canceled; skipping (use --force to receive it anyway)",
                file=sys.stderr,
            )
            continue
        actionable.append(shipment)

    if not actionable:
        print("nothing to receive", file=sys.stderr)
        return 0

    if not (args.yes or from_listing) and not _confirm(actionable, args.dry_run):
        print("aborted", file=sys.stderr)
        return 0

    failures = 0
    for shipment in actionable:
        sid = shipment.get("shipment_id")
        if args.dry_run:
            preview = {"shipment_id": sid, "status": "Received"}
            if args.reception_date is not None:
                preview["reception_date"] = args.reception_date
            print(json.dumps(preview))
            continue
        try:
            updated, responseText = util.receive_shipment(
                sid,
                access_token=access_token,
                user=args.user_name,
                reception_date=args.reception_date,
            )
        except Exception as e:
            print(f"error: shipment {sid}: {type(e).__name__}: {e}", file=sys.stderr)
            failures += 1
            continue
        if not args.quiet:
            dest = _location_name(updated, "to_location")
            n_items = len(updated.get("shipmentitems") or [])
            print(
                f"shipment {sid} Received — {n_items} part(s) moved to {dest}  [{responseText}]",
                file=sys.stderr,
            )

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())

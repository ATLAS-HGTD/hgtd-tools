#!/usr/bin/env python3
"""CLI for SN reservation and part registration (HGTD Module Assembly).

Two mutually exclusive modes:

  --n-reserve N   let hgtd-tools propose N new serial numbers for the given
                  site/production/batch and ask for name label, version and
                  comment per SN (Kind of Part is always Module)
  --csv FILE      read sn or module_sn rows plus name_label[,version][,comment];
                  SNs already in the DB are updated with PUT, unknown ones are
                  created with POST

A `module_sn` header implies Kind of Part Module. A generic `sn` header makes
hgtd-tools ask for the Kind of Part (or take it from --kind).

The existence check only looks at the Kind of Part being written. Since SNs are
unique across kinds, a clash with a part of another kind (or one created
concurrently) comes back as a backend error; it is reported with a hint that the
SN may already exist.

With --dryrun nothing is uploaded and no confirmation is asked: the planned
action is printed instead.

-u is used as record_insertion_user on creation and as record_lastupdate_user
on update.
"""

from argparse import ArgumentParser
from pprint import pprint

from hgtd_tools import api, data, util

# === Small CLI helpers


def _confirm(prompt, assume_yes=False, dryrun=False):
    """Yes/no confirmation.

    In dryrun the question is not asked: the prompt is echoed with a dryrun
    marker and True is returned, so the planned action gets printed.
    --yes short-circuits to True as well.
    """
    if dryrun:
        print(f"{prompt}[dryrun: confirmation not asked]")
        return True
    if assume_yes:
        print(f"{prompt}[auto-confirmed]")
        return True
    return input(prompt).strip().lower() in ("y", "yes")


def _print_dryrun_banner(dryrun):
    if dryrun:
        print(
            "DRYRUN: no data will be uploaded and no confirmation will be asked. "
            "hgtd-tools will print the requests it would send."
        )


def _describe_http_error(err):
    """(status_code, body_excerpt) of a requests.HTTPError, or (None, None).

    Used to tell a server-side crash (5xx, e.g. Locations.DoesNotExist in the
    PUT view) apart from a rejected payload (4xx) — the two need different
    advice, and the old catch-all text blamed a duplicate SN for both.
    """
    response = getattr(err, "response", None)
    if response is None:
        return None, None
    body = (response.text or "").strip()
    if len(body) > 800:
        body = body[:800] + " …"
    return response.status_code, body


def _report_upload_failure(detail, sn, kind_of_part, action, status=None, body=None):
    """Print a failure, with the likely cause narrowed down by status code."""
    print(f"{action} of {sn} ({kind_of_part}) failed:\n{detail}")
    if status is not None:
        print(f"HTTP status: {status}")
    if body:
        print(f"Server response:\n{body}")

    if status is None:
        print(
            "Could not reach the API, or the error carried no response. Check "
            "your connection and the access token."
        )
    elif status >= 500:
        print(
            "The server raised while processing the request (5xx). That is a bug "
            "or an unexpected DB state, not a validation problem: the request "
            "reached the view and the view raised. On PUT the usual cause is a "
            "missing or unresolvable location, kind_of_part or manufacturer. "
            "Send the traceback above to the DB admins; do not blindly re-run."
        )
    elif status == 409 or (status == 400 and body and "exist" in body.lower()):
        print(
            f"A part with serial number {sn} probably already exists. Only "
            f"'{kind_of_part}' parts were checked before uploading, and serial "
            "numbers are unique across all kinds, so it may exist under another "
            "Kind of Part, or have been created since this run started."
        )
    else:
        print(
            "The payload was rejected (4xx). The response body lists the "
            "offending fields; compare them with the printed payload."
        )


class _PartIndexCache:
    """Lazily built {serial_number: part} per Kind of Part, one fetch per kind."""

    def __init__(self):
        self._by_kind = {}

    def get(self, kind_of_part):
        if kind_of_part not in self._by_kind:
            self._by_kind[kind_of_part] = util.build_part_index(kind_of_part)
        return self._by_kind[kind_of_part]


def _report_upload_failure(detail, sn, kind_of_part, action):
    """Print a failure with the most likely cause spelled out."""
    print(f"{action} of {sn} ({kind_of_part}) failed:\n{detail}")
    print(
        "Possible reasons:\n"
        f"  - a part with serial number {sn} already exists in the database. Only "
        f"'{kind_of_part}' parts were checked before uploading, and serial numbers "
        "are unique across all kinds, so it may exist under another Kind of Part "
        "(or have been created concurrently since this run started).\n"
        "  - a previously deleted record with this SN is still present in the DB.\n"
        "  - the payload was rejected (check the fields printed above).\n"
        "Verify in the DB web view before retrying; do not blindly re-run."
    )


def _post_part(payload, sn, kind_of_part, myToken, dryrun):
    """POST a new part; on failure explain the duplicate-SN possibility and raise."""
    if dryrun:
        api.post_information(util.PARTS_ENDPOINT, payload, dryrun=True, existing_token=myToken)
        print(f"Dryrun: would have created {sn} ({kind_of_part}); nothing was sent.")
        return

    try:
        response_text = api.post_information(
            util.PARTS_ENDPOINT, payload, dryrun=False, existing_token=myToken
        )
    except util.API_ERRORS as err:
        _report_upload_failure(err, sn, kind_of_part, "Creation")
        raise

    if response_text[:2] != "20":
        _report_upload_failure(response_text, sn, kind_of_part, "Creation")
        raise RuntimeError(f"Creation failed for {sn}")

    print(f"Creation of {sn} succeeded ({response_text}).")


def _put_part(existing_part, sn, kind_of_part, changes, username, myToken, dryrun):
    """PUT an update; `changes` is the body from util.build_part_update_payload."""
    path = util.PART_ENDPOINT.format(part_id=int(existing_part["part_id"]))
    if dryrun:
        api.put_information(path, changes, dryrun=True, existing_token=myToken)
        print(f"Dryrun: would have updated {sn} ({kind_of_part}); nothing was sent.")
        return

    try:
        response_text = api.put_information(path, changes, dryrun=False, existing_token=myToken)
    except util.API_ERRORS as err:
        status, body = _describe_http_error(err)
        _report_upload_failure(err, sn, kind_of_part, "Update", status, body)
        raise

    if response_text[:2] != "20":
        _report_upload_failure(response_text, sn, kind_of_part, "Update")
        raise RuntimeError(f"Update failed for {sn}")

    print(f"Update of {sn} succeeded ({response_text}).")


# === Mode 1: reserve N serial numbers


def run_reserve_mode(args, username, default_comment, myToken, dryrun, fill_holes=True):
    my_site, my_prod, my_batch = args.site, args.prod, args.batch
    how_many_to_reserve = int(args.nToReserve)

    modules, _ = util.get_relevant_parts("Module")
    module_SNs = util.get_SN_of_parts(modules)
    my_prefix = util.get_MO_SN_prefix(my_site, my_prod, my_batch)

    def find_matching_SNs(prefix, existing_SNs):
        return [ex for ex in existing_SNs if str(ex[:8]) == str(prefix)]

    def find_matching_sorted_counters(matching_SN_list):
        return sorted([SN[8:] for SN in matching_SN_list])

    def change_counter_digits_to_ints(counters):
        return [int(c) for c in counters]

    def find_max(my_list):
        return max(my_list) if len(my_list) > 0 else 0

    def collect_possible_holes(counters_as_INT, max_match):
        holes = []
        # no zero-counting: human-readable counters start from 1
        for i in range(1, max_match + 1):
            if i not in counters_as_INT:
                holes.append(i)
        return holes

    def build_recommended_SNs(N_to_reserve, holes_to_use, max_so_far, prefix):
        n_holes_to_use = len(holes_to_use)
        if n_holes_to_use >= N_to_reserve:
            recom_counters = holes_to_use[:N_to_reserve]
        else:
            still_to_build = N_to_reserve - n_holes_to_use
            recom_counters = holes_to_use + [
                new_ones for new_ones in range(max_so_far + 1, max_so_far + 1 + still_to_build)
            ]
        return [f"{prefix}{counter:06}" for counter in recom_counters]

    my_matching_SNs = find_matching_SNs(my_prefix, module_SNs)
    matched_sorted_counters = find_matching_sorted_counters(my_matching_SNs)
    matched_sorted_counters_as_INT = change_counter_digits_to_ints(matched_sorted_counters)
    max_matched = find_max(matched_sorted_counters_as_INT)

    if fill_holes:
        holes_in_matched = collect_possible_holes(matched_sorted_counters_as_INT, max_matched)
    else:
        # start right after the highest counter in use; skipped SNs stay unused
        holes_in_matched = []

    recommended_SNs = build_recommended_SNs(
        how_many_to_reserve, holes_in_matched, max_matched, my_prefix
    )

    if len(my_matching_SNs) > 0:
        print(
            "hgtd-tools found the following SNs matching your prefix criteria "
            f"on site/prod/batch: {my_prefix}"
        )
        pprint(my_matching_SNs)
        if fill_holes:
            print(
                "hgtd-tools will now recommend unused SNs, attempting to fill any "
                "skipped SNs and continuing with the next ones."
            )
        else:
            print(
                "hgtd-tools will now recommend the next unused SNs after the "
                "highest counter found (--no-fill-holes: skipped SNs are not reused)."
            )
    else:
        print(
            f"hgtd-tools will recommend suitable SNs to you, starting from the prefix: {my_prefix}"
        )

    for i, sn in enumerate(recommended_SNs, start=1):
        print(
            f"\n\n[{i}/{how_many_to_reserve}] You are about to introduce the "
            f"following Serial Number in the database: {sn}"
        )

        # per-part values; nothing is carried over to the next SN
        user_not_yet_happy = True
        part_to_upload = None
        while user_not_yet_happy:
            print(f"hgtd-tools needs more detail information for {sn}.\n")
            name_label = util.ask(
                "Name Label of this part (local nomenclature known in your lab)",
                required=True,
            )
            version = util.ask(
                "Version of this part (local nomenclature, recommended for your "
                "component group; [Enter] for empty)"
            )
            comment = util.ask(f"Comment for {sn}", default=default_comment)

            part_to_upload = util.build_part_payload(
                sn, name_label, version, comment, username, my_site
            )

            print(
                "\nThis is what would be uploaded for this part, with human-readable "
                "location, manufacturer and Kind Of Part already translated to DB IDs:"
            )
            pprint(part_to_upload)

            if dryrun:
                print(
                    "Dryrun: not asking for confirmation. In a real run hgtd-tools "
                    "would ask you to confirm this part now."
                )
                user_not_yet_happy = False
            else:
                happy = input(
                    'Are you happy with this? Type "Y" to upload, any other input '
                    "to modify again before uploading. "
                )
                if happy.strip().lower() == "y":
                    user_not_yet_happy = False

        _post_part(part_to_upload, sn, "Module", myToken, dryrun)

    if dryrun:
        print("\nConcluding dryrun: no part was created.")


# === Mode 2: create/update parts from a CSV


def run_csv_mode(args, username, default_comment, myToken, dryrun):
    rows = util.read_parts_csv(args.csvFile)
    print(f"{len(rows)} row(s) in {args.csvFile}.")

    index = _PartIndexCache()
    n_created = n_updated = n_skipped = 0
    n_would_create = n_would_update = 0

    for row in rows:
        sn = row["sn"]
        print(f"\n--- {sn} (CSV line {row['line']}) ---")

        name_label = row["name_label"]
        version = row["version"] or None
        comment = row["comment"] or None

        # ---- resolve the Kind of Part (needed for lookup and creation) ----
        kind_of_part = row["kind_of_part"]
        if kind_of_part is not None:
            print(f"Kind of Part: {kind_of_part} (from the 'module_sn' header)")
        elif args.kind is not None:
            kind_of_part = args.kind
            print(f"Kind of Part: {kind_of_part} (from --kind)")
        else:
            print("CSV uses a generic 'sn' column, so the Kind of Part is unknown.")
            print(f"Serial number in question: {sn} (name label: {name_label})")
            kind_of_part = util.ask_kind_of_part()
            print(f"Kind of Part: {kind_of_part} (chosen interactively)")

        # only the relevant KoP is checked; clashes with other kinds surface
        # as a backend error on POST/PUT and are reported there
        existing_part = index.get(kind_of_part).get(sn)

        if existing_part is not None:
            # ---- already in the DB: PUT only, never create a duplicate ----
            part_id = int(existing_part["part_id"])
            print(
                f"{sn} is already in the database as '{kind_of_part}' "
                f"(part_id {part_id}). hgtd-tools will not create it again and "
                "will send a PUT update."
            )
            print(f"Part view: {util.part_url(part_id)}")

            changes = util.build_part_update_payload(
                existing_part,
                name_label=name_label,
                version=version,
                comment=comment,
                kind_of_part=kind_of_part,
                user=username,
            )
            print("PUT payload:")
            pprint(changes)

            if not _confirm(
                f"Update {sn} with the fields above? [y/N] ",
                assume_yes=args.yes,
                dryrun=dryrun,
            ):
                print("Skipped.")
                n_skipped += 1
                continue

            _put_part(existing_part, sn, kind_of_part, changes, username, myToken, dryrun)
            if dryrun:
                n_would_update += 1
            else:
                n_updated += 1
            continue

        # ---- not in the DB yet: create it --------------------------------
        payload = util.build_part_payload(
            sn,
            name_label,
            version or "",
            comment or default_comment,
            username,
            args.site,
            kind_of_part=kind_of_part,
        )
        print(
            f"{sn} ({kind_of_part}) is not in the database yet. Proposed new part "
            "(location/manufacturer/KoP resolved to DB IDs):"
        )
        pprint(payload)

        if not _confirm(f"Create {sn}? [y/N] ", assume_yes=args.yes, dryrun=dryrun):
            print("Skipped.")
            n_skipped += 1
            continue

        _post_part(payload, sn, kind_of_part, myToken, dryrun)
        if dryrun:
            n_would_create += 1
        else:
            n_created += 1

    if dryrun:
        print(
            f"\nSummary (DRYRUN, nothing uploaded): {n_would_create} would be "
            f"created, {n_would_update} would be updated, {n_skipped} skipped "
            f"(of {len(rows)} CSV rows)."
        )
    else:
        print(
            f"\nSummary: {n_created} created, {n_updated} updated, {n_skipped} "
            f"skipped (of {len(rows)} CSV rows)."
        )


# === Entry point


def main():
    parser = ArgumentParser(
        "CLI for SN reservation and part registration, targeted at Module Assembly."
    )
    parser.add_argument(
        "-u",
        "--user-name",
        dest="userName",
        help="Your CERN user name. Stored as record_insertion_user on creation "
        "and as record_lastupdate_user on update.",
        default=None,
        required=True,
    )
    parser.add_argument(
        "--site",
        dest="site",
        help=f"Site. Must be one of {','.join(data.MO_site_id.keys())}",
        default=None,
        required=True,
    )

    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--n-reserve",
        dest="nToReserve",
        help="Number of SNs to reserve automatically. Must be an integer. "
        "Requires --prod and --batch.",
        default=None,
    )
    mode.add_argument(
        "--csv",
        dest="csvFile",
        help="CSV with header module_sn|sn,name_label[,version][,comment]. "
        "module_sn implies Kind of Part Module; a generic sn makes hgtd-tools "
        "ask for the Kind of Part. SNs already in the DB get a PUT update, "
        "unknown ones are created.",
        default=None,
    )

    parser.add_argument(
        "--prod",
        dest="prod",
        help=f"Production (--n-reserve only). Must be one of {','.join(data.MO_prod_id.keys())}",
        default=None,
    )
    parser.add_argument(
        "--batch",
        dest="batch",
        help="Batch (--n-reserve only). Must be alphanumerical",
        default=None,
    )
    parser.add_argument(
        "--kind",
        dest="kind",
        choices=util.CSV_KINDS_OF_PART,
        help="[Optional, --csv with a generic 'sn' column only] Kind of Part to "
        "use for all rows, skipping the interactive question.",
        default=None,
    )
    parser.add_argument(
        "--no-fill-holes",
        dest="fillHoles",
        action="store_false",
        help="[Optional, --n-reserve only] Do not reuse skipped counters. "
        "Default: fill gaps in the existing SN sequence first, then continue "
        "after the highest counter.",
    )
    parser.add_argument(
        "--local-folder",
        dest="localFolder",
        help="Path to the folder that will hold temporary DB data for uploading, "
        "including a token for the user. If not given, hgtd-tools uses "
        "~/.hgtd_tools/local_info (creating it if needed), falling back to "
        "./local_info in the current working directory.",
        default=None,
    )
    parser.add_argument("--comment", dest="comment", help="[Optional] Set a comment.", default=None)
    parser.add_argument(
        "--dryrun",
        dest="dryrun",
        action="store_true",
        help="[Optional] Do everything up to the last step, but do not upload "
        "and do not ask for confirmation.",
    )
    parser.add_argument(
        "--yes",
        dest="yes",
        action="store_true",
        help="[Optional] Skip the per-row confirmation in CSV mode.",
    )
    parser.set_defaults(fillHoles=True)
    args = parser.parse_args()

    username = (args.userName or "").strip()
    if not username:
        parser.error("-u/--user-name must not be empty (it is stored as record_insertion_user)")

    default_comment = args.comment or "part SN reserved via hgtd-tools"
    dryrun = bool(args.dryrun)

    if args.csvFile is None:
        if args.prod is None or args.batch is None:
            parser.error("--prod and --batch are required when using --n-reserve")
        if args.kind is not None:
            parser.error("--kind only applies to --csv")
    else:
        if not args.fillHoles:
            parser.error("--no-fill-holes only applies to --n-reserve")
        if args.prod is not None or args.batch is not None:
            parser.error("--prod and --batch only apply to --n-reserve")

    _print_dryrun_banner(dryrun)

    if args.localFolder is not None:
        api.set_local_folder(args.localFolder)
    local_folder = api.resolve_local_folder()
    # disentangle user auth from DB token, always get a new DB one later on
    api.user_auth_cli(username, local_folder)
    myToken = api.get_access_token()

    if args.csvFile is not None:
        run_csv_mode(args, username, default_comment, myToken, dryrun)
    else:
        run_reserve_mode(
            args,
            username,
            default_comment,
            myToken,
            dryrun,
            fill_holes=args.fillHoles,
        )


if __name__ == "__main__":
    main()

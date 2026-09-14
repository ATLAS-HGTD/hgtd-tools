import os
import time
from argparse import ArgumentParser
from datetime import datetime
from datetime import UTC

import hgtd_tools.data as data
import hgtd_tools.relation_validation as relation_validation
import hgtd_tools.util as util
import numpy as np

parser = ArgumentParser(
    "Hybrid matcher (recommender system to pair Hybrids for HV- and LV-side)"
)
parser.add_argument(
    "--mode-alias",
    dest="mode_alias",
    help="Matching algorithm mode alias. (Default: %(default)s)",
    default="Only_Sensor_VBD_closest",
    choices=[
        "Only_Sensor_VBD_closest",  # default: 1D sorting, Sensor-Wafer info only, if VBD not stored, fallback manual calc from sensor IV
        # "Only_Hybrid_IV_VBD_closest",  # alternative: 1D sorting, Hybrid info only
        # "Sensor_VBD_closest_Fallback_Hybrid_IV_VBD_closest",  # alternative: Sensor-Wafer info, or if not available, Hybrid info
        # "Sensor_VBD_closest_AND_Hybrid_IV_VBD_closest_2D_DeltaR",  # alternative: both Sensor-Wafer info and Hybrid info, like CA-Clustering
    ],
)
parser.add_argument(
    "--location",
    dest="location",
    help="Location short name for which to run hybrid matching recommendation.",
    default=None,
    choices=data.MA_sites_to_monitor,
    required=True,
)
parser.add_argument(
    "--manual_ignore_hybrid_sns",
    dest="manual_ignore_hybrid_sns",
    help=(
        "SNs of Hybrids to ignore in the pairing algorithm. Accepted as: "
        "(a) a single SN, (b) multiple comma-separated SNs "
        "(e.g. '20USX123,20USX456'), or (c) a path to a .txt-like file with "
        "one SN per line ('#' starts a comment, blank lines are ignored). "
        "Duplicates are removed. Ignored parts are reported with reason "
        "'Manually ignored by user' and excluded from pairing."
    ),
    default=None,
)
parser.add_argument(
    "--dev",
    dest="dev",
    help="[Optional] Developer mode. Limit number of parts to process.",
    default=False,
)
parser.add_argument(
    "--max-workers",
    dest="max_workers",
    help=(
        "[Optional] Max threads for concurrent DB lookups during data-source prep. "
        "(Default: %(default)s)"
    ),
    default=4,
    type=int,
)
args = parser.parse_args()

mode_alias = args.mode_alias
location = args.location
max_workers = args.max_workers


# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
# Resolve --manual_ignore_hybrid_sns into a clean list of unique SN strings.
# Accepts either an inline value (single SN or comma-separated) or a path
# to a text file with one SN per line.
# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
def _looks_like_file_path(s):
    return os.path.sep in s or s.lower().endswith(
        (".txt", ".list", ".ignore", ".sn", ".sns")
    )


def _parse_manual_ignore_hybrid_sns(raw):
    if raw is None:
        return []
    if os.path.isfile(raw):
        # Path to an existing file: one SN per line.
        # Strip whitespace, drop blank lines and '#'-comment lines.
        with open(raw) as f:
            sns = [
                line.strip()
                for line in f
                if line.strip() and not line.lstrip().startswith("#")
            ]
    elif _looks_like_file_path(raw):
        # Looks like a path but the file is missing -> fail loud, don't
        # silently treat the bad path as an SN.
        raise FileNotFoundError(f"--manual_ignore_hybrid_sns: file not found: {raw}")
    elif "," in raw:
        sns = [s.strip() for s in raw.split(",") if s.strip()]
    else:
        sns = [raw.strip()] if raw.strip() else []

    # De-duplicate while preserving order, so a SN listed in both the
    # inline value and a file (or twice in the file) is reported once.
    seen = set()
    deduped = []
    for sn in sns:
        if sn not in seen:
            seen.add(sn)
            deduped.append(sn)
    return deduped


manual_ignore_hybrid_sns = _parse_manual_ignore_hybrid_sns(
    args.manual_ignore_hybrid_sns
)
dev = util.str2bool(args.dev)


# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
# Filter Hybrid parts for matching.
# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
def prepare_parts(location, dev):
    parts = util.get_relevant_parts("Hybrid")[0]
    # Hybrids for pairing must be located at the selected MA-site
    # and have a valid SN according to our latest SN specs
    # and not be connected yet to a Module
    # select_parts is already parallelized (in util)
    parts = util.select_parts(
        parts,
        location_shortname=location,
        check_valid_SN_latest_spec=True,
        no_parents_ofKind="Module",
    )
    if dev:
        parts = parts[:2]
    return parts


# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
# Depending on mode, need different data sources.
# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
#
## a. Only_Sensor_VBD_closest (default):
### get Sensor child -> get Wafer parent -> get VBD(@SensorSN)
### if this fails at VBD stage because not uploaded -> try calculating manually from full iv
### if also fallback fails anywhere in the process -> ignore Hybrid
#
## b. Only_Hybrid_IV_VBD_closest:
### get Hybrid IVs(@HybridSN) -> calculate VBD
### if this fails anywhere in the process -> ignore Hybrid
#
## c. Sensor_VBD_closest_Fallback_Hybrid_IV_VBD_closest:
### get Sensor child -> get Wafer parent -> get VBD(@SensorSN)
### if this fails anywhere in the process -> do Only_Hybrid_IV_VBD_closest
### if also fallback fails anywhere in the process -> ignore Hybrid
#
## d. Sensor_VBD_closest_AND_Hybrid_IV_VBD_closest_2D_DeltaR:
### Only_Sensor_VBD_closest AND Only_Hybrid_IV_VBD_closest -> calculate 2D pairing
### if this fails anywhere in the process -> ignore Hybrid


def get_decision_scores_only_Sensor_VBD_closest(p):
    part_id = p["part_id"]
    part_SN = p["serial_number"]
    children_S = util.get_children(part_id, ofKind="Sensor")[0]
    rel_val_result, rel_val_reason = relation_validation.validate_HY_chi_S(children_S)
    if rel_val_result == False:
        # Not a valid connection to Sensor child.
        # Must ignore this Hybrid for matching.
        return False, [
            part_id,
            part_SN,
            rel_val_reason,
        ]
    else:
        # Sensor child exists, valid connection.
        # We know it is exactly one Sensor child (@ index 0) at empty position.
        # Now check sensor parent Wafer.
        child_S_part_id = children_S[0]["part"]["part_id"]
        child_S_part_SN = children_S[0]["part"]["serial_number"]
        parents_W = util.get_parents(child_S_part_id, ofKind="Wafer")[0]
        rel_val_result, rel_val_reason = relation_validation.validate_S_par_W(parents_W)
        if rel_val_result == False:
            # Not a valid connection to Wafer parent.
            # Must ignore this Hybrid for matching.
            return False, [
                part_id,
                part_SN,
                f"Relation to Sensor is valid, but problem with Sensor: {rel_val_reason}",
            ]
        else:
            # Wafer parent exists, valid connection.
            # We know it is exactly one Wafer parent (@ index 0).
            # Now check Wafer-Sensor VBD table.
            parent_W_part_id = parents_W[0]["part_parent"]["part_id"]
            parent_W_part_SN = parents_W[0]["part_parent"]["serial_number"]
            vbd_value, vbd_reason = util.get_vbd_for_sensor_via_wafer(
                child_S_part_SN, parent_W_part_SN, metric="VBD_AVERAGE"
            )
            if vbd_reason != "":
                # VBD could not be retrieved from sensorvbdv2view.
                # Fallback solution: obtain IV curves for pads if they exist and calculate VBD manually.
                vbd_value, vbd_reason = util.get_vbd_for_sensor_via_iv(child_S_part_SN)
                if vbd_reason != "":
                    # Must ignore this Hybrid for matching.
                    return False, [
                        part_id,
                        part_SN,
                        (
                            f"Relation to Sensor is valid, relation to Wafer is valid, but problem with VBD retrieval, "
                            f"after already falling back to manual calculation of VBD from IV because VBD value not stored in DB: {vbd_reason}"
                        ),
                    ]
                else:
                    # All relations valid.
                    # Can put this part into the list for matching, with the manually calculated vbd_value as a score.
                    return True, [
                        part_id,
                        part_SN,
                        vbd_value,
                    ]
            else:
                # All relations valid.
                # Can put this part into the list for matching, with the already uploaded vbd_value as a score.
                return True, [
                    part_id,
                    part_SN,
                    vbd_value,
                ]


def get_decision_scores_only_Sensor_VBD_closest_safe(p):
    """Same as get_decision_scores_only_Sensor_VBD_closest, but converts
    any unhandled exception into a (False, reason) tuple so a single
    failing part does not abort the whole parallel run."""
    try:
        return get_decision_scores_only_Sensor_VBD_closest(p)
    except Exception as e:
        return False, [
            p["part_id"],
            p["serial_number"],
            f"Unhandled exception during scoring: {type(e).__name__}: {e}",
        ]


def prepare_data_sources(mode_alias, parts, max_workers=4):
    # this will hold all Hybrids we have to ignore given the matching algorithm
    # and the reason why it can not be matched
    ignored_parts = []  # list of lists
    # this holds all Hybrids that passed matchable criteria
    # and the scores by which to match them
    kept_parts_and_scoring = []  # list of lists
    if mode_alias == "Only_Sensor_VBD_closest":
        # I/O-bound fan-out (multiple DB lookups per part): threading is
        # appropriate and matches the pattern of util.parallel_keeps.
        # Use the *_safe variant so one bad part doesn't abort the run.
        kept_parts_and_scoring, ignored_parts = util.parallel_partition(
            parts,
            get_decision_scores_only_Sensor_VBD_closest_safe,
            max_workers=max_workers,
        )
    else:
        raise NotImplementedError

    return ignored_parts, kept_parts_and_scoring


def get_pairs_totaldiff_via_chunking(arr, at_column=2):
    """
    Pair (0,1),(2,3)... and return (pairs, total_distance).
    at_column: which column of inner lists to calc diff with
    """
    pairs = []
    total = 0.0
    for i in range(0, len(arr), 2):
        a, b = arr[i], arr[i + 1]
        dist = abs(float(b[at_column]) - float(a[at_column]))
        total += dist
        pairs.append((a.tolist(), b.tolist()))
    return pairs, total


def get_optimal_pairs_with_leftover_1D_On2(parts_scores, at_column=2):
    """
    O(n^2) algorithm to get optimal pairing, for 1-column comparisons.
    Works for even (just chunking) & odd no. of parts (with optimal leftover).

    at_column: which column of inner lists to calc diff with
    """
    # Guard: empty pool -> no pairs, no leftover, total distance = 0.
    # Without this, np.array([], dtype=object) is 1-D and arr[:, 2]
    # would raise IndexError("too many indices for array").
    if not parts_scores:
        return [], 0.0, []

    arr = np.array(parts_scores, dtype=object)
    order = np.argsort(arr[:, 2].astype(float), kind="mergesort")
    sarr = arr[order]

    n = len(sarr)
    if n % 2 == 0:
        return (*get_pairs_totaldiff_via_chunking(sarr, at_column), [])

    best_total = np.inf
    best_j = -1
    best_pairs = []
    for j in range(n):
        # remove j, pair the rest
        remain = np.delete(sarr, j, axis=0)
        pairs, tot = get_pairs_totaldiff_via_chunking(remain, at_column)
        if tot < best_total:
            best_total, best_j, best_pairs = tot, j, pairs

    leftover = sarr[best_j].tolist()
    return best_pairs, best_total, [leftover]


def run_pairing(parts, algorithm):
    if algorithm == "Only_Sensor_VBD_closest":
        # Guard: nothing survived filtering. Return the canonical
        # (empty_pairs, 0.0, empty_leftover) shape so callers can rely
        # on unpacking the triple unconditionally.
        if not parts:
            return [], 0.0, []
        return get_optimal_pairs_with_leftover_1D_On2(parts)
    else:
        raise NotImplementedError


def hybridmatch(
    mode_alias,
    location,
    dev,
    printouts=False,
    manual_ignore_hybrid_sns=[],
    max_workers=4,
):
    if printouts:
        print(
            "\n"
            + """
██╗    ██╗███████╗██╗      ██████╗ ██████╗ ███╗   ███╗███████╗    ████████╗ ██████╗
██║    ██║██╔════╝██║     ██╔════╝██╔═══██╗████╗ ████║██╔════╝    ╚══██╔══╝██╔═══██╗
██║ █╗ ██║█████╗  ██║     ██║     ██║   ██║██╔████╔██║█████╗         ██║   ██║   ██║
██║███╗██║██╔══╝  ██║     ██║     ██║   ██║██║╚██╔╝██║██╔══╝         ██║   ██║   ██║
╚███╔███╔╝███████╗███████╗╚██████╗╚██████╔╝██║ ╚═╝ ██║███████╗       ██║   ╚██████╔╝
 ╚══╝╚══╝ ╚══════╝╚══════╝ ╚═════╝ ╚═════╝ ╚═╝     ╚═╝╚══════╝       ╚═╝    ╚═════╝
██╗  ██╗██╗   ██╗██████╗ ██████╗ ██╗██████╗ ███╗   ███╗ █████╗ ████████╗ ██████╗██╗  ██╗
██║  ██║╚██╗ ██╔╝██╔══██╗██╔══██╗██║██╔══██╗████╗ ████║██╔══██╗╚══██╔══╝██╔════╝██║  ██║
███████║ ╚████╔╝ ██████╔╝██████╔╝██║██║  ██║██╔████╔██║███████║   ██║   ██║     ███████║
██╔══██║  ╚██╔╝  ██╔══██╗██╔══██╗██║██║  ██║██║╚██╔╝██║██╔══██║   ██║   ██║     ██╔══██║
██║  ██║   ██║   ██████╔╝██║  ██║██║██████╔╝██║ ╚═╝ ██║██║  ██║   ██║   ╚██████╗██║  ██║
╚═╝  ╚═╝   ╚═╝   ╚═════╝ ╚═╝  ╚═╝╚═╝╚═════╝ ╚═╝     ╚═╝╚═╝  ╚═╝   ╚═╝    ╚═════╝╚═╝  ╚═╝
            """
            + "\n"
        )
        print("%" * 80 + "\n")
        print(">>> Settings:")
        print(f"- {mode_alias=}")
        print(f"- {location=}")
        print(f"- {dev=}")
        print(f"- {manual_ignore_hybrid_sns=}")
        print(f"- {max_workers=}")

        print("\n" + "%" * 80 + "\n")
        print(">>> 1. Preparing relevant Hybrids at your location...\n")
    parts = prepare_parts(location, dev)

    # %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    # Apply --manual_ignore_hybrid_sns:
    # Pull the listed SNs out of the pool BEFORE prepare_data_sources
    # so we don't waste DB calls on parts the user already told us to skip,
    # and record them with an explicit reason so they show up in the
    # ignored-parts reporting together with algorithm-ignored parts.
    #
    # This is pure Python set/list work, not I/O -> sequential is fine,
    # threading would just add overhead.
    # %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    manual_ignored_parts = []
    if manual_ignore_hybrid_sns:
        remaining_parts = []
        for p in parts:
            if p["serial_number"] in manual_ignore_hybrid_sns:
                manual_ignored_parts.append(
                    [
                        p["part_id"],
                        p["serial_number"],
                        "Manually ignored by user via --manual_ignore_hybrid_sns",
                    ]
                )
            else:
                remaining_parts.append(p)
        parts = remaining_parts

    if printouts:
        print("%" * 80)
        print("\n>>> 2. Preparing data sources for pairing...\n")

    t0 = time.perf_counter()
    ignored_parts, kept_parts_and_scoring = prepare_data_sources(
        mode_alias, parts, max_workers=max_workers
    )
    print(
        f"prepare_data_sources took {time.perf_counter() - t0:.2f}s with {max_workers} workers"
    )

    # Prepend manual ignores so the operator sees them together with the
    # algorithm-ignored parts in the same flat list.
    ignored_parts = manual_ignored_parts + ignored_parts

    if printouts:
        print("\nIgnored parts:\n")
        for ip in ignored_parts:
            print(ip)
        print("\nKept parts for matching:\n")
        for kp in kept_parts_and_scoring:
            print(kp)
        print("\n" + "%" * 80)
        print("\n>>> 3. Running pairing algorithm...\n")

    # Guard: no parts survived all filters -> skip pairing entirely and
    # tell the operator why the pool is empty, instead of crashing in
    # numpy with an IndexError on arr[:, 2].
    if not kept_parts_and_scoring:
        n_manual = len(manual_ignored_parts)
        n_algo = len(ignored_parts) - n_manual
        n_total_seen = len(manual_ignored_parts) + len(kept_parts_and_scoring) + n_algo
        if printouts:
            print(
                "No parts survived for pairing.\n"
                f"  - Candidates seen after prepare_parts: {n_total_seen}\n"
                f"  - Filtered out by --manual_ignore_hybrid_sns: {n_manual}\n"
                f"  - Filtered out by the matching algorithm: {n_algo}\n"
                f"  - Surviving candidates: {len(kept_parts_and_scoring)}\n"
                "Skipping pairing. See 'Ignored parts' above for reasons."
            )
        return ignored_parts, kept_parts_and_scoring, [], 0.0, []

    pairings, total, leftover = run_pairing(
        kept_parts_and_scoring, algorithm=mode_alias
    )
    if printouts:
        if leftover != []:
            print(
                f"\nOdd number of parts for pairing, optimal leftover to minimize the total distance: {leftover}"
            )
        print(f"\nTotal distance for optimal pairing: {total}")
        print("\nOptimal pairings:\n")
        for pairing in pairings:
            print(pairing)
        print()
    return ignored_parts, kept_parts_and_scoring, pairings, total, leftover


def main():
    (ignored_parts, kept_parts_and_scoring, pairings, total, leftover) = hybridmatch(
        mode_alias,
        location,
        dev,
        printouts=True,
        manual_ignore_hybrid_sns=manual_ignore_hybrid_sns,
        max_workers=max_workers,
    )
    dt = datetime.now(UTC)

    md_content = f"# Hybridmatch logbook\n\nDate / time in UTC: {dt}\n\n## Settings\n\n"
    md_content += f"- `mode_alias` = `{mode_alias}`\n"
    md_content += f"- `location` = `{location}`\n"
    md_content += f"- `dev` = `{dev}`\n"
    md_content += f"- `manual_ignore_hybrid_sns` = `{manual_ignore_hybrid_sns}`\n"
    md_content += f"- `max_workers` = `{max_workers}`\n\n"

    # %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    # Step 1
    # %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    md_content += "## Step 1: Preparing relevant Hybrids at your location\n\n"
    md_content += (
        "Hybrids were selected from the DB via `prepare_parts` "
        "(location filter, latest-SN-spec validity, no Module parents; "
        "`dev` mode truncates to 2 parts).\n\n"
    )

    # %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    # Step 2 — Ignored parts and Kept parts, mirroring the console printout.
    # %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    md_content += "## Step 2: Preparing data sources for pairing\n\n"

    md_content += "### Ignored parts\n\n"
    if ignored_parts:
        for ip in ignored_parts:
            md_content += "- `[" + "  |  ".join(str(x) for x in ip) + "]`\n"
        md_content += "\n"
    else:
        md_content += "_None._\n\n"

    md_content += "### Kept parts for matching\n\n"
    if kept_parts_and_scoring:
        for kp in kept_parts_and_scoring:
            md_content += "- `[" + "  |  ".join(str(x) for x in kp) + "]`\n"
        md_content += "\n"
    else:
        md_content += "_None._\n\n"

    # %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    # Step 3 — Pairing results (or empty-pool explanation).
    # %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    md_content += "## Step 3: Running pairing algorithm\n\n"

    if not kept_parts_and_scoring:
        # Reproduce the same breakdown the console prints so the markdown
        # tells the operator why the pool is empty without them having to
        # re-run the script with verbose output.
        n_manual = sum(
            1
            for ip in ignored_parts
            if len(ip) > 2 and "Manually ignored" in str(ip[2])
        )
        n_algo = len(ignored_parts) - n_manual
        n_total_seen = len(ignored_parts) + len(kept_parts_and_scoring)
        md_content += "**No parts survived for pairing; pairing step was skipped.**\n\n"
        md_content += f"- Candidates seen after `prepare_parts`: {n_total_seen}\n"
        md_content += f"- Filtered out by `--manual_ignore_hybrid_sns`: {n_manual}\n"
        md_content += f"- Filtered out by the matching algorithm: {n_algo}\n"
        md_content += f"- Surviving candidates: {len(kept_parts_and_scoring)}\n\n"
    else:
        if leftover != []:
            md_content += (
                "Odd number of parts for pairing, optimal leftover to minimize "
                "the total distance:\n\n"
            )
            for lo in leftover:
                md_content += "- `[" + "  |  ".join(str(x) for x in lo) + "]`\n"
            md_content += "\n"

        md_content += f"Optimal total distance: `{total}`\n\n"

        md_content += "### Optimal pairings\n\n"
        if pairings:
            for pairing in pairings:
                l_pairing = list(pairing)
                hy_a = [str(content) for content in l_pairing[0]]
                hy_b = [str(content) for content in l_pairing[1]]
                md_content += "- " + ", ".join(hy_a) + "  +  " + ", ".join(hy_b) + "\n"
            md_content += "\n"
        else:
            md_content += "_None._\n\n"

    with open(f"pairings_{mode_alias}_{location}.md", "w") as f:
        f.write(md_content)


if __name__ == "__main__":
    main()

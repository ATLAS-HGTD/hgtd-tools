from argparse import ArgumentParser
from datetime import datetime
from datetime import UTC

import numpy as np

import data
import relation_validation
import util

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
        "Only_Hybrid_IV_VBD_closest",  # alternative: 1D sorting, Hybrid info only
        "Sensor_VBD_closest_Fallback_Hybrid_IV_VBD_closest",  # alternative: Sensor-Wafer info, or if not available, Hybrid info
        "Sensor_VBD_closest_AND_Hybrid_IV_VBD_closest_2D_DeltaR",  # alternative: both Sensor-Wafer info and Hybrid info, like CA-Clustering
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
    "--dev",
    dest="dev",
    help="[Optional] Developer mode. Limit number of parts to process.",
    default=False,
)
args = parser.parse_args()

mode_alias = args.mode_alias
location = args.location
dev = util.str2bool(args.dev)


# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
# Filter Hybrid parts for matching.
# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
def prepare_parts(location, dev):
    parts = util.get_relevant_parts("Hybrid")[0]
    # Hybrids for pairing must be located at the selected MA-site
    # and have a valid SN according to our latest SN specs
    # and not be connected yet to a Module
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


def prepare_data_sources(mode_alias, parts):
    # this will hold all Hybrids we have to ignore given the matching algorithm
    # and the reason why it can not be matched
    ignored_parts = []  # list of lists
    # this holds all Hybrids that passed matchable criteria
    # and the scores by which to match them
    kept_parts_and_scoring = []  # list of lists
    if mode_alias == "Only_Sensor_VBD_closest":
        for p in parts:
            decision, output_list = get_decision_scores_only_Sensor_VBD_closest(p)
            if decision:
                kept_parts_and_scoring.append(output_list)
            else:
                ignored_parts.append(output_list)

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
        return get_optimal_pairs_with_leftover_1D_On2(parts)


def hybridmatch(mode_alias, location, dev, printouts=False):
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

        print("\n" + "%" * 80 + "\n")
        print(">>> 1. Preparing relevant Hybrids at your location...\n")
    parts = prepare_parts(location, dev)
    if printouts:
        print("%" * 80)
        print("\n>>> 2. Preparing data sources for pairing...\n")
    ignored_parts, kept_parts_and_scoring = prepare_data_sources(mode_alias, parts)
    if printouts:
        print("\nIgnored parts:\n")
        for ip in ignored_parts:
            print(ip)
        print("\nKept parts for matching:\n")
        for kp in kept_parts_and_scoring:
            print(kp)
        print("\n" + "%" * 80)
        print("\n>>> 3. Running pairing algorithm...\n")
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


if __name__ == "__main__":
    (ignored_parts, kept_parts_and_scoring, pairings, total, leftover) = hybridmatch(
        mode_alias, location, dev, printouts=True
    )
    dt = datetime.now(UTC)
    md_content = f"# Hybridmatch logbook\n\nDate / time in UTC: {dt}\n\n## Settings\n\n"
    md_content += f"{mode_alias=}\n{location=}\n\n## Results\n\n"
    if leftover != []:
        md_content += f"Odd number of parts for pairing, optimal leftover to minimize the total distance: {leftover}\n\n"
    md_content += f"Optimal total distance: {total}\n\nOptimal pairings:\n\n"
    for pairing in pairings:
        l_pairing = list(pairing)
        hy_a = [str(content) for content in l_pairing[0]]
        hy_b = [str(content) for content in l_pairing[1]]
        md_content += ", ".join(hy_a) + "  +  " + ", ".join(hy_b) + "\n\n"
    with open(f"pairings.md", "w") as f:
        f.write(md_content)

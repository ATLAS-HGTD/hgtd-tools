from argparse import ArgumentParser

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


def optimal_pairs_with_leftover_1D(parts_scores):
    """
    AI-assisted. (GPT OSS 120B, JGU KI).

    Find the pairing that minimises the sum of absolute differences of the
    third column (the numeric value). If the number of rows is odd, one row
    is left unpaired; the function chooses the leftover that yields the
    smallest possible total distance.

    Returns
    -------
    pairs: list of (part_a, part_b)
    total_distance: float
    leftover: [] (even case, empty list) or [leftover_part] (odd case)
    """
    # convert
    arr = np.array(parts_scores, dtype=object)
    # sort by score (in third column)
    values = arr[:, 2].astype(float)
    order = np.argsort(values, kind="mergesort")
    sarr = arr[order]

    n = len(sarr)
    # even => trivial, chunk neighbors
    if n % 2 == 0:
        pairs = []
        total = 0.0
        for i in range(0, n, 2):
            a, b = sarr[i], sarr[i + 1]
            dist = abs(float(b[2]) - float(a[2]))
            total += dist
            pairs.append((a.tolist(), b.tolist()))
        return pairs, total, []

    # odd => decide which index to drop
    #
    #    Let diff[i] = sarr[i+1][2] - sarr[i][2]  (i from 0 to n-2)
    #    If we drop element j, the pairs are:
    #        (0,1), (2,3), ... up to the element just before j,
    #        then (j+1, j+2), (j+3, j+4), ... after j.
    #
    #    For fast evaluation we pre-compute two prefix-sums:
    #        pref_even[i] = sum of diff[0] + diff[2] + ... up to index i (even indices)
    #        pref_odd[i]  = sum of diff[1] + diff[3] + ... up to index i (odd indices)
    #
    #    Obtain the total distance for any possible j
    #    in O(1) and then pick the minimum.
    diffs = values[1:] - values[:-1]  # shape (n-1,)

    # prefix sums for even-indexed diffs (0,2,4,...)
    even_mask = np.arange(len(diffs)) % 2 == 0
    pref_even = np.cumsum(np.where(even_mask, diffs, 0.0))

    # prefix sums for odd‑indexed diffs (1,3,5,...)
    odd_mask = ~even_mask
    pref_odd = np.cumsum(np.where(odd_mask, diffs, 0.0))

    # Helper to get sum of even-indexed diffs up to (and including) idx
    def sum_even(upto):
        if upto < 0:
            return 0.0
        return float(pref_even[upto])

    # Helper to get sum of odd-indexed diffs up to (and including) idx
    def sum_odd(upto):
        if upto < 0:
            return 0.0
        return float(pref_odd[upto])

    # check every possible leftover index j (0 ... n-1)
    best_total = np.inf
    best_j = -1

    for j in range(n):
        # left side (elements before j)
        # If number of elements before j is even, they are paired (0-1,2-3,...)
        #   => we need the sum of *even* diffs up to j-2
        left_len = j  # count of elements left of j
        left_total = (
            sum_even(left_len - 2) if left_len % 2 == 0 else sum_odd(left_len - 2)
        )

        # right side (elements after j)
        # After removing j, the parity of the first element on the right flips.
        #   If left_len is even => the first element on the right takes the
        #   position with *odd* index in the original diff array,
        #   otherwise it takes the *even* index.
        right_len = n - j - 1
        if right_len == 0:
            right_total = 0.0
        else:
            # The first diff on the right is at index j (between j and j+1)
            start_idx = j
            # We need to sum every second diff starting from start_idx.
            # That is either the even-sum from start_idx to end
            # or the odd-sum, depending on the parity of start_idx.
            if start_idx % 2 == 0:
                # start at an even position => use even-indexed diffs for the right side
                right_total = sum_even(len(diffs) - 1) - sum_even(start_idx - 2)
            else:
                right_total = sum_odd(len(diffs) - 1) - sum_odd(start_idx - 2)

        total_j = left_total + right_total
        if total_j < best_total:
            best_total = total_j
            best_j = j

    # determine optimal pairing and leftover
    leftover_part = sarr[best_j].tolist()
    # Remove it from the sorted array
    remaining = np.delete(sarr, best_j)

    pairs = []
    for i in range(0, len(remaining), 2):
        a, b = remaining[i], remaining[i + 1]
        pairs.append((a.tolist(), b.tolist()))

    return pairs, best_total, [leftover_part]


def run_pairing(parts, algorithm):
    if algorithm == "Only_Sensor_VBD_closest":
        return optimal_pairs_with_leftover_1D(parts)


if __name__ == "__main__":
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
    print("%" * 80)
    print("\n>>> 2. Preparing data sources for pairing...\n")
    ignored_parts, kept_parts_and_scoring = prepare_data_sources(mode_alias, parts)
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
    if leftover != []:
        print(
            f"\nOdd number of parts for pairing, optimal leftover to minimize the total distance: {leftover}"
        )
    print(f"\nTotal distance for optimal pairing: {total}")
    print("\nOptimal pairings:\n")
    for pairing in pairings:
        print(pairing)
    print()

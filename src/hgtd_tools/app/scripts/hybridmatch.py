import os
import sys
import time
from argparse import ArgumentParser
from datetime import UTC, datetime

import numpy as np

from hgtd_tools import data, relation_validation, util

parser = ArgumentParser("Hybrid matcher (recommender system to pair Hybrids for HV- and LV-side)")
parser.add_argument(
    "--mode-alias",
    dest="mode_alias",
    help="Matching algorithm mode alias. (Default: %(default)s)",
    default="Only_Sensor_VBD_closest",
    choices=[
        "Only_Sensor_VBD_closest",
        # "Only_Hybrid_IV_VBD_closest",
        # "Sensor_VBD_closest_Fallback_Hybrid_IV_VBD_closest",
        # "Sensor_VBD_closest_AND_Hybrid_IV_VBD_closest_2D_DeltaR",
    ],
)
parser.add_argument(
    "--location",
    dest="location",
    help="Location short name for which to run hybrid matching recommendation. "
    "Optional when --hybrid-sns is given; combining both is an intersection "
    "by default (see --location-or-sns).",
    default=None,
    choices=data.MA_sites_to_monitor,
)
parser.add_argument(
    "--hybrid-sns",
    dest="hybrid_sns",
    help=(
        "Explicit list of Hybrid SNs to pair, instead of selecting by location. "
        "Accepted as: (a) a single SN, (b) multiple comma-separated SNs "
        "(e.g. '20WH...1,20WH...2'), or (c) a path to a .txt-like file with "
        "one SN per line ('#' starts a comment, blank lines are ignored). "
        "Duplicates are removed. Every SN is checked against the DB: it must "
        "exist as a Hybrid, pass the latest SN spec and have no Module parent "
        "yet (plus the location check when --location is also given). Rejected "
        "SNs are reported with the reason instead of being dropped silently."
    ),
    default=None,
)
scope = parser.add_mutually_exclusive_group()
scope.add_argument(
    "--location-and-sns",
    dest="location_scope",
    action="store_const",
    const="and",
    help=(
        "With both --location and --hybrid-sns: pair only the listed SNs that "
        "are also at that location (intersection). This is the default; the "
        "flag exists to make scripts explicit."
    ),
)
scope.add_argument(
    "--location-or-sns",
    dest="location_scope",
    action="store_const",
    const="or",
    help=(
        "With both --location and --hybrid-sns: pair the listed SNs (wherever "
        "they are) together with every other Hybrid at that location (union). "
        "The SNs themselves are still checked, just not for their location."
    ),
)
parser.set_defaults(location_scope="and")
parser.add_argument(
    "--strict-sns",
    dest="strict_sns",
    action="store_true",
    help=(
        "[Optional] Exit non-zero if any SN passed via --hybrid-sns was "
        "rejected and did not make it into the pairing set. The logbook is "
        "still written. (Default: %(default)s)"
    ),
)
parser.add_argument(
    "--manual_ignore_hybrid_sns",
    dest="manual_ignore_hybrid_sns",
    help=(
        "SNs of Hybrids to ignore in the pairing algorithm. Accepted as: "
        "(a) a single SN, (b) multiple comma-separated SNs "
        "(e.g. '20WH...1,20WH...2'), or (c) a path to a .txt-like file with "
        "one SN per line ('#' starts a comment, blank lines are ignored). "
        "Duplicates are removed. Ignored parts are reported with reason "
        "'Manually ignored by user' and excluded from pairing."
    ),
    default=None,
)
parser.add_argument(
    "--allow-mixed-sensor-designs",
    dest="allow_mixed_sensor_designs",
    help=(
        "[Optional] Allow pairing IHEP-IME and USTC-IME sensors with each other. "
        "By default the two sensor designs are never mixed: every VBD bin is "
        "built once per design (IHEP and USTC) and pairing runs inside each of "
        "those groups separately. Passing this flag drops the design axis, so "
        "each bin holds both designs. (Default: %(default)s)"
    ),
    action="store_true",
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

if args.location is None and not args.hybrid_sns:
    parser.error("pass --location, --hybrid-sns, or both")
if args.location_scope == "or" and not (args.location and args.hybrid_sns):
    parser.error(
        "--location-or-sns needs both --location and --hybrid-sns; "
        "with only one of them the scope is already unambiguous"
    )

mode_alias = args.mode_alias
location = args.location
max_workers = args.max_workers
allow_mixed_sensor_designs = args.allow_mixed_sensor_designs

# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
# VBD-bin configuration for the grouped pairing step.
#
# Parts with VBD < VBD_IGNORE_BELOW are excluded from pairing and reported
# alongside the other ignores with an explicit reason. The remaining parts
# are split into the bins below and paired within each bin separately,
# so a low-VBD hybrid is never matched against a high-VBD one.
#
# Bin convention: [lower_edge, next_lower_edge), i.e. half-open on the
# right. So:
#   vbd = 150.0  -> "150-160V"
#   vbd = 160.0  -> "160-170V"
#   ...
#   vbd = 190.0  -> ">190V"
#   vbd = 149.99 -> ignored (< VBD_IGNORE_BELOW)
#
# Change these three constants to retune the binning without touching
# the rest of the script.
# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
VBD_IGNORE_BELOW = 150.0
VBD_BIN_LOWER_EDGES = [150.0, 160.0, 170.0, 180.0, 190.0]
VBD_BIN_LABELS = [
    "150-160V",
    "160-170V",
    "170-180V",
    "180-190V",
    ">190V",
]
assert len(VBD_BIN_LABELS) == len(VBD_BIN_LOWER_EDGES), (
    "VBD_BIN_LABELS and VBD_BIN_LOWER_EDGES must have the same length; "
    "the last label is the open-ended bin for vbd >= VBD_BIN_LOWER_EDGES[-1]."
)
assert VBD_IGNORE_BELOW >= VBD_BIN_LOWER_EDGES[0], (
    "VBD_IGNORE_BELOW must be >= the lowest bin edge, otherwise values "
    "between the two would be clipped into the first bin instead of ignored."
)

# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
# Sensor design axis.
#
# Hybrids are paired per sensor design (IHEP-IME / USTC-IME) by default, so
# every group below (currently: every VBD bin) exists once per design.
# `--allow-mixed-sensor-designs` collapses the axis: the same code path then
# produces one group per bin, holding both designs.
#
# Any future grouping (2D DeltaR, fallback chains, ...) should keep this
# shape: the design axis stays the OUTER key, and the algorithm-specific
# grouping happens INSIDE a single design group.
# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
SENSOR_DESIGN_AXIS = tuple(data.SENSOR_DESIGNS)

DESIGN_UNKNOWN_REASON = (
    "Sensor design (IHEP/USTC) could not be determined from the Sensor/Wafer SN; "
    "excluded because pairing across designs is disabled by default "
    "(pass --allow-mixed-sensor-designs to keep such parts)"
)


# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
# Resolve --hybrid-sns & --manual_ignore_hybrid_sns into a clean list of unique SN strings.
# Accepts either an inline value (single SN or comma-separated) or a path
# to a text file with one SN per line.
# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
def _looks_like_file_path(s):
    return os.path.sep in s or s.lower().endswith((".txt", ".list", ".ignore", ".sn", ".sns"))


def _parse_sn_list(raw, flag_name):
    """Inline SNs (single or comma-separated) or a path to a file of SNs."""
    if raw is None:
        return []
    if os.path.isfile(raw):
        with open(raw) as f:
            sns = [line.strip() for line in f if line.strip() and not line.lstrip().startswith("#")]
    elif _looks_like_file_path(raw):
        raise FileNotFoundError(f"{flag_name}: file not found: {raw}")
    elif "," in raw:
        sns = [s.strip() for s in raw.split(",") if s.strip()]
    else:
        sns = [raw.strip()] if raw.strip() else []

    seen = set()
    deduped = []
    for sn in sns:
        if sn not in seen:
            seen.add(sn)
            deduped.append(sn)
    return deduped


manual_ignore_hybrid_sns = _parse_sn_list(
    args.manual_ignore_hybrid_sns, "--manual_ignore_hybrid_sns"
)
hybrid_sns = _parse_sn_list(args.hybrid_sns, "--hybrid-sns")
location_scope = args.location_scope
dev = util.str2bool(args.dev)


SN_REJECT_UNKNOWN = "not found in the DB as a Hybrid (typo, or not registered yet)"
SN_REJECT_INVALID = "SN does not pass the latest SN spec"
SN_REJECT_ASSEMBLED = "already has a Module parent (already assembled into a Module)"
SN_REJECT_LOCATION = "not at the requested location ({location})"


def _location_ids(shortname):
    """Location ids for a shortname; the table may hold a scalar or a sequence."""
    ids = data.relevant_location_IDs_by_shortname.get(shortname)
    if ids is None:
        return set()
    if isinstance(ids, (list, tuple, set)):
        return {str(i) for i in ids}
    return {str(ids)}


def resolve_hybrid_sns(hybrids, hybrid_sns, location=None, check_location=True):
    """Select the requested Hybrids from an already-loaded Hybrid list.

    Every requested SN ends up either in the returned parts list or in
    `rejected` with a reason, so a typo cannot silently shrink the pairing
    set. Returns (parts, rejected), rejected entries of the form
    [sn, reason].

    Checks, in order (cheapest and most fundamental first, so an out-of-scope
    part costs no API call):
      1. SN present among the Hybrids loaded from the DB
      2. SN passes the latest SN spec
      3. currently at `location`, if `check_location` and a location is given
      4. no Module parent yet

    "Is a Hybrid" needs no separate test: the list handed in is the Hybrid
    list, so a non-Hybrid SN simply fails check 1.
    """
    by_sn = {}
    for part in hybrids:
        by_sn.setdefault(str(part.get("serial_number") or "").strip(), part)

    wanted_ids = _location_ids(location) if (check_location and location is not None) else None
    parts, rejected = [], []
    for sn in hybrid_sns:
        part = by_sn.get(sn)
        if part is None:
            rejected.append([sn, SN_REJECT_UNKNOWN])
            continue
        if not util.check_SN_valid(sn)[0]:
            rejected.append([sn, SN_REJECT_INVALID])
            continue
        if wanted_ids is not None:
            part_loc = str((part.get("location") or {}).get("location_id"))
            if part_loc not in wanted_ids:
                rejected.append([sn, SN_REJECT_LOCATION.format(location=location)])
                continue
        if util.get_parents(part["part_id"], ofKind="Module")[0]:
            rejected.append([sn, SN_REJECT_ASSEMBLED])
            continue
        parts.append(part)
    return parts, rejected


# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
# Filter Hybrid parts for matching.
# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
def prepare_parts(location, dev, hybrid_sns=None, location_scope="and"):
    """Hybrids to pair, in one of three selection modes.

    * only --location        -> the existing location filter, unchanged
    * only --hybrid-sns      -> exactly the listed SNs, no location check
    * both, scope "and"      -> listed SNs that are also at the location
    * both, scope "or"       -> listed SNs (wherever) + everything else at
                                the location

    Returns (parts, rejected_sns); rejected_sns is empty whenever no SN list
    is involved, and never contains a SN that made it into `parts`.
    """
    hybrids = util.get_relevant_parts("Hybrid")[0]

    if not hybrid_sns:
        parts = util.select_parts(
            hybrids,
            location_shortname=location,
            check_valid_SN_latest_spec=True,
            no_parents_ofKind="Module",
        )
        rejected_sns = []
    else:
        check_location = location is not None and location_scope == "and"
        parts, rejected_sns = resolve_hybrid_sns(
            hybrids, hybrid_sns, location=location, check_location=check_location
        )
        if location is not None and location_scope == "or":
            at_location = util.select_parts(
                hybrids,
                location_shortname=location,
                check_valid_SN_latest_spec=True,
                no_parents_ofKind="Module",
            )
            seen = {int(p["part_id"]) for p in parts}
            parts += [p for p in at_location if int(p["part_id"]) not in seen]
            # A SN rejected above can still be a legitimate member of the
            # location population (e.g. rejected for its location in "and"
            # mode, which "or" does not test). Do not report a part as
            # rejected while it is being paired.
            present = {str(p.get("serial_number") or "").strip() for p in parts}
            rejected_sns = [r for r in rejected_sns if r[0] not in present]

    if dev:
        parts = parts[:2]
    return parts, rejected_sns


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
#
## Kept records always have the shape
##   [part_id, part_SN, vbd_value, sensor_design_or_None]
## so the design travels with the part through grouping, pairing and reporting.


def get_decision_scores_only_Sensor_VBD_closest(p):
    part_id = p["part_id"]
    part_SN = p["serial_number"]

    children_S = util.get_children(part_id, ofKind="Sensor")[0]
    rel_val_result, rel_val_reason = relation_validation.validate_HY_chi_S(children_S)
    if not rel_val_result:
        return False, [part_id, part_SN, rel_val_reason]

    # Sensor child exists, valid connection: exactly one, at empty position.
    child_S = children_S[0]["part"]
    child_S_part_id = child_S["part_id"]
    child_S_part_SN = child_S["serial_number"]

    parents_W = util.get_parents(child_S_part_id, ofKind="Wafer")[0]
    rel_val_result, rel_val_reason = relation_validation.validate_S_par_W(parents_W)
    if not rel_val_result:
        return False, [
            part_id,
            part_SN,
            f"Relation to Sensor is valid, but problem with Sensor: {rel_val_reason}",
        ]

    parent_W_part_SN = parents_W[0]["part_parent"]["serial_number"]

    vbd_value, vbd_reason = util.get_vbd_for_sensor_via_wafer(
        child_S_part_SN, parent_W_part_SN, metric="VBD_AVERAGE"
    )
    if vbd_reason != "":
        # Fallback: obtain IV curves for the pads and calculate VBD manually.
        vbd_value, vbd_reason = util.get_vbd_for_sensor_via_iv(child_S_part_SN)
        if vbd_reason != "":
            return False, [
                part_id,
                part_SN,
                (
                    f"Relation to Sensor is valid, relation to Wafer is valid, but problem with VBD retrieval, "
                    f"after already falling back to manual calculation of VBD from IV because VBD value not stored in DB: {vbd_reason}"
                ),
            ]

    # Design is resolved here, next to the SNs it is derived from, but NOT
    # enforced here: whether an unknown design is fatal depends on
    # --allow-mixed-sensor-designs, which is applied at grouping time.
    sensor_design, _design_reason = util.resolve_sensor_design(child_S_part_SN, parent_W_part_SN)

    return True, [part_id, part_SN, vbd_value, sensor_design]


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
    ignored_parts = []
    kept_parts_and_scoring = []
    if mode_alias == "Only_Sensor_VBD_closest":
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
    if not parts_scores:
        return [], 0.0, []

    arr = np.array(parts_scores, dtype=object)
    # sort by the comparison column (was hardcoded to 2 before)
    order = np.argsort(arr[:, at_column].astype(float), kind="mergesort")
    sarr = arr[order]

    n = len(sarr)
    if n % 2 == 0:
        return (*get_pairs_totaldiff_via_chunking(sarr, at_column), [])

    best_total = np.inf
    best_j = -1
    best_pairs = []
    for j in range(n):
        remain = np.delete(sarr, j, axis=0)
        pairs, tot = get_pairs_totaldiff_via_chunking(remain, at_column)
        if tot < best_total:
            best_total, best_j, best_pairs = tot, j, pairs

    leftover = sarr[best_j].tolist()
    return best_pairs, best_total, [leftover]


def run_pairing(parts, algorithm):
    if algorithm == "Only_Sensor_VBD_closest":
        if not parts:
            return [], 0.0, []
        return get_optimal_pairs_with_leftover_1D_On2(parts)
    else:
        raise NotImplementedError


# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
# VBD-bin assignment.
#
# Given a kept part of the form [part_id, part_SN, vbd_value, design], return:
#   ("ignore", reason_string)   if vbd < VBD_IGNORE_BELOW
#   ("group",  bin_label)       otherwise
#
# Bin convention: [lower_edge_i, lower_edge_{i+1}), except the last bin
# which is open-ended (>= last edge).
# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
def assign_vbd_bin(part_record):
    # record is [part_id, part_SN, vbd_value, design]; never unpack the whole
    # thing positionally, the design field is optional for older callers.
    vbd_value = part_record[2]
    try:
        vbd = float(vbd_value)
    except (TypeError, ValueError):
        return ("ignore", f"VBD value is not a valid number: {vbd_value!r}")

    if vbd < VBD_IGNORE_BELOW:
        return ("ignore", f"VBD ({vbd} V) is below {VBD_IGNORE_BELOW} V; excluded from pairing")

    edges = np.asarray(VBD_BIN_LOWER_EDGES, dtype=float)
    idx = int(np.searchsorted(edges, vbd, side="right")) - 1
    if idx < 0:
        return (
            "ignore",
            f"VBD ({vbd} V) is below the lowest bin edge {edges[0]} V; excluded from pairing",
        )
    return ("group", VBD_BIN_LABELS[min(idx, len(VBD_BIN_LABELS) - 1)])


# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
# Grouping, with the sensor design as the OUTER key.
#
# A group is identified by (design, label):
#   design = "IHEP" / "USTC"  -> non-mixed default
#   design = None             -> --allow-mixed-sensor-designs (single set of
#                                labels holding both designs)
#
# `group_parts` is generic on purpose: it takes the label space and the
# key function, so a future algorithm only has to supply its own
# `group_key_fn` (returning ("ignore", reason) or ("group", label)) and the
# design axis keeps working without touching the rest of the pipeline.
# %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
def _group_keys(allow_mixed_sensor_designs, labels=None):
    """Ordered list of (design, label) keys defining report order."""
    labels = list(labels or VBD_BIN_LABELS)
    if allow_mixed_sensor_designs:
        return [(None, label) for label in labels]
    return [(design, label) for design in SENSOR_DESIGN_AXIS for label in labels]


def group_title(design, label):
    """Human-readable group name, e.g. 'IHEP | 150-160V' or '150-160V'."""
    return f"{design} | {label}" if design else label


def group_parts(
    records,
    allow_mixed_sensor_designs=False,
    group_key_fn=None,
    group_labels=None,
):
    """Split kept records into (sensor design, label) groups.

    group_key_fn(record) -> ("ignore", reason) | ("group", label).
    Defaults to `assign_vbd_bin` over `VBD_BIN_LABELS`.

    Returns (grouped, ignored, kept_in_groups). `kept_in_groups` is the
    authoritative kept list: every record is either in it or in `ignored`,
    never both.
    """
    group_key_fn = group_key_fn or assign_vbd_bin
    grouped = {key: [] for key in _group_keys(allow_mixed_sensor_designs, group_labels)}
    ignored = []
    for rec in records:
        design = rec[3] if len(rec) > 3 else None
        if design is None and not allow_mixed_sensor_designs:
            ignored.append([rec[0], rec[1], DESIGN_UNKNOWN_REASON])
            continue
        kind, payload = group_key_fn(rec)
        if kind == "ignore":
            ignored.append([rec[0], rec[1], payload])
            continue
        key = (None if allow_mixed_sensor_designs else design, payload)
        if key not in grouped:  # be robust against unexpected labels
            grouped[key] = []
        grouped[key].append(rec)
    kept_in_groups = [rec for key in grouped for rec in grouped[key]]
    return grouped, ignored, kept_in_groups


def group_by_vbd_bin(kept_parts_and_scoring, allow_mixed_sensor_designs=False):
    """VBD binning, once per sensor design unless mixing is allowed."""
    return group_parts(
        kept_parts_and_scoring,
        allow_mixed_sensor_designs=allow_mixed_sensor_designs,
        group_key_fn=assign_vbd_bin,
        group_labels=VBD_BIN_LABELS,
    )


def empty_group_results(allow_mixed_sensor_designs=False, labels=None):
    return [
        {
            "design": design,
            "label": label,
            "title": group_title(design, label),
            "n": 0,
            "pairs": [],
            "total": 0.0,
            "leftover": [],
        }
        for design, label in _group_keys(allow_mixed_sensor_designs, labels)
    ]


def pair_within_groups(grouped_by_bin, algorithm):
    """Run the pairing algorithm inside every (design, label) group."""
    group_results = []
    for (design, label), parts_in_group in grouped_by_bin.items():
        pairs, total, leftover = run_pairing(parts_in_group, algorithm=algorithm)
        group_results.append(
            {
                "design": design,
                "label": label,
                "title": group_title(design, label),
                "n": len(parts_in_group),
                "pairs": pairs,
                "total": total,
                "leftover": leftover,
            }
        )
    return group_results


def hybridmatch(
    mode_alias,
    location,
    dev,
    printouts=False,
    manual_ignore_hybrid_sns=[],
    max_workers=4,
    allow_mixed_sensor_designs=False,
    hybrid_sns=None,
    location_scope="and",
    strict_sns=False,
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
        print(f"- {hybrid_sns=}")
        print(f"- {location_scope=}")
        print(f"- {strict_sns=}")
        print(f"- {dev=}")
        print(f"- {manual_ignore_hybrid_sns=}")
        print(f"- {max_workers=}")
        print(f"- {allow_mixed_sensor_designs=}")
        print(f"- VBD-bin grouping: ignore below {VBD_IGNORE_BELOW} V, bins = {VBD_BIN_LABELS}")
        if allow_mixed_sensor_designs:
            print("- Sensor designs: IHEP and USTC are MIXED within each bin (opt-in)")
        else:
            print(
                f"- Sensor designs: NOT mixed, every bin exists once per design "
                f"({list(SENSOR_DESIGN_AXIS)})"
            )

        print("\n" + "%" * 80 + "\n")
        print(">>> 1. Preparing relevant Hybrids ...\n")
    parts, rejected_sns = prepare_parts(
        location, dev, hybrid_sns=hybrid_sns, location_scope=location_scope
    )

    if printouts and rejected_sns:
        print(f"Rejected SNs from --hybrid-sns ({len(rejected_sns)}):\n")
        for sn, reason in rejected_sns:
            print(f"  {sn}: {reason}")
        print()

    # %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    # Apply --manual_ignore_hybrid_sns before any DB work.
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
    print(f"prepare_data_sources took {time.perf_counter() - t0:.2f}s with {max_workers} workers")

    ignored_parts = manual_ignored_parts + ignored_parts

    # Bin BEFORE reporting: a part leaves the kept list at the same moment it
    # enters the ignored list, so the two reports stay disjoint. The design
    # axis is applied here, i.e. every bin is created once per design.
    grouped_by_bin, ignored_vbd, kept_in_bins = group_by_vbd_bin(
        kept_parts_and_scoring,
        allow_mixed_sensor_designs=allow_mixed_sensor_designs,
    )
    ignored_parts = ignored_parts + ignored_vbd
    kept_parts_and_scoring = kept_in_bins

    n_by_design = {}
    for rec in kept_in_bins:
        design = rec[3] if len(rec) > 3 else None
        key = design or "unknown"
        n_by_design[key] = n_by_design.get(key, 0) + 1

    stats = {
        "n_manual": len(manual_ignored_parts),
        "n_vbd": len(ignored_vbd),
        "n_algo": len(ignored_parts) - len(manual_ignored_parts) - len(ignored_vbd),
        "n_kept": len(kept_parts_and_scoring),
        "allow_mixed_sensor_designs": allow_mixed_sensor_designs,
        "n_by_design": n_by_design,
        "hybrid_sns": list(hybrid_sns or []),
        "location_scope": location_scope,
        "n_sns_rejected": len(rejected_sns),
        "rejected_sns": rejected_sns,
    }

    if printouts:
        print("\nIgnored parts:\n")
        for ip in ignored_parts:
            print(ip)
        print("\nKept parts for matching:\n")
        for kp in kept_parts_and_scoring:
            print(kp)
        print(f"\nKept parts per sensor design: {n_by_design}")
        print("\n" + "%" * 80)
        print("\n>>> 3. Running pairing algorithm (grouped by sensor design and VBD bin)...\n")

    if not kept_parts_and_scoring:
        if printouts:
            print(
                "No parts survived for pairing.\n"
                f"  - Rejected before selection (--hybrid-sns): {stats['n_sns_rejected']}\n"
                f"  - Filtered out by --manual_ignore_hybrid_sns: {stats['n_manual']}\n"
                f"  - Filtered out by VBD < {VBD_IGNORE_BELOW} V / unbinnable VBD / unknown design: {stats['n_vbd']}\n"
                f"  - Filtered out by the matching algorithm: {stats['n_algo']}\n"
                "Skipping pairing. See 'Ignored parts' above for reasons."
            )
        return (
            ignored_parts,
            kept_parts_and_scoring,
            empty_group_results(allow_mixed_sensor_designs),
            0.0,
            [],
            stats,
        )

    group_results = pair_within_groups(grouped_by_bin, algorithm=mode_alias)

    all_pairs = [p for gr in group_results for p in gr["pairs"]]
    total = sum(gr["total"] for gr in group_results)
    leftover = [lo for gr in group_results for lo in gr["leftover"]]

    if printouts:
        for gr in group_results:
            print(f"\n--- Group {gr['title']} ({gr['n']} parts) ---")
            if gr["leftover"]:
                print(
                    f"  Odd count in group, optimal leftover to minimize total distance: {gr['leftover']}"
                )
            print(f"  Total distance for optimal pairing in this group: {gr['total']}")
            print("  Optimal pairings in this group:")
            for pairing in gr["pairs"]:
                print(f"    {pairing}")

        if leftover:
            print(
                f"\nOdd-count groups -> aggregated optimal leftovers (sum across groups): {leftover}"
            )
        print(f"\nAggregated total distance across all groups: {total}")
        print(f"\nAggregated optimal pairings ({len(all_pairs)} pairs):\n")
        for pairing in all_pairs:
            print(pairing)
        print()

    return ignored_parts, kept_parts_and_scoring, group_results, total, leftover, stats


def main():
    (ignored_parts, kept_parts_and_scoring, group_results, total, leftover, stats) = hybridmatch(
        mode_alias,
        location,
        dev,
        printouts=True,
        manual_ignore_hybrid_sns=manual_ignore_hybrid_sns,
        max_workers=max_workers,
        allow_mixed_sensor_designs=allow_mixed_sensor_designs,
        hybrid_sns=hybrid_sns,
        location_scope=location_scope,
        strict_sns=args.strict_sns,
    )
    dt = datetime.now(UTC)

    md_content = f"# Hybridmatch logbook\n\nDate / time in UTC: {dt}\n\n## Settings\n\n"
    md_content += f"- `mode_alias` = `{mode_alias}`\n"
    md_content += f"- `location` = `{location}`\n" if location else "- `location` = *(not used)*\n"
    md_content += f"- `hybrid_sns` = `{hybrid_sns}`\n"
    md_content += f"- `location_scope` = `{location_scope}`\n"
    md_content += f"- `dev` = `{dev}`\n"
    md_content += f"- `manual_ignore_hybrid_sns` = `{manual_ignore_hybrid_sns}`\n"
    md_content += f"- `max_workers` = `{max_workers}`\n"
    md_content += f"- `allow_mixed_sensor_designs` = `{allow_mixed_sensor_designs}`\n"
    md_content += (
        f"- VBD-bin grouping: ignore below `{VBD_IGNORE_BELOW}` V, bins = `{VBD_BIN_LABELS}`\n"
    )
    if allow_mixed_sensor_designs:
        md_content += (
            "- Sensor design axis: **dropped** (IHEP and USTC mixed inside each bin, opt-in)\n\n"
        )
    else:
        md_content += (
            f"- Sensor design axis: **enforced**, every bin exists once per design "
            f"`{list(SENSOR_DESIGN_AXIS)}`\n\n"
        )

    md_content += "## Step 1: Preparing relevant Hybrids\n\n"
    if hybrid_sns and location and location_scope == "or":
        md_content += (
            f"Union of two populations: the `{len(hybrid_sns)}` requested SNs "
            f"(wherever they are, still checked for SN spec and an existing "
            f"Module parent) and every valid, not-yet-assembled Hybrid at "
            f"location `{location}`. Duplicates are paired once. "
            "`dev` mode truncates to 2 parts.\n\n"
        )
    elif hybrid_sns:
        md_content += (
            f"Hybrids were taken from the explicit SN list (`{len(hybrid_sns)}` "
            "unique SNs after de-duplication)"
            + (f", restricted to location `{location}`" if location else "")
            + "; each SN was checked for existence, SN spec and an existing "
            "Module parent. `dev` mode truncates to 2 parts.\n\n"
        )
    else:
        md_content += (
            "Hybrids were selected from the DB via `prepare_parts` "
            "(location filter, latest-SN-spec validity, no Module parents; "
            "`dev` mode truncates to 2 parts).\n\n"
        )

    if hybrid_sns:
        if stats["rejected_sns"]:
            md_content += "### Rejected SNs from `--hybrid-sns`\n\n"
            for sn, reason in stats["rejected_sns"]:
                md_content += f"- `{sn}`: {reason}\n"
            md_content += "\n"
        else:
            md_content += "All requested SNs were accepted.\n\n"

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

    if stats.get("n_by_design"):
        md_content += "### Kept parts per sensor design\n\n"
        for design, count in stats["n_by_design"].items():
            md_content += f"- `{design}`: {count}\n"
        md_content += "\n"

    md_content += "## Step 3: Running pairing algorithm (grouped by sensor design and VBD bin)\n\n"

    if not kept_parts_and_scoring:
        n_total_seen = len(ignored_parts) + len(kept_parts_and_scoring)
        md_content += "**No parts survived for pairing; pairing step was skipped.**\n\n"
        md_content += f"- Candidates seen after `prepare_parts`: {n_total_seen}\n"
        md_content += f"- Filtered out by `--manual_ignore_hybrid_sns`: {stats['n_manual']}\n"
        md_content += (
            f"- Filtered out by VBD < `{VBD_IGNORE_BELOW}` V / unbinnable VBD / "
            f"unknown sensor design: {stats['n_vbd']}\n"
        )
        md_content += f"- Filtered out by the matching algorithm: {stats['n_algo']}\n"
        md_content += f"- Surviving candidates: {stats['n_kept']}\n\n"
    else:
        for gr in group_results:
            md_content += f"### Group `{gr['title']}` ({gr['n']} parts)\n\n"
            if gr["leftover"]:
                md_content += (
                    "Odd number of parts in this group, optimal leftover to minimize "
                    "the total distance:\n\n"
                )
                for lo in gr["leftover"]:
                    md_content += "- `[" + "  |  ".join(str(x) for x in lo) + "]`\n"
                md_content += "\n"
            md_content += f"Total distance in this group: `{gr['total']}`\n\n"
            md_content += "Optimal pairings in this group:\n\n"
            if gr["pairs"]:
                for pairing in gr["pairs"]:
                    l_pairing = list(pairing)
                    hy_a = [str(content) for content in l_pairing[0]]
                    hy_b = [str(content) for content in l_pairing[1]]
                    md_content += "- " + ", ".join(hy_a) + "  +  " + ", ".join(hy_b) + "\n"
                md_content += "\n"
            else:
                md_content += "_None._\n\n"

        md_content += "### Aggregated across all groups\n\n"
        if leftover:
            md_content += (
                "Odd-count groups -> aggregated optimal leftovers (sum across groups):\n\n"
            )
            for lo in leftover:
                md_content += "- `[" + "  |  ".join(str(x) for x in lo) + "]`\n"
            md_content += "\n"
        md_content += f"Aggregated total distance: `{total}`\n\n"

    suffix = "_mixeddesigns" if allow_mixed_sensor_designs else ""
    if hybrid_sns:
        suffix += f"_sns{len(hybrid_sns)}"
        if location:
            suffix += f"_{location_scope}"
    with open(f"pairings_{mode_alias}_{location or 'sns'}{suffix}.md", "w") as f:
        f.write(md_content)

    if args.strict_sns and stats["rejected_sns"]:
        print(
            f"\n[error] {len(stats['rejected_sns'])} SN(s) from --hybrid-sns were "
            f"rejected (see above); exiting non-zero because of --strict-sns.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

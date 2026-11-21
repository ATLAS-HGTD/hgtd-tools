"""Shared read/validate layer for the HGTD CLIs.

Used by ``count.py`` (tables, CSV, JSON) and by ``order.py`` (the relation
validation report). Everything here is read-only: no part, shipment or tree
record is ever written.

The two consumers differ only in presentation, so the SN classification, the
relation-validation dispatch and the per-site attribution live here exactly
once. That is the point: the numbers in ``validation.md`` and the numbers
printed by ``hgtd-count`` cannot drift apart.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from hgtd_tools import data, relation_validation, util

# re-exported so callers can catch API failures without importing util
API_ERRORS = util.API_ERRORS

# validation mode alias -> Kind of Part it validates
VALIDATION_CATEGORY = {
    "Module Loading": "Detector Unit",
    "Module Assembly": "Module",
    "Hybridization": "Hybrid",
    "Sensor_Parents": "Sensor",
}
VALIDATABLE = {cat: mode for mode, cat in VALIDATION_CATEGORY.items()}

VALIDATORS = {
    "Module Loading": relation_validation.validate_DU,
    "Module Assembly": relation_validation.validate_module,
    "Hybridization": relation_validation.validate_hybrid,
    "Sensor_Parents": relation_validation.validate_sensor,
}

# prefix of the "validation_result_<prefix>..." / "validation_reason_<prefix>..."
# keys that belong to a given mode
REASON_PREFIX = {
    "Module Loading": "DU",
    "Module Assembly": "MO",
    "Hybridization": "HY",
    "Sensor_Parents": "S_par",
}

# the child relations each mode checks, in reporting order
CHILD_CHECKS = {
    "Module Loading": ("DU_chi_MO", "DU_chi_SU"),
    "Module Assembly": ("MO_chi_MF", "MO_chi_HY"),
    "Hybridization": ("HY_chi_S",),
}

# manufacturer shortnames the nightly report monitors, per mode
MONITORED_SITES = {
    "Module Loading": list(data.ML_sites_to_monitor),
    "Module Assembly": list(data.MA_sites_to_monitor),
    "Hybridization": list(data.HY_sites_to_monitor),
    "Sensor_Parents": list(data.S_W_manus_to_monitor),
}

# the kinds data.py offers, split the way the reports split them
CAT_SETS = {
    "all": list(data.all_cats),
    "public": list(data.public_cats),
    "test": list(data.test_cats),
}

LIST_TARGETS = ("all", "valid", "invalid", "fake", "connected", "failed", "new")

# name_label marker of digital modules: SN-valid, but not physically validated
DIGITAL_LABEL = "_Digital"


# === Loading and filtering


def load_parts(kind, filters=None, sites=None, dev=None, use_local=False):
    """Fetch one Kind of Part, apply `select_parts` filters and site narrowing.

    Returns (parts, n_loaded) where n_loaded is the unfiltered DB count, so a
    report can show "x of y".
    """
    parts, _ = util.get_relevant_parts(kind, useLocal=bool(use_local) and kind == "Slot")
    loaded = len(parts)
    if filters:
        parts = util.select_parts(parts, **filters)
    parts = filter_sites(parts, sites)
    if dev is not None:
        parts = parts[:dev]
    return parts, loaded


def resolve_sites(raw, mode):
    """Manufacturer shortnames to restrict to, or None for "all".

    "monitored" expands to the site list data.py defines for this mode, which
    is the set the nightly report covers.
    """
    if raw is None:
        return None
    if raw.strip().lower() in ("monitored", "default"):
        if mode is None:
            raise ValueError(
                "'monitored' needs a Kind of Part with a relation validation "
                f"({', '.join(sorted(VALIDATABLE))})"
            )
        return list(MONITORED_SITES[mode])
    return [s.strip() for s in raw.split(",") if s.strip()]


def filter_sites(parts, sites):
    """Keep parts manufactured at any of `sites` (union, not intersection)."""
    if not sites:
        return parts
    keep_ids = set()
    for site in sites:
        keep_ids |= {int(p["part_id"]) for p in util.select_parts(parts, manu_shortname=site)}
    return [p for p in parts if int(p["part_id"]) in keep_ids]


def parts_by_site(parts, sites):
    """{site: [parts]} in `sites` order; a part may appear under several sites."""
    return {site: util.select_parts(parts, manu_shortname=site) for site in sites}


def display_filters(filters):
    """Filters as shown in a report header (lists joined, no-ops dropped)."""
    shown = {}
    for key, value in (filters or {}).items():
        if value is None or value is False or value == "":
            continue
        if isinstance(value, (list, tuple)):
            if not value:
                continue
            value = ", ".join(str(v) for v in value)
        shown[key] = value
    return shown


# === SN category split (mirrors the validation report)


def split_by_sn(parts, mode_alias=None):
    """Split `parts` into (valid, invalid, fake) SN categories.

    For "Module Assembly" digital modules (name_label contains "_Digital") are
    valid in terms of SN but are not validated; the report counts them as
    invalid, so they are moved over here too.
    """
    valid = util.select_parts(parts, check_valid_SN_latest_spec=True)
    invalid = util.select_parts(parts, check_invalid_SN_latest_spec=True)
    if mode_alias == "Module Assembly":
        digital = util.select_parts(valid, name_label_does_include=DIGITAL_LABEL)
        valid = util.select_parts(valid, name_label_does_not_include=DIGITAL_LABEL)
        invalid = invalid + digital
    fake = util.select_parts(parts, check_fake_SN=True)
    return valid, invalid, fake


# === Relation validation


def validate_parts(valid_parts, mode_alias, max_workers=4):
    """{part_id: raw validation result} for every part, validated concurrently.

    A failed API call is stored as ``{"validation_error": "<reason>"}`` instead
    of aborting the run, so one unreachable part does not lose the report.
    """
    if not valid_parts:
        return {}
    validator = VALIDATORS[mode_alias]

    def run(part):
        try:
            return validator(int(part["part_id"]))
        except API_ERRORS as exc:
            return {"validation_error": str(exc)}

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        results = list(ex.map(run, valid_parts))
    return {int(p["part_id"]): r for p, r in zip(valid_parts, results)}


def failure_reasons(result, mode_alias):
    """Human-readable reasons for a failed relation validation."""
    if "validation_error" in result:
        return [f"API error: {result['validation_error']}"]
    prefix = REASON_PREFIX[mode_alias]
    reasons = []
    for key, value in result.items():
        if not key.startswith("validation_result_"):
            continue
        suffix = key[len("validation_result_") :]
        if not suffix.startswith(prefix):
            continue
        if value is True or value == "new":
            continue
        reason = result.get("validation_reason_" + suffix)
        reasons.append(f"{suffix}: {reason}" if reason else f"{suffix}: failed")
    return reasons


def classify_validation_result(result, mode_alias):
    """("connected" | "new" | "failed", [reasons]) for one part."""
    if result.get("validation_result_overall"):
        return "connected", []
    if (
        mode_alias == "Sensor_Parents"
        and result.get("validation_result_S_par_HY") == "new"
        and result.get("validation_result_S_par_W")
    ):
        # Wafer parent fine, Hybrid parent simply not there yet
        return "new", []
    return "failed", failure_reasons(result, mode_alias)


def classify_outcomes(raw, mode_alias):
    """{part_id: (outcome, reasons)} from the raw results of validate_parts."""
    return {pid: classify_validation_result(r, mode_alias) for pid, r in raw.items()}


# === Counting


def outcome_of(outcomes, part):
    return (outcomes or {}).get(int(part["part_id"]), ("failed", []))[0]


def counts_for(parts_all, valid, invalid, fake, outcomes=None, validate=False):
    counts = {
        "total": len(parts_all),
        "valid": len(valid),
        "invalid": len(invalid),
        "fake": len(fake),
    }
    if validate:
        connected = sum(1 for p in valid if outcome_of(outcomes, p) == "connected")
        new = sum(1 for p in valid if outcome_of(outcomes, p) == "new")
        counts["valid_connected"] = connected
        counts["valid_new"] = new
        counts["valid_failed"] = len(valid) - connected - new
    return counts


# === Grouping


def _shortname_lookup(mapping):
    return {str(v): k for k, v in mapping.items()}


def group_label(part, group_by, inv_manu, inv_loc):
    if group_by == "manufacturer":
        ref = part.get("manufacturer") or {}
        mid = str(ref.get("manufacturer_id"))
        return inv_manu.get(mid) or str(ref.get("manufacturer_name") or mid)
    if group_by == "location":
        ref = part.get("location") or {}
        lid = str(ref.get("location_id"))
        return inv_loc.get(lid) or str(ref.get("location_name") or lid)
    return "all"


def build_groups(parts, valid, invalid, fake, outcomes, group_by, validate):
    """Per-group counts, sorted by size.

    Sorted, not in `data.*_to_monitor` order — the pie charts in order.py need
    the site order preserved and therefore use parts_by_site, not this.
    """
    inv_manu = _shortname_lookup(data.relevant_manufacturer_IDs_by_shortname)
    inv_loc = _shortname_lookup(data.relevant_location_IDs_by_shortname)
    labels = {int(p["part_id"]): group_label(p, group_by, inv_manu, inv_loc) for p in parts}

    groups = []
    for name in sorted(set(labels.values())):
        members = [p for p in parts if labels[int(p["part_id"])] == name]
        ids = {int(p["part_id"]) for p in members}
        groups.append(
            {
                "group": name,
                "counts": counts_for(
                    members,
                    [p for p in valid if int(p["part_id"]) in ids],
                    [p for p in invalid if int(p["part_id"]) in ids],
                    [p for p in fake if int(p["part_id"]) in ids],
                    outcomes,
                    validate=validate,
                ),
            }
        )
    groups.sort(key=lambda g: (-g["counts"]["total"], g["group"]))
    return groups


# === One Kind of Part, end to end


def summarize(
    kind,
    filters=None,
    sites=None,
    dev=None,
    validate=False,
    max_workers=4,
    use_local=False,
    info=None,
):
    """Load, filter, split and (optionally) validate one Kind of Part.

    Returns a row dict with both the counts and the underlying part lists, so a
    caller can build a listing or a per-group table without re-querying.
    """
    info = info or (lambda msg: None)
    # the mode is a property of the kind, not of the request: --sites monitored
    # needs it even when no validation is run
    mode = VALIDATABLE.get(kind)
    do_validate = bool(validate and mode)
    if validate and mode is None:
        info(f"[warn] no relation validation for '{kind}'; counting only.")

    resolved_sites = resolve_sites(sites, mode)
    parts, loaded = load_parts(
        kind,
        filters=filters,
        sites=resolved_sites,
        dev=dev,
        use_local=use_local,
    )
    valid, invalid, fake = split_by_sn(parts, mode)

    raw, outcomes = {}, {}
    if do_validate and valid:
        info(f"{kind}: validating relations ({mode}) for {len(valid)} part(s)...")
        raw = validate_parts(valid, mode, max_workers=max_workers)
        outcomes = classify_outcomes(raw, mode)

    return {
        "kind": kind,
        "validation_mode": mode if do_validate else None,
        "validated": do_validate,
        "sensor_mode": do_validate and mode == "Sensor_Parents",
        "loaded": loaded,
        "sites": resolved_sites,
        "counts": counts_for(parts, valid, invalid, fake, outcomes, validate=do_validate),
        "parts": parts,
        "valid": valid,
        "invalid": invalid,
        "fake": fake,
        "raw": raw,
        "outcomes": outcomes,
    }


def build_listing(target, row):
    """Flat SN listing for one category of one summarized Kind of Part."""

    def entry(part, reasons=None):
        return {
            "kind": row["kind"],
            "serial_number": part.get("serial_number"),
            "part_id": int(part["part_id"]),
            "reasons": reasons or [],
        }

    outcomes = row["outcomes"]
    valid = row["valid"]
    by_outcome = {
        outcome: [p for p in valid if outcome_of(outcomes, p) == outcome]
        for outcome in ("connected", "new", "failed")
    }
    return {
        "all": [entry(p) for p in row["parts"]],
        "valid": [entry(p) for p in valid],
        "invalid": [entry(p) for p in row["invalid"]],
        "fake": [entry(p) for p in row["fake"]],
        "connected": [entry(p) for p in by_outcome["connected"]],
        "new": [entry(p) for p in by_outcome["new"]],
        "failed": [
            entry(p, outcomes.get(int(p["part_id"]), ("failed", []))[1])
            for p in by_outcome["failed"]
        ],
    }[target]

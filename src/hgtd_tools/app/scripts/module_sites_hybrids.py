#!/usr/bin/env python3
"""module-sites-hybrids — modules per monitored site, split by hybrid SN category.

Reads through ``hgtd_tools.parts_query`` (the layer ``hgtd-count`` and the
validation report share) and plots through ``hgtd_tools.plotter``, so neither
the counts nor the figure style can drift from the rest of the reporting.

Three figures are produced:

  * per site: modules assembled there (split by the SN prefix of their two
    hybrids; mixed pairs get their own "A + B" entry, modules with 0 / 1 / >2
    hybrids are the grey hatched buckets) next to the hybrids currently
    *located* there (same prefixes). Horizontal bars, one row per site.
  * per hybrid SN prefix: the locations those hybrids currently sit at — all
    locations in data.relevant_location_IDs_by_shortname, one colour and legend
    entry each (``--locations monitored`` restricts this to the monitored
    sites). Vertical bars, one bar per prefix, stacked by location.
  * the prefix census: how many hybrids exist per prefix.

Each figure is written as counts and as fractions, following the convention of
report_stats.py: this CLI normalises and passes "counts" / "fractions" as the
first part of the file name, so a run writes e.g.

    counts_site_modules_vs_hybrids_at_location_7chars_monitored_lin.pdf
    fractions_site_modules_vs_hybrids_at_location_7chars_monitored_lin.pdf
    counts_hybrid_prefix_by_location_7chars_monitored_lin.pdf
    fractions_hybrid_prefix_by_location_7chars_monitored_lin.pdf
    hybrid_sn_prefixes_7chars_monitored_lin.pdf

The active selection (sites, version / name_label / SN filters, valid-SN rule)
is printed in the lower left corner and stored in the JSON cache. Figures go
into a directory named after the selection, e.g.
``plots/validSNs_sitesMonitored_locAll_versionALTIROC_A/``.

Hybrids whose location is outside the plotted universe are reported in the
console table, described by their ``location_id``, ``location_name`` and any
other fields the location dict carries, so an unknown location can be
identified instead of silently disappearing.

Examples
--------
    module-sites-hybrids
    module-sites-hybrids --version-includes-any "some version" \
                         --version-includes-any "another"
    module-sites-hybrids --locations monitored --prefix-len 8
    module-sites-hybrids --subtitle False
    module-sites-hybrids --dump-json cache.json
    module-sites-hybrids --from-json cache.json
"""

from __future__ import annotations

import hashlib
import json
import sys
from argparse import ArgumentParser
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

from hgtd_tools import data, parts_query, plotter, util

MODULE_KIND = "Module"
HYBRID_KIND = "Hybrid"
MODE_MODULE = parts_query.VALIDATABLE[MODULE_KIND]  # "Module Assembly"
MODE_HYBRID = parts_query.VALIDATABLE[HYBRID_KIND]  # "Hybridization"

NO_HYBRID = "0 hybrids"
ONE_HYBRID = "1 hybrid"
MANY_HYBRIDS = ">2 hybrids"
SHADED_BUCKETS = (NO_HYBRID, ONE_HYBRID, MANY_HYBRIDS)

# grey with increasing alpha + different hatch: one "not exactly two" group,
# still distinguishable from the coloured hybrid-SN categories
SHADED_STYLES = {
    NO_HYBRID: {"alpha": 0.25, "hatch": "//"},
    ONE_HYBRID: {"alpha": 0.50, "hatch": "\\\\"},
    MANY_HYBRIDS: {"alpha": 0.80, "hatch": "xx"},
}


# === Serial-number helpers


def _prefix(serial_number, length):
    sn = str(serial_number or "").strip()
    return sn[:length] if sn else "?"


def bucket_of(n_hybrids):
    """Legend entry for a module that does NOT have exactly two hybrids."""
    if n_hybrids == 0:
        return NO_HYBRID
    if n_hybrids == 1:
        return ONE_HYBRID
    return MANY_HYBRIDS


def module_entry(prefixes):
    """Legend entry for a module with exactly two hybrids.

    Two hybrids of the same prefix map to that prefix (so the module bar and the
    location bar share the entry); two different prefixes get an entry of their
    own, "A + B", with its own colour.
    """
    a, b = sorted(prefixes)
    return a if a == b else f"{a} + {b}"


def category(prefixes):
    """Human-readable category, stored in the JSON cache only."""
    if len(prefixes) == 2:
        return module_entry(prefixes)
    return bucket_of(len(prefixes))


def prefix_label(prefix, human_map=None):
    """'20WHPMI\\n(PacTech)' for a known hybrid SN prefix, the prefix otherwise.

    The map is ``data.hybrid_SN_human_map``, keyed by the 7-character prefix; a
    longer prefix (``--prefix-len > 7``) falls back to its 7-character head, so
    the names keep working for every prefix length. Mixed module entries
    ("A + B") get both names on a second line.
    """
    human_map = data.hybrid_SN_human_map if human_map is None else human_map

    def one(p):
        human = human_map.get(p)
        if human is None:
            human = next((v for k, v in human_map.items() if p.startswith(k)), None)
        return p, human

    if " + " in prefix:
        a, b = prefix.split(" + ", 1)
        pa, ha = one(a)
        pb, hb = one(b)
        if ha and hb:
            return f"{pa} + {pb}\n({ha} + {hb})"
        if ha or hb:
            return f"{pa} + {pb}\n({ha or pa} + {hb or pb})"
        return prefix

    p, human = one(prefix)
    return f"{p}\n({human})" if human else p


def ordered_entries(module_counts, bucket_counts, hybrid_by_site):
    """Prefixes by combined weight, then mixed pairs, then the grey buckets."""
    location_totals, module_totals = Counter(), Counter()
    for counts in hybrid_by_site.values():
        location_totals.update(counts)
    for counts in module_counts.values():
        module_totals.update(counts)

    prefixes = {
        e
        for e in set(module_totals) | set(location_totals)
        if " + " not in e and e not in SHADED_BUCKETS
    }

    def weight(entry):
        return location_totals.get(entry, 0) + module_totals.get(entry, 0)

    prefixes = sorted(prefixes, key=lambda e: (-weight(e), e))
    mixed = sorted(
        (e for e in module_totals if " + " in e),
        key=lambda e: (-module_totals[e], e),
    )
    used_buckets = set()
    for counts in bucket_counts.values():
        used_buckets.update(counts)
    return prefixes + mixed + [b for b in SHADED_BUCKETS if b in used_buckets]


# === Location helpers


def describe_location(location, shortname=None):
    """One-line description of a part's location dict.

    Reads ``location_id`` and ``location_name`` explicitly (they are what the DB
    returns) and appends any other non-empty key, so a location the shortname
    table does not know can still be identified from the printed table.
    """
    location = location or {}
    loc_id = location.get("location_id")
    loc_name = location.get("location_name")
    parts = [
        f"location_id={loc_id if loc_id is not None else '?'}",
        f"location_name={loc_name!r}",
    ]
    if shortname:
        parts.append(f"shortname={shortname}")
    extra = {
        key: value
        for key, value in location.items()
        if key not in ("location_id", "location_name") and value not in (None, "")
    }
    for key in sorted(extra):
        parts.append(f"{key}={extra[key]!r}")
    return ", ".join(parts)


def _location_id_to_shortname():
    mapping = {}
    for shortname, ids in data.relevant_location_IDs_by_shortname.items():
        for i in ids if isinstance(ids, (list, tuple, set)) else [ids]:
            mapping[str(i)] = shortname
    return mapping


def location_universe(sites):
    """Location shortnames to split by: the given ones, or every known location."""
    if sites is None:
        return sorted(data.relevant_location_IDs_by_shortname)
    return list(sites)


# === Normalisation, done here as in report_stats.py


def normalized_rows(counts_by_category):
    """{category: {segment: count / row total}} — empty rows stay empty."""
    fractions = {}
    for cat, counts in counts_by_category.items():
        total = sum(counts.values())
        fractions[cat] = (
            {segment: value / total for segment, value in counts.items()} if total else {}
        )
    return fractions


# === Hybrid census: all hybrids, and hybrids by current location


def hybrid_census(prefix_len, info=None):
    """(Counter over all hybrids, Counter over valid hybrids, n_loaded)."""
    hybrids, loaded = parts_query.load_parts(HYBRID_KIND)
    valid, _, _ = parts_query.split_by_sn(hybrids, MODE_HYBRID)
    all_counts = Counter(_prefix(h.get("serial_number"), prefix_len) for h in hybrids)
    valid_counts = Counter(_prefix(h.get("serial_number"), prefix_len) for h in valid)
    if info is not None:
        info(f"[hybrid] {loaded} loaded, {len(valid)} with valid SN")
    return all_counts, valid_counts, loaded


def hybrid_location_census(
    sites=None,
    prefix_len=7,
    only_valid=True,
    version_alternatives=None,
    info=None,
):
    """Hybrids grouped by the LOCATION they are currently at.

    Returns (per_site, per_prefix, elsewhere, n_used):
        per_site:   {location shortname: Counter(prefix)}
        per_prefix: {prefix: Counter(location shortname)}
        elsewhere:  {describe_location(...): n} for hybrids whose location is
                    outside the requested universe, keyed by the location's id,
                    name and any other fields it carries
        n_used:     number of hybrids considered

    `sites=None` uses every shortname in data.relevant_location_IDs_by_shortname,
    which is what the per-prefix figure wants; passing the monitored list keeps
    that figure restricted to the monitored sites.
    """
    hybrids, loaded = parts_query.load_parts(HYBRID_KIND)
    if version_alternatives:
        hybrids = util.select_parts(hybrids, version_does_include_any=version_alternatives)
    if only_valid:
        hybrids, _, _ = parts_query.split_by_sn(hybrids, MODE_HYBRID)

    universe = location_universe(sites)
    inv_loc = _location_id_to_shortname()
    per_site = {site: Counter() for site in universe}
    per_prefix = defaultdict(Counter)
    elsewhere = Counter()

    for hybrid in hybrids:
        location = hybrid.get("location") or {}
        shortname = inv_loc.get(str(location.get("location_id")))
        prefix = _prefix(hybrid.get("serial_number"), prefix_len)
        if shortname in per_site:
            per_site[shortname][prefix] += 1
            per_prefix[prefix][shortname] += 1
        else:
            elsewhere[describe_location(location, shortname)] += 1

    if info is not None:
        inside = sum(sum(c.values()) for c in per_site.values())
        info(
            f"[hybrid] {len(hybrids)} of {loaded} usable, {inside} at a known "
            f"location ({len(universe)} locations), {sum(elsewhere.values())} "
            f"elsewhere ({len(elsewhere)} distinct)"
        )
    return per_site, {p: dict(c) for p, c in per_prefix.items()}, dict(elsewhere), len(hybrids)


# === Modules: fetch + classify


def _site_index(parts, sites):
    """{part_id: site shortname}; parts_by_site has union semantics."""
    index = {}
    for site, members in parts_query.parts_by_site(parts, sites).items():
        for part in members:
            index[int(part["part_id"])] = site
    return index


def _hybrid_prefixes(module_part_id, prefix_len, version_alternatives, only_valid):
    """SN prefixes of a module's Hybrid children (optionally filtered)."""
    records, _ = util.get_children(module_part_id, onlyNonDeleted=True, ofKind=HYBRID_KIND)
    nodes = [r["part"] for r in records if isinstance(r.get("part"), dict)]
    if version_alternatives:
        nodes = util.select_parts(nodes, version_does_include_any=version_alternatives)
    if only_valid:
        nodes, _, _ = parts_query.split_by_sn(nodes, MODE_HYBRID)
    return [_prefix(n.get("serial_number"), prefix_len) for n in nodes]


def fetch_records(
    prefix_len=7,
    sites="monitored",
    filters=None,
    hybrid_version_alternatives=None,
    only_valid=True,
    dev=None,
    workers=4,
    info=None,
):
    """Return (records, site_list, meta); one record per module."""
    resolved = parts_query.resolve_sites(sites, MODE_MODULE)
    parts, loaded = parts_query.load_parts(MODULE_KIND, filters=filters, sites=resolved, dev=dev)
    valid, invalid, fake = parts_query.split_by_sn(parts, MODE_MODULE)
    selected = valid if only_valid else parts
    if info is not None:
        info(
            f"[module] {loaded} loaded, {len(parts)} after filters, "
            f"{len(valid)} valid / {len(invalid)} invalid / {len(fake)} fake"
            + ("" if only_valid else " (keeping all)")
        )

    site_list = list(resolved) if resolved else ["all sites"]
    if resolved:
        site_of = _site_index(selected, resolved)
    else:
        site_of = {int(p["part_id"]): "all sites" for p in selected}

    def work(part):
        sn = str(part.get("serial_number") or "")
        try:
            prefixes = _hybrid_prefixes(
                part["part_id"],
                prefix_len,
                hybrid_version_alternatives,
                only_valid,
            )
            error = None
        except parts_query.API_ERRORS as exc:
            prefixes, error = [], str(exc)
        return {
            "module_id": int(part["part_id"]),
            "serial_number": sn,
            "site": site_of.get(int(part["part_id"]), "unknown"),
            "version": str(part.get("version") or ""),
            "hybrid_prefixes": prefixes,
            "category": category(prefixes),
            "error": error,
        }

    records = []
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for done, record in enumerate(ex.map(work, selected), start=1):
            records.append(record)
            if info is not None and (done % 25 == 0 or done == len(selected)):
                info(f"  {done}/{len(selected)} modules")

    meta = {
        "mode": MODE_MODULE,
        "sites_requested": sites,
        "sites": resolved,
        "loaded": loaded,
        "after_filters": len(parts),
        "valid": len(valid),
        "invalid": len(invalid),
        "fake": len(fake),
    }
    return records, site_list, meta


def aggregate(records, site_list):
    """(totals, two_hy, module counts per entry, non-two bucket counts)."""
    totals, two = Counter(), Counter()
    module_counts = defaultdict(Counter)
    bucket_counts = defaultdict(Counter)

    for record in records:
        site = record["site"] or "unknown"
        totals[site] += 1
        prefixes = record["hybrid_prefixes"]
        if len(prefixes) == 2:
            two[site] += 1
            module_counts[site][module_entry(prefixes)] += 1
        else:
            bucket_counts[site][bucket_of(len(prefixes))] += 1

    for site in site_list:  # keep empty monitored sites visible
        totals.setdefault(site, 0)
        two.setdefault(site, 0)
        module_counts.setdefault(site, Counter())
        bucket_counts.setdefault(site, Counter())

    return totals, two, module_counts, bucket_counts


# === Output: tables


def print_tables(
    all_counts,
    valid_counts,
    totals,
    two,
    module_counts,
    bucket_counts,
    hybrid_by_site,
    elsewhere,
    entries,
    prefix_by_location,
):
    for counts, header in (
        (all_counts, "Hybrid SN prefixes — all hybrids in the DB"),
        (valid_counts, "Hybrid SN prefixes — valid SNs only"),
    ):
        print(f"\n{header} ({sum(counts.values())} hybrids):")
        if not counts:
            print("  (none)")
            continue
        width = max(len(p) for p in counts)
        for prefix, count in counts.most_common():
            print(f"  {prefix.ljust(width)}  {count:5d}")

    head = ["site", "modules", "= 2 HY"] + entries
    rows = []
    for site in sorted(totals, key=lambda s: (-totals[s], s)):
        rows.append(
            [site, totals[site], two[site]]
            + [module_counts[site].get(e) or bucket_counts[site].get(e) or "-" for e in entries]
        )
    widths = [max(len(str(r[i])) for r in [head] + rows) for i in range(len(head))]
    print("\nModules per site (SN columns: modules with exactly two hybrids):")
    print("  ".join(str(v).ljust(w) for v, w in zip(head, widths)).rstrip())
    print("  ".join("-" * w for w in widths))
    for row in rows:
        print("  ".join(str(v).ljust(w) for v, w in zip(row, widths)).rstrip())

    if hybrid_by_site:
        location_totals = Counter()
        for counts in hybrid_by_site.values():
            location_totals.update(counts)
        prefixes = [p for p, _ in sorted(location_totals.items(), key=lambda kv: (-kv[1], kv[0]))]
        head = ["location", "hybrids"] + prefixes
        rows = []
        for site in sorted(hybrid_by_site, key=lambda s: (-sum(hybrid_by_site[s].values()), s)):
            counts = hybrid_by_site[site]
            rows.append([site, sum(counts.values())] + [counts.get(p, 0) or "-" for p in prefixes])
        widths = [max(len(str(r[i])) for r in [head] + rows) for i in range(len(head))]
        print("\nHybrids per location, by SN prefix:")
        print("  ".join(str(v).ljust(w) for v, w in zip(head, widths)).rstrip())
        print("  ".join("-" * w for w in widths))
        for row in rows:
            print("  ".join(str(v).ljust(w) for v, w in zip(row, widths)).rstrip())
        if elsewhere:
            print(f"  elsewhere (not plotted, {sum(elsewhere.values())} hybrids):")
            rows = sorted(elsewhere.items(), key=lambda kv: (-kv[1], kv[0]))
            width = max(len(key) for key, _ in rows)
            for key, count in rows:
                print(f"    {key.ljust(width)}  {count:5d}")

    if prefix_by_location:
        prefix_totals = Counter(
            {p: sum(counts.values()) for p, counts in prefix_by_location.items()}
        )
        location_totals = Counter()
        for counts in prefix_by_location.values():
            location_totals.update(counts)
        locations = [
            loc for loc, _ in sorted(location_totals.items(), key=lambda kv: (-kv[1], kv[0]))
        ]
        head = ["hybrid SN prefix", "hybrids"] + locations
        rows = []
        for prefix, _ in sorted(prefix_totals.items(), key=lambda kv: (-kv[1], kv[0])):
            counts = prefix_by_location[prefix]
            rows.append(
                [prefix, prefix_totals[prefix]] + [counts.get(loc, 0) or "-" for loc in locations]
            )
        widths = [max(len(str(r[i])) for r in [head] + rows) for i in range(len(head))]
        print("\nHybrids per SN prefix, split by location:")
        print("  ".join(str(v).ljust(w) for v, w in zip(head, widths)).rstrip())
        print("  ".join("-" * w for w in widths))
        for row in rows:
            print("  ".join(str(v).ljust(w) for v, w in zip(row, widths)).rstrip())


def selection_lines(args):
    """The active selection, as printed into the corner of every figure."""
    lines = [f"sites: {args.sites}" if args.sites else "sites: all"]
    if args.version_includes_any:
        lines.append(
            "module version contains: " + ", ".join(f'"{v}"' for v in args.version_includes_any)
        )
    if args.hybrid_version_includes_any:
        lines.append(
            "hybrid version contains: "
            + ", ".join(f'"{v}"' for v in args.hybrid_version_includes_any)
        )
    if args.name_label_includes:
        lines.append(f'name_label contains: "{args.name_label_includes}"')
    if args.name_label_excludes:
        lines.append(f'name_label excludes: "{args.name_label_excludes}"')
    if args.sn_includes_any:
        lines.append(f'serial number contains: "{args.sn_includes_any}"')
    lines.append("SNs valid only" if args.only_valid else "including invalid / fake SNs")
    lines.append(
        "locations: all known" if args.locations == "all" else "locations: monitored sites only"
    )
    return lines


# === Output: directory


def _shorten(tokens, limit=90):
    """Join tokens into a filesystem-safe name, hashing if it gets too long."""
    name = "_".join(t for t in tokens if t)
    if len(name) <= limit:
        return name
    digest = hashlib.md5(name.encode()).hexdigest()[:6]
    return name[: limit - 7].rstrip("_") + "_" + digest


def output_dir_name(args):
    """Directory name describing the selection."""
    tokens = ["validSNs" if args.only_valid else "allSNs"]

    sites = (args.sites or "monitored").strip()
    if sites.lower() in ("monitored", "default"):
        tokens.append("sitesMonitored")
    else:
        tokens.append("sites" + "_".join(sites.split(",")))

    tokens.append("locAll" if args.locations == "all" else "locMonitored")

    if args.version_includes_any:
        tokens.append("version" + "_".join(util.sanitize(v) for v in args.version_includes_any))
    if args.hybrid_version_includes_any:
        tokens.append(
            "hyVersion" + "_".join(util.sanitize(v) for v in args.hybrid_version_includes_any)
        )
    if args.name_label_includes:
        tokens.append("label" + util.sanitize(args.name_label_includes))
    if args.name_label_excludes:
        tokens.append("nolabel" + util.sanitize(args.name_label_excludes))
    if args.sn_includes_any:
        tokens.append("sn" + util.sanitize(args.sn_includes_any))
    if args.prefix_len != 7:
        tokens.append(f"prefix{args.prefix_len}")
    if args.hide_non_two:
        tokens.append("onlyTwoHY")
    if args.dev:
        tokens.append(f"dev{args.dev}")

    return _shorten([util.sanitize(t) for t in tokens if t])


def prepare_output_dir(args, info=None):
    """Directory for this run's figures: --output-dir, else derived from the selection."""
    if args.no_subdir:
        return None
    root = Path(args.output_dir or "plots")
    path = root / (args.postfix or output_dir_name(args))
    path.mkdir(parents=True, exist_ok=True)
    if info is not None:
        info(f"[out] writing figures to {path}")
    return path


# === CLI


def build_parser():
    parser = ArgumentParser(
        prog="module-sites-hybrids",
        description="Modules per monitored site next to the hybrids stored there, "
        "both split by hybrid SN prefix, plus a per-prefix location breakdown. "
        "Shares the read layer (parts_query) and the plot style (plotter) with "
        "hgtd-count.",
    )
    parser.add_argument(
        "--sites",
        default="monitored",
        metavar="LIST",
        help="'monitored' (default) for the site list data defines for the Module "
        "Assembly mode, or comma-separated manufacturer shortnames "
        "(e.g. ihep,mainz).",
    )
    parser.add_argument(
        "--locations",
        choices=("all", "monitored"),
        default="all",
        help="Scope of the per-prefix location figure: 'all' (default) uses every "
        "shortname in data.relevant_location_IDs_by_shortname, 'monitored' only "
        "the monitored sites.",
    )
    parser.add_argument(
        "--version-includes-any",
        action="append",
        default=None,
        metavar="TEXT",
        help="Keep modules whose version contains any of these substrings. Repeat "
        "the flag for alternatives containing spaces, e.g. "
        "--version-includes-any 'ALTIROC A'. Values are verbatim.",
    )
    parser.add_argument(
        "--hybrid-version-includes-any",
        action="append",
        default=None,
        metavar="TEXT",
        help="Same filter, applied to the Hybrid children instead.",
    )
    parser.add_argument(
        "--name-label-includes",
        default=None,
        metavar="TEXT",
        help="Case-insensitive substring filter on name_label.",
    )
    parser.add_argument(
        "--name-label-excludes",
        default=None,
        metavar="TEXT",
        help="Case-insensitive negative substring filter on name_label.",
    )
    parser.add_argument(
        "--sn-includes-any",
        default=None,
        metavar="TEXT",
        help="Keep modules whose SN contains any of these whitespace-separated substrings.",
    )
    parser.add_argument(
        "--all-parts",
        dest="only_valid",
        action="store_false",
        help="Include modules/hybrids with invalid or fake SNs (default: valid SNs "
        "only, as in the validation report).",
    )
    parser.add_argument(
        "--prefix-len",
        type=int,
        default=7,
        metavar="N",
        help="SN characters used as category (default: %(default)s)",
    )
    parser.add_argument(
        "--hide-non-two",
        action="store_true",
        help="Drop the 0 / 1 / >2 hybrid buckets from the module bar.",
    )
    parser.add_argument(
        "--scale",
        choices=("lin", "log"),
        default="lin",
        help="Value-axis scale (default: %(default)s)",
    )
    parser.add_argument(
        "--exp-text",
        default="Internal",
        metavar="TEXT",
        help="Second line of the ATLAS label (default: %(default)s)",
    )
    parser.add_argument(
        "--subtitle",
        default=True,
        metavar="BOOL",
        help="[Optional] Add a subtitle with the used hgtd-tools commit and the "
        "date of generation (default: True; pass --subtitle False to drop it).",
    )
    parser.add_argument(
        "--title-prefix",
        default="",
        metavar="TEXT",
        help="Prefix inside the subtitle line.",
    )
    parser.add_argument(
        "--output-dir",
        default="plots",
        metavar="PATH",
        help="Parent directory for the figures; each run writes into a "
        "subdirectory named after its selection (default: %(default)s).",
    )
    parser.add_argument(
        "--no-subdir",
        action="store_true",
        help="Write the figures directly into --output-dir instead of a "
        "selection-specific subdirectory.",
    )
    parser.add_argument(
        "--postfix",
        default=None,
        metavar="TEXT",
        help="File-name postfix; also overrides the selection-specific subdirectory name.",
    )
    parser.add_argument("--max-workers", type=int, default=4, metavar="N")
    parser.add_argument(
        "--dev",
        type=int,
        default=None,
        metavar="N",
        help="Only the first N modules (smoke test).",
    )
    parser.add_argument("--dump-json", default=None, metavar="PATH")
    parser.add_argument("--from-json", default=None, metavar="PATH")
    parser.add_argument("--no-plots", action="store_true", help="Tables only.")
    parser.add_argument("--quiet", action="store_true")
    return parser


def build_filters(args):
    """Keyword arguments for util.select_parts (None values are no-ops)."""
    return {
        "version_does_include_any": args.version_includes_any,
        "name_label_does_include": args.name_label_includes,
        "name_label_does_not_include": args.name_label_excludes,
        "sn_does_include_any": args.sn_includes_any,
    }


def main(argv=None):
    args = build_parser().parse_args(argv)
    args.subtitle = util.str2bool(args.subtitle)
    info = (lambda msg: None) if args.quiet else (lambda msg: print(msg, file=sys.stderr))

    if args.from_json:
        payload = json.loads(Path(args.from_json).read_text(encoding="utf-8"))
        records = payload["records"]
        sites = payload["sites"]
        all_counts = Counter(payload.get("prefix_counts_all") or {})
        valid_counts = Counter(payload.get("prefix_counts_valid") or {})
        hybrid_by_site = {
            site: Counter(counts) for site, counts in (payload.get("hybrid_by_site") or {}).items()
        }
        prefix_by_location = {
            prefix: dict(counts)
            for prefix, counts in (payload.get("hybrid_prefix_by_location") or {}).items()
        }
        elsewhere = dict(payload.get("hybrid_elsewhere") or {})
        cached_selection = payload.get("selection")
        info(f"Loaded {len(records)} modules from {args.from_json}")

        if any(
            [
                args.version_includes_any,
                args.hybrid_version_includes_any,
                args.name_label_includes,
                args.name_label_excludes,
                args.sn_includes_any,
            ]
        ):
            info(
                "[warn] filters are applied when the cache is written, not when it "
                "is read - the --version/--name-label/--sn filters are ignored for "
                "--from-json. Re-run without --from-json to change the selection."
            )
        if not hybrid_by_site:
            info(
                "[warn] cache has no hybrid-by-location data (written by an older "
                "version); the 'hybrids at location' bar stays empty. Re-run with "
                "--dump-json to refresh it."
            )
        if not prefix_by_location:
            info(
                "[warn] cache has no hybrid-prefix-by-location data (written by an "
                "older version); the per-prefix location figure is skipped."
            )
        plot_selection = cached_selection or ["selection: (not recorded in cache)"]
    else:
        filters = build_filters(args)
        all_counts, valid_counts, _ = hybrid_census(args.prefix_len, info=info)

        monitored = list(
            parts_query.resolve_sites(args.sites, MODE_MODULE)
            or parts_query.MONITORED_SITES[MODE_MODULE]
        )
        universe = None if args.locations == "all" else monitored
        hybrid_by_site, prefix_by_location, elsewhere, _ = hybrid_location_census(
            universe,
            args.prefix_len,
            only_valid=args.only_valid,
            version_alternatives=args.hybrid_version_includes_any,
            info=info,
        )

        records, sites, meta = fetch_records(
            prefix_len=args.prefix_len,
            sites=args.sites,
            filters=filters,
            hybrid_version_alternatives=args.hybrid_version_includes_any,
            only_valid=args.only_valid,
            dev=args.dev,
            workers=args.max_workers,
            info=info,
        )
        plot_selection = selection_lines(args)
        if args.dump_json:
            Path(args.dump_json).write_text(
                json.dumps(
                    {
                        "records": records,
                        "sites": sites,
                        "meta": meta,
                        "prefix_counts_all": dict(all_counts),
                        "prefix_counts_valid": dict(valid_counts),
                        "hybrid_by_site": {s: dict(c) for s, c in hybrid_by_site.items()},
                        "hybrid_prefix_by_location": prefix_by_location,
                        "hybrid_elsewhere": elsewhere,
                        "selection": plot_selection,
                    },
                    indent=1,
                ),
                encoding="utf-8",
            )
            info(f"Wrote {args.dump_json}")

    broken = [r for r in records if r.get("error")]
    if broken:
        info(f"[warn] {len(broken)} module(s) unreadable, counted as '{NO_HYBRID}'")

    totals, two, module_counts, bucket_counts = aggregate(records, sites)
    entries = ordered_entries(module_counts, bucket_counts, hybrid_by_site)
    print_tables(
        all_counts,
        valid_counts,
        totals,
        two,
        module_counts,
        bucket_counts,
        hybrid_by_site,
        elsewhere,
        entries,
        prefix_by_location,
    )

    n_modules, n_two = sum(totals.values()), sum(two.values())
    print(
        f"\n{n_modules} module(s) at {len([s for s in sites if totals.get(s)])} site(s), "
        f"{n_two} with exactly two hybrids "
        f"({100.0 * n_two / n_modules:.1f}%)"
        if n_modules
        else "\nno modules"
    )

    if args.no_plots:
        return 0

    outdir = prepare_output_dir(args, info=info)
    postfix = args.postfix or util.sanitize(f"{args.prefix_len}chars_{args.sites or 'monitored'}")
    written = []

    # --- figure 1: per site, modules assembled there vs hybrids stored there -
    plot_entries = [e for e in entries if not args.hide_non_two or e not in SHADED_BUCKETS]
    if plot_entries:
        order = sorted(range(len(sites)), key=lambda i: (totals[sites[i]], sites[i]))
        ordered_sites = [sites[i] for i in order]

        matrix = np.zeros((len(ordered_sites), 2, len(plot_entries)))
        for i, site in enumerate(ordered_sites):
            for j, entry in enumerate(plot_entries):
                if entry in SHADED_BUCKETS:
                    matrix[i, 0, j] = bucket_counts[site].get(entry, 0)
                else:
                    matrix[i, 0, j] = module_counts[site].get(entry, 0)
                    matrix[i, 1, j] = hybrid_by_site.get(site, Counter()).get(entry, 0)

        # each bar normalised to itself, as report_stats.py does it
        fractions = np.zeros_like(matrix)
        bar_totals = matrix.sum(axis=2, keepdims=True)
        np.divide(matrix, np.where(bar_totals > 0, bar_totals, 1.0), out=fractions)

        annotations = [
            [
                f"modules: {totals[site]:.0f}",
                f"hybrids: {sum(hybrid_by_site.get(site, Counter()).values()):.0f}",
            ]
            for site in ordered_sites
        ]

        for quantity, values, xlabel in (
            ("counts", matrix, "Number of modules / hybrids"),
            ("fractions", fractions, "Fraction within each bar"),
        ):
            stem = plotter.plot_grouped_stacked_bars(
                values,
                ordered_sites,
                ["modules", "hybrids at location"],
                [prefix_label(e) for e in plot_entries],
                f"{quantity}_site_modules_vs_hybrids_at_location",
                "Hybrid SN prefix",
                args.exp_text,
                title_prefix=args.title_prefix,
                subtitle=args.subtitle,
                scale=args.scale,
                postfix=postfix,
                shaded=SHADED_STYLES,
                xlabel=xlabel,
                ylabel="Site",
                annotations=annotations,
                bar_height=0.40,
                group_gap=0.02,
                site_spacing=1.0,
                exp_text_loc=0,
                figsize=(10.5, 0.85 * len(ordered_sites) + 2.2),
                selection_lines=plot_selection,
                outdir=outdir,
            )
            if stem:
                written.append(stem)
    else:
        info("[warn] nothing to plot for the per-site figure")

    # --- figure 2: one bar per hybrid SN prefix, stacked by location ---------
    if prefix_by_location:
        prefix_totals = {
            prefix: sum(counts.values()) for prefix, counts in prefix_by_location.items()
        }
        prefixes = [p for p, _ in sorted(prefix_totals.items(), key=lambda kv: (-kv[1], kv[0]))]
        location_totals = Counter()
        for counts in prefix_by_location.values():
            location_totals.update(counts)
        locations = [
            loc for loc, _ in sorted(location_totals.items(), key=lambda kv: (-kv[1], kv[0]))
        ]
        # width from the number of bars, plus room for the y label, the outside
        # legend and the corner text; no fixed floor, three bars stay narrow
        figsize = (1.2 * len(prefixes) + 3.0, 6.0)
        # raw counts on top of every bar, in both variants
        bar_labels = [f"{prefix_totals[p]:.0f}" for p in prefixes]

        # human-readable names for the known prefixes, as tick labels
        labeled_counts = {
            prefix_label(prefix): counts for prefix, counts in prefix_by_location.items()
        }
        labeled_prefixes = [prefix_label(p) for p in prefixes]

        for quantity, payload, ylabel in (
            ("counts", labeled_counts, "Number of hybrids"),
            ("fractions", normalized_rows(labeled_counts), "Fraction of hybrids"),
        ):
            written += plotter.plot_stacked_bars_from_counts(
                payload,
                f"{quantity}_hybrid_prefix_by_location",
                "Hybrid location",
                args.exp_text,
                segment_order=locations,
                category_order=labeled_prefixes,
                title_prefix=args.title_prefix,
                subtitle=args.subtitle,
                scale=args.scale,
                postfix=postfix,
                xlabel=f"Hybrid SN prefix (first {args.prefix_len} characters)",
                ylabel=ylabel,
                horizontal=False,
                rotate_xticks=90,
                annotations=bar_labels,
                figsize=figsize,
                labels_outside=True,
                exp_text_loc=0,
                selection_lines=plot_selection,
                outdir=outdir,
            )
    else:
        info("[warn] no hybrid-by-location data; per-prefix location figure skipped")

    # --- figure 3: prefix census --------------------------------------------
    if all_counts:
        counted = all_counts.most_common()
        stem = plotter.plot_category_counts(
            [prefix_label(p) for p, _ in counted],
            [count for _, count in counted],
            "hybrid_sn_prefixes",
            args.exp_text,
            xlabel=f"Hybrid SN prefix (first {args.prefix_len} characters)",
            ylabel="Number of hybrids",
            title_prefix=args.title_prefix,
            subtitle=args.subtitle,
            scale=args.scale,
            postfix=postfix,
            rotate_xticks=90,
            exp_text_loc=0,
            selection_lines=plot_selection,
            outdir=outdir,
        )
        if stem:
            written.append(stem)

    for stem in written:
        print(f"Wrote {stem}.{{pdf,png}}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

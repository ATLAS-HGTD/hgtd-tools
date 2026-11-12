import csv
import json
import re
import textwrap
import webbrowser
from argparse import ArgumentTypeError
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import requests

from hgtd_tools import api, data
from hgtd_tools.asset_helpers import load_json_from_assets
from hgtd_tools.templates import tree_header

API_ERRORS = (
    requests.exceptions.HTTPError,
    requests.exceptions.ConnectionError,
    requests.exceptions.Timeout,
    requests.exceptions.RequestException,
    ValueError,
    RuntimeError,
)

# === Helper for argparse

# Source - https://stackoverflow.com/a/43357954
# Posted by Maxim, modified by community. See post 'Timeline' for change history
# Retrieved 2026-02-04, License - CC BY-SA 4.0


def str2bool(v):
    if isinstance(v, bool):
        return v
    if v.lower() in ("yes", "true", "t", "y", "1"):
        return True
    elif v.lower() in ("no", "false", "f", "n", "0"):
        return False
    else:
        raise ArgumentTypeError("Boolean value expected.")


# from : https://svn.blender.org/svnroot/bf-blender/trunk/blender/build_files/scons/tools/bcolors.py
class bcolors:
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"


# === Operations with standard objects (lists, dicts, strings etc.)
def flatten(xss):
    return [x for xs in xss for x in xs]


def get_sorted_list_of_lists_by_Nth_column(unsorted_list, column):
    sortList = unsorted_list.copy()
    sortList.sort(key=lambda x: x[column])
    return sortList


def get_relevant_SNs_and_partIDs(partsList):
    these_SNs_and_partIDs = get_sorted_list_of_lists_by_Nth_column(
        [[pL["serial_number"], pL["part_id"]] for pL in partsList], 0
    )
    return these_SNs_and_partIDs


# https://stackoverflow.com/a/45287550
class CustomTextWrapper(textwrap.TextWrapper):
    def wrap(self, text):
        split_text = text.split("\n")
        lines = [line for para in split_text for line in textwrap.TextWrapper.wrap(self, para)]
        return lines


### function to get the first 8 chars of MO SNs
def get_MO_SN_prefix(site, prod, batch):
    if site not in data.MO_site_id.keys():
        raise RuntimeError(f"Provided site {site} is invalid")
    if prod not in data.MO_prod_id.keys():
        raise RuntimeError(f"Provided prod {prod} is invalid")

    if site == "test":
        leading = "99"
    else:
        leading = "20"

    k = data.MO_site_id[site.lower()]
    p = data.MO_prod_id[prod.lower()]
    b = str(batch)
    if len(b) > 1:
        raise RuntimeError(f"SN : batch should be a single character but you passed {b}")
    if not b.isalnum():
        raise RuntimeError(f"SN : batch should be alphanumeric but you passed {b}")
    snprefix = f"{leading}WMO{k}{p}{b}"
    return snprefix.upper()


# === Operations with API or Browser
def open_webbrowser_with_url(url, debug=False, noExtraPrefix=False):
    if noExtraPrefix:
        if debug:
            print(f">>> Opening {url} in webbrowser...")
        webbrowser.open_new_tab(url)
    else:
        if debug:
            print(f">>> Opening {api.frontendUrlPrefix + url} in webbrowser...")
        webbrowser.open_new_tab(api.frontendUrlPrefix + url)


def delete_children(par_partID, onlyNonDeleted=True, ofKind="all", dryrun=False):
    try:
        partstree, responseText = api.fetch_information(f"/childrenlist/{par_partID}/")
        if onlyNonDeleted:
            interesting_partstree = []
            for p in partstree:
                if str(p["is_record_deleted"]) == "F":
                    if ofKind == "all" or str(data.KoPID_from_partKoPName[ofKind]) == str(
                        p["part"]["kind_of_part"]["kind_of_part_id"]
                    ):
                        interesting_partstree.append(p)
        else:
            interesting_partstree = partstree
            del partstree
        for ip in interesting_partstree:
            responseText = api.delete_information(
                f"/partstreedelete/{ip['record_id']}/", dryrun=dryrun
            )
        return responseText
    except API_ERRORS as e:
        raise e


def delete_parents(chi_partID, onlyNonDeleted=True, ofKind="all", dryrun=False):
    try:
        partstree, responseText = api.fetch_information(f"/parentslist/{chi_partID}/")
        if onlyNonDeleted:
            interesting_partstree = []
            for p in partstree:
                if str(p["is_record_deleted"]) == "F":
                    if ofKind == "all" or str(data.KoPID_from_partKoPName[ofKind]) == str(
                        p["part_parent"]["kind_of_part"]["kind_of_part_id"]
                    ):
                        interesting_partstree.append(p)
        else:
            interesting_partstree = partstree
            del partstree
        for ip in interesting_partstree:
            responseText = api.delete_information(
                f"/partstreedelete/{ip['record_id']}/", dryrun=dryrun
            )
        return responseText
    except API_ERRORS as e:
        raise e


def get_info_of_part_id(part_id):
    try:
        details, responseText = api.fetch_information(f"/part/{part_id}/")
        return details, responseText
    except API_ERRORS as e:
        raise e


def get_attributes_of_part_id(part_id):
    try:
        attributes, responseText = api.fetch_information(f"/partattrlist/{part_id}/")
        return attributes, responseText
    except API_ERRORS as e:
        raise e


def get_measurement_types_of_module_SN(part_SN):
    try:
        measurements, responseText = api.fetch_information(
            f"/module_threshold_run_type?serial_number={part_SN}"
        )
        return measurements, responseText
    except API_ERRORS as e:
        raise e


def get_SN_of_parts(parts):
    return [part["serial_number"] for part in parts]


def parallel_partition(parts, fn, max_workers=4):
    """Apply `fn(part)` to each part concurrently.

    `fn` must return `(keep_bool, output)` for each part.
    Returns `(kept_outputs, ignored_outputs)` as two lists, each
    preserving the original order of `parts`.

    Generalizes `parallel_keeps` for cases where you also need the
    output payload (e.g. a reason string) for *both* kept and ignored
    parts.

    Note: assumes `fn` and any I/O it performs are thread-safe.
    """
    if not parts:
        return [], []
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        results = list(ex.map(fn, parts))
    kept, ignored = [], []
    for keep, out in results:
        (kept if keep else ignored).append(out)
    return kept, ignored


def parallel_keeps(parts, predicate, max_workers=4):
    """Apply `predicate(part_id)` to each part concurrently.

    Returns the subset of `parts` whose predicate returns truthy,
    preserving the original order.
    """
    if not parts:
        return parts
    part_ids = [p["part_id"] for p in parts]
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        results = list(ex.map(predicate, part_ids))
    return [p for p, keep in zip(parts, results) if keep]


def select_parts(
    parts,
    location_shortname=None,
    location_name=None,
    location_id=None,
    manu_shortname=None,
    manu_name=None,
    manu_id=None,
    sn_does_include=None,
    sn_does_include_any=None,
    sn_chars_9_to_10_eq=None,
    name_label_does_include=None,  # case-insensitive
    name_label_does_not_include=None,  # case-insensitive
    check_valid_SN_latest_spec=False,
    check_invalid_SN_latest_spec=False,
    check_fake_SN=False,
    no_parents_ofKind=None,
    no_children_ofKind=None,
    has_parents_ofKind=None,
    has_children_ofKind=None,
    connection_predicate=None,
):
    if location_name in (None, "", "All locations"):
        location_name = None
    if manu_name in (None, "", "All manufacturers"):
        manu_name = None
    if sn_does_include == "":
        sn_does_include = None

    if location_shortname is not None:
        parts = [
            iP
            for iP in parts
            if str(iP["location"]["location_id"])
            == str(data.relevant_location_IDs_by_shortname[location_shortname])
        ]
    if location_name is not None:
        parts = [iP for iP in parts if str(iP["location"]["location_name"]) == str(location_name)]
    if location_id is not None:
        parts = [iP for iP in parts if str(iP["location"]["location_id"]) == str(location_id)]
    if manu_shortname is not None:
        parts = [
            iP
            for iP in parts
            if str(iP["manufacturer"]["manufacturer_id"])
            == str(data.relevant_manufacturer_IDs_by_shortname[manu_shortname])
        ]
    if manu_name is not None:
        parts = [
            iP for iP in parts if str(iP["manufacturer"]["manufacturer_name"]) == str(manu_name)
        ]
    if manu_id is not None:
        parts = [iP for iP in parts if str(iP["manufacturer"]["manufacturer_id"]) == str(manu_id)]
    if sn_does_include_any is not None:
        alts = sn_does_include_any.split()
        parts = [iP for iP in parts if any(alt in str(iP["serial_number"]) for alt in alts)]
    if sn_does_include is not None:
        parts = [iP for iP in parts if str(sn_does_include) in str(iP["serial_number"])]
    if sn_chars_9_to_10_eq is not None:
        parts = [
            iP
            for iP in parts
            if len(str(iP["serial_number"])) >= 11
            and int(str(iP["serial_number"])[9:11]) == int(sn_chars_9_to_10_eq)
        ]
    if name_label_does_include is not None:  # case-insensitive
        parts = [
            iP
            for iP in parts
            if str(name_label_does_not_include).lower() in str(iP["name_label"]).lower()
        ]
    if name_label_does_not_include is not None:  # case-insensitive
        parts = [
            iP
            for iP in parts
            if str(name_label_does_not_include).lower() not in str(iP["name_label"]).lower()
        ]
    if check_valid_SN_latest_spec:
        parts = [iP for iP in parts if check_SN_valid(str(iP["serial_number"]))[0]]
    if check_invalid_SN_latest_spec:
        parts = [
            iP
            for iP in parts
            if (str(iP["serial_number"])[:3] == "20W")
            and not check_SN_valid(str(iP["serial_number"]))[0]
        ]
    if check_fake_SN:
        parts = [iP for iP in parts if (str(iP["serial_number"])[:3] != "20W")]
    if no_parents_ofKind is not None:
        parts = parallel_keeps(
            parts,
            lambda pid: get_parents(pid, ofKind=no_parents_ofKind)[0] == [],
        )
    if no_children_ofKind is not None:
        parts = parallel_keeps(
            parts,
            lambda pid: get_children(pid, ofKind=no_children_ofKind)[0] == [],
        )
    if has_parents_ofKind is not None:
        parts = parallel_keeps(
            parts,
            lambda pid: len(get_parents(pid, ofKind=has_parents_ofKind)[0]) > 0,
        )
    if has_children_ofKind is not None:
        parts = parallel_keeps(
            parts,
            lambda pid: len(get_children(pid, ofKind=has_children_ofKind)[0]) > 0,
        )
    if connection_predicate is not None:
        parts = parallel_keeps(parts, connection_predicate)

    return parts


def get_relevant_parts(
    partKoP_shortname, onlyNonDeleted=True, getFullAttributes=False, useLocal=False
):
    KoP_ID = data.KoPID_from_partKoPName[partKoP_shortname]
    retrieve = "partattributelistbykop" if getFullAttributes else "partslistbykop"
    try:
        if not useLocal:
            if partKoP_shortname == "Slot":
                slots, responseText = api.fetch_information(f"/partslistbykop/{KoP_ID}/")
                these_parts, responseText = api.fetch_information(
                    f"/partattributelistbykop/{KoP_ID}/"
                )
                for alSl in these_parts:
                    for s in slots:
                        if str(alSl["part_serial_number"]) == str(s["serial_number"]):
                            alSl["part_id"] = s["part_id"]
            else:
                these_parts, responseText = api.fetch_information(f"/{retrieve}/{KoP_ID}/")
                if retrieve != "partattributelistbykop":
                    these_parts = [tP for tP in these_parts if tP["is_record_deleted"] == "F"]
        else:
            # slot table is the one table that basically only acts as a static lookup;
            # contains the various location definitions (local & global) but during
            # the lifetime of the detector, the Slot table itself stays constant
            # => can be stored as a local file, don't need to load it freshly each time
            # the following two files result from manually downloading, exporting and converting them
            if partKoP_shortname != "Slot":
                raise NotImplementedError
            these_parts = load_json_from_assets(
                "Slot_Table_fullJuly2026_withPreliminaryNTC_fix.json"
            )
            slots = load_json_from_assets("Slot_fullJuly2026_withPreliminaryNTC_fix.json")
            responseText = "200: Local File"
            for alSl in these_parts:
                for s in slots:
                    if str(alSl["part_serial_number"]) == str(s["Serial #"]):
                        alSl["part_id"] = s["Part ID"]
        return these_parts, responseText
    except API_ERRORS as e:
        raise e


def resolve_part_id_by_sn(serial_number, kind):
    """part_id of the part with this SN in the given kind of part.

    Uses get_relevant_parts(kind) + select_parts(sn_does_include=...), then
    requires exactly one match.
    """
    parts, _ = get_relevant_parts(kind)
    matches = select_parts(parts, sn_does_include=serial_number)
    # sn_does_include is a substring filter, so "1234" also hits "12345"
    exact = [p for p in matches if str(p.get("serial_number")) == str(serial_number)]
    if len(exact) == 1:
        return int(exact[0]["part_id"])

    if not exact:
        hint = ""
        if matches:
            near = ", ".join(str(p["serial_number"]) for p in matches[:5])
            hint = f" (substring matches: {near})"
        raise RuntimeError(f"No part with serial number '{serial_number}' of kind '{kind}'{hint}")
    raise RuntimeError(
        f"Serial number '{serial_number}' of kind '{kind}' is ambiguous: "
        f"part_ids {[int(p['part_id']) for p in exact]}"
    )


def get_parents(chi_partID, onlyNonDeleted=True, ofKind="all"):
    try:
        partstree, responseText = api.fetch_information(f"/parentslist/{chi_partID}/")
        if onlyNonDeleted:
            interesting_partstree = []
            for p in partstree:
                if str(p["is_record_deleted"]) == "F":
                    if ofKind == "all" or str(data.KoPID_from_partKoPName[ofKind]) == str(
                        p["part_parent"]["kind_of_part"]["kind_of_part_id"]
                    ):
                        interesting_partstree.append(p)
            return interesting_partstree, responseText
        else:
            return partstree, responseText
    except API_ERRORS as e:
        raise e


# this is quicker (a bit) because it only reads the children of the given parent
def get_children(par_partID, onlyNonDeleted=True, ofKind="all"):
    try:
        partstree, responseText = api.fetch_information(f"/childslist/{par_partID}/")
        if onlyNonDeleted:
            interesting_partstree = []
            for p in partstree:
                if str(p["is_record_deleted"]) == "F":
                    if ofKind == "all" or str(data.KoPID_from_partKoPName[ofKind]) == str(
                        p["part"]["kind_of_part"]["kind_of_part_id"]
                    ):
                        interesting_partstree.append(p)
            return interesting_partstree, responseText
        else:
            return partstree, responseText
    except API_ERRORS as e:
        raise e


# === Parts tree rendering

PART_VIEW_URL = "https://nginx-hgtddb.app.cern.ch/viewparts/{part_id}"


def part_url(part_id, template=PART_VIEW_URL):
    """Clickable link target for a part in the HGTD DB web view."""
    return template.format(part_id=int(part_id))


def _format_part_node(node, position=None):
    label = f"{node.get('serial_number') or '?'} (part_id {node.get('part_id')})"
    if position not in (None, ""):
        label += f"  [position: {position}]"
    return label


def _part_tree_lines(root_node, children_by_parent, dupes_by_parent, ascii=False, max_lines=None):
    """Render the tree as box-drawing lines.

    `children_by_parent` / `dupes_by_parent` map parent part_id to lists of
    (node, position). Duplicate edges are shown in place but not expanded.
    """
    tee = "|-- " if ascii else "├── "
    last_tee = "`-- " if ascii else "└── "
    pipe = "|   " if ascii else "│   "
    blank = "    "

    lines = [_format_part_node(root_node)]

    def walk(node, prefix):
        pid = int(node["part_id"])
        entries = [(n, p, False) for n, p in children_by_parent.get(pid, [])]
        entries += [(n, p, True) for n, p in dupes_by_parent.get(pid, [])]
        for i, (child, position, is_dupe) in enumerate(entries):
            last = i == len(entries) - 1
            label = _format_part_node(child, position)
            if is_dupe:
                label += "  [already listed above]"
            lines.append(prefix + (last_tee if last else tee) + label)
            if not is_dupe:
                walk(child, prefix + (blank if last else pipe))

    walk(root_node, "")
    if max_lines is not None and len(lines) > max_lines:
        lines = lines[:max_lines] + [f"... (tree truncated, {len(lines) - max_lines} more lines)"]
    return lines


def write_tree_txt(path, lines):
    """Write rendered lines (plain tree or Markdown) to a UTF-8 file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


# Attribute list appended to inline links; requires the `attr_list` extension.
NEW_TAB_ATTRS = '{target="_blank"}'


def md_link(text, url, new_tab=True, attrs=NEW_TAB_ATTRS):
    """Inline link, optionally opening in a new tab via attr_list."""
    link = f"[{text}]({url})"
    if new_tab:
        link += attrs
    return link


def _md_title(node, position=None, link=True, url_template=PART_VIEW_URL, new_tab=True):
    """Admonition title; with link=True the SN itself is the clickable link."""
    sn = str(node.get("serial_number") or "?")
    pid = node.get("part_id")
    text = f"{sn} (part_id {pid})"
    if link and pid is not None:
        text = md_link(text, part_url(pid, url_template), new_tab=new_tab)
    # Escape only what would be misread as inline Markdown. Brackets are left
    # alone when linking, otherwise the link syntax breaks.
    chars = ("\\", "`", "*", "_", '"') if link else ("\\", "`", "*", "_", "[", "]", '"')
    for ch in chars:
        text = text.replace(ch, "\\" + ch)
    if position not in (None, ""):
        text += f" — {position}"
    return text


def _tree_to_markdown_lines(
    root_node,
    children_by_parent,
    dupes_by_parent,
    admonition_type="note",
    indent=4,
    open_root=True,
    max_depth=None,
    dedupe_note="already listed above",
    link=True,
    url_template=PART_VIEW_URL,
    new_tab=True,
):
    """Render the tree as nested collapsible admonitions (??? / ???+).

    Each title links to <url_template>/{part_id}. Requires the `details` and
    `admonition` extensions on the site side.
    """
    pad = " " * indent

    def render(node, position, depth, is_dupe):
        pid = int(node["part_id"])
        marker = "???+" if (open_root and depth == 0) else "???"
        title = _md_title(node, position, link=link, url_template=url_template, new_tab=new_tab)
        header = f'{marker} {admonition_type} "{title}"'
        blocks = []

        meta = []
        if position not in (None, ""):
            meta.append(f"Position: `{position}`")
        if is_dupe:
            meta.append(f"*{dedupe_note}*")
        if meta:
            blocks.append(meta)

        if not is_dupe and (max_depth is None or depth < max_depth):
            for child, cpos in children_by_parent.get(pid, []):
                blocks.append(render(child, cpos, depth + 1, False))
            for child, cpos in dupes_by_parent.get(pid, []):
                blocks.append(render(child, cpos, depth + 1, True))

        out = [header, ""]
        for i, block in enumerate(blocks):
            if i:
                out.append("")
            for line in block:
                out.append(pad + line if line else "")
        if not blocks:
            out.append(pad + "_no children_")
        return out

    return render(root_node, None, 0, False)


def _yaml_str(value):
    return '"' + str(value).replace("\\", "\\\\").replace('"', '\\"') + '"'


def _count_nodes(children_by_parent, dupes_by_parent):
    n = sum(len(v) for v in children_by_parent.values())
    n += sum(len(v) for v in dupes_by_parent.values())
    return n


def write_detector_tree_page(
    path,
    root_node,
    children_by_parent,
    dupes_by_parent,
    title="Detector parts tree",
    description=None,
    admonition_type="note",
    max_depth=None,
    include_index=False,
    index_limit=50,
    indent=4,
    link=True,
    url_template=PART_VIEW_URL,
    new_tab=True,
):
    """Write a single Markdown page holding the whole parts tree.

    The page is built from `templates.tree_header` (front matter, H1, the
    "automatic reports" info admonition, and the "## Nightly report: parts
    tree" heading), followed by a short summary block, an optional flat index
    of the root's direct children, and the full tree as nested collapsible
    admonitions (`???` / `???+`).

    The parent directories of `path` are created if missing and the file is
    written as UTF-8 (required for the box-drawing characters that may appear
    in titles).

    Parameters:
        path: output file path, e.g. "out/detector_tree.md"
        root_node: the root part dict (needs at least "part_id"; a
            "serial_number" is used for display and falls back to "?")
        children_by_parent: mapping parent part_id -> list of
            (node, position) tuples, in display order. Nodes are part dicts
            with "part_id" and "serial_number".
        dupes_by_parent: same shape, for child edges that were already
            visited elsewhere in the tree. They are rendered in place but
            never expanded, and marked as duplicates, so the page stays a
            tree instead of a graph.
        title: page title; YAML-quoted before being handed to the template
        description: front-matter description; generated from the root SN and
            part count when None, YAML-quoted before use
        admonition_type: admonition class for every node, e.g. "note",
            "info", "abstract" (any class supported by the admonition
            extension)
        max_depth: deepest tree level rendered as admonitions, counting the
            root as level 0. Nodes deeper than this are omitted from the
            Markdown only; the traversal result and the .txt output are
            unaffected. None means no limit.
        include_index: add a flat "Direct children" list of the root's
            immediate children above the tree
        index_limit: maximum number of entries in that index list; the
            remainder is summarised as "… and N more". Has no effect on the
            nested tree, which is always complete. Must be an int (None would
            raise a TypeError on slicing); use include_index=False to drop the
            section instead.
        indent: spaces per admonition nesting level. Four is the Markdown
            convention and what the admonition extension expects.
        link: wrap each serial number in a link to the parts DB
        url_template: URL template for those links, formatted with
            part_id=...; see PART_VIEW_URL
        new_tab: append `{target="_blank" rel="noopener noreferrer"}` to each
            link so it opens in a new tab. Requires the `attr_list`
            extension on the site side, otherwise the attribute block is
            rendered as literal text.

    Returns:
        pathlib.Path of the written file.

    Site-side requirements:
        The `admonition` extension for `!!!`, and `pymdownx.details` for the
        collapsible `???` / `???+` blocks (without it the markers appear
        literally). Both must be listed in the *list* form of
        `markdown_extensions` on `[project]` in zensical.toml — the
        table-only form silently skips third-party Python-Markdown
        extensions. `attr_list` is additionally required when new_tab=True.

    Notes:
        - The page itself is deterministic; the "last updated" line comes from
          `config.extra.build_time` in the template, so the file only changes
          when the tree changes.
        - Each part costs roughly five lines of Markdown. A tree with a few
          hundred parts is fine; several thousand will make the page slow and
          hard to navigate.
        - Nesting is indentation-based and gets fragile beyond ~4 levels.
          With the HGTD construction depth (Detector > Detector Unit >
          Module > Hybrid > Sensor) the default of no limit is safe; for
          deeper or unexpected trees consider max_depth=3.
        - Duplicate edges are shown with an "already listed above" marker and
          no children, which is the signal to check before building a
          shipment from the traversal result.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    root_id = int(root_node["part_id"])
    root_sn = root_node.get("serial_number") or "?"
    n_children = len(children_by_parent.get(root_id, []))
    n_edges = _count_nodes(children_by_parent, dupes_by_parent)

    if description is None:
        description = f"Recursive part tree below {root_sn} ({n_edges} parts)."

    root_label = f"`{root_sn}` (part_id {root_id})"
    if link:
        root_label = md_link(root_label, part_url(root_id, url_template), new_tab=new_tab)

    header = tree_header(_yaml_str(title), _yaml_str(description), title).rstrip("\n")
    lines = header.split("\n")

    lines += [
        "",
        f"**Root:** {root_label}  ",
        f"**Direct children:** {n_children}  ",
        f"**Parts in tree:** {n_edges}",
        "",
    ]

    if include_index and n_children:
        lines += ["### Direct children", ""]
        shown = children_by_parent.get(root_id, [])[:index_limit]
        for child, cpos in shown:
            label = f"`{child.get('serial_number') or '?'}` (part_id {child['part_id']})"
            if link:
                label = md_link(
                    label,
                    part_url(child["part_id"], url_template),
                    new_tab=new_tab,
                )
            if cpos not in (None, ""):
                label += f" — {cpos}"
            lines.append(f"- {label}")
        if n_children > len(shown):
            lines.append(f"- … and {n_children - len(shown)} more")
        lines.append("")

    lines += _tree_to_markdown_lines(
        root_node,
        children_by_parent,
        dupes_by_parent,
        admonition_type=admonition_type,
        indent=indent,
        max_depth=max_depth,
        link=link,
        url_template=url_template,
        new_tab=new_tab,
    )

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def get_recursive_children(
    part_id,
    ofKind="all",
    max_depth=None,
    max_workers=4,
    include_parent=False,
    onlyNonDeleted=True,
    with_edges=False,
    progress=None,
    print_tree=False,
    tree_ascii=False,
    tree_max_lines=None,
    tree_file=None,
    position_key="position",
    tree_txt_path=None,
    tree_md_path=None,
    md_admonition_type="note",
    md_max_depth=None,
    page_title="Detector parts tree",
    page_description=None,
    md_link_parts=True,
    md_new_tab=True,
    part_url_template=PART_VIEW_URL,
):
    """Collect all descendants of `part_id` in the part tree (breadth-first).

    Parameters:
        ofKind: only follow/collect children of this KoP shortname ("all" = no filter)
        max_depth: levels below the root to traverse (None = unlimited)
        max_workers: threads for the /childslist/ calls per level
        include_parent: also return the root itself (first element)
        with_edges: return (descendants, [(parent_part_id, child), ...])
        progress: callable(depth, n_collected)
        print_tree / tree_txt_path: pretty tree to stdout / to a .txt file
        tree_max_lines: truncates the printed AND written txt tree (None = all)
        position_key: field holding the child's position inside its parent
        tree_md_path: single page with the whole tree as nested admonitions
        md_max_depth: deepest admonition nesting (deeper nodes omitted from .md)
        page_title / page_description: front matter + H1 of that page

    Returns descendants in BFS order (deduplicated, parents before children),
    or (descendants, edges) if with_edges=True.

    Notes:
        - `seen` is seeded with the root, so cycles and parts mounted under two
          parents cannot loop; the repeat is collected once, at the shallowest
          level, and only rendered as a non-expanded duplicate edge.
        - get_children raises on HTTP errors, so a failed call aborts instead of
          producing a silently truncated (and therefore wrong) shipment.
    """
    if ofKind != "all" and ofKind not in data.KoPID_from_partKoPName:
        raise RuntimeError(f"Unknown kind of part '{ofKind}'")

    root_id = int(part_id)
    seen = {root_id}
    collected, edges = [], []
    children_by_parent, dupes_by_parent = {}, {}
    frontier, depth = [root_id], 0

    def fetch_children(pid):
        children, _ = get_children(pid, onlyNonDeleted=onlyNonDeleted, ofKind=ofKind)
        return children

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        while frontier and (max_depth is None or depth < max_depth):
            results = list(ex.map(fetch_children, frontier))
            next_frontier = []
            for parent_id, children in zip(frontier, results):
                for c in children:
                    node = c["part"]
                    position = c.get(position_key)
                    if position is None:
                        position = node.get(position_key)
                    child_id = int(node["part_id"])
                    if child_id in seen:
                        dupes_by_parent.setdefault(parent_id, []).append((node, position))
                        continue
                    seen.add(child_id)
                    collected.append(node)
                    edges.append((parent_id, node))
                    children_by_parent.setdefault(parent_id, []).append((node, position))
                    next_frontier.append(child_id)
            if progress is not None:
                progress(depth + 1, len(collected))
            frontier, depth = next_frontier, depth + 1

    needs_root = bool(print_tree or include_parent or tree_txt_path or tree_md_path)
    root_node = get_info_of_part_id(root_id)[0] if needs_root else None

    if include_parent and root_node is not None:
        collected.insert(0, root_node)

    if root_node is not None and (print_tree or tree_txt_path):
        lines = _part_tree_lines(
            root_node,
            children_by_parent,
            dupes_by_parent,
            ascii=tree_ascii,
            max_lines=tree_max_lines,
        )
        if print_tree:
            print("\n".join(lines), file=tree_file)
        if tree_txt_path:
            write_tree_txt(tree_txt_path, lines)

    if root_node is not None and tree_md_path:
        write_detector_tree_page(
            tree_md_path,
            root_node,
            children_by_parent,
            dupes_by_parent,
            title=page_title,
            description=page_description,
            admonition_type=md_admonition_type,
            max_depth=md_max_depth,
            link=md_link_parts,
            url_template=part_url_template,
            new_tab=md_new_tab,
        )

    if with_edges:
        return collected, edges
    return collected


def get_locations(onlyNonDeleted=True):
    try:
        locations, responseText = api.fetch_information("/locations")
        if onlyNonDeleted:
            interesting_locations = []
            for m in locations:
                if str(m["is_record_deleted"]) == "F":
                    interesting_locations.append(m)
            return interesting_locations, responseText
        else:
            return locations, responseText
    except API_ERRORS as e:
        raise e


def get_manufacturers(onlyNonDeleted=True):
    try:
        manufacturers, responseText = api.fetch_information("/manufacturers")
        if onlyNonDeleted:
            interesting_manufacturers = []
            for m in manufacturers:
                if str(m["is_record_deleted"]) == "F":
                    interesting_manufacturers.append(m)
            return interesting_manufacturers, responseText
        else:
            return manufacturers, responseText
    except API_ERRORS as e:
        raise e


def get_shipment_companies(onlyNonDeleted=True):
    try:
        # NOTE: "shipmentcomany" (sic) is the real route on the ProdDB API,
        # confirmed against https://hgtddb-api.web.cern.ch/hgtddb/shipmentcomany.
        # /shipmentcompanies does NOT exist — do not "fix" the spelling.
        companies, responseText = api.fetch_information("/shipmentcomany")
        if onlyNonDeleted:
            companies = [c for c in companies if str(c["is_record_deleted"]) == "F"]
        return companies, responseText
    except API_ERRORS as e:
        raise e


# this loads the full partstree, quite slow (and big!)
def load_partstree(onlyNonDeleted=True):
    try:
        partstree, responseText = api.fetch_information("/partstreelist")
        interesting_partstree = []
        for p in partstree:
            if str(p["is_record_deleted"]) == "F":
                if (
                    p["part"]["kind_of_part"]["kind_of_part_id"] == 1005
                    and p["part_parent"]["kind_of_part"]["kind_of_part_id"] == 2407
                ):
                    interesting_partstree.append(p)
        return interesting_partstree, responseText
    except API_ERRORS as e:
        raise e


# this checks if a SN is valid, i.e. fulfills the ATLAS convention
def check_SN_valid(snIn, debug=False):
    messageOut = "Invalid Serial Number"
    lengthMessageOut = ""
    propertiesOut = ""
    if (snIn[:3] == "99W") or (snIn[:3] == "98W"):
        messageOut = "This is a test SN only / dummy placeholder for DB development."
        return False, messageOut
    elif snIn[:3] == "20W":
        messageOut = "Attempting to decode ATLAS SN"
        if len(snIn) < 14:
            lengthMessageOut = "ATLAS SN must have 14 digits. Found too few."
            return False, lengthMessageOut
        elif len(snIn) > 14:
            lengthMessageOut = "ATLAS SN must have 14 digits. Found too many."
            return False, lengthMessageOut
        else:
            # check for Sensor (sensor is special, it has only one digit for its component type)
            # first make sure to not get a Support Unit (SU) which also starts with S
            if (snIn[3] == "S") and (snIn[4] != "U"):
                # either Sensor or Sensor Wafer
                if snIn[4] == "0":
                    # Wafer
                    messageOut = "Attempting to decode Wafer SN"
                    try:
                        # note, every variable that is called somethingExplainer
                        # is just for human-readable decoding with a meaning
                        # not necessary to be stored in the DB
                        # (component groups should complain if they should be stored)
                        manu = snIn[5]
                        if manu == "0":
                            manuExplainer = "IHEP-IME"
                        elif manu == "1":
                            manuExplainer = "USTC-IME"
                        else:
                            manuExplainer = "Unknown Manufacturer / Vendor attribute!"
                            return False, manuExplainer
                    except Exception:
                        messageOut = "Failed to decode Wafer SN, check if you used this pattern: 20WS0MPBBONNNN"
                        return False, messageOut
                else:
                    # Sensor
                    try:
                        manu = snIn[4]
                        if manu == "1":
                            manuExplainer = "IHEP-IME Pre-production"
                        elif manu == "2":
                            manuExplainer = "IHEP-IME Production"
                        elif manu == "3":
                            manuExplainer = "USTC-IME Pre-production"
                        elif manu == "4":
                            manuExplainer = "USTC-IME Production"
                        else:
                            manuExplainer = "Unknown Sensor type attribute!"
                            return False, manuExplainer
                        stype = snIn[5]
                        if stype == "0":
                            stypeExplainer = "main sensor"
                        elif stype == "1":
                            stypeExplainer = "QC-TS of main sensor"
                        elif stype == "2":
                            stypeExplainer = "main partial sensor"
                        elif stype == "3":
                            stypeExplainer = "QC-TS of main partial sensor"
                        else:
                            stypeExplainer = "Unknown Sensor type attribute!"
                            return False, stypeExplainer
                        batchn = f"{snIn[6]}{snIn[7]}"
                        wafern = f"{snIn[8]}{snIn[9]}{snIn[10]}{snIn[11]}"
                        locInWaf = f"{snIn[12]}{snIn[13]}"
                        if int(locInWaf) <= 52:
                            locInWafExplainer = "main sensor"
                        elif int(locInWaf) >= 61:
                            locInWafExplainer = "partial sensor"
                        else:
                            locInWafExplainer = "Unknown Location in wafer attribute!"
                            return False, locInWafExplainer
                        propertiesOut = (
                            f"Manufacturer / Vendor: {manu} ({manuExplainer}), Sensor type: {stype} ({stypeExplainer}), "
                            f"Batch number: {batchn}, Wafer number: {wafern}, Location in wafer: {locInWaf} ({locInWafExplainer})"
                        )
                        if debug:
                            print(propertiesOut)
                        if lengthMessageOut == "":
                            messageOut = "Successfully decoded Sensor SN"
                        else:
                            messageOut = ""
                    except Exception:
                        messageOut = "Failed to decode Sensor SN, check if you used this pattern: 20WSMEBBNNNNXY"
                        return False, messageOut
            elif snIn[3] == "F" and snIn[4] == "T":
                messageOut = "Attempting to decode Flex Tail SN"
                try:
                    manu = snIn[5]
                    snGeneration = 2  # 0: pre 24052023, 1: post 24052023 but pre 2025, 1.2: new demonstrator order 2024/2025, 2 (default): from 2025 for (pre-)production
                    if manu == "G":
                        manuExplainer = "Germany"
                    elif manu == "C":
                        manuExplainer = "China"
                    elif manu == "S":
                        manuExplainer = "Slovenia"
                    elif manu == "M":
                        manuExplainer = "Morocco"
                    elif manu == "1":
                        snGeneration = 0
                        manuExplainer = "Germany"
                    elif manu == "2":
                        snGeneration = 0
                        manuExplainer = "China"
                    elif manu == "3":
                        snGeneration = 0
                        manuExplainer = "Slovenia"
                    else:
                        manuExplainer = "Unknown Vendor attribute!"
                        return False, manuExplainer
                    digitSeven = snIn[6]
                    digitEight = snIn[7]
                    if digitEight == "D" and int(digitSeven) <= 2:
                        snGeneration = 1
                        messageOut = "Recognize old Flex Tail SN definition, used for demonstrator from 24.05.2023 until 2024"
                        prodExplainer = "demonstrator"
                    elif digitEight == "1" and digitSeven == "1":
                        snGeneration = 1
                        messageOut = "Recognize old Flex Tail SN definition, used for demonstrator from 24.05.2023 until 2024"
                        prodExplainer = "demonstrator"
                    elif digitEight == "2" and digitSeven == "1":
                        snGeneration = 1.2
                        messageOut = "Recognize old Flex Tail SN definition, used for new demonstrator order 2024/2025"
                        prodExplainer = "demonstrator"
                    else:
                        if snGeneration == 2:
                            messageOut = "Recognize newest Flex Tail SN definition, used from 2025 for (pre-)production as documented in ATL-COM-HGTD-2024-026"
                        else:
                            messageOut = "Recognize old Flex Tail SN definition, used for demonstrator until 24.05.2023"
                    readout = f"{snIn[8]}"
                    if readout == "R":
                        readoutExplainer = "single readout"
                    elif readout == "F":
                        readoutExplainer = "full readout"
                    else:
                        readoutExplainer = "Unknown Readout attribute!"
                        return False, readoutExplainer
                    fttype = (
                        f"{snIn[9]}{snIn[10]}"  # what they mean is different for each generation
                    )
                    fttypeExplainer = "Small length type: long cable, conversion to mm found in Slot table for vessel D (demonstrator) or A/C (production), work in progress"
                    ftcounter = f"{snIn[11]}{snIn[12]}{snIn[13]}"
                    # now we know the SN generation, we can proceed
                    if snGeneration == 2:
                        prod = digitSeven
                        if prod == "M":
                            prodExplainer = "Main production"
                        elif prod == "P":
                            prodExplainer = "Pre-production"
                        elif prod == "D":
                            prodExplainer = "demonstrator"
                        elif prod == "T":
                            prodExplainer = "test"
                        elif prod == "O":
                            prodExplainer = "other"
                        else:
                            prodExplainer = "Unknown Production attribute!"
                            return False, prodExplainer
                        batchn = digitEight
                    elif snGeneration == 1.2:
                        prod = digitSeven
                        # prodExplainer already known above
                        batchn = digitEight
                    elif snGeneration == 1:
                        prod = digitEight
                        # prodExplainer already known above
                        batchn = digitSeven
                    else:
                        prod = digitEight
                        if prod == "0":
                            prodExplainer = "Main production"
                        elif prod == "1":
                            prodExplainer = "demonstrator"
                        elif prod == "2":
                            prodExplainer = "test"
                        elif prod == "3":
                            prodExplainer = "other"
                        else:
                            prodExplainer = "Unknown Production attribute!"
                            return False, prodExplainer
                        batchn = digitSeven
                    propertiesOut = f"Manufacturer / Vendor: {manu} ({manuExplainer}), Production: {prod} ({prodExplainer}), Batch number: {batchn}, Readout: {readout}, Type: {fttype} ({fttypeExplainer}), Counter: {ftcounter}"
                    if debug:
                        print(propertiesOut)
                    if lengthMessageOut == "":
                        if snGeneration == 2:
                            messageOut = "Successfully decoded newest Flex Tail SN definition, used from 2025 for (pre-)production as documented in ATL-COM-HGTD-2024-026"
                        elif snGeneration == 1.2:
                            messageOut = "Successfully decoded old Flex Tail SN definition, used for new demonstrator order 2024/2025"
                        elif snGeneration == 1:
                            messageOut = "Successfully decoded old Flex Tail SN definition, used for demonstrator from 24.05.2023 until 2024"
                        else:
                            messageOut = "Successfully decoded old Flex Tail SN definition, used for demonstrator until 24.05.2023"
                    else:
                        messageOut = ""
                except Exception:
                    messageOut = "Failed to decode FT SN, check if you used this pattern: 20WFTMBPQTTNNN (or an older SN pattern for the demonstrator)"
                    return False, messageOut
            elif snIn[3] == "M" and snIn[4] == "O":
                messageOut = "Attempting to decode Module SN"
                try:
                    as_ = snIn[5]
                    if as_ == "F":
                        asExplainer = "IFAE"
                    elif as_ == "H":
                        asExplainer = "IHEP"
                    elif as_ == "J":
                        asExplainer = "IJCLab"
                    elif as_ == "M":
                        asExplainer = "Mainz"
                    elif as_ == "A":
                        asExplainer = "MAScIR"
                    elif as_ == "U":
                        asExplainer = "USTC"
                    else:
                        asExplainer = "Unknown Assembly site attribute!"
                        return False, asExplainer
                    prod = snIn[6]
                    if prod == "M":
                        prodExplainer = "Main production"
                    elif prod == "P":
                        prodExplainer = "Pre-production"
                    elif prod == "D":
                        prodExplainer = "demonstrator"
                    elif prod == "T":
                        prodExplainer = "test"
                    elif prod == "O":
                        prodExplainer = "other"
                    else:
                        prodExplainer = "Unknown Production attribute!"
                        return False, prodExplainer
                    batchn = snIn[7]
                    counter = "".join(snIn[8:14])
                    propertiesOut = f"Assembly site: {as_} ({asExplainer}), Production: {prod} ({prodExplainer}), Batch number: {batchn}, Counter: {counter}"
                    if debug:
                        print(propertiesOut)
                    if lengthMessageOut == "":
                        messageOut = "Successfully decoded Module SN"
                    else:
                        messageOut = ""
                except Exception:
                    messageOut = (
                        "Failed to decode Module SN, check if you used this pattern: 20WMOKPBNNNNNN"
                    )
                    return False, messageOut
            elif snIn[3] == "H":
                messageOut = "Attempting to decode Hybrid SN"
                try:
                    manu_step2 = snIn[4]
                    if manu_step2 == "N":
                        manu_step2Explainer = "NCAP"
                    elif manu_step2 == "P":
                        manu_step2Explainer = "Patech"
                    else:
                        manu_step2Explainer = "Unknown Assembly site attribute for Step 2!"
                        return False, manu_step2Explainer
                    manu_step3 = snIn[5]
                    if manu_step3 == "N":
                        manu_step3Explainer = "NCAP"
                    elif manu_step3 == "D":
                        manu_step3Explainer = "Disco"
                    elif manu_step3 == "M":
                        manu_step3Explainer = "micropack"
                    else:
                        manu_step3Explainer = "Unknown Assembly site attribute for Step 3!"
                        return False, manu_step3Explainer
                    manu_step4 = snIn[6]
                    if manu_step4 == "N":
                        manu_step4Explainer = "NCAP"
                    elif manu_step4 == "I":
                        manu_step4Explainer = "IFAE"
                    elif manu_step4 == "C":
                        manu_step4Explainer = "CNM"
                    else:
                        manu_step4Explainer = "Unknown Assembly site attribute for Step 4!"
                        return False, manu_step4Explainer
                    prod = snIn[7]
                    if prod == "M" or prod == "0":
                        prodExplainer = "Main production"
                    elif prod == "P":
                        prodExplainer = "Pre-production"
                    elif prod == "D" or prod == "1":
                        prodExplainer = "demonstrator"
                    elif prod == "T" or prod == "2":
                        prodExplainer = "test"
                    elif prod == "O" or prod == "3":
                        prodExplainer = "other"
                    else:
                        prodExplainer = "Unknown Production attribute!"
                        return False, prodExplainer
                    batchn = f"{snIn[8]}{snIn[9]}"
                    counter = "".join(snIn[10:14])
                    propertiesOut = f"Manufacturer / Vendor (Step 2): {manu_step2} ({manu_step2Explainer}), Manufacturer / Vendor (Step 3): {manu_step3} ({manu_step3Explainer}), Manufacturer / Vendor (Step 4): {manu_step4} ({manu_step4Explainer}), Production: {prod} ({prodExplainer}), Batch number: {batchn}, Counter: {counter}"
                    if debug:
                        print(propertiesOut)
                    if lengthMessageOut == "":
                        messageOut = "Successfully decoded Hybrid SN"
                    else:
                        messageOut = ""
                except Exception:
                    messageOut = (
                        "Failed to decode Hybrid SN, check if you used this pattern: 20WHMMMPBBNNNN"
                    )
                    return False, messageOut
            elif snIn[3] == "A" and snIn[4] == "S":
                messageOut = "Attempting to decode ASIC SN"
                try:
                    tests = snIn[5]
                    if tests == "H":
                        testsExplainer = "IHEP"
                    elif tests == "J":
                        testsExplainer = "IJCLab"
                    else:
                        testsExplainer = "Unknown Assembly site attribute!"
                        return False, testsExplainer
                    prod = snIn[6]
                    if prod in ("M"):
                        prodExplainer = "Main production"
                    elif prod == "P":
                        prodExplainer = "Pre-production"
                    else:
                        prodExplainer = "Unknown Production attribute!"
                        return False, prodExplainer
                    waferID = "".join(snIn[7:14])
                    waferNr = "".join(snIn[7:11])
                    chipID = "".join(snIn[11:14])
                    propertiesOut = f"Test site: {tests} ({testsExplainer}), Production: {prod} ({prodExplainer}), Wafer_ID: {waferID}, Wafer_Nr: {waferNr}, Chip_ID: {chipID}"
                    if debug:
                        print(propertiesOut)
                    if lengthMessageOut == "":
                        messageOut = "Successfully decoded ASIC SN"
                    else:
                        messageOut = ""
                except Exception:
                    messageOut = (
                        "Failed to decode ASIC SN, check if you used this pattern: 20WASVPDDDDCCC"
                    )
                    return False, messageOut
            elif snIn[3] == "M" and snIn[4] == "F":
                messageOut = "Attempting to decode Module Flex SN"
                try:
                    manu = snIn[5]
                    if manu == "H":
                        manuExplainer = "IHEP"
                    else:
                        manuExplainer = "Unknown Assembly site attribute!"
                        return False, manuExplainer
                    prod = snIn[6]
                    if prod in ("M", "0"):
                        prodExplainer = "Main production"
                    elif prod == "P":
                        prodExplainer = "Pre-production"
                    elif prod in ("D", "1"):
                        prodExplainer = "demonstrator"
                    elif prod in ("T", "2"):
                        prodExplainer = "test"
                    elif prod in ("O", "3"):
                        prodExplainer = "other"
                    else:
                        prodExplainer = "Unknown Production attribute!"
                        return False, prodExplainer
                    batchn = snIn[7]
                    grounding = snIn[8]
                    counter = "".join(snIn[9:14])
                    propertiesOut = f"Manufacturer / Vendor: {manu} ({manuExplainer}), Production: {prod} ({prodExplainer}), Batch number: {batchn}, Grounding scheme: {grounding}, Counter: {counter}"
                    if debug:
                        print(propertiesOut)
                    if lengthMessageOut == "":
                        messageOut = "Successfully decoded Module Flex SN"
                    else:
                        messageOut = ""
                except Exception:
                    messageOut = "Failed to decode Module Flex SN, check if you used this pattern: 20WMFMPBJNNNNN"
                    return False, messageOut
            elif snIn[3] == "S" and snIn[4] == "U":
                messageOut = "Attempting to decode Support Unit SN"
                try:
                    manu = snIn[5]
                    if manu == "C":
                        manuExplainer = "China"
                    else:
                        manuExplainer = "Unknown Vendor attribute!"
                        return False, manuExplainer
                    prod = snIn[6]
                    if prod in ["M", "0"]:
                        prodExplainer = "Main production"
                        sn_meta_gen = "new"
                    elif prod == "P":
                        prodExplainer = "Pre-production"
                        sn_meta_gen = "new"
                    elif prod in ["D", "1"]:
                        prodExplainer = "demonstrator"
                        sn_meta_gen = "old"
                    elif prod in ["T", "2"]:
                        prodExplainer = "test"
                        sn_meta_gen = "old"
                    elif prod in ["O", "3"]:
                        prodExplainer = "other"
                        sn_meta_gen = "old"
                    else:
                        prodExplainer = "Unknown Production attribute!"
                        return False, prodExplainer
                    if sn_meta_gen == "new":
                        batchn = str(snIn[7])
                        side = str(snIn[8])
                        if side == "F":
                            sideExplainer = "F"
                        elif side == "B":
                            sideExplainer = "B"
                        else:
                            sideExplainer = "Unknown F or B type attribute!"
                            return False, sideExplainer
                        ring = str(snIn[9])
                        if ring == "I":
                            ringExplainer = "inner"
                        elif ring == "M":
                            ringExplainer = "middle"
                        elif ring == "O":
                            ringExplainer = "outer"
                        else:
                            ringExplainer = "Unknown Ring attribute!"
                            return False, ringExplainer
                        numerictype = str(snIn[10]) + str(snIn[11])
                        counter = str(snIn[12]) + str(snIn[13])
                        propertiesOut = f"Manufacturer / Vendor: {manu} ({manuExplainer}), Production: {prod} ({prodExplainer}), Batch number: {batchn}, F or B type: {side} ({sideExplainer}), Ring: {ring} ({ringExplainer}), Type: {numerictype}, Counter: {counter}"
                        if debug:
                            print(propertiesOut)
                        if lengthMessageOut == "":
                            messageOut = "Successfully decoded new-gen Support Unit SN"
                        else:
                            messageOut = ""
                    else:
                        side = str(snIn[7])
                        if side == "F":
                            sideExplainer = "F"
                        elif side == "B":
                            sideExplainer = "B"
                        else:
                            sideExplainer = "Unknown F or B type attribute!"
                            return False, sideExplainer
                        ring = str(snIn[8])
                        if ring == "I":
                            ringExplainer = "inner"
                        elif ring == "M":
                            ringExplainer = "middle"
                        elif ring == "O":
                            ringExplainer = "outer"
                        else:
                            ringExplainer = "Unknown Ring attribute!"
                            return False, ringExplainer
                        numerictype = str(snIn[9]) + str(snIn[10])
                        counter = str(snIn[11]) + str(snIn[12]) + str(snIn[13])
                        propertiesOut = f"Manufacturer / Vendor: {manu} ({manuExplainer}), Production: {prod} ({prodExplainer}), F or B type: {side} ({sideExplainer}), Ring: {ring} ({ringExplainer}), Type: {numerictype}, Counter: {counter}"
                        if debug:
                            print(propertiesOut)
                        if lengthMessageOut == "":
                            messageOut = "Successfully decoded old-gen Support Unit SN"
                        else:
                            messageOut = ""
                except Exception:
                    messageOut = "Failed to decode Support Unit SN, check if you used this pattern: 20WSUMPBZRTTNN"
                    return False, messageOut
            elif snIn[3] == "D" and snIn[4] == "U":
                messageOut = "Attempting to decode Detector Unit SN"
                try:
                    manu = snIn[5]
                    if manu == "F" or manu == "1":
                        manuExplainer = "IFAE"
                    elif manu == "H" or manu == "2":
                        manuExplainer = "IHEP"
                    elif manu == "P" or manu == "3":
                        manuExplainer = "LPNHE"
                    elif manu == "M" or manu == "4":
                        manuExplainer = "Mainz"
                    elif manu == "A" or manu == "5":
                        manuExplainer = "MAScIR"
                    elif manu == "U" or manu == "6":
                        manuExplainer = "USTC"
                    else:
                        manuExplainer = "Unknown Site attribute!"
                        return False, manuExplainer
                    prod = snIn[6]
                    if prod == "M" or prod == "0":
                        prodExplainer = "Main production"
                        sn_meta_gen = "new"
                    elif prod == "P":
                        prodExplainer = "Pre-production"
                        sn_meta_gen = "new"
                    elif prod == "D" or prod == "1":
                        prodExplainer = "demonstrator"
                        sn_meta_gen = "old"
                    elif prod == "T" or prod == "2":
                        prodExplainer = "test"
                        sn_meta_gen = "old"
                    elif prod == "O" or prod == "3":
                        prodExplainer = "other"
                        sn_meta_gen = "old"
                    else:
                        prodExplainer = "Unknown Production attribute!"
                        return False, prodExplainer
                    if sn_meta_gen == "new":
                        batchn = str(snIn[7])
                        side = str(snIn[8])
                        if side == "F":
                            sideExplainer = "F"
                        elif side == "B":
                            sideExplainer = "B"
                        else:
                            sideExplainer = "Unknown F or B type attribute!"
                            return False, sideExplainer
                        ring = str(snIn[9])
                        if ring == "I":
                            ringExplainer = "inner"
                        elif ring == "M":
                            ringExplainer = "middle"
                        elif ring == "O":
                            ringExplainer = "outer"
                        else:
                            ringExplainer = "Unknown Ring attribute!"
                            return False, ringExplainer
                        numerictype = str(snIn[10]) + str(snIn[11])
                        counter = str(snIn[12]) + str(snIn[13])
                        propertiesOut = f"Sites that install modules on SU: {manu} ({manuExplainer}), Production: {prod} ({prodExplainer}), Batch number: {batchn}, F or B type: {side} ({sideExplainer}), Ring: {ring} ({ringExplainer}), Type: {numerictype}, Counter: {counter}"
                        if debug:
                            print(propertiesOut)
                        if lengthMessageOut == "":
                            messageOut = "Successfully decoded new-gen Detector Unit SN"
                        else:
                            messageOut = ""
                    else:
                        side = str(snIn[7])
                        if side == "F":
                            sideExplainer = "F"
                        elif side == "B":
                            sideExplainer = "B"
                        else:
                            sideExplainer = "Unknown F or B type attribute!"
                            return False, sideExplainer
                        ring = str(snIn[8])
                        if ring == "I":
                            ringExplainer = "inner"
                        elif ring == "M":
                            ringExplainer = "middle"
                        elif ring == "O":
                            ringExplainer = "outer"
                        else:
                            ringExplainer = "Unknown Ring attribute!"
                            return False, ringExplainer
                        numerictype = str(snIn[9]) + str(snIn[10])
                        counter = str(snIn[11]) + str(snIn[12]) + str(snIn[13])
                        propertiesOut = f"Sites that install modules on SU: {manu} ({manuExplainer}), Production: {prod} ({prodExplainer}), F or B type: {side} ({sideExplainer}), Ring: {ring} ({ringExplainer}), Type: {numerictype}, Counter: {counter}"
                        if debug:
                            print(propertiesOut)
                        if lengthMessageOut == "":
                            messageOut = "Successfully decoded old-gen Detector Unit SN"
                        else:
                            messageOut = ""
                except Exception:
                    messageOut = "Failed to decode Detector Unit SN, check if you used this pattern: 20WDUKPBZRTTNN"
                    return False, messageOut
            elif snIn[3] == "G" and snIn[4] == "L":
                messageOut = "Attempting to decode Glue SN"
                try:
                    manu = snIn[5]
                    if manu in ("F", "1"):
                        manuExplainer = "IFAE"
                    elif manu in ("H", "2"):
                        manuExplainer = "IHEP"
                    elif manu in ("J", "3"):
                        manuExplainer = "IJCLab"
                    elif manu in ("M", "4"):
                        manuExplainer = "Mainz"
                    elif manu in ("A", "5"):
                        manuExplainer = "MAScIR"
                    elif manu in ("U", "6"):
                        manuExplainer = "USTC"
                    else:
                        manuExplainer = "Unknown Site attribute!"
                        return False, manuExplainer
                    prod = snIn[6]
                    if prod in ("M", "0"):
                        prodExplainer = "Main production"
                    elif prod == "P":
                        prodExplainer = "Pre-production"
                    elif prod in ("D", "1"):
                        prodExplainer = "demonstrator"
                    elif prod in ("T", "2"):
                        prodExplainer = "test"
                    elif prod in ("O", "3"):
                        prodExplainer = "other"
                    else:
                        prodExplainer = "Unknown Production attribute!"
                        return False, prodExplainer
                    counter = "".join(snIn[7:14])
                    propertiesOut = f"Manufacturer / Vendor: {manu} ({manuExplainer}), Production: {prod} ({prodExplainer}), Counter: {counter}"
                    if debug:
                        print(propertiesOut)
                    if lengthMessageOut == "":
                        messageOut = "Successfully decoded Glue SN"
                    else:
                        messageOut = ""
                except Exception:
                    messageOut = (
                        "Failed to decode Glue SN, check if you used this pattern: 20WGLMPNNNNNNN"
                    )
                    return False, messageOut
            elif snIn[3] == "P" and snIn[4] == "E":
                messageOut = "Attempting to decode PEB SN"
                try:
                    manu = snIn[5]
                    if manu == "H":
                        manuExplainer = "IHEP"
                    elif manu == "N":
                        manuExplainer = "NJU"
                    else:
                        manuExplainer = "Unknown Manufacturer / Vendor attribute!"
                        return False, manuExplainer
                    prod = snIn[6]
                    if prod == "M" or prod == "0":
                        prodExplainer = "Main production"
                    elif prod == "P":
                        prodExplainer = "Pre-production"
                    elif prod == "D" or prod == "1":
                        prodExplainer = "demonstrator"
                    elif prod == "T" or prod == "2":
                        prodExplainer = "test"
                    elif prod == "O" or prod == "3":
                        prodExplainer = "other"
                    else:
                        prodExplainer = "Unknown Production attribute!"
                        return False, prodExplainer
                    batchn = str(snIn[7])
                    grounding = str(snIn[8])
                    numerictype = str(snIn[9]) + str(snIn[10])
                    counter = str(snIn[11]) + str(snIn[12]) + str(snIn[13])
                    propertiesOut = f"Manufacturer / Vendor: {manu} ({manuExplainer}), Production: {prod} ({prodExplainer}), Batch number: {batchn}, Grounding scheme: {grounding}, Type: {numerictype}, Counter: {counter}"
                    if debug:
                        print(propertiesOut)
                    if lengthMessageOut == "":
                        messageOut = "Successfully decoded PEB SN"
                    else:
                        messageOut = ""
                except Exception:
                    messageOut = (
                        "Failed to decode PEB SN, check if you used this pattern: 20WPEMPBJNNNNN"
                    )
                    return False, messageOut
            elif snIn[3] == "C" and snIn[4] == "S":
                messageOut = "Attempting to decode HV Power Supply Crate SN"
                try:
                    manu = f"{snIn[5]}{snIn[6]}"
                    if manu == "P0":
                        manuExplainer = "IHEP-SDU Pre-production"
                    elif manu == "P1":
                        manuExplainer = "IHEP-SDU Production"
                    else:
                        manuExplainer = "Unknown Manufacturer / Vendor attribute!"
                        return False, manuExplainer
                    prod = f"{snIn[7]}{snIn[8]}{snIn[9]}{snIn[10]}"
                    batchn = f"{snIn[11]}{snIn[12]}{snIn[13]}"
                    propertiesOut = f"Manufacturer / Vendor: {manu} ({manuExplainer}), Production time YYMM: {prod}, Batch number: {batchn}"
                    if debug:
                        print(propertiesOut)
                    if lengthMessageOut == "":
                        messageOut = "Successfully decoded HV Power Supply Crate SN"
                    else:
                        messageOut = ""
                except Exception:
                    messageOut = "Failed to decode HV Power Supply Crate SN, check if you used this pattern: 20WTPMMYYMMBBB"
                    return False, messageOut
            elif snIn[3] == "M" and snIn[4] == "D":
                messageOut = "Attempting to decode HV Module SN"
                try:
                    manu = f"{snIn[5]}{snIn[6]}"
                    if manu == "P0":
                        manuExplainer = "IHEP-SDU Pre-production"
                    elif manu == "P1":
                        manuExplainer = "IHEP-SDU Production"
                    else:
                        manuExplainer = "Unknown Manufacturer / Vendor attribute!"
                        return False, manuExplainer
                    prod = f"{snIn[7]}{snIn[8]}{snIn[9]}{snIn[10]}"
                    batchn = f"{snIn[11]}{snIn[12]}{snIn[13]}"
                    propertiesOut = f"Manufacturer / Vendor: {manu} ({manuExplainer}), Production time YYMM: {prod}, Batch number: {batchn}"
                    if debug:
                        print(propertiesOut)
                    if lengthMessageOut == "":
                        messageOut = "Successfully decoded HV Module SN"
                    else:
                        messageOut = ""
                except Exception:
                    messageOut = "Failed to decode HV Module SN, check if you used this pattern: 20WTPMMYYMMBBB"
                    return False, messageOut
            else:
                messageOut = "Invalid or incomplete Serial Number"
                return False, messageOut
    elif snIn[0] == "V":
        messageOut = "Attempting to decode Slot SN"
        if len(snIn) < 14:
            lengthMessageOut = "Slot SN must have at least 14 digits. Found too few."
            return False, lengthMessageOut
        elif len(snIn) > 16:
            lengthMessageOut = "Slot SN must have at most 16 digits. Found too many."
            return False, lengthMessageOut
        else:
            lengthMessageOut = ""
        try:
            vessel = snIn[1]
            layer = snIn[4]
            quadrant = snIn[7]
            row = snIn.split("R")[-1].split(":")[0]
            mod = snIn.split("M")[1]
            propertiesOut = (
                f"Vessel: {vessel}, Layer: {layer}, Quadrant: {quadrant}, Row: {row}, Module: {mod}"
            )
            if debug:
                print(propertiesOut)
            if lengthMessageOut == "":
                messageOut = "Successfully decoded Slot SN"
            else:
                messageOut = ""
        except Exception:
            messageOut = "Failed to decode Slot SN, check if you used this pattern: Vx:Lx:Qx:Rx:Mx"
            return False, messageOut
    else:
        messageOut = "Invalid Serial Number"
        return False, messageOut
    return True, ""


def get_vbd_for_sensor_via_wafer(sensor_SN, wafer_SN, metric="VBD_AVERAGE"):
    vbd, _ = api.fetch_information(f"/sensorvbdv2view?serial_number={wafer_SN}")
    available_vbd_meas_per_sensor = []
    for s in vbd:
        if s["SERIAL_NUMBER"] == sensor_SN:
            available_vbd_meas_per_sensor.append(s)
    if len(available_vbd_meas_per_sensor) > 0:
        return (
            float(
                sorted(
                    available_vbd_meas_per_sensor,
                    key=lambda d: d["RUN_END_TIMESTAMP"],
                    reverse=True,
                )[0][metric]
            ),
            "",
        )
    else:
        return (
            -999999,
            f"Could not retrieve VBD via /sensorvbdv2view for Sensor {sensor_SN} and Wafer {wafer_SN}",
        )


def get_vbd_from_iv(i, v, method="interpolate_linear", debug=False, threshold_in_A=5e-5):
    """
    Determine Vbd for a given IV curve with measured currents per voltage (needs two lists as input)

    interpolate_linear: find the V-range between which the threshold for BD was exceeded and interpolate linearly between them
    first_to_exceed: the first V-value for which the threshold for BD was exceeded

    threshold in A, take 500nA=5e-7 from sensor paper for sensor, but 100*500nA=5e-5 for hybrid

    behavior: if multiple passes cross the threshold, return only the first (lowest V)

    Algorithm discussed at February 26 HGTD Week, Annika + Stefano
    """

    # convert the list into numpy array and continue with absolute values
    i = np.abs(np.array(i))
    v = np.abs(np.array(v))

    if debug:
        print(i >= threshold_in_A)

    if np.all(i < threshold_in_A):
        # if during the entire measurement range, the threshold was never exceeded, we have not seen Vbd
        # output a reasonable dummy value that coincides with the worst-case (BD could happen at next 5V step)
        # this is to make sure the average determination has good inputs to work with,
        # but different handling is possible (e.g. excluding such a value from AVG, if it comes from a single pad)
        return 205

    # index in array for which current (I) first exceeds threshold
    first_pass_index = np.where(i >= threshold_in_A)[0][0]

    # use this index to get the corresponding V, I and the last values just before this
    first_v_above_threshold = v[first_pass_index]
    if method == "first_to_exceed":
        return first_v_above_threshold
    else:
        # linear interpolation between two points (just below, just above threshold)
        last_v_below_threshold = v[first_pass_index - 1]
        first_i_above_threshold = i[first_pass_index]
        last_i_below_threshold = i[first_pass_index - 1]

        # relative amount of current between consecutive measured points covered to exceed threshold
        estimated_path_fraction = (threshold_in_A - last_i_below_threshold) / (
            first_i_above_threshold - last_i_below_threshold
        )
        # this fraction of covered voltage between consecutive steps to estimate the interpolated Vbd
        return last_v_below_threshold + estimated_path_fraction * (
            first_v_above_threshold - last_v_below_threshold
        )


def get_i_v_from_iv_pad_str(iv_long_formatted_string):
    string_as_json = json.loads(iv_long_formatted_string)
    i_strings = string_as_json["I"]
    v_strings = string_as_json["V"]
    list_of_currents = [float(i) for i in i_strings]
    list_of_voltages = [float(v) for v in v_strings]
    return list_of_currents, list_of_voltages


def get_ivs_for_all_pads_of_sensor(sensor_SN):
    ivs, _ = api.fetch_information(f"/sensorivview?serial_number={sensor_SN}")
    types = []
    for iv in ivs:
        if str(iv["RUN_TYPE"]) == "15x15":
            types.append("15x15")
        elif str(iv["RUN_TYPE"]) == "15X15":
            types.append("15X15")
        elif str(iv["RUN_TYPE"]) == "15x1":
            types.append("15x1")
        elif str(iv["RUN_TYPE"]) == "15X1":
            types.append("15X1")
        elif str(iv["RUN_TYPE"]) == "1x1":
            types.append("1x1")
        elif str(iv["RUN_TYPE"]) == "1X1":
            types.append("1X1")
    if len(types) == 0:
        return (
            {},
            f"Could not retrieve IV via /sensorivview for Sensor {sensor_SN}",
        )

    # there could be different types, just pick one of them in hierarchy
    if "15x15" in types:
        ivs, _ = api.fetch_information(f"/sensorivview?serial_number={sensor_SN}&run_type=15x15")
    else:
        if "15X15" in types:
            ivs, _ = api.fetch_information(
                f"/sensorivview?serial_number={sensor_SN}&run_type=15X15"
            )
        else:
            if "15x1" in types:
                ivs, _ = api.fetch_information(
                    f"/sensorivview?serial_number={sensor_SN}&run_type=15x1"
                )
            else:
                if "15X1" in types:
                    ivs, _ = api.fetch_information(
                        f"/sensorivview?serial_number={sensor_SN}&run_type=15X1"
                    )
                else:
                    if "1x1" in types:
                        ivs, _ = api.fetch_information(
                            f"/sensorivview?serial_number={sensor_SN}&run_type=1x1"
                        )
                    else:
                        if "1X1" in types:
                            ivs, _ = api.fetch_information(
                                f"/sensorivview?serial_number={sensor_SN}&run_type=1X1"
                            )
                        else:
                            return (
                                -999999,
                                f"Could not retrieve IV via /sensorivview for Sensor {sensor_SN}, unknown run types only {', '.join(types)}",
                            )
    ivs_per_pad = {}
    for curve in ivs:
        pad_loc = int(curve["PAD_LOCATION"])
        if pad_loc in list(range(1, 256)):
            if str(curve["GUARD_RING"]) == "" and str(curve["IV_GUARD_RING"]) == "":
                if pad_loc not in ivs_per_pad:
                    ivs_per_pad[pad_loc] = curve["IV_PAD"]
                else:
                    if ivs_per_pad[pad_loc]["RUN_END_TIMESTAMP"] < curve[pad_loc][
                        "RUN_END_TIMESTAMP"
                    ] or int(ivs_per_pad[pad_loc]["RUN_NUMBER"]) < int(
                        curve[pad_loc]["RUN_NUMBER"]
                    ):
                        # current curve is newer than previously stored one
                        ivs_per_pad[pad_loc] = curve["IV_PAD"]
    return ivs_per_pad, ""


def get_sum_iv_for_sensor(sensor_SN, ivs_per_pad=None):
    if ivs_per_pad is None:
        ivs_per_pad, ivs_response = get_ivs_for_all_pads_of_sensor(sensor_SN)
        if ivs_per_pad == {}:
            return [], ivs_response
    sum_I = []
    list_of_voltages = []
    for pad in ivs_per_pad.keys():
        list_of_currents, list_of_voltages = get_i_v_from_iv_pad_str(ivs_per_pad[pad])
        if sum_I == []:
            sum_I = list_of_currents
        else:
            sum_I = [a + b for a, b in zip(sum_I, list_of_voltages)]
    return [sum_I, list_of_voltages], ""


def get_vbd_for_sensor_via_iv(sensor_SN, threshold_in_A=5e-7, ivs_per_pad=None):
    if ivs_per_pad is None:
        ivs_per_pad, ivs_response = get_ivs_for_all_pads_of_sensor(sensor_SN)
        if ivs_per_pad == {}:
            return [], ivs_response
    # after all ivs, for each pad, are collected, calculate VBD for each of them using 500nA as threshold
    vbd_per_pad = {}
    for pad in ivs_per_pad.keys():
        i, v = get_i_v_from_iv_pad_str(ivs_per_pad[pad])
        vbd_per_pad[pad] = float(get_vbd_from_iv(i, v, threshold_in_A=threshold_in_A))
    return sum(vbd_per_pad.values()) / len(vbd_per_pad.keys()), ""


def get_all_hybrid_ivs():
    ivs, _ = api.fetch_information("/hybridivview")
    return ivs


def get_all_module_ivs():
    ivs, _ = api.fetch_information("/moduleivview")
    return ivs


def get_iv_for_hybrid_or_module(part_SN, all_ivs=None, KoP=None):
    """
    Returns up to one Hybrid (Module) IV for a given Hybrid (Module) SN.
    If multiple are found, pick the one with less None currents.
    If the evaluated curves share the same number of None currents,
    pick the one with larger SR_NO (counts through curves).
    Ignore curves with I = V (data entry errors).

    Parameters:
        part_SN: serial number of Hybrid (Module) to get IV curve for
        all_ivs: list of Hybrid (Module) IVs, or None, if they still need to be obtained from API
        KoP: choices "Module" or "Hybrid", default: "Hybrid", only necessary if all_ivs = None

    Returns:
        List of two lists ([list of currents, list of voltages]), if a valid curve was found, else empty list
        Empty string if IV returned, or reason why no IV returned
    """
    if all_ivs is None:
        if KoP == "Hybrid":
            all_ivs = get_all_hybrid_ivs()
        elif KoP == "Module":
            all_ivs = get_all_module_ivs()
        else:
            return (
                [],
                "You need to provide a KoP out of Hybrid or Module to proceed. "
                "There was no list of IV curves provided.",
            )
    designated_iv_curve_for_part_SN = None
    for ivcurve in all_ivs:
        eval_ivcurve = eval("{" + ivcurve["IV"][1:-1] + "}")
        if eval_ivcurve != {}:
            if eval_ivcurve["I"] != eval_ivcurve["V"]:
                if part_SN == str(ivcurve["SERIAL_NUMBER"]):
                    if designated_iv_curve_for_part_SN is None:
                        designated_iv_curve_for_part_SN = {
                            "IV": eval_ivcurve,
                            "SR_NO": ivcurve["SR_NO"],
                            "RUN_END_TIMESTAMP": ivcurve["RUN_END_TIMESTAMP"],
                        }
                    else:
                        # more than one found
                        # next modifications necessary because many HY/MO IVs do not come with any way to distinguish them (time / user / site etc.)
                        counting_None_inDesignated = len(
                            [i for i in designated_iv_curve_for_part_SN["IV"]["I"] if i == "None"]
                        )
                        counting_None_inCurrent = len([i for i in eval_ivcurve["I"] if i == "None"])
                        if counting_None_inDesignated > counting_None_inCurrent:
                            # replace with another curve with fewer None currents
                            designated_iv_curve_for_part_SN = {
                                "IV": eval_ivcurve,
                                "SR_NO": ivcurve["SR_NO"],
                                "RUN_END_TIMESTAMP": ivcurve["RUN_END_TIMESTAMP"],
                            }
                        elif counting_None_inDesignated == counting_None_inCurrent:
                            if designated_iv_curve_for_part_SN["RUN_END_TIMESTAMP"] < ivcurve[
                                "RUN_END_TIMESTAMP"
                            ] or int(designated_iv_curve_for_part_SN["SR_NO"]) < int(
                                ivcurve["SR_NO"]
                            ):
                                # replace with another curve with higher SR_NO (later upload)
                                designated_iv_curve_for_part_SN = {
                                    "IV": eval_ivcurve,
                                    "SR_NO": ivcurve["SR_NO"],
                                    "RUN_END_TIMESTAMP": ivcurve["RUN_END_TIMESTAMP"],
                                }
    if designated_iv_curve_for_part_SN is not None:
        i_to_return = []
        v_to_return = []
        for ind in range(len(designated_iv_curve_for_part_SN["IV"]["I"])):
            if designated_iv_curve_for_part_SN["IV"]["I"][ind] != "None":
                i_to_return.append(abs(float(designated_iv_curve_for_part_SN["IV"]["I"][ind])))
                v_to_return.append(abs(float(designated_iv_curve_for_part_SN["IV"]["V"][ind])))
        return [i_to_return, v_to_return], ""
    else:
        return [], f"No valid IV curve found for {part_SN}."


def get_vbd_for_hybrid_or_module_via_iv(part_SN, all_ivs=None, KoP=None, threshold_in_A=None):
    if threshold_in_A is None:
        if KoP == "Hybrid":
            threshold_in_A = 5e-5  # to check
        elif KoP == "Module":
            threshold_in_A = 2 * 5e-5  # to check, just guessing here
        else:
            return (
                -999999,
                "You need to provide a KoP out of Hybrid or Module to proceed. "
                "Threshold current could not be inferred. Pass a KoP, or alternatively the threshold in A.",
            )
    iv, response = get_iv_for_hybrid_or_module(part_SN, all_ivs, KoP)
    if response != "":
        return -999999, response
    else:
        return float(get_vbd_from_iv(iv[0], iv[1], threshold_in_A=threshold_in_A))


def module_voltage_correction(currents, voltages):
    return [
        (voltages[i] / ((voltages[i] / currents[i]) - data.module_flex_ohm_res))
        for i in range(len(voltages))
    ]


def sanitize(str_to_sanitize):
    san = re.sub(r"[\s-]+", "_", str_to_sanitize)
    san = re.sub(r"[^\w\.]", "", san)
    san = re.sub(r"__+", "_", san)
    san = re.sub(r"\.\.+", ".", san)
    return san.strip("_.")


# === Shipments

SHIPMENTS_ENDPOINT = "/shipment"
SHIPMENT_ENDPOINT = "/shipment/{shipment_id}/"


def _shipment_post(path, payload, dryrun=False, access_token=None):
    return api.post_information(path, payload, dryrun=dryrun, existing_token=access_token)


def _shipment_put(path, payload, dryrun=False, access_token=None):
    return api.put_information(path, payload, dryrun=dryrun, existing_token=access_token)


def _find_shipment_by_tracking(tracking_number, include_children=True):
    """Look up a shipment by its tracking number (unique per record)."""
    shipments, _ = get_shipments(include_children=include_children)
    matches = [s for s in shipments if str(s.get("tracking_number")) == str(tracking_number)]
    if len(matches) == 1:
        return matches[0]
    if not matches:
        raise RuntimeError(
            f"no shipment with tracking number '{tracking_number}' found after writing it"
        )
    raise RuntimeError(
        f"tracking number '{tracking_number}' is not unique: "
        f"shipment_ids {[s.get('shipment_id') for s in matches]}"
    )


def _ref_id(value, key):
    """FK refs (location, company) are sent as strings, e.g. "1521", "2"."""
    if isinstance(value, dict):
        value = value[key]
    return str(value)


def _part_id(value):
    """part_id stays an int."""
    if isinstance(value, dict):
        value = value["part_id"]
    return int(value)


def part_comment(part):
    """The part's own comment_description, or '' if absent/blank."""
    if not isinstance(part, dict):
        return ""
    return str(part.get("comment_description") or "").strip()


def backfill_part_comments(parts, max_workers=4):
    """Ensure every part dict has `field`, fetching /part/{id}/ where missing.

    Mutates and returns `parts`. One request per part that lacks the field;
    parts that already carry it (e.g. from get_info_of_part_id) are untouched.
    """
    missing = [p for p in parts if isinstance(p, dict) and "comment_description" not in p]
    if not missing:
        return parts

    def fetch(part):
        details, _ = get_info_of_part_id(part["part_id"])
        return details.get("comment_description") or ""

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        for part, value in zip(missing, ex.map(fetch, missing)):
            part["comment_description"] = value
    return parts


def get_shipments(include_children=True, onlyNonDeleted=True):
    try:
        path = SHIPMENTS_ENDPOINT
        if not include_children:
            path += "?include_children=false"
        shipments, responseText = api.fetch_information(path)
        if onlyNonDeleted:
            shipments = [s for s in shipments if str(s["is_record_deleted"]) == "F"]
        return shipments, responseText
    except API_ERRORS as e:
        raise e


def get_shipment(shipment_id):
    try:
        shipment, responseText = api.fetch_information(
            SHIPMENT_ENDPOINT.format(shipment_id=shipment_id)
        )
        return shipment, responseText
    except API_ERRORS as e:
        raise e


def build_shipment_payload(
    from_location,
    to_location,
    company,
    items=None,
    tracking_number=None,
    status="Created",
    shipment_date=None,
    edh_link=None,
    from_contact=None,
    from_contact_email=None,
    to_contact=None,
    to_contact_email=None,
    record_insertion_user=None,
    is_record_deleted="F",
):
    """Build the POST body for a new shipment.

    `from_location`, `to_location`, `company` may be IDs or the nested dicts
    returned by the API; they are serialized as strings. `items` is a list of
    {"part_id": int, "comment": str, optional "serial_number"}. `shipment_date`
    is "YYYY-MM-DD". None values are dropped; empty strings are kept (they are
    how fields get cleared).
    """
    payload = {
        "from_location": _ref_id(from_location, "location_id"),
        "to_location": _ref_id(to_location, "location_id"),
        "company": _ref_id(company, "company_id"),
        "tracking_number": tracking_number,
        "status": status,
        "shipment_date": shipment_date,
        "edh_link": edh_link,
        "from_contact": from_contact,
        "from_contact_email": from_contact_email,
        "to_contact": to_contact,
        "to_contact_email": to_contact_email,
        "record_insertion_user": record_insertion_user,
        "is_record_deleted": is_record_deleted,
    }
    payload = {k: v for k, v in payload.items() if v is not None}
    if items:
        shipmentitems = []
        for it in items:
            # The view does child_data['comment'] with no default, so the key
            # must always be present; the value always comes from the part.
            entry = {"part_id": _part_id(it), "comment": part_comment(it)}
            if it.get("serial_number"):
                entry["serial_number"] = it["serial_number"]
            shipmentitems.append(entry)
        payload["shipmentitems"] = shipmentitems
    return payload


def create_shipment(payload, dryrun=False, access_token=None):
    """POST a new shipment. Returns (shipment_dict, responseText).

    post_information only returns a status string, so the created record is
    read back via its tracking_number. That also means the tracking number
    must be unique — a duplicate makes this lookup ambiguous.
    """
    for key in ("from_location", "to_location", "company"):
        if payload.get(key) in (None, ""):
            raise RuntimeError(f"Shipment payload is missing required field '{key}'")
    tracking_number = payload.get("tracking_number")
    if not tracking_number:
        raise RuntimeError("Shipment payload is missing 'tracking_number'")
    if dryrun:
        return payload, "dryrun: not sent"
    try:
        responseText = _shipment_post(
            SHIPMENTS_ENDPOINT, payload, dryrun=dryrun, access_token=access_token
        )
        created = _find_shipment_by_tracking(tracking_number)
        return created, responseText
    except API_ERRORS as e:
        raise e


def create_shipment_for_parts(
    parts,
    from_location,
    to_location,
    company,
    dryrun=False,
    access_token=None,
    **fields,
):
    """`parts` may be part dicts (get_children / get_info_of_part_id) or IDs.

    Each item's comment is taken from the part's comment_description; it
    cannot be overridden per shipment.
    """
    items = []
    for p in parts:
        entry = {"part_id": _part_id(p)}
        if isinstance(p, dict) and p.get("serial_number"):
            entry["serial_number"] = p["serial_number"]
        items.append(entry)
    payload = build_shipment_payload(
        from_location=from_location,
        to_location=to_location,
        company=company,
        items=items,
        **fields,
    )
    return create_shipment(payload, dryrun=dryrun, access_token=access_token)


def update_shipment(shipment_id, changes, dryrun=False, access_token=None, user=None):
    """PUT a partial change onto an existing shipment.

    The view resolves company/from_location/to_location unconditionally on PUT,
    so merge onto the current record and always send those three as IDs.
    `user` is sent as record_lastupdate_user.
    """
    current, _ = get_shipment(shipment_id)
    payload = {
        "from_location": _ref_id(current["from_location"], "location_id"),
        "to_location": _ref_id(current["to_location"], "location_id"),
        "company": _ref_id(current["company"], "company_id"),
    }
    if user is not None:
        payload["record_lastupdate_user"] = user
    payload.update(changes)
    if dryrun:
        return payload, "dryrun: not sent"
    try:
        responseText = _shipment_put(
            SHIPMENT_ENDPOINT.format(shipment_id=shipment_id),
            payload,
            dryrun=dryrun,
            access_token=access_token,
        )
        updated, _ = get_shipment(shipment_id)
        return updated, responseText
    except API_ERRORS as e:
        raise e


def receive_shipment(shipment_id, dryrun=False, access_token=None, user=None, reception_date=None):
    """Mark as Received -> server side this also moves every item's part
    to the shipment's `to_location`.

    `reception_date` is "YYYY-MM-DD"; None leaves the field untouched.
    """
    changes = {"status": "Received"}
    if reception_date is not None:
        changes["reception_date"] = reception_date
    return update_shipment(
        shipment_id,
        changes,
        dryrun=dryrun,
        access_token=access_token,
        user=user,
    )


# === Parts: bulk creation / update from CSV

PARTS_ENDPOINT = "/partslist"
PART_ENDPOINT = "/part/{part_id}/"

# Kinds of Part accepted in a generic `sn` CSV. Extend this tuple when a new
# KoP gets a working creation path (location/manufacturer mapping per site).
CSV_KINDS_OF_PART = ("Module",)

PART_CSV_REQUIRED_COLUMNS = ("name_label",)
PART_CSV_OPTIONAL_COLUMNS = ("version", "comment")
PART_CSV_SN_COLUMNS = ("module_sn", "sn")


def ask(prompt, default=None, required=False):
    """Prompt until an acceptable value is entered.

    Enter accepts `default` (which may be "" for an optional field).
    `required=True` without a default means the field cannot be left empty.
    """
    shown = f" [{default}]" if default not in (None, "") else ""
    while True:
        value = input(f"{prompt}{shown}: ").strip()
        if value:
            return value
        if default is not None:
            return default
        if not required:
            return ""
        print("  This field is required, please type a value.")


def ask_kind_of_part(kinds=None, default="Module"):
    """Interactively pick a Kind of Part from `kinds` (default: CSV_KINDS_OF_PART).

    With a single candidate the question is skipped entirely. Otherwise the
    candidate list is numbered and the user must pick one of them: either the
    number, or the name (case-insensitive). Enter alone selects `default` when
    it is among `kinds`.
    """
    kinds = list(kinds or CSV_KINDS_OF_PART)
    if not kinds:
        raise RuntimeError("No Kind of Part available to choose from")
    if len(kinds) == 1:
        print(f"Only one Kind of Part available: {kinds[0]} (selected automatically).")
        return kinds[0]

    fallback = default if default in kinds else None
    print("\nPlease pick one of the following kinds of part:")
    for i, kind in enumerate(kinds, start=1):
        suffix = "   (default)" if kind == fallback else ""
        print(f"  {i}) {kind}{suffix}")

    while True:
        raw = input(
            f"Enter the number of your choice (1-{len(kinds)})"
            + (f" or press [Enter] for {fallback}" if fallback else "")
            + ", then confirm with [Enter]: "
        ).strip()
        if not raw:
            if fallback:
                return fallback
            print(f"  No default set — please type a number between 1 and {len(kinds)}.")
            continue
        if raw.isdigit() and 1 <= int(raw) <= len(kinds):
            return kinds[int(raw) - 1]
        for kind in kinds:
            if raw.lower() == kind.lower():
                return kind
        print(
            f"  '{raw}' is not one of the options above. "
            f"Valid answers: 1-{len(kinds)}"
            + (f", or {', '.join(kinds)}" if len(kinds) > 1 else "")
            + "."
        )


def read_parts_csv(path):
    """Read a parts CSV.

    Accepted headers:
        module_sn,name_label[,version][,comment]   -> KoP is Module, no prompt
        sn,name_label[,version][,comment]          -> KoP unknown, ask the user

    Returns a list of dicts with keys sn, kind_of_part, name_label, version,
    comment, line. `kind_of_part` is "Module" for a module_sn header and None
    for a generic sn header (the CLI then asks, or applies --kind).
    Missing optional columns default to "". Rows with an empty SN are skipped.

    Raises ValueError on anything structural (missing/ambiguous header,
    missing name_label, duplicate SN) so the CLI fails before writing to the DB.
    """
    rows, seen = [], {}
    with open(path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames is None:
            raise ValueError(f"{path}: file is empty, expected a header row")

        # tolerate capitalisation and stray whitespace in the header
        header = {(name or "").strip().lower(): name for name in reader.fieldnames}
        present_sn_columns = [c for c in PART_CSV_SN_COLUMNS if c in header]
        if not present_sn_columns:
            raise ValueError(
                f"{path}: no SN column; expected one of "
                f"{', '.join(PART_CSV_SN_COLUMNS)} in the header"
            )
        if len(present_sn_columns) > 1:
            raise ValueError(
                f"{path}: ambiguous header, found both "
                f"{' and '.join(present_sn_columns)}; use exactly one"
            )
        sn_column = present_sn_columns[0]
        # module_sn carries the KoP implicitly, a bare sn does not
        fixed_kind = "Module" if sn_column == "module_sn" else None

        missing = [c for c in PART_CSV_REQUIRED_COLUMNS if c not in header]
        if missing:
            raise ValueError(
                f"{path}: missing required column(s) {missing}; expected header "
                f"{sn_column},name_label,version[optional],comment[optional]"
            )
        absent_optional = [c for c in PART_CSV_OPTIONAL_COLUMNS if c not in header]
        if absent_optional:
            print(f"[warn] {path}: no column(s) {absent_optional}, treating them as empty")

        for lineno, raw in enumerate(reader, start=2):
            row = {
                (k or "").strip().lower(): (v or "").strip()
                for k, v in raw.items()
                if k is not None
            }
            sn = row.get(sn_column, "")
            if not sn:
                continue
            if sn in seen:
                raise ValueError(
                    f"{path}:{lineno}: duplicate SN '{sn}' (first seen on line {seen[sn]})"
                )
            seen[sn] = lineno
            if not row.get("name_label"):
                raise ValueError(f"{path}:{lineno}: name_label must not be empty")
            rows.append(
                {
                    "sn": sn,
                    "kind_of_part": fixed_kind,
                    "name_label": row["name_label"],
                    "version": row.get("version", ""),
                    "comment": row.get("comment", ""),
                    "line": lineno,
                }
            )

    if not rows:
        raise ValueError(f"{path}: no data rows found")
    return rows


def index_parts_by_SN(parts):
    """{serial_number: part} for an already fetched part list."""
    return {str(p["serial_number"]).strip(): p for p in parts if p.get("serial_number")}


def build_part_index(kind_of_part, verbose=True):
    """{serial_number: part} for ONE Kind of Part.

    Deliberately scoped to a single kind: SNs are unique across kinds, but the
    only SNs a caller can act on are those of the kind it is writing. A clash
    with another kind therefore surfaces as a backend error on POST/PUT, which
    the CLI reports instead of pre-empting with a full-DB lookup.
    """
    parts, _ = get_relevant_parts(kind_of_part)
    if verbose:
        print(f"Loaded {len(parts)} '{kind_of_part}' part(s) from the DB.")
    return index_parts_by_SN(parts)


def build_part_payload(
    serial_number,
    name_label,
    version,
    comment,
    username,
    site,
    kind_of_part="Module",
):
    """POST body for a new part, with location/manufacturer/KoP resolved to IDs.

    `username` is stored as record_insertion_user; it comes from the CLI (-u),
    never from the CSV.
    """
    return {
        "barcode": "",
        "serial_number": serial_number,
        "is_record_deleted": "F",
        "version": version or "",
        "name_label": name_label,
        "comment_description": comment,
        "kind_of_part": str(data.KoPID_from_partKoPName[kind_of_part]),
        "location": str(data.relevant_location_IDs_by_shortname[site]),
        "manufacturer": str(data.relevant_manufacturer_IDs_by_shortname[site]),
        "record_insertion_user": username,
    }


def _fk_id(part, field, key):
    """FK of a part record as a string id; raises if the record has none.

    The PUT view resolves location, manufacturer and kind_of_part
    unconditionally (Locations.objects.get(...) with no default), so a body
    without them makes the server raise DoesNotExist -> HTTP 500, not 400.
    """
    value = part.get(field)
    ref = value.get(key) if isinstance(value, dict) else value
    if ref in (None, "", "None"):
        raise RuntimeError(
            f"part {part.get('part_id')} has no usable '{field}'; the PUT view "
            "resolves it unconditionally, so this record cannot be updated"
        )
    return str(ref)


def _kop_id(part, kind_of_part=None):
    """kind_of_part as a string id, from the record or from a shortname."""
    kop = part.get("kind_of_part")
    if isinstance(kop, dict) and kop.get("kind_of_part_id") is not None:
        return str(kop["kind_of_part_id"])
    if isinstance(kop, (str, int)) and str(kop) not in ("", "None"):
        return str(kop)
    if kind_of_part is None:
        raise RuntimeError(
            f"part {part.get('part_id')} carries no kind_of_part; pass kind_of_part="
        )
    return str(data.KoPID_from_partKoPName.get(kind_of_part, kind_of_part))


def build_part_update_payload(
    part, name_label=None, version=None, comment=None, kind_of_part=None, user=None
):
    """PUT body for an existing part.

    PartsDetailApiView.put resolves location, kind_of_part and manufacturer with
    a bare .get() before validating anything, so those three ids must always be
    present — they are taken from the stored record and therefore unchanged.
    Everything else is only sent when a new value was given (the serializer runs
    with partial=True, so omitted fields keep their stored value).

    `user` is sent as record_lastupdate_user. The view also fills that field
    from the X-Oidc-User header, but passing it explicitly is accepted and is
    what the shipment PUT does as well.

    Deliberately NOT sent:
      is_record_deleted  — "T" makes the view delete the part's tree records
      part_id, barcode, serial_number — nothing to change
    """
    if not isinstance(part, dict):
        raise TypeError("build_part_update_payload needs the full part record")
    payload = {
        "location": _fk_id(part, "location", "location_id"),
        "manufacturer": _fk_id(part, "manufacturer", "manufacturer_id"),
        "kind_of_part": _kop_id(part, kind_of_part),
    }
    if user is not None:
        payload["record_lastupdate_user"] = user
    if name_label is not None:
        payload["name_label"] = name_label
    if version is not None:
        payload["version"] = version
    if comment is not None:
        payload["comment_description"] = comment
    return payload


def update_part(
    part,
    name_label=None,
    version=None,
    comment=None,
    kind_of_part=None,
    user=None,
    dryrun=False,
    access_token=None,
):
    """PUT name_label / version / comment_description onto an existing part.

    `part` must be the full record (get_relevant_parts / get_info_of_part_id),
    because the body has to carry location, manufacturer and kind_of_part.
    Fields left as None keep their stored value. `user` becomes
    record_lastupdate_user when given.

    Returns the "<status>, <reason>" string from api.put_information.
    """
    payload = build_part_update_payload(
        part,
        name_label=name_label,
        version=version,
        comment=comment,
        kind_of_part=kind_of_part,
        user=user,
    )
    return api.put_information(
        PART_ENDPOINT.format(part_id=_part_id(part)),
        payload,
        dryrun=dryrun,
        existing_token=access_token,
    )


def update_part_by_SN(
    serial_number,
    name_label=None,
    version=None,
    comment=None,
    kind_of_part="Module",
    user=None,
    dryrun=False,
    access_token=None,
):
    """`update_part` with the part looked up by SN (raises if unknown/ambiguous)."""
    part_id = resolve_part_id_by_sn(serial_number, kind_of_part)
    part, _ = get_info_of_part_id(part_id)
    return update_part(
        part,
        name_label=name_label,
        version=version,
        comment=comment,
        kind_of_part=kind_of_part,
        user=user,
        dryrun=dryrun,
        access_token=access_token,
    )


def recommend_MO_SNs(site, prod, batch, count, existing_SNs, fill_holes=True):
    """Propose `count` unused Module SNs for site/prod/batch.

    Counters are human-readable and start at 1. With fill_holes=True, gaps in
    the existing sequence are filled first; otherwise numbering continues right
    after the highest counter in use. `existing_SNs` is the set of SNs already
    taken, so the result never collides with them.
    """
    prefix = get_MO_SN_prefix(site, prod, batch)
    counters = sorted(
        int(str(sn)[8:]) for sn in existing_SNs if str(sn)[:8] == prefix and str(sn)[8:].isdigit()
    )
    taken = set(counters)
    max_so_far = max(counters) if counters else 0

    holes = [i for i in range(1, max_so_far + 1) if i not in taken] if fill_holes else []
    if len(holes) >= count:
        chosen = holes[:count]
    else:
        chosen = holes + list(range(max_so_far + 1, max_so_far + 1 + (count - len(holes))))
    return [f"{prefix}{counter:06d}" for counter in chosen]

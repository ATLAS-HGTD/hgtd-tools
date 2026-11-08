#!/usr/bin/env python3
"""Generate the HGTD detector parts tree as a text file and/or Markdown page.

Traverses the parts tree below a root part and renders it two ways: a pretty
box-drawing tree (.txt) and a Zensical/MkDocs page where every part is a
collapsible admonition linking to the ProdDB view.

The root can be given either as a part_id or as a serial number plus the kind
of part it belongs to (which is resolved through the ProdDB).

Examples:
    # by part_id, both outputs
    hgtd-tree 28833 --txt out/detector_tree.txt --md docs/detector_tree.md

    # by serial number: --kind only finds the part_id, the whole subtree is walked
    hgtd-tree --sn Detector_Assembly_CERN --kind Detector --md docs/detector_tree.md

    # detector units only, preview in the terminal
    hgtd-tree 28833 --child-kind "Detector Unit" --print

Exit codes: 0 success, 1 runtime/API failure, 2 bad usage.
"""

import argparse
import sys
from pathlib import Path

from hgtd_tools import data, util

DEFAULT_MD_PATH = "out/detector_tree.md"
DEFAULT_TXT_PATH = "out/detector_tree.txt"
DEFAULT_TITLE = "HGTD Detector Parts Tree"


def build_parser():
    p = argparse.ArgumentParser(
        prog="hgtd-tree",
        description="Render the HGTD detector parts tree from the ProdDB.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__.split("Examples:", 1)[1].strip(),
    )

    root = p.add_argument_group("root selection")
    root.add_argument(
        "part_id",
        type=int,
        nargs="?",
        default=None,
        help="root part_id to traverse from (alternative to --sn + --kind)",
    )
    root.add_argument(
        "--sn",
        default=None,
        metavar="SERIAL_NUMBER",
        help="root serial number; requires --kind and resolves to a part_id",
    )
    root.add_argument(
        "--kind",
        default=None,
        metavar="KoP",
        help='kind of part the --sn root belongs to (e.g. "Detector"); '
        "used only to find the part_id, never as a traversal filter",
    )

    trav = p.add_argument_group("traversal")
    trav.add_argument(
        "--max-depth",
        type=int,
        default=None,
        metavar="N",
        help="stop traversal N levels below the root (default: unlimited)",
    )
    trav.add_argument(
        "--child-kind",
        default="all",
        metavar="KoP",
        help='only follow children of this kind (e.g. "Detector Unit"); '
        "default: all — unrelated to --kind",
    )
    trav.add_argument(
        "--workers",
        type=int,
        default=4,
        metavar="N",
        help="threads for the per-level /childslist/ calls (default: 4)",
    )
    trav.add_argument(
        "--include-parent",
        action="store_true",
        help="also include the root part itself in the result "
        "(redundant with --txt/--md, which already start at the root)",
    )
    trav.add_argument(
        "--include-deleted",
        dest="only_non_deleted",
        action="store_false",
        help="follow soft-deleted partstree records too (default: skip them)",
    )
    trav.add_argument(
        "--position-key",
        default="position",
        metavar="FIELD",
        help='field holding the position inside the parent (default: "position")',
    )
    trav.add_argument(
        "--progress",
        action="store_true",
        help="print a per-level trace to stderr while traversing",
    )

    out = p.add_argument_group("output")
    out.add_argument(
        "--txt",
        nargs="?",
        const=DEFAULT_TXT_PATH,
        default=None,
        metavar="PATH",
        help=f"write the plain tree here (default: {DEFAULT_TXT_PATH})",
    )
    out.add_argument(
        "--md",
        nargs="?",
        const=DEFAULT_MD_PATH,
        default=None,
        metavar="PATH",
        help=f"write the Markdown page here (default: {DEFAULT_MD_PATH})",
    )
    out.add_argument(
        "--print",
        dest="print_tree",
        action="store_true",
        help="print the tree to stdout (status messages go to stderr)",
    )
    out.add_argument(
        "--print-file",
        default=None,
        metavar="PATH",
        help="send the --print output to PATH instead of stdout",
    )
    out.add_argument(
        "--ascii",
        action="store_true",
        help="use ASCII connectors in the txt/stdout tree",
    )
    out.add_argument(
        "--txt-max-lines",
        type=int,
        default=None,
        metavar="N",
        help="truncate the txt/stdout tree after N lines (default: no limit)",
    )

    page = p.add_argument_group("markdown page")
    page.add_argument(
        "--title", default=None, metavar="TEXT", help=f'page title (default: "{DEFAULT_TITLE}")'
    )
    page.add_argument(
        "--description",
        default=None,
        metavar="TEXT",
        help="front-matter description (default: generated)",
    )
    page.add_argument(
        "--admonition",
        default="note",
        metavar="CLASS",
        help="admonition class for tree nodes (default: note)",
    )
    page.add_argument(
        "--md-max-depth",
        type=int,
        default=None,
        metavar="N",
        help="deepest admonition nesting, root = 0 (default: no limit)",
    )
    page.add_argument(
        "--no-links",
        dest="link_parts",
        action="store_false",
        help="render serial numbers as plain text instead of ProdDB links",
    )
    page.add_argument(
        "--same-tab",
        dest="new_tab",
        action="store_false",
        help='do not append {target="_blank"} to links',
    )
    page.add_argument(
        "--url-template",
        default=util.PART_VIEW_URL,
        metavar="TPL",
        help="link template containing {part_id} (default: ProdDB viewparts)",
    )

    p.add_argument("--quiet", action="store_true", help="suppress the summary on stderr")
    return p


def _summary(root_id, parts, edges, txt_path, md_path):
    """Human-readable summary printed to stderr."""
    depth = {int(root_id): 0}
    kinds = {}
    for parent_id, node in edges:
        pid = int(node["part_id"])
        depth.setdefault(pid, depth.get(int(parent_id), 0) + 1)
        kop = (node.get("kind_of_part") or {}).get("kind_of_part_name")
        if kop:
            kinds[kop] = kinds.get(kop, 0) + 1

    n_top = sum(1 for parent_id, _ in edges if int(parent_id) == int(root_id))
    deepest = max(depth.values()) if depth else 0

    lines = [
        f"root part_id {root_id}: {len(parts)} parts, {n_top} direct children, "
        f"deepest level {deepest}"
    ]
    if kinds:
        lines.append(
            "  kinds: "
            + ", ".join(f"{k}={v}" for k, v in sorted(kinds.items(), key=lambda kv: -kv[1]))
        )
    if txt_path:
        lines.append(f"  txt: {txt_path}")
    if md_path:
        lines.append(f"  md:  {md_path}")
    return "\n".join(lines)


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    # --- root selection
    if args.part_id is not None and args.sn is not None:
        parser.error("give either a part_id or --sn + --kind, not both")
    if args.part_id is None and args.sn is None:
        parser.error("give a part_id, or --sn together with --kind")
    if args.sn is not None and not args.kind:
        parser.error("--sn requires --kind (which parts table to search)")
    if args.sn is None and args.kind is not None:
        parser.error("--kind only resolves --sn; use --child-kind to filter the traversal")

    for opt, value in (("--kind", args.kind), ("--child-kind", args.child_kind)):
        if value is not None and value != "all" and value not in data.KoPID_from_partKoPName:
            parser.error(
                f"unknown kind of part '{value}' for {opt}; choose from: "
                f"all, {', '.join(sorted(data.KoPID_from_partKoPName))}"
            )

    # --- numeric sanity
    for name in ("max_depth", "md_max_depth", "txt_max_lines"):
        value = getattr(args, name)
        if value is not None and value < 0:
            parser.error(f"--{name.replace('_', '-')} must be >= 0")
    if args.workers < 1:
        parser.error("--workers must be >= 1")

    # --- output sanity
    wants_page = args.md is not None
    wants_txt = args.txt is not None
    if not (wants_page or wants_txt or args.print_tree):
        parser.error("nothing to do: pass at least one of --md, --txt, --print")
    if args.print_file is not None and not args.print_tree:
        parser.error("--print-file only makes sense with --print")

    include_parent = args.include_parent
    if include_parent and (wants_txt or wants_page):
        print(
            "warning: --include-parent is redundant with --txt/--md "
            "(the renderers already start at the root); ignored",
            file=sys.stderr,
        )
        include_parent = False

    kind_for_traversal = args.child_kind
    title = args.title or DEFAULT_TITLE

    # --- resolve the root
    root_id = args.part_id
    if args.sn is not None:
        try:
            root_id = util.resolve_part_id_by_sn(args.sn, args.kind)
        except Exception as e:
            print(f"error: {type(e).__name__}: {e}", file=sys.stderr)
            return 1
        if root_id is None:
            print(
                f"error: could not resolve serial number '{args.sn}' "
                f"of kind '{args.kind}' to a part_id",
                file=sys.stderr,
            )
            return 1
        if not args.quiet:
            print(f"resolved {args.sn} ({args.kind}) -> part_id {root_id}", file=sys.stderr)

    # --- optional per-level trace
    progress = None
    if args.progress:

        def progress(depth, n_collected):
            print(f"  depth {depth}: {n_collected} parts", file=sys.stderr)

    # --- --print-file handling
    stream = None
    close_stream = False
    if args.print_file is not None:
        path = Path(args.print_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        stream = path.open("w", encoding="utf-8")
        close_stream = True

    try:
        collected, edges = util.get_recursive_children(
            root_id,
            ofKind=kind_for_traversal,
            max_depth=args.max_depth,
            max_workers=args.workers,
            include_parent=include_parent,
            onlyNonDeleted=args.only_non_deleted,
            with_edges=True,
            progress=progress,
            print_tree=args.print_tree,
            tree_ascii=args.ascii,
            tree_max_lines=args.txt_max_lines,
            tree_file=stream,
            position_key=args.position_key,
            tree_txt_path=args.txt,
            tree_md_path=args.md,
            md_admonition_type=args.admonition,
            md_max_depth=args.md_max_depth,
            page_title=title,
            page_description=args.description,
            md_link_parts=args.link_parts,
            md_new_tab=args.new_tab,
            part_url_template=args.url_template,
        )

    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"error: {type(e).__name__}: {e}", file=sys.stderr)
        return 1
    finally:
        if close_stream and stream is not None:
            stream.close()

    if not args.quiet:
        print(
            _summary(root_id, collected, edges, args.txt, args.md),
            file=sys.stderr,
        )
    if not collected:
        print("warning: tree is empty (no children found)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

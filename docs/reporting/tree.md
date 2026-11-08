# Detector parts tree (`hgtd-tree`)

Renders the HGTD detector parts tree below a chosen root, either as a pretty box-drawing text tree or as a Zensical/MkDocs page in which every part is a collapsible admonition linking to the ProdDB. Both outputs can be produced in a single run, and the tree can additionally be previewed on stdout.

The root is selected either directly by `part_id` or by serial number plus the kind of part it belongs to, which is resolved to a `part_id` through the ProdDB. Traversal follows `/childslist/` level by level, in parallel.

| Property | Value |
|---|---|
| **Script** | `app/scripts/tree.py` |
| **Entry point** | `hgtd-tree` |
| **Output** | `--txt` file, `--md` page, stdout (`--print`), stderr summary |
| **Writes to the DB** | No — read-only |
| **Direct link to internal page** | [https://hgtd-tools-internal.web.cern.ch/reports/detector_tree/](https://hgtd-tools-internal.web.cern.ch/reports/detector_tree/){target="_blank"} |

---

## Usage

```bash
# by part_id, both outputs
hgtd-tree 28833 --txt out/detector_tree.txt --md docs/detector_tree.md

# by serial number: --kind only finds the part_id, the whole subtree is walked
hgtd-tree --sn Detector_Assembly_CERN --kind Detector --md docs/detector_tree.md

# detector units only, preview in the terminal
hgtd-tree 28833 --child-kind "Detector Unit" --print

# default paths for both renderers
hgtd-tree 28833 --txt --md
```

At least one of `--md`, `--txt` or `--print` is required; otherwise the script exits with *"nothing to do"*.

### Root selection

| Argument | Description |
|---|---|
| `part_id` | Positional root `part_id` to traverse from. Alternative to `--sn` + `--kind`. |
| `--sn SERIAL_NUMBER` | Root serial number. Requires `--kind` and is resolved to a `part_id` via `util.resolve_part_id_by_sn()`. |
| `--kind KoP` | Kind of part the `--sn` root belongs to (e.g. `Detector`). Used **only** to find the `part_id`, never as a traversal filter. |

!!! warning "`--kind` is not a filter"
    `--kind` exists solely to disambiguate `--sn`. To restrict which children are followed, use `--child-kind`. Passing `--kind` without `--sn` is a usage error, and giving both a `part_id` and `--sn` is rejected too.

### Traversal

| Argument | Default | Description |
|---|---|---|
| `--max-depth N` | unlimited | Stop traversal `N` levels below the root. |
| `--child-kind KoP` | `all` | Only follow children of this kind (e.g. `Detector Unit`). Unrelated to `--kind`. |
| `--workers N` | `4` | Threads used for the per-level `/childslist/` calls. Must be `>= 1`. |
| `--include-parent` | off | Also include the root part itself in the collected result. Ignored with a warning when `--txt` or `--md` is used, because those renderers already start at the root. |
| `--include-deleted` | off | Follow soft-deleted `partstree` records too. Internally inverts `only_non_deleted`. |
| `--position-key FIELD` | `position` | Field holding the position inside the parent, used for ordering. |
| `--progress` | off | Print a per-level trace (`depth N: M parts`) to stderr while traversing. |

### Output

| Argument | Default | Description |
|---|---|---|
| `--txt [PATH]` | `out/detector_tree.txt` | Write the plain tree. Bare `--txt` uses the default path. |
| `--md [PATH]` | `out/detector_tree.md` | Write the Markdown page. Bare `--md` uses the default path. |
| `--print` | off | Print the tree to stdout; status messages go to stderr. |
| `--print-file PATH` | *(stdout)* | Send the `--print` output to `PATH` instead. Requires `--print`. |
| `--ascii` | off | Use ASCII connectors instead of box-drawing characters in the txt/stdout tree. |
| `--txt-max-lines N` | unlimited | Truncate the txt/stdout tree after `N` lines. |

### Markdown page

| Argument | Default | Description |
|---|---|---|
| `--title TEXT` | `HGTD Detector Parts Tree` | Page title. |
| `--description TEXT` | generated | Front-matter description. |
| `--admonition CLASS` | `note` | Admonition class used for tree nodes (`note`, `example`, `abstract`, ...). |
| `--md-max-depth N` | unlimited | Deepest admonition nesting; the root is level `0`. |
| `--no-links` | off | Render serial numbers as plain text instead of ProdDB links. |
| `--same-tab` | off | Do not append `{target="_blank"}` to links (links open in the same tab). |
| `--url-template TPL` | `util.PART_VIEW_URL` | Link template containing `{part_id}`. Defaults to the ProdDB `viewparts` endpoint. |

### Miscellaneous

| Argument | Description |
|---|---|
| `--quiet` | Suppress the summary printed to stderr after the run. |

---

## Exit codes

| Code | Meaning |
|---|---|
| `0` | Success — also when the tree turned out to be empty (a warning is printed). |
| `1` | Runtime or API failure: unresolvable serial number, or any exception during traversal/rendering. |
| `2` | Bad usage — rejected by argparse, e.g. missing output target, unknown kind, negative `--max-depth`. |
| `130` | Interrupted with `Ctrl-C` during traversal. |

---

## Output

### Text tree

A box-drawing rendering of the subtree, ordered by `--position-key`. Long trees can be clipped with `--txt-max-lines`, and terminals without Unicode support can use `--ascii`. The same renderer feeds `--print` and `--print-file`.

### Markdown page

Every part becomes a nested collapsible admonition of class `--admonition`, carrying the serial number as a link to `--url-template` (formatted with `{part_id}`). Nesting depth is bounded by `--md-max-depth`, which is useful because deeply nested admonitions become unreadable in a browser and Zensical/MkDocs will not render arbitrarily deep levels well.

### stderr summary

Unless `--quiet` is given, the run ends with a compact summary: root `part_id`, total parts, number of direct children, deepest level reached, a kind histogram sorted by count, and the written file paths. The summary is built from the collected parts and edges, so its counts are exactly what the renderers saw.

---

## Gotchas

- **`--sn` without `--kind` is a usage error**, and `--kind` without `--sn` is rejected as well. The pair only serves root resolution.
- **`--include-parent` silently does nothing when `--txt` or `--md` is set.** A warning is printed and the flag is ignored, since both renderers already start at the root.
- **Directories are created only for `--print-file`.** That path gets `mkdir(parents=True, exist_ok=True)`, but `--txt` and `--md` do not — create `out/` or `docs/` beforehand.
- **An empty result is not a failure.** A missing or wrong root simply yields `warning: tree is empty (no children found)` and exit code `0`.
- **`--child-kind` prunes the walk, it does not filter the output.** Pruned branches are never fetched, so their descendants cannot appear either.
- **Soft-deleted `partstree` records are skipped by default.** Use `--include-deleted` when investigating history, otherwise the tree may look shorter than the DB suggests.
- **`--workers` multiplies load on the ProdDB.** The default of 4 is fine; raise it only for large trees.

*Last updated: {{ last_updated }}*

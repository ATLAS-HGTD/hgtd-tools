# Module / hybrid site report (`module-sites-hybrids`)

Module assembly accounting: for every monitored site it puts the modules assembled there next to the hybrids currently located there, both split by the SN prefix (so the "vendor") of the hybrids. Two further figures show where the hybrids of each prefix currently sit, and how many hybrids exist per prefix at all.

Module and hybrid counts come from the same read layer that `hgtd-count` and the validation report use (`parts_query`), and the figures go through `plotter`, so neither the numbers nor the plot style can drift from the rest of the reporting.

Classification is purely serial-number based, as everywhere else: hybrids and modules are split with `parts_query.split_by_sn()`, and only *valid* serial numbers are used unless `--all-parts` is given. A module is then categorised by the SN prefix of its two Hybrid children — same prefix gives that prefix, two different prefixes give a `A + B` entry of their own. Modules with 0, 1 or more than two hybrids cannot be assigned a prefix and land in three grey hatched buckets.

| Property | Value |
|---|---|
| **Script** | `hgtd_tools/app/scripts/module_sites_hybrids.py` |
| **Entry point** | `module-sites-hybrids` |
| **Output** | `counts_site_modules_vs_hybrids_at_location*`, `fractions_site_modules_vs_hybrids_at_location*`, `counts_hybrid_prefix_by_location*`, `fractions_hybrid_prefix_by_location*`, `hybrid_sn_prefixes*` plots (PDF + PNG), plus a console table set |
| **Writes to the DB** | No — read-only |
| **Direct link to internal page** | [https://hgtd-tools-internal.web.cern.ch/reports/module_hybrid_accounting/](https://hgtd-tools-internal.web.cern.ch/reports/module_hybrid_accounting/){target="_blank"} |

---

## Usage

```bash
module-sites-hybrids                                    # monitored sites, all known locations, valid SNs
module-sites-hybrids --locations monitored              # restrict the location universe to the monitored sites
module-sites-hybrids --version-includes-any "some version" --version-includes-any "another"
module-sites-hybrids --prefix-len 8 --scale log
module-sites-hybrids --hide-non-two                     # drop the 0 / 1 / >2 hybrid buckets
module-sites-hybrids --no-plots                         # tables only, no figures
module-sites-hybrids --dump-json cache.json             # cache the query result
module-sites-hybrids --from-json cache.json --postfix somethingcustom
```

### Parameters

| Parameter | Default | Description |
|---|---|---|
| `--sites` | `monitored` | `monitored` (the site list `data` defines for the Module Assembly mode) or comma-separated manufacturer shortnames, e.g. `ihep,mainz`. |
| `--locations` | `all` | Location universe of the per-prefix figure: `all` uses every shortname in `data.relevant_location_IDs_by_shortname`, `monitored` only the monitored sites. |
| `--version-includes-any` | *(none)* | Keep modules whose `version` contains any of these substrings. Repeat the flag for alternatives containing spaces. Values are verbatim (case-sensitive). |
| `--hybrid-version-includes-any` | *(none)* | Same filter, applied to the Hybrid children instead. |
| `--name-label-includes` | *(none)* | Case-insensitive substring filter on `name_label`. |
| `--name-label-excludes` | *(none)* | Case-insensitive negative substring filter on `name_label`. |
| `--sn-includes-any` | *(none)* | Keep modules whose SN contains any of these whitespace-separated substrings. |
| `--all-parts` | *(off)* | Include modules and hybrids with invalid or fake SNs. Without it, only valid SNs are used, as in the validation report. |
| `--prefix-len` | `7` | Number of SN characters used as category. |
| `--hide-non-two` | *(off)* | Drop the `0 hybrids` / `1 hybrid` / `>2 hybrids` buckets from the per-site figure. |
| `--scale` | `lin` | Value-axis scale: `lin` or `log`. Singular — not `--scales`. |
| `--exp-text` | `Internal` | Second part of the ATLAS label. |
| `--subtitle` | `True` | Add a subtitle with the `hgtd-tools` commit and the generation date. |
| `--title-prefix` | *(empty)* | Prefix inside the subtitle line. |
| `--output-dir` | `plots` | Parent directory for the figures; each run writes into a selection-specific subdirectory below it. |
| `--no-subdir` | *(off)* | Write directly into `--output-dir` instead of a selection-specific subdirectory. |
| `--postfix` | *(derived)* | File-name postfix; also overrides the selection-specific subdirectory name. |
| `--max-workers` | `4` | Threads used to fetch the Hybrid children of each module. |
| `--dev` | *(none)* | Only the first N modules (smoke test). Hybrids are *not* truncated. |
| `--dump-json` | *(none)* | Write the query result and the selection to a JSON cache. |
| `--from-json` | *(none)* | Replot from such a cache instead of querying the DB. |
| `--no-plots` | *(off)* | Print the tables only. |
| `--quiet` | *(off)* | Suppress the progress lines on stderr. |

!!! warning "`--subtitle` takes a value"
    `--subtitle` is passed through `util.str2bool()`; it is **not** a `store_true` switch. Pass an explicit value (`--subtitle True`, `--subtitle False`). Writing `--subtitle` alone makes argparse fail with *"expected one argument"*.

!!! note "`--scale` is singular"
    There is one `--scale` value per run, not a list. Both variants have to be produced by two runs; the scale suffix in the filename keeps them apart (see [Output](#output)).

!!! note "`--all-parts` is a negated flag"
    The internal name is `only_valid`, defaulting to `True`. The flag only ever *widens* the selection; there is no `--only-valid` counterpart.

---

## What is counted

Three independent populations feed the three figures:

| Population | Source | Filtered by |
|---|---|---|
| Hybrid census | every `Hybrid` part in the DB | `--hybrid-version-includes-any`, valid-SN rule |
| Hybrids by location | every `Hybrid` part with a known location | `--hybrid-version-includes-any`, valid-SN rule, `--locations` |
| Modules by site | `Module` parts of the resolved sites | `--version-includes-any`, `--name-label-*`, `--sn-includes-any`, `--dev`, valid-SN rule |

The module's own category comes from its Hybrid children, which are fetched per module and filtered with `--hybrid-version-includes-any` and the valid-SN rule.

### Module categories

| Entry | Condition | Style |
|---|---|---|
| `<prefix>` | exactly two hybrids, both with the same prefix | coloured, one entry per prefix |
| `<prefix A> + <prefix B>` | exactly two hybrids, different prefixes | coloured, one entry per pair |
| `0 hybrids` | no (surviving) Hybrid child | grey, `alpha=0.25`, hatch `//` |
| `1 hybrid` | exactly one | grey, `alpha=0.50`, hatch `\\` |
| `>2 hybrids` | three or more | grey, `alpha=0.80`, hatch `xx` |

Legend order is by combined weight (modules + hybrids at location), then the mixed `A + B` pairs by module count, then the grey buckets in their fixed order. Prefix labels are expanded to two lines with the manufacturer from `data.hybrid_SN_human_map`, e.g. `20WHPMI\n(PacTech)`; with `--prefix-len > 7` the label falls back to the 7-character head of the prefix, so the names keep working at any prefix length.

### Locations

Locations are resolved through `data.relevant_location_IDs_by_shortname` (id → shortname). Hybrids whose location is outside the plotted universe are **not** dropped silently: they are counted and printed in the console table as `location_id=…, location_name=…, shortname=…` plus any other non-empty fields the location dict carries, so an unknown location can be identified.

---

## Output

### Directory

Figures go into a subdirectory of `--output-dir`, named after the active selection:

```
plots/validSNs_sitesMonitored_locAll/
plots/validSNs_sitesMonitored_locAll_versionALTIROC_A_ALTIROCA_ALTIROC_A_ALTRIOC_A/
plots/allSNs_sitesihep_mainz_locMonitored_prefix8_onlyTwoHY/
```

| Token | Comes from |
|---|---|
| `validSNs` / `allSNs` | `--all-parts` |
| `sitesMonitored` / `sites<list>` | `--sites` |
| `locAll` / `locMonitored` | `--locations` |
| `version…` | `--version-includes-any` |
| `hyVersion…` | `--hybrid-version-includes-any` |
| `label…` / `nolabel…` | `--name-label-includes` / `--name-label-excludes` |
| `sn…` | `--sn-includes-any` |
| `prefix<N>` | `--prefix-len`, only when not 7 |
| `onlyTwoHY` | `--hide-non-two` |
| `dev<N>` | `--dev` |

Tokens are sanitised and joined with `_`. Names longer than 90 characters are truncated and suffixed with a 6-character MD5 of the full name, so the directory stays filesystem-safe and still unique. `--no-subdir` skips the subdirectory entirely; `--postfix` replaces its name.

### Plots

Five figures per run, each written as `.pdf` and `.png`, all ending in the postfix:

```
<stem>_<postfix>_<scale>.<pdf|png>
```

`<postfix>` defaults to `<prefix-len>chars_<sites>`, e.g. `7chars_monitored`, and `<scale>` is appended by `plotter`:

| Filename stem | Figure |
|---|---|
| `counts_site_modules_vs_hybrids_at_location` | Horizontal grouped/stacked bars, one row per site: modules assembled vs. hybrids located there, split by prefix. Totals annotated per row. |
| `fractions_site_modules_vs_hybrids_at_location` | Same, each bar normalised to itself. |
| `counts_hybrid_prefix_by_location` | Vertical bars, one per prefix, stacked by location; total above each bar. |
| `fractions_hybrid_prefix_by_location` | Same, each bar normalised to itself. |
| `hybrid_sn_prefixes` | Single-series bar, hybrids per prefix (all hybrids in the DB). |

Concrete examples:

```
counts_site_modules_vs_hybrids_at_location_7chars_monitored_lin.pdf
fractions_site_modules_vs_hybrids_at_location_7chars_monitored_lin.png
counts_hybrid_prefix_by_location_7chars_monitored_lin.pdf
fractions_hybrid_prefix_by_location_7chars_monitored_lin.pdf
hybrid_sn_prefixes_7chars_monitored_lin.png
```

The prefix census has **no** fractions variant — a bar per prefix is already a fraction of the total by construction. Figure 1 is skipped when there is nothing to draw (no modules *and* no hybrids in the selection); figure 2 is skipped when the location census is empty.

### Console tables

Printed to stdout regardless of `--no-plots`, and repeated in the CI log:

| Table | Content |
|---|---|
| Prefix census | all hybrids and valid hybrids, per prefix, most common first |
| Modules per site | `site`, `modules`, `= 2 HY`, then one column per entry; empty cells as `-` |
| Hybrids per location | `location`, `hybrids`, then one column per prefix |
| Hybrids per prefix | `hybrid SN prefix`, `hybrids`, then one column per location |
| Elsewhere | hybrids at locations outside the universe, by `describe_location()` key |
| Summary | `N module(s) at M site(s), K with exactly two hybrids (P%)` |

---

## Re-plotting without DB access

`--dump-json` stores the module records, the resolved site list, the prefix censuses, the per-location breakdown, the `elsewhere` listing and the selection lines. `--from-json` replays that payload:

```bash
module-sites-hybrids --dump-json cache.json
module-sites-hybrids --from-json cache.json --postfix check --scale log
```

The selection is taken from the cache, so `--sites` and the filter flags have no effect on read — see Gotchas. Caches written by an older version of the script may lack `hybrid_by_site` and `hybrid_prefix_by_location`; the corresponding figures are then skipped with a warning on stderr.

---

## Collecting the outputs in CI

The figures land in a subdirectory, so the CI step does **not** need `mkdir` or `mv` — point `--output-dir` at the artefact directory and let the script create the rest:

```yaml
- module-sites-hybrids --output-dir ../generated
- module-sites-hybrids --version-includes-any "ALTIROC A" --version-includes-any "ALTIROCA" --version-includes-any "ALTIROC-A" --version-includes-any "ALTRIOC A" --output-dir ../generated
```

Both runs fit in one job because their subdirectories differ, and the nested layout is preserved when `generated/` is copied into the site. If you prefer a flat artefact directory, use `--no-subdir` and distinct `--postfix` values instead.

---

## Gotchas

- **The file names do not encode the filters.** Only the prefix length, the site scope and the scale appear in the filename; everything else lives in the directory name. Two filtered runs with `--no-subdir` — or with the same `--postfix` — overwrite each other's figures.
- **`--postfix` changes the directory too.** It overrides both the filename postfix *and* the selection-specific subdirectory name, so a fixed postfix in CI collapses all selections into one directory.
- **`--from-json` ignores the filters.** `--version-includes-any`, `--hybrid-version-includes-any`, `--name-label-*` and `--sn-includes-any` are applied when the cache is *written*. Re-run without `--from-json` to change the selection; the script prints a warning to that effect.
- **`--locations monitored` changes the first figure as well.** The universe feeds both the hybrid segments of the per-site bars and the per-prefix figure, so hybrids at non-monitored locations move into the `elsewhere` listing instead of the bars.
- **`--dev` truncates modules only.** Hybrids are counted in full, so the module/hybrid ratio in a `--dev` run is meaningless. Use it with `--no-plots`.
- **`--hide-non-two` affects the figure, not the tables.** The grey buckets stay in the printed matrices; only the bars lose them.
- **Unreadable modules are counted as `0 hybrids`.** A failed `util.get_children()` call is caught per module, logged as a warning and the module lands in the `0 hybrids` bucket rather than being dropped — so the module totals stay right but the bucket can be inflated.
- **Zero-height stacks vanish on a log axis.** With `--scale log`, empty segments cannot be drawn; use `--scale lin` when the absence of a prefix matters.
- **The scale is not part of the default postfix.** It is appended by `plotter` at the very end of the name, which is why `_lin` and `_log` variants coexist in the same directory — do not add the scale to `--postfix` yourself.
- **`--prefix-len > 7` degrades the human labels.** Only 7-character prefixes are known to `data.hybrid_SN_human_map`; longer prefixes are labelled by their 7-character head, so `20WHPMI1` and `20WHPMI2` both read `(PacTech)`.
- **Long selections are hashed.** Above 90 characters the directory name is truncated and given a 6-character MD5 suffix; grep for the `[out] writing figures to …` line on stderr rather than reconstructing the path by hand.
- **`--quiet` silences stderr, not stdout.** The tables and the `Wrote <stem>.{pdf,png}` lines behave differently: progress and warnings go to stderr, tables to stdout.

*Last updated: {{ last_updated }}*

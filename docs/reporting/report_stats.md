# Parts statistics report (`report-stats`)

Collects every part in the selected categories from the Production Database, classifies it by serial-number validity, and produces the statistics plots used in the production reporting: stacked bar charts (counts and fractions) per feature and per category, plus upload time trends.

Classification is purely serial-number based. Parts whose SN starts with `20W` are checked with `util.check_SN_valid()` and split into *valid* and *invalid* (i.e. not following the ATLAS convention); everything else is counted as *fake*. Each of the three classes gets its own full set of plots and its own JSON cache file.

| Property | Value |
|---|---|
| **Script** | `hgtd_tools/app/scripts/report_stats.py` |
| **Entry point** | `report-stats` |
| **Output** | `counts*`, `fractions*`, `newly_uploaded*`, `cumulative_counts*` plots (PDF + PNG), `report_stats_*.json`, `output_invalid.txt` |
| **Writes to the DB** | No — read-only |
| **Direct link to internal page** | [https://hgtd-tools-internal.web.cern.ch/reports/yields/](https://hgtd-tools-internal.web.cern.ch/reports/yields/){target="_blank"} |

---

## Usage

```bash
report-stats                                   # all categories, fresh DB queries
report-stats --categories public               # only the public categories
report-stats --categories test --custom-text Internal
report-stats --skip-data-prep True             # replot from the existing JSON caches
report-stats --log-axis True                   # logarithmic y-axis
```

### Parameters

| Parameter | Default | Description |
|---|---|---|
| `--categories` | *(all)* | Category set to process: omit for `data.all_cats`, `public` for `data.public_cats`, `test` for `data.test_cats`. |
| `--skip-data-prep` | `False` | Do not query the DB. Load `report_stats_valid.json`, `report_stats_invalid.json` and `report_stats_fakes.json` from the working directory and only regenerate the plots. |
| `--subtitle` | `True` | Add a subtitle with the SN validity category and the `hgtd-tools` commit hash + generation date. |
| `--custom-text` | `Production Database` | Replaces the "Production Database" label in the plot captions, e.g. `Preliminary` or `Internal`. |
| `--log-axis` | `False` | Use a logarithmic y-axis instead of a linear one. |

!!! warning "Boolean flags take a value"
    `--skip-data-prep`, `--subtitle` and `--log-axis` are passed through `util.str2bool()`; they are **not** `store_true` switches. Pass an explicit value (`--skip-data-prep True`, `--log-axis false`, `--subtitle 0`). Writing `--skip-data-prep` alone makes argparse fail with *"expected one argument"*.

---

## Categories

The categories are resolved once at startup and drive everything downstream: which part sets are fetched, which bars appear in the plots, and which keys the JSON caches contain.

| `--categories` | Source |
|---|---|
| *(omitted)* | `data.all_cats` |
| `public` | `data.public_cats` |
| `test` | `data.test_cats` |

There is no argparse `choices` list here, so any other value is accepted by the parser and then fails later with an `UnboundLocalError` (see Gotchas).

---

## Classification

Every part of every category is fetched via `util.get_relevant_parts(c)[0]` and sorted into exactly one bucket:

| Bucket | Condition | Plot postfix | Title prefix |
|---|---|---|---|
| Valid | SN starts with `20W` and `util.check_SN_valid()` passes | `valid` | *Serial Numbers starting with 20W, fulfilling the ATLAS convention.* |
| Invalid | SN starts with `20W` and `util.check_SN_valid()` fails | `invalid` | *Serial Numbers starting with 20W, NOT fulfilling the ATLAS convention.* |
| Fake | SN does not start with `20W` | `fakes` | *Serial Numbers NOT starting with 20W.* |

For each invalid part, one line `<serial_number>: <reason>` is appended to `output_invalid.txt`, which is deleted at the start of every non-cached run. The file therefore always reflects the most recent DB query, not an accumulation across runs.

### Features

The features are fixed in the script (`interesting_features`); to add or remove one, edit that list — it is not exposed on the command line.

| Feature | Source field | Notes |
|---|---|---|
| `Location` | `location.location_name` | |
| `Manufacturer` | `manufacturer.manufacturer_name` | |
| `Uploaded by` | `record_insertion_user` | |
| `Uploaded in YYYY-MM` | `record_insertion_time[:7]` | `None` becomes the literal `Unknown`; also drives the time-trend plots. |

---

## Output

All files are written to the **current working directory**, flat — there are no subdirectories and no configurable output path.

### JSON caches

| File | Content |
|---|---|
| `report_stats_valid.json` | `category → feature → {legend entry: count}` for valid parts |
| `report_stats_invalid.json` | same, for invalid parts |
| `report_stats_fakes.json` | same, for fake parts |

The nested dictionaries are built with `collections.Counter`. These are the files consumed by `--skip-data-prep`, so archiving them is what makes a re-plot without DB access possible.

### `output_invalid.txt`

Plain-text log of SN validation failures, one `SN: reason` line per invalid part. Only written during a data-preparation run; it is untouched (and not read) when `--skip-data-prep True`.

### Plots

`batch_yield_plot()` is called three times, once per class (invalid, fakes, valid — in that order), and loops over the four features. Legend entries are unioned across all selected categories and sorted, so a category that has no parts for a given entry contributes explicit zeros rather than a shorter array.

Every plot is written twice, as `.pdf` and `.png`, and the filename starts with the plot kind:

| Filename prefix | Function | Content |
|---|---|---|
| `counts*` | `plotter.plot_categorical_bar_stack(..., "counts", ...)` | Stacked bar per category, absolute counts per legend entry. |
| `fractions*` | `plotter.plot_categorical_bar_stack(..., "fractions", ...)` | Same, normalised per category. |
| `newly_uploaded*` | `plotter.plot_multi_categorical_time_trend(..., "newly_uploaded", ...)` | `Uploaded in YYYY-MM` only: parts per month, per category. |
| `cumulative_counts*` | `plotter.plot_multi_categorical_time_trend(..., "cumulative_counts", ...)` | `Uploaded in YYYY-MM` only: running total per category. |

The rest of the filename is assembled by `plotter` and carries the class postfix (`valid` / `invalid` / `fakes`) plus the caption text, so the three classes never overwrite each other.

A full run over all four features and all three classes produces, per format: 12 `counts` and 12 `fractions` plots (4 features × 3 classes) plus 3 `newly_uploaded` and 3 `cumulative_counts` trends (month feature only) — i.e. 30 PDFs and 30 PNGs.

### Time trends

For `Uploaded in YYYY-MM` the months are expanded to a *consecutive* `pd.date_range(..., freq="MS")` between the first and last entry, so months without uploads appear as gaps instead of collapsing the axis. If the `Unknown` bucket is the alphabetically last legend entry, it is excluded from the range end, because it is not a real month. The cumulative series starts at the number of `Unknown` parts (the early sensors were entered without a date) or at `0` when all dates are known.

---

## Re-plotting without DB access

`--skip-data-prep True` short-circuits the entire query and classification block and loads the three JSON files instead. This is the intended path for tweaking plot appearance (`--custom-text`, `--log-axis`, `--subtitle`) on a machine or in a CI job that has no ProdDB access:

```bash
report-stats --skip-data-prep True --custom-text Preliminary --log-axis True
```

The category selection still matters: the loaded dictionaries are indexed by category, so `--categories public` against caches generated for all categories simply plots a subset.

---

## Collecting the outputs in CI

Because everything lands flat in the working directory, a CI job usually runs the report in a scratch directory and moves the artefacts out by glob:

```yaml
- report-stats --log-axis True
- mkdir ../generated
- mv counts*.pdf ../generated
- mv counts*.png ../generated
- mv fractions*.pdf ../generated
- mv fractions*.png ../generated
- mv newly_uploaded*.pdf ../generated
- mv newly_uploaded*.png ../generated
- mv cumulative_counts*.pdf ../generated
- mv cumulative_counts*.png ../generated
- mv report_stats*.json ../generated
- mv output_invalid.txt ../generated
```

The JSON caches are moved along with the plots so that a later `--skip-data-prep` run (or an archived artefact set) can regenerate the figures without touching the database.

---

## Gotchas

- **All file paths are relative to the working directory.** The JSON caches, `output_invalid.txt` and the plots are written where you run the command, and `--skip-data-prep` reads from there too. `cd` into the report directory first.
- **`--skip-data-prep` needs all three JSON files, even for a single class.** They are opened unconditionally and raise `FileNotFoundError` if any is missing.
- **An invalid `--categories` value crashes late.** There are no `choices`, so `--categories foo` parses fine and dies on the unbound `categories` variable. Use only `public`, `test`, or omit the flag.
- **`output_invalid.txt` is only cleared on a fresh run.** With `--skip-data-prep True` the file is left as it was, which can look stale next to freshly regenerated plots.
- **Zero-count legend entries break a log axis.** Counts and fractions of `0` cannot be drawn on a log scale; expect gaps or warnings when `--log-axis True` and some categories have no parts for an entry.
- **The features are hard-coded.** There is no CLI switch for `interesting_features`; adding a feature means editing the list *and* the three `if "<feature>" in interesting_features:` blocks per bucket.
- **The three classes are plotted in the order invalid → fakes → valid**, so the valid plots are written last and a run interrupted in between leaves a complete invalid/fakes set but no valid set.

*Last updated: {{ last_updated }}*

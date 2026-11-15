# Parts statistics report (`report-stats`)

Collects every part in the selected categories from the Production Database, classifies it by serial-number validity, and produces the statistics plots used in the production reporting: stacked bar charts (counts and fractions) per feature and per category, plus upload time trends — each in a linear and/or logarithmic y-axis variant.

Classification is purely serial-number based. Parts whose SN starts with `20W` are checked with `util.check_SN_valid()` and split into *valid* and *invalid* (i.e. not following the ATLAS convention); everything else is counted as *fake*. Each of the three classes gets its own full set of plots and its own JSON cache file.

| Property | Value |
|---|---|
| **Script** | `hgtd_tools/app/scripts/report_stats.py` |
| **Entry point** | `report-stats` |
| **Output** | `counts*`, `fractions*`, `newly_uploaded*`, `cumulative_counts*` plots (PDF + PNG, `_lin` / `_log` variant), `report_stats_*.json`, `output_invalid.txt` |
| **Writes to the DB** | No — read-only |
| **Direct link to internal page** | [https://hgtd-tools-internal.web.cern.ch/reports/yields/](https://hgtd-tools-internal.web.cern.ch/reports/yields/){target="_blank"} |

---

## Usage

```bash
report-stats                                   # all categories, fresh DB queries, lin + log plots
report-stats --categories public               # only the public categories
report-stats --categories test --custom-text Internal
report-stats --skip-data-prep True             # replot from the existing JSON caches
report-stats --scales log                      # only the logarithmic y-axis variant
report-stats --scales lin                      # only the linear y-axis variant
report-stats --scales lin,log                  # explicit both (same as omitting the flag)
```

### Parameters

| Parameter | Default | Description |
|---|---|---|
| `--categories` | *(all)* | Category set to process: omit for `data.all_cats`, `public` for `data.public_cats`, `test` for `data.test_cats`. |
| `--skip-data-prep` | `False` | Do not query the DB. Load `report_stats_valid.json`, `report_stats_invalid.json` and `report_stats_fakes.json` from the working directory and only regenerate the plots. |
| `--subtitle` | `True` | Add a subtitle with the SN validity category and the `hgtd-tools` commit hash + generation date. |
| `--custom-text` | `Production Database` | Replaces the "Production Database" label in the plot captions, e.g. `Preliminary` or `Internal`. |
| `--scales` | `lin log` | Y-axis scale(s) to produce: `lin`, `log`, or both. Accepts `--scales lin,log`, `--scales lin log`, or a single value. The chosen scale(s) are appended to every plot filename. |

!!! warning "Boolean flags take a value"
    `--skip-data-prep` and `--subtitle` are passed through `util.str2bool()`; they are **not** `store_true` switches. Pass an explicit value (`--skip-data-prep True`, `--subtitle 0`). Writing `--skip-data-prep` alone makes argparse fail with *"expected one argument"*.

!!! note "`--scales` is a normal multi-value flag"
    `--scales` does **not** go through `str2bool`. It takes one or more values (`nargs="+"`), which are additionally split on commas and lower-cased, then validated against `lin` / `log`. Anything else aborts with a parser error before any DB access happens. Omitting the flag is equivalent to `--scales lin log`.

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

The nested dictionaries are built with `collections.Counter`. These are the files consumed by `--skip-data-prep`, so archiving them is what makes a re-plot without DB access possible. They are **independent of `--scales`** — the scale only affects the plotting step.

### `output_invalid.txt`

Plain-text log of SN validation failures, one `SN: reason` line per invalid part. Only written during a data-preparation run; it is untouched (and not read) when `--skip-data-prep True`.

### Plots

`batch_yield_plot()` is called once per requested scale, and inside each call three times — once per class (invalid, fakes, valid — in that order) — looping over the four features. Legend entries are unioned across all selected categories and sorted, so a category that has no parts for a given entry contributes explicit zeros rather than a shorter array.

Every plot is written twice, as `.pdf` and `.png`, and the filename starts with the plot kind and ends with the scale:

```
<plot kind>[_<feature>|_time_trend_by_KoP]_<class>_<scale>.<pdf|png>
```

| Filename prefix | Function | Content |
|---|---|---|
| `counts*` | `plotter.plot_categorical_bar_stack(..., "counts", ...)` | Stacked bar per category, absolute counts per legend entry. |
| `fractions*` | `plotter.plot_categorical_bar_stack(..., "fractions", ...)` | Same, normalised per category. |
| `newly_uploaded*` | `plotter.plot_multi_categorical_time_trend(..., "newly_uploaded", ...)` | `Uploaded in YYYY-MM` only: parts per month, per category. |
| `cumulative_counts*` | `plotter.plot_multi_categorical_time_trend(..., "cumulative_counts", ...)` | `Uploaded in YYYY-MM` only: running total per category. |

Concrete examples:

```
counts_Location_valid_lin.pdf
counts_Location_valid_log.pdf
fractions_Uploaded by_fakes_lin.png
newly_uploaded_time_trend_by_KoP_invalid_log.pdf
cumulative_counts_time_trend_by_KoP_valid_lin.png
```

The rest of the filename carries the class postfix (`valid` / `invalid` / `fakes`) and the scale, so the three classes and the two scales never overwrite each other.

A full run over all four features and all three classes produces, **per scale and per format**: 12 `counts` and 12 `fractions` plots (4 features × 3 classes) plus 3 `newly_uploaded` and 3 `cumulative_counts` trends (month feature only) — i.e. 30 PDFs and 30 PNGs.

| `--scales` | Files written |
|---|---|
| `lin` | 30 PDFs + 30 PNGs |
| `log` | 30 PDFs + 30 PNGs |
| `lin log` *(default)* | 60 PDFs + 60 PNGs |

### Y-axis scales

`--scales` selects which variants are drawn; the scale is applied to counts, fractions and both time trends alike.

- **`lin`** — linear y-axis. Bars and trend lines start at 0 (the time trend uses `0 … 1.1 × max`).
- **`log`** — logarithmic y-axis. Bars whose bottom sits on 0 are drawn from the axis floor upwards; the floor is set to `1e-4 × max` when the default lower limit would be non-positive. The time trend keeps its historical hard-coded lower limit of `8e-1`.

---

### Time trends

For `Uploaded in YYYY-MM` the months are expanded to a *consecutive* `pd.date_range(..., freq="MS")` between the first and last entry, so months without uploads appear as gaps instead of collapsing the axis. If the `Unknown` bucket is the alphabetically last legend entry, it is excluded from the range end, because it is not a real month. The cumulative series starts at the number of `Unknown` parts (the early sensors were entered without a date) or at `0` when all dates are known.

---

## Re-plotting without DB access

`--skip-data-prep True` short-circuits the entire query and classification block and loads the three JSON files instead. This is the intended path for tweaking plot appearance (`--custom-text`, `--scales`, `--subtitle`) on a machine or in a CI job that has no ProdDB access:

```bash
report-stats --skip-data-prep True --custom-text Preliminary --scales log
report-stats --skip-data-prep True --custom-text Preliminary --scales lin,log
```

The category selection still matters: the loaded dictionaries are indexed by category, so `--categories public` against caches generated for all categories simply plots a subset.

---

## Collecting the outputs in CI

Because everything lands flat in the working directory, a CI job usually runs the report in a scratch directory and moves the artefacts out by glob:

```yaml
- report-stats --scales lin,log
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

The globs are unchanged by the scale suffix; if only one variant is wanted in a given job, filter on the suffix instead, e.g. `mv *_log.pdf ../generated` or `mv *_lin.* ../generated`.

The JSON caches are moved along with the plots so that a later `--skip-data-prep` run (or an archived artefact set) can regenerate the figures without touching the database.

---

## Gotchas

- **All file paths are relative to the working directory.** The JSON caches, `output_invalid.txt` and the plots are written where you run the command, and `--skip-data-prep` reads from there too. `cd` into the report directory first.
- **`--skip-data-prep` needs all three JSON files, even for a single class.** They are opened unconditionally and raise `FileNotFoundError` if any is missing.
- **An invalid `--categories` value crashes late.** There are no `choices`, so `--categories foo` parses fine and dies on the unbound `categories` variable. Use only `public`, `test`, or omit the flag.
- **`output_invalid.txt` is only cleared on a fresh run.** With `--skip-data-prep True` the file is left as it was, which can look stale next to freshly regenerated plots.
- **Zero-count legend entries vanish on a log axis.** Counts and fractions of `0` cannot be drawn on a log scale; the corresponding stack segments are simply missing in the `_log` variant, and Matplotlib may emit warnings. Use the `_lin` variant when zero entries matter.
- **The default produces twice as many files.** Omitting `--scales` writes both variants (60 PDFs + 60 PNGs for a full run). Pass `--scales lin` or `--scales log` to halve that, e.g. in CI.
- **`--scales` replaces the old `--log-axis` flag.** Calls like `report-stats --log-axis True` now fail with *"unrecognized arguments"*; use `--scales log`.
- **The features are hard-coded.** There is no CLI switch for `interesting_features`; adding a feature means editing the list *and* the three `if "<feature>" in interesting_features:` blocks per bucket.
- **The three classes are plotted in the order invalid → fakes → valid**, and the scales are looped outermost (`lin` first when both are requested), so an interrupted run leaves the valid set missing last.

*Last updated: {{ last_updated }}*

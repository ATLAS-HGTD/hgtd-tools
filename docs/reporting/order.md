# Relation validation report (`order`)

Generates the HGTD production **relation validation report** as a Markdown page, together with the accompanying pie charts, split per manufacturer and per production stage. The script walks all parts of one category (Detector Unit, Module, Hybrid, Sensor), checks the parent/child relations stored in the Production Database against the expected topology, and renders the outcome into collapsible admonitions — one per manufacturer — plus a summary block per mode.

| Property | Value |
|---|---|
| **Script** | `app/scripts/order.py` |
| **Entry point** | `order` |
| **Output** | `validation.md` (+ `validation_<MODE>.md`, pie-chart PNGs) |
| **Writes to the DB** | No — read-only |
| **Direct link to internal page** | [https://hgtd-tools-internal.web.cern.ch/reports/validation/](https://hgtd-tools-internal.web.cern.ch/reports/validation/){target="_blank"} |

---

## Usage

```bash
order                                  # all modes, all monitored manufacturers
order --mode-alias Hybridization       # single mode
order --mode-alias Sensor_Parents --single-manufacturer IHEP
order --mode-alias "Module Assembly" --dev True --custom-text Preliminary
```

### Parameters

| Parameter | Default | Description |
|---|---|---|
| `--mode-alias` | `all` | Which validation to run. One of `Module Loading`, `Module Assembly`, `Sensor_Parents`, `Hybridization`, `all`. |
| `--single-manufacturer` | *(none)* | Run only for this manufacturer short name. Overrides the default list for the chosen mode. Intended for development/debugging. |
| `--dev` | `False` | Developer mode: process at most the first 10 parts of each manufacturer subset for faster feedback. |
| `--merge` | `False` | Do not query the DB. Concatenate the previously generated `validation_ML.md`, `validation_MA.md`, `validation_HY.md` and `validation_SP.md` into `validation.md`. |
| `--subtitle` | `True` | Add a subtitle with the SN validity category and the `hgtd-tools` commit hash + generation date. |
| `--custom-text` | `Production Database` | Replaces the "Production Database" label in the plot captions, e.g. `Preliminary` or `Internal`. |

!!! warning "Boolean flags take a value"
    `--dev`, `--merge` and `--subtitle` are passed through `util.str2bool()`; they are **not** `store_true` switches. Pass an explicit value (`--dev True`, `--merge true`, `--subtitle 0`). Writing `--dev` alone makes argparse fail with *"expected one argument"*.

---

## Validation modes

Each mode picks a category via `util.get_relevant_parts()` and resolves the manufacturer list from `data`:

| `--mode-alias` | Category | Manufacturers | File postfix | Pie-chart prefix |
|---|---|---|---|---|
| `Module Loading` | Detector Unit | `data.ML_sites_to_monitor` | `ML` | `ML_*` |
| `Module Assembly` | Module | `data.MA_sites_to_monitor` | `MA` | `MA_*` |
| `Hybridization` | Hybrid | `data.HY_sites_to_monitor` | `HY` | `HY_*` |
| `Sensor_Parents` | Sensor | `data.S_W_manus_to_monitor` | `S` | `S_*` |

With `--mode-alias all` the four modes run in the order `Module Loading → Module Assembly → Hybridization → Sensor_Parents` into a single `validation.md`.

### Part selection

Before any relation is checked, every part is sorted into three buckets with `util.select_parts()`:

| Bucket | Filter | Consequence |
|---|---|---|
| Valid | `check_valid_SN_latest_spec=True` | Relations are validated. |
| Invalid | `check_invalid_SN_latest_spec=True` | Counted only, **not** validated. |
| Fake | `check_fake_SN=True` | Counted only, **not** validated. |

!!! note "Digital modules"
    In `Module Assembly`, modules whose *Name Label* contains `_Digital` are physically valid but must not be assembled. They are moved out of the valid set (via `name_label_does_include="_Digital"`) and counted with the invalid ones. The report states this explicitly in the per-manufacturer note.

---

## What is checked

Relations are delegated to `relation_validation`:

| Mode | Function | Expected relation |
|---|---|---|
| `Module Loading` | `validate_DU(part_id)` | Detector Unit → children `MO`, `SU` |
| `Module Assembly` | `validate_module(part_id)` | Module → children `MF`, `HY` |
| `Hybridization` | `validate_hybrid(part_id)` | Hybrid → children `S` (ASICs not yet checked) |
| `Sensor_Parents` | `validate_sensor(part_id)` | Sensor → parents `HY` **and** `W` (inverted direction) |

For the three *parent → children* modes the rule is strict: every valid part must have all its children at the expected positions. For `Sensor_Parents` the direction is inverted, so a sensor that is not yet bonded to a Hybrid is a **legitimate production state**, not an error:

- `validation_result_S_par_HY == "new"` and the Wafer parent is fine → counted as *new* and reported in the `example` block.
- `"new"` but the Wafer parent is broken → **failure**, because the Wafer connection is the non-negotiable one.
- `S_par_HY` fails outright (wrong position, or more than one Hybrid parent) → **failure**, with the Wafer reason appended if that one also fails.

---

## Output

### `validation.md`

Always written. It contains `templates.validation_header()` followed by, per mode, an intro block (`templates.module_loading_intro()`, etc.) and a summary block (`templates.module_loading_all(...)`, ...) that receives the aggregated counts `n_valid_parts`, `n_valid_connected_parts`, `n_invalid_parts`, `n_fake_parts` and — for sensors — `n_valid_new_parts`.

Each manufacturer then gets a `??? note "<manufacturer>"` admonition with the counts and up to three collapsible detail sections:

| Section | Content |
|---|---|
| `??? success "Relation validation OK for these parts:"` | One link per part, `Part <SN>` → `frontendUrlPrefix/viewparts/<part_id>`. Replaced by `!!! warning "Not a single relation validation passed!"` if the count is zero. |
| `??? example "These parts are not connected yet to a Hybrid:"` | Sensors only. Replaced by `!!! info "No new Sensors not yet connected to HY."` if empty. |
| `??? failure "Relation validation failed for <SN>:"` | DB link plus the individual `validation_reason_*` messages. Empty when everything passed. |

### Per-mode files

When **exactly one** mode is selected, the same content for that mode is also written to `validation_ML.md`, `validation_MA.md`, `validation_HY.md` or `validation_SP.md`. These are the inputs consumed by `--merge`.

### Pie charts

`plotter.pie_chart()` is called per mode with the manufacturer contributions:

| File postfix | Content |
|---|---|
| `<PFX>_valid_all` | Valid parts, by manufacturer |
| `<PFX>_valid_connected_all` | Valid **and correctly connected** parts, by manufacturer |
| `S_valid_new_all` | Sensors only: valid and *new* (Wafer OK, Hybrid pending) |

Captions are built from `extra_text` (e.g. `Module Loading: Detector Units (valid). `) plus `exp_text` (the `--custom-text` value) and the optional subtitle.

---

## Splitting and merging a long run

Validating all four modes in one go is slow. The intended workflow is:

```bash
# 1. run each mode separately (also produces validation_<MODE>.md)
order --mode-alias "Module Loading"
order --mode-alias "Module Assembly"
order --mode-alias Hybridization
order --mode-alias Sensor_Parents

# 2. stitch the four partial reports into the final page (no DB access)
order --merge True
```

!!! danger "`--merge` needs all four partial files in the working directory"
    The merge step opens `validation_ML.md`, `validation_MA.md`, `validation_HY.md` and `validation_SP.md` unconditionally and raises `FileNotFoundError` if any is missing. All four must have been produced by single-mode runs first.

---

## Gotchas

- **Working directory matters.** All reports and plots are written relative to the current directory, and the merge step reads from it too. `cd` into a dedicated output folder before running.
- **`--single-manufacturer` bypasses the mode's manufacturer list entirely** and also changes the pie charts, which then show a single slice. Use it only for debugging, not for published reports.
- **`--custom-text` maps to `args.customText`** (camelCase destination). There is no `--custom_text` spelling.
- **Invalid-SN parts are never validated.** A missing failure for a part usually means it fell into the invalid or fake bucket — check the counts in the mode summary first.
- **`all` is not a valid value for `--single-manufacturer`**, and unknown short names silently yield empty subsets (zero valid parts → the *"Not a single relation validation passed!"* warning).
- **`--dev` caps at 10 parts per manufacturer**, so the numbers in `validation.md` are not publication-grade.

*Last updated: {{ last_updated }}*

# Hybrid Matching

## Data sources

We restrict to Hybrids that are

- not yet connected to a Module, and
- selected either by their **location** (the `Location` field in the DB), by an
  **explicit list of serial numbers**, or a combination of the two — see
  [Choosing which Hybrids to pair](#choosing-which-hybrids-to-pair).

For these, in the present implementation, the connection to Sensors (and to Wafer) is checked to obtain data for matching

- Hybrids not connected to Sensors can not be paired.
- Hybrids connected to Sensors, where the Sensor **is** connected to Wafer, may be paired, if there is `VBD` information available that is stored for that Wafer-Sensor relation.
- Hybrids connected to Sensors, where the Sensor **is not** connected to Wafer, may be paired, if sufficient IV curve information for every Sensor pad is available to determine an overall score.

For the algorithm in the current implementation, we pair by `VBD` of the Sensor. We do not use IV curve information of Hybrids, as there is nearly no data of that kind available to begin with. The data source can be either:

- `VBD_AVERAGE` as entered to the `VBD` table, if the connection to Wafer-Sensor exists, and the value exists for the given Sensor.
    - We use the latest upload, if there are multiple uploads, a higher `RUN_END_TIMESTAMP` or a higher `RUN_NUMBER` wins.

- Average over all individual `VBD` values by manually calculating them for all pads, if these values exist. The method to calculate these values follows the interpolation technique, and uses the per-pad threshold current of $5\cdot10^{-7}\,\mathrm{A}$.
    - Because IV information for Sensors comes in different "flavors" aka `RUN_TYPE`, an assumption had to be made which values to use for the algorithm. `15x15` takes precedence over `15X15`, over `15x1`, over `15X1`, over `1x1`, over `1X1`. Any other run type is not considered.
    - We use the latest upload, if there are multiple uploads, a higher `RUN_END_TIMESTAMP` or a higher `RUN_NUMBER` wins.

- Hybrids for which neither of these techniques yield a score, have to be ignored for the pairing algorithm.

Alongside the `VBD` score, each surviving Hybrid carries the **sensor design** it belongs to (see below), which decides which group it is paired in.

## Choosing which Hybrids to pair

`--location` and `--hybrid-sns` define the candidate pool. At least one of them
is required; how they combine is controlled by `--location-and-sns` (default)
and `--location-or-sns`, which are mutually exclusive.

| `--location` | `--hybrid-sns` | scope | pairing pool |
|---|---|---|---|
| ✓ | – | – | every valid, unassembled Hybrid currently at that location (the historical behaviour) |
| – | ✓ | – | exactly the listed SNs; **no location check at all** |
| ✓ | ✓ | `and` *(default)* | the listed SNs that are also currently at that location |
| ✓ | ✓ | `or` | the listed SNs (wherever they are) **plus** every valid, unassembled Hybrid at that location |

```shell
# only by location (unchanged)
hybridmatch --location mainz

# only by SN, from anywhere
hybridmatch --hybrid-sns 20W12345678901,20W12345678902

# both, intersection (default) - the SNs must currently be in Mainz
hybridmatch --location mainz --hybrid-sns ./this_week.txt

# both, union - the SNs wherever they are, plus the rest of Mainz
hybridmatch --location mainz --hybrid-sns ./this_week.txt --location-or-sns
```

`--location-and-sns` is the default and changes nothing on its own; it exists so
that a script which relies on the intersection says so explicitly, and so both
options appear side by side in `--help`. Passing `--location-or-sns` with only
one of the two selectors is a usage error, since the union of one population is
that population.

### Checks on supplied SNs

Every SN passed via `--hybrid-sns` is checked before pairing, cheapest test
first, so an out-of-scope part costs no API call:

| Check | Rejection reason in the logbook |
|---|---|
| present in the DB as a `Hybrid` | `not found in the DB as a Hybrid (typo, or not registered yet)` |
| passes the latest SN spec | `SN does not pass the latest SN spec` |
| currently at `--location` *(only in `and` mode)* | `not at the requested location (<location>)` |
| no `Module` parent yet | `already has a Module parent (already assembled into a Module)` |

A rejected SN never disappears silently: it is listed in the CLI output and in
its own section of the markdown logbook, and it is counted in the empty-pool
breakdown. `--strict-sns` turns any rejection into a non-zero exit code (the
logbook is still written) — useful in CI, where a hand-edited SN list that lost
entries should fail loudly instead of quietly pairing fewer parts.

Note what is *not* checked at selection time: the Sensor child, the Wafer parent,
the `VBD` value and the sensor design are resolved in Step 2, exactly as in
location mode. A supplied SN can therefore still end up in `Ignored parts` with a
`VBD`- or relation-related reason — the difference is only that its selection was
explicit.

In `or` mode the two populations are merged by `part_id`, with the SN-resolved
parts first, so a hand-picked Hybrid that also sits at the location is paired
once. Rejections that the union would re-admit anyway are dropped from the
rejected list, so nothing is ever reported as rejected while being paired.

## Sensor design axis: IHEP vs USTC

Hybrids are paired **within one sensor design** by default. IHEP-IME and USTC-IME sensors are never matched against each other unless explicitly requested (reason: possibly different aging).

The design is read off the SN, using the same decoding as `check_SN_valid`:

| Part | SN characters | Design |
|---|---|---|
| Sensor `20WS<M>…` | `M` = `1`, `2` (pre-production, production) | IHEP-IME |
| Sensor `20WS<M>…` | `M` = `3`, `4` (pre-production, production) | USTC-IME |
| Wafer `20WS0<M>…` | `M` = `0` | IHEP-IME |
| Wafer `20WS0<M>…` | `M` = `1` | USTC-IME |

The Sensor SN is authoritative; the Wafer SN is only used as a fallback if the Sensor SN does not decode (e.g. unexpected manufacturer digit). This is implemented as `util.resolve_sensor_design(sensor_SN, wafer_SN)`, backed by the maps `data.sensor_design_by_manu_char` and `data.wafer_design_by_manu_char`.

The design is the **outer** axis of the grouping: every bin exists once per design, so the default run produces `len(SENSOR_DESIGNS) × len(VBD_BIN_LABELS)` groups (currently 2 × 5 = 10). Empty groups are reported with `n = 0`, the same way empty VBD bins already were.

Passing `--allow-mixed-sensor-designs` drops the design axis entirely: each bin then holds both designs and pairing runs across them. Use this only when you deliberately want mixed-design modules.

Any future grouping (2D `DeltaR`, fallback chains, …) should keep this shape — the design axis stays outside, the algorithm-specific grouping happens inside a single design group. `group_parts` takes a `group_key_fn` and a label list for exactly this reason, so a new algorithm only has to supply its own key function.

## Pairing strategy: VBD-bin grouping

Once a `VBD` score has been retrieved for each Hybrid, the script does not pair across the entire surviving pool at once. Instead, parts are split into VBD bins first, and pairing is run **independently within each bin** — and, by default, independently within each sensor design. This prevents a low-VBD Hybrid from being matched against a high-VBD one, which would inflate the total pairing distance and produce pairings that are not useful for module assembly.

A group is therefore identified by the tuple `(sensor design, bin label)`, rendered in the output as `IHEP | 150-160V`. With `--allow-mixed-sensor-designs` the design part of the tuple is `None` and the group is just the bin label.

The binning is configurable at the top of the script via three constants (to be agreed on in project):

| Constant | Default | Purpose |
|---|---|---|
| `VBD_IGNORE_BELOW` | `150.0` | Parts below this `VBD` (in V) are excluded from pairing and reported in `Ignored parts` with reason `VBD (<value> V) is below 150.0 V; excluded from pairing`. |
| `VBD_BIN_LOWER_EDGES` | `[150, 160, 170, 180, 190]` | Lower edge (in V) of each consecutive bin. |
| `VBD_BIN_LABELS` | `["150-160V", "160-170V", "170-180V", "180-190V", ">190V"]` | Human-readable label for each bin. The last label corresponds to the open-ended bin `VBD >= 190 V`. |

The design axis is configured separately, in `data.py`:

| Constant | Default | Purpose |
|---|---|---|
| `data.SENSOR_DESIGNS` | `("IHEP", "USTC")` | The designs, in report order. Reordering this reorders the output groups. |
| `data.sensor_design_by_manu_char` | `{"1": "IHEP", "2": "IHEP", "3": "USTC", "4": "USTC"}` | Sensor SN manufacturer digit → design. |
| `data.wafer_design_by_manu_char` | `{"0": "IHEP", "1": "USTC"}` | Wafer SN manufacturer digit → design (fallback only). |

Bin convention: `[lower_edge, next_lower_edge)`, i.e. lower edge inclusive and upper edge exclusive. So `VBD = 150.0` lands in `150-160V`, `VBD = 160.0` in `160-170V`, `VBD = 190.0` and above in `>190V`.

The pairing algorithm itself (`get_optimal_pairs_with_leftover_1D_On2`) is unchanged, apart from now honouring its `at_column` argument for the sort instead of hardcoding column 2. The new steps are thin wrappers: `group_by_vbd_bin` bins the inputs (applying the design axis), and `pair_within_groups` calls the existing pairer once per group. Groups are iterated in `(design, label)` order — design first in `SENSOR_DESIGNS` order, then label order — so the output is stable run-to-run, and per-group results are aggregated for the summary report.

If the three VBD constants are retuned, they must satisfy `len(VBD_BIN_LABELS) == len(VBD_BIN_LOWER_EDGES)`, enforced by an `assert` at the top of the script. A second `assert` requires `VBD_IGNORE_BELOW >= VBD_BIN_LOWER_EDGES[0]`, so no value can slip between the ignore threshold and the lowest bin edge.

The record shape that travels through grouping and pairing is

```text
[part_id, part_SN, vbd_value, sensor_design_or_None]
```

so the design stays attached to the part without a side table. `assign_vbd_bin` reads the `VBD` field positionally (`record[2]`) rather than unpacking the whole record, so a future algorithm can append more fields without breaking the binning. Records with only three elements are still accepted and treated as "design unknown".

## Using the `hybridmatch` script for module assembly

When performing module assembly, you can pair Hybrids that are available for your use case.

Execute the following (using either Anaconda Prompt or your preferred shell with which you installed miniconda or any environment with the required packages):

```shell
conda activate hgtd # or another method with which you activate your environment, such as: source hgtd/bin/activate
hybridmatch --location <your-site>
```

The location is optional: `hybridmatch --hybrid-sns <SN[,SN…]|file>` pairs an explicit list instead, and `--location` together with `--hybrid-sns` narrows or widens that list (see [Choosing which Hybrids to pair](#choosing-which-hybrids-to-pair)).

This shows the pairing algorithm results in the CLI, but also stores a report for further use as markdown document using the pattern `pairings_Only_Sensor_VBD_closest_{location}.md` — or `pairings_Only_Sensor_VBD_closest_sns{N}.md` when no location was given.

## Optional arguments

The `hybridmatch` script accepts several optional arguments to control which parts are considered and how the data is fetched.

### `--hybrid-sns`

Explicit list of Hybrid SNs to pair, instead of (or in addition to) selecting by
location. Accepted as:

- A single SN.
  ```shell
  hybridmatch --location mainz --hybrid-sns 20W12345678901
  ```
- Multiple SNs, comma-separated.
  ```shell
  hybridmatch --hybrid-sns 20W12345678901,20W12345678902,20W12345678903
  ```
- A path to a `.txt`-like file with one SN per line. Blank lines are ignored,
  lines starting with `#` are comments, duplicates are collapsed.
  ```shell
  hybridmatch --location mainz --hybrid-sns ./this_week.txt
  ```

  ```text
  # Hybrids for the Monday assembly slot
  20W12345678901
  20W12345678902
  ```

Same parsing as `--manual_ignore_hybrid_sns`, including the file-vs-inline
detection. Every SN is validated (see [Checks on supplied SNs](#checks-on-supplied-sns)).
`--location` is optional when this flag is given; without it, the SNs are paired
regardless of where they currently sit.

### `--location-and-sns` / `--location-or-sns`

How `--location` and `--hybrid-sns` combine. Mutually exclusive, default `and`.

| flag | effect with both selectors |
|---|---|
| `--location-and-sns` *(default)* | intersection: only the listed SNs that are also at that location |
| `--location-or-sns` | union: the listed SNs wherever they are, plus every other Hybrid at that location |

```shell
hybridmatch --location mainz --hybrid-sns ./this_week.txt                  # intersection
hybridmatch --location mainz --hybrid-sns ./this_week.txt --location-or-sns # union
```

`--location-or-sns` requires both selectors — combining it with only one is a
usage error, because the union of one population is that population. Neither flag
is needed when only one selector is used.

### `--strict-sns`

Exit non-zero if any SN from `--hybrid-sns` was rejected and did not make it into
the pairing set. The markdown logbook is written either way, so the reasons are
still available.

```shell
hybridmatch --location mainz --hybrid-sns ./this_week.txt --strict-sns
```

Without it, a misspelled SN is reported loudly but the run continues on the rest;
with it, a CI job fails instead of silently producing a smaller pairing.

### `--allow-mixed-sensor-designs`

Drops the sensor design axis. By default every VBD bin is built once per design (IHEP-IME and USTC-IME) and pairing runs inside each of those groups separately; with this flag, each bin holds both designs and pairing may match an IHEP sensor Hybrid against a USTC sensor Hybrid.

```shell
hybridmatch --location mainz --allow-mixed-sensor-designs
```

Notes:

- The flag is a plain `store_true`, so it takes no value. `--allow-mixed-sensor-designs` alone enables it.
- This does not change which parts are *kept*, only how they are grouped. It does change the treatment of Hybrids whose design cannot be determined (see `Guardrails`).
- The report file gets a `_mixeddesigns` suffix, so a mixed run never overwrites the separated report.

### `--manual_ignore_hybrid_sns`

Hybrids that you want to exclude from the pairing algorithm, identified by their `serial_number` (SN). Useful for parts that are known to be reserved, defective, in R&D, or otherwise unavailable for pairing.

Accepted as:

- A single SN.
  ```shell
  hybridmatch --location mainz --manual_ignore_hybrid_sns 20W12345678901
  ```
- Multiple SNs, comma-separated.
  ```shell
  hybridmatch --location mainz --manual_ignore_hybrid_sns 20W12345678901,20W23456789012,20W34567890123
  ```
- A path to a `.txt`-like file with one SN per line. Blank lines are ignored, and lines starting with `#` are treated as comments. Duplicates across the inline value and the file (or within the file) are collapsed.
  ```shell
  hybridmatch --location mainz --manual_ignore_hybrid_sns ./ignore.txt
  ```

  Example `ignore.txt`:
  ```text
  # Hybrids reserved for R&D
  20W12345678901

  # Hybrids flagged defective in QA
  20W23456789012
  20W34567890123
  ```

Manually-ignored parts are reported in the output with the reason `Manually ignored by user via --manual_ignore_hybrid_sns` and excluded from the pairing step. They do not consume any DB calls during scoring (the filter runs after `prepare_parts` and before the per-part data-source lookups).

If a SN listed here does not exist in the candidate pool — not a valid unassembled Hybrid, not at the chosen `--location`, or not among the SNs passed via `--hybrid-sns` — it is silently skipped. This flag only ever removes parts; it cannot add one that the selectors did not provide. It is applied after `prepare_parts` and before any per-part DB work, so it behaves identically in all three selection modes.

### `--dev`

Developer mode. Truncates the candidate pool to the first 2 Hybrids after `prepare_parts`, to make local iteration on the script fast without pulling the full site inventory.

```shell
hybridmatch --location mainz --dev True
```

### `--max-workers`

Number of threads to use for the per-part data-source lookups (Sensor child, Wafer parent, `VBD` retrieval, IV-based `VBD` fallback). The work is I/O-bound (DB calls), so threading is appropriate. (Default: `4`)

```shell
hybridmatch --location mainz --max-workers 2
```

Notes:

- Requires the underlying DB helpers (`get_children`, `get_parents`, `get_vbd_for_sensor_via_wafer`, `get_vbd_for_sensor_via_iv`) to be thread-safe. If they share a single DB connection without locking, increase this value with care.
- A higher value does not always help: past the point where the DB is saturated, you only add thread-spawn overhead. If unsure, start at `4` and benchmark with `--max-workers 1` vs `--max-workers 8` on the same input.

## Output

The script prints the full pipeline to the CLI:

1. **Settings** — the values of `--mode-alias`, `--location` (or a note that it is not used), `--hybrid-sns`, the effective `location_scope` (`and` / `or`), `--dev`, `--manual_ignore_hybrid_sns`, `--max-workers`, `--allow-mixed-sensor-designs`, `--strict-sns`, the active VBD-bin configuration (`VBD_IGNORE_BELOW` plus the list of bin labels), and an explicit line stating whether the sensor designs are mixed or enforced (with the list of designs).
2. **Step 1** — the candidate Hybrids: selected by location, from the explicit SN list, or the union of both. In SN mode the section states how many unique SNs were requested and lists every rejection with its reason; `All requested SNs were accepted.` is printed when there are none.
3. **Step 2** — per-part decision: either in `Ignored parts` (with reason) or in `Kept parts for matching` (with the `VBD` score that will be used for pairing, and the resolved sensor design). A short `Kept parts per sensor design: {...}` line summarises how many parts each design contributed.
4. **Step 3** — pairing algorithm, run per group. For each group in `(design, label)` order, the CLI prints:

    - the group title and the number of parts in it, e.g. `--- Group IHEP | 150-160V (7 parts) ---`;
    - if the group has an odd count, the optimal leftover Hybrid (the one whose removal minimizes the total distance);
    - the total pairing distance for that group;
    - the optimal pairings for that group.

    After the per-group detail, an aggregated summary is printed: the per-group leftovers (across any odd-count groups), the aggregated total distance, and the aggregated list of optimal pairings.

A markdown report is also written next to the script, using the pattern `pairings_<mode-alias>_<location>.md`. Without `--location` the location part becomes `sns<N>`, with `N` the number of unique SNs. The suffix chain grows with the options, in this order:

| Option | Suffix |
|---|---|
| `--allow-mixed-sensor-designs` | `_mixeddesigns` |
| `--hybrid-sns` | `_sns<N>` with `N` = number of unique SNs |
| `--hybrid-sns` together with `--location` | `_<scope>`, i.e. `_and` or `_or` |

So `hybridmatch --location mainz --hybrid-sns ./w46.txt --location-or-sns` writes `pairings_Only_Sensor_VBD_closest_mainz_sns12_or.md`, and a run without `--location` writes `pairings_Only_Sensor_VBD_closest_sns12.md`. The report contains the same information as the CLI in a structured form. The markdown includes:

- the `Ignored parts` list (covering parts excluded by `VBD < VBD_IGNORE_BELOW`, by an undeterminable sensor design, and by the matching algorithm) and the `Kept parts for matching` list;
- a `Kept parts per sensor design` breakdown;
- a `Rejected SNs from --hybrid-sns` section when an SN list was used, or `All requested SNs were accepted.`;
- one section per group, titled with the group name (e.g. `### Group \`IHEP | 150-160V\` (7 parts)`), with its own leftover (if any), total distance, and optimal pairings;
- an aggregated section summarising the totals and leftover across all groups;
- the empty-pool breakdown if no part survived.

## Guardrails

- Every SN passed via `--hybrid-sns` is either paired or reported: unknown, failing the SN spec, at the wrong location (`and` mode only) or already assembled all produce a named reason in the CLI and the logbook. With `--strict-sns` the run then exits non-zero, after the logbook has been written.
- If the candidate pool is empty after filtering, the pairing step is skipped and a clear explanation is printed (candidates seen, rejected `--hybrid-sns` entries, filtered out by `--manual_ignore_hybrid_sns`, filtered out by the matching algorithm, survivors). The markdown logbook is still produced, with every group present and empty so the structure stays comparable between runs.
- If a Hybrid's sensor design cannot be determined from either the Sensor or the Wafer SN, it is reported in `Ignored parts` with the reason `Sensor design (IHEP/USTC) could not be determined from the Sensor/Wafer SN; …` and excluded — because non-mixed pairing needs the design to place the part in a group. With `--allow-mixed-sensor-designs` such a part is kept instead, since the design no longer gates pairing.
- If a per-part lookup raises an unhandled exception, it is converted into an `Ignored parts` entry with reason `Unhandled exception during scoring: <ExceptionType>: <message>`, so a single bad row does not abort the whole run.

*Last updated: {{ last_updated }}*

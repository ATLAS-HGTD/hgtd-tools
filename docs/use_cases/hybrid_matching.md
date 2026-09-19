# Hybrid Matching

## Data sources

We restrict to Hybrids

- at a given site (checking the Location field in DB!),
- not yet connected to a Module.

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

## Using the `hybridmatch` script for module assembly

When performing module assembly, you can pair Hybrids that are available for your use case.

Execute the following (using either Anaconda Prompt or your preferred shell with which you installed miniconda or any environment with the required packages):

```shell
conda activate hgtd # or another method with which you activate your environment, such as: source hgtd/bin/activate
hybridmatch --location <your-site>
```

This shows the pairing algorithm results in the CLI, but also stores a report for further use as markdown document using the pattern `pairings_Only_Sensor_VBD_closest_{location}.md`.

## Optional arguments

The `hybridmatch` script accepts several optional arguments to control which parts are considered and how the data is fetched.

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

If a SN listed here does not exist at the chosen `--location` (or was already filtered out by `prepare_parts` for another reason), it is silently skipped.

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

1. **Settings** — the values of `--mode-alias`, `--location`, `--dev`, `--manual_ignore_hybrid_sns`, `--max-workers`.
2. **Step 1** — relevant Hybrids at the chosen location.
3. **Step 2** — per-part decision: either in `Ignored parts` (with reason) or in `Kept parts for matching` (with the `VBD` score that will be used for pairing).
4. **Step 3** — the optimal pairings, the total pairing distance, and — if there is an odd number of survivors — the optimal leftover Hybrid (the one whose removal minimizes the total distance).

A markdown report is also written next to the script, using the pattern `pairings_<mode-alias>_<location>.md`, and contains the same information in a structured form, including the `Ignored parts` and `Kept parts for matching` lists, the empty-pool breakdown if no part survived, and the optimal pairings.

## Guardrails

- If the candidate pool is empty after filtering, the pairing step is skipped and a clear explanation is printed (candidates seen, filtered out by `--manual_ignore_hybrid_sns`, filtered out by the matching algorithm, survivors). The markdown logbook is still produced.
- If a per-part lookup raises an unhandled exception, it is converted into an `Ignored parts` entry with reason `Unhandled exception during scoring: <ExceptionType>: <message>`, so a single bad row does not abort the whole run.

*Last updated: {{ last_updated }}*

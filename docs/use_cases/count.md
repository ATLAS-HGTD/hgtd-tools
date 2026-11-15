# Parts Count (`hgtd-count`) - CLI queries

Counts parts in the HGTD production database and, optionally, checks their
relations. It answers the questions that come up outside a scheduled report:
*how many Modules has `<SOME SITE>` built, how many of them are valid serial numbers,
how many are correctly connected, and which SNs are the ones that are not.*

The script loads one Kind of Part (or a whole category set), narrows the list
with the same `util.select_parts()` filters the reporting CLIs use, sorts the
result into valid / invalid / fake serial numbers, and — with `--validate` —
runs the same `relation_validation` check as the nightly report.

It is **read-only**: no part, tree or shipment record is ever written.

| Property | Value |
|---|---|
| **Script** | `app/scripts/count.py` |
| **Entry point** | `hgtd-count` |
| **Shared logic** | `hgtd_tools/parts_query.py` (also used by `order`) |
| **Output** | stdout, or `--output PATH` |
| **Writes to the DB** | No — read-only |

---

## Usage

```bash
hgtd-count Module                                     # one Kind of Part
hgtd-count Module --validate --group-by manufacturer   # + relation check, per site
hgtd-count --cats public                               # every public kind
hgtd-count Module --version-includes-any "ALTIROC A"      # version filter
```

### What is counted

The positional argument is a Kind of Part from `data.KoPID_from_partKoPName`,
or a validation mode alias, which is translated to its Kind of Part:

| positional | Kind of Part |
|---|---|
| `Module Loading` | Detector Unit |
| `Module Assembly` | Module |
| `Hybridization` | Hybrid |
| `Sensor_Parents` | Sensor |

Without a positional argument, every kind in `--cats` is counted and printed as
one row per kind:

| `--cats` | Source list | Note |
|---|---|---|
| `all` *(default)* | `data.all_cats` | 13 kinds, including ASIC and PEB_MUX64 |
| `public` | `data.public_cats` | ASIC and PEB_MUX64 are left out until a significant portion is uploaded |
| `test` | `data.test_cats` | HV_PS and HV_module only |

`--cats` is ignored when a Kind of Part is given. Kinds that `data.py` lists but
that have no KoP ID are rejected before any request is made.

## Counting buckets

Every loaded part lands in exactly one bucket, using the same rules as the
validation report:

| Bucket | Filter | Validated? |
|---|---|---|
| Valid | `check_valid_SN_latest_spec=True` | yes, with `--validate` |
| Invalid | `check_invalid_SN_latest_spec=True` | no |
| Fake | `check_fake_SN=True` | no |

"Invalid" means *starts with `20W` but fails the current SN spec*; "fake" means
*does not start with `20W`* at all (dummy and test records). The three buckets
are disjoint, so `valid + invalid + fake ≤ filtered` — parts whose SN is neither
`20W…` nor decodable are counted in one of them, but a part that appears in no
bucket is not counted at all.

The buckets depend only on the Kind of Part, not on `--validate`. A `Module` run
therefore reports the same `valid` / `invalid` / `fake` numbers with and without
the flag, which makes the two directly comparable.

!!! note "Digital modules"
    For `Module Assembly`, modules whose *Name Label* contains `_Digital` are
    valid serial numbers but are not physically assembled. They are moved out of
    the valid set and added to the invalid count, so the numbers match the
    validation report. To look at them on their own:

    ```bash
    hgtd-count Module --name-label-includes _Digital
    ```

## Relation validation

`--validate` runs `relation_validation` on every **valid** part and adds three
columns. The mode is derived from the Kind of Part, so it cannot be chosen
inconsistently:

| Kind of Part | Mode | Function | Expected relation |
|---|---|---|---|
| Detector Unit | `Module Loading` | `validate_DU` | DU → children `MO`, `SU` |
| Module | `Module Assembly` | `validate_module` | Module → children `MF`, `HY` |
| Hybrid | `Hybridization` | `validate_hybrid` | Hybrid → children `S` |
| Sensor | `Sensor_Parents` | `validate_sensor` | Sensor → parents `HY` **and** `W` |

Kinds without a validator are still counted; the script says so on stderr and
leaves the connection columns as `-`.

For sensors the direction is inverted, so an unconnected sensor is a legitimate
production state:

| Situation | Counted as |
|---|---|
| `S_par_HY == "new"` and the Wafer parent is fine | *new* — Wafer OK, Hybrid pending |
| `"new"` but the Wafer parent is broken | *failed* — the Wafer connection is the non-negotiable one |
| `S_par_HY` fails outright (wrong position, more than one Hybrid) | *failed*, with the Wafer reason appended if that one also fails |

For the other three modes the rule is strict: every child must be present at the
expected position, otherwise the part is *failed*.

## Command-line parameters

**Selection**

| flag | default | meaning |
|---|---|---|
| `kind_of_part` | *(none)* | Kind of Part or validation mode alias; omit to count every kind in `--cats` |
| `--cats {all,public,test}` | `all` | category set used when no Kind of Part is given |
| `--validate` | off | run the relation check on every valid part |
| `--use-local` | off | for `Slot`, read the cached JSON from `assets/` instead of the API |

**Filters** — all map onto `util.select_parts()` and compose with AND:

| flag | keeps parts whose … |
|---|---|
| `--location-shortname NAME` | location is this shortname (`choices=` from `data.relevant_location_IDs_by_shortname`) |
| `--location-name NAME` | location name matches exactly |
| `--location-id ID` | location id matches |
| `--manu-shortname NAME` | manufacturer is this shortname (`choices=` from `data.relevant_manufacturer_IDs_by_shortname`) |
| `--manu-name NAME` | manufacturer name matches exactly |
| `--manu-id ID` | manufacturer id matches |
| `--sites LIST` | manufacturer is any of these comma-separated shortnames, or `monitored` |
| `--sn-includes TEXT` | SN contains `TEXT` |
| `--sn-includes-any TEXT` | SN contains any of these whitespace-separated substrings |
| `--sn-chars-9-10 N` | SN characters 10 and 11 equal `N` (SNs shorter than 11 chars are dropped) |
| `--version-includes-any TEXT` | `version` contains `TEXT`; repeat the flag for several alternatives |
| `--name-label-includes TEXT` | `name_label` contains `TEXT`, case-insensitive |
| `--name-label-excludes TEXT` | `name_label` does **not** contain `TEXT`, case-insensitive |
| `--no-parents-of-kind KOP` | has no parent of Kind of Part `KOP` |
| `--has-parents-of-kind KOP` | has at least one parent of Kind of Part `KOP` |
| `--no-children-of-kind KOP` | has no child of Kind of Part `KOP` |
| `--has-children-of-kind KOP` | has at least one child of Kind of Part `KOP` |

`--sites monitored` expands to the manufacturer list `data.py` defines for the
kind's validation mode — `ML_sites_to_monitor`, `MA_sites_to_monitor`,
`HY_sites_to_monitor` or `S_W_manus_to_monitor`. That is the set the nightly
report covers, so it is the right filter when you want to reproduce its numbers:

```bash
hgtd-count Module --sites monitored                     # counting only
hgtd-count Module --sites monitored --validate           # same set, with relation check
```

The list is resolved from the Kind of Part, so `--validate` is **not** required.
It does require a kind that has a validation mode at all (Detector Unit, Module,
Hybrid, Sensor); for any other kind the script exits with a usage error and asks
you to list the shortnames explicitly.

!!! warning "The four `*_of-kind` filters cost one request per part"
    They are the only filters that talk to the API per part, so they are slow on
    a full category. Use a cheaper filter first (`--manu-shortname`,
    `--sn-includes`, `--dev`) to shrink the list before adding one of them. They
    use a fixed pool of 4 workers; `--max-workers` does not affect them.

**Output**

| flag | default | meaning |
|---|---|---|
| `--group-by {none,manufacturer,location}` | `none` | second table with one row per group; single Kind of Part only |
| `--list {all,valid,invalid,fake,connected,failed,new}` | *(none)* | append the SNs of that category, with failure reasons for `failed`; single Kind of Part only |
| `--format {text,md,csv,json}` | from `-o` suffix, else `text` | output format |
| `--output PATH`, `-o` | stdout | write the report to a file, creating parent directories |
| `--quiet` | off | suppress the progress messages on stderr |

**Execution**

| flag | default | meaning |
|---|---|---|
| `--dev N` | *(none)* | only look at the first `N` parts after filtering |
| `--max-workers N` | `4` | threads for the per-part relation checks |

`--group-by`, `--list`, `--use-local` and `--sites monitored` all require a
single Kind of Part; combining any of them with `--cats` is a usage error.

## Output columns

| column | meaning |
|---|---|
| `kind` | the Kind of Part counted |
| `loaded` | parts returned by the DB before any filter |
| `filtered` | parts left after the filters — the base for the three buckets |
| `valid` / `invalid` / `fake` | the SN buckets |
| `connected` / `not connected` | only with `--validate`: valid parts whose relations pass / do not pass |
| `new (no HY)` | sensors only: valid, Wafer parent OK, not yet mounted on a Hybrid |

Columns that would be `-` in every row are trimmed, so a run without
`--validate` shows only the six base columns.

```
kind    loaded  filtered  valid  invalid  fake
Some      4120      3811   3620       61   130
```

## Output formats

| format | content |
|---|---|
| `text` | aligned table, plus the `Sites:` / `Filters:` header and any `--list` output |
| `md` | the same as a Markdown table under a `# HGTD parts count` heading |
| `csv` | the table only, for spreadsheets and diffs |
| `json` | the whole report structure, including the part records and the raw validation results |

`--format` wins over the `-o` suffix; an unrecognised suffix falls back to `text`.

## Exit codes

| code | meaning |
|---|---|
| `0` | everything counted |
| `1` | at least one Kind of Part failed (API error); that row is marked `ERR` and the rest of the table is still printed |
| `2` | bad usage — unknown Kind of Part, invalid shortname, `--group-by`/`--list` with `--cats`, or `--sites monitored` on a kind without a validation mode |

## Examples

```
    # how many valid modules per site, and how many are correctly connected
    hgtd-count Module --validate --group-by manufacturer

    # all valid Modules built by IJCLab, with the SNs that are connected
    hgtd-count Module --manu-shortname ijclab --validate --list connected

    # what is wrong with them
    hgtd-count Module --manu-shortname ijclab --validate --list failed

    # reproduce the nightly report's scope for one kind
    hgtd-count Module --sites monitored --validate

    # which version strings exist among the monitored modules
    hgtd-count Module --sites monitored --format json \
        | jq -r '.rows[0].parts[] | .version // "(empty)"' | sort | uniq -c | sort -rn

    # modules of two versions, per manufacturer, with relation check
    hgtd-count Module --validate --group-by manufacturer \
        --version-includes-any "ALTIROC A" --version-includes-any "ALTIROC B"

    # production overview across all kinds, as a page
    hgtd-count --cats public --format md -o overview.md

    # module variants by version string
    hgtd-count module --version-includes-any "ALTIROC A" --version-includes-any ALTIROCA

    # monitor the total number of valid AA modules and breakdown per site
    hgtd-count Module --sites monitored --validate \
      --version-includes-any "ALTIROC A" --version-includes-any "ALTIROCA" \
      --version-includes-any "ALTIROC-A" --version-includes-any "ALTRIOC A" \
      --group-by manufacturer

    # output the total number of valid AA modules to csv (no breakdown)
    hgtd-count Module --sites monitored --validate \
      --version-includes-any "ALTIROC A" --version-includes-any "ALTIROCA" \
      --version-includes-any "ALTIROC-A" --version-includes-any "ALTRIOC A" \
      --format csv -o modules_altiroc.csv

    # quick smoke test before a long run
    hgtd-count Hybrid --validate --dev 10
```

## Behaviour notes

!!! warning "`--version-includes-any` takes values verbatim"
    Unlike `--sn-includes-any`, the version filter does **not** split on
    whitespace or commas, because a version string may contain a space
    (`ALTIROC A`). Each flag occurrence is one alternative:

    ```bash
    hgtd-count Module --version-includes-any "ALTIROC A"                        # one alternative
    hgtd-count Module --version-includes-any "ALTIROC A" --version-includes-any ALTIROCA
    hgtd-count Module --version-includes-any "ALTIROC A,ALTIROCA"               # one literal, matches nothing
    ```

    Passing a comma-joined value in a single flag is therefore a silent
    no-match, not an error. The match is a case-sensitive substring test, so
    `ALTIROC A` does not match `ALTIROCA` or `ALTIROC-A`; dump the distinct
    values first (see Examples) when the result is unexpectedly empty.

!!! note "`--sites` filters by manufacturer, not by location"
    For sensors the monitored list holds manufacturer names (`IHEP-IME`,
    `USTC-IME`), not site shortnames, which is why the filter is applied to
    `manu_shortname` throughout. To filter by where a part currently is, use
    `--location-shortname`.

!!! note "Invalid and fake parts are never validated"
    A part that is missing from a `--list failed` run usually fell into the
    invalid or fake bucket. Check `filtered` against `valid` first.

!!! tip "A failing kind does not abort the run"
    When one Kind of Part cannot be loaded, its row is marked `ERR`, the reason
    goes to stderr, the remaining kinds are still counted and the exit code is
    `1`. With `--quiet` the reason is suppressed, so prefer not to combine the
    two when scripting.

!!! tip "`--format json` is the full dump"
    The JSON report contains the complete part records and the raw
    `relation_validation` results, not just the counts, so it grows with the
    number of parts. Use `--format csv` for tables and `--format json` only when
    you want to post-process individual parts. In `jq`, guard against records
    without a version (`.version // "(empty)"`) — otherwise every such part is
    grouped under the literal `null`.

!!! note "Working directory is irrelevant"
    Unlike `order`, this script writes nothing unless `-o` is given, and no
    partial files are produced. A failed run leaves no state behind, so it is
    safe to repeat.

## Extra information on version usage for Modules

??? warning "What is actually used in the version field"
    Execute this to see all possible variants of the version field, this
    determines which filters you need to pass to catch all interesting modules:

    ```bash
    hgtd-count Module --sites monitored --format json | jq -r '.rows[0].parts[].version' | sort | uniq -c | sort -rn
    ```

## Relation to `order`

Both CLIs share `hgtd_tools/parts_query.py`, so the figures cannot drift apart:

```bash
hgtd-count Module --sites monitored --validate --format csv > count_MA.csv
order --mode-alias "Module Assembly"
```

The `valid` column of `count_MA.csv` equals the sum of the per-manufacturer
*"Valid Modules (using latest SN spec, ...)"* numbers in `validation_MA.md`, and
`connected` equals the sum of *"of which correctly connected with children
(MF, HY)"*. If they disagree, the problem is in the report rendering, not in the
counting.

Rule of thumb: use `hgtd-count` for ad-hoc questions and for numbers you paste
into a mail; use `order` when a published page with links and pie charts is
needed.

*Last updated: {{ last_updated }}*

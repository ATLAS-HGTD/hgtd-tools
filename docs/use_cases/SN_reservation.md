# SN Reservation

`SN-reservation` registers HGTD parts in the ProdDB — either by letting it propose
fresh serial numbers for a site/production/batch, or by reading a CSV of
existing or planned serial numbers.

It is meant for Module Assembly: the routine case where a handful of new modules
get serial numbers, or where a prepared list of modules has to be entered or
corrected in one go.

The script runs in four phases:

1. **Authentication** against the ProdDB (before any other request).
2. **Input resolution** — either the SN prefix and the set of counters already
   in use, or the rows of the CSV including the kind of part of each row.
3. **Existence check** — for CSV rows, the targeted kind of part is loaded once
   and each SN is looked up in it. Known SNs become `PUT` updates, unknown ones
   become `POST` creations.
4. **Write** — unless `--dryrun` is given, in which case the requests are only
   printed and nothing is written (and no confirmation is asked).

## Modes

Exactly one mode must be chosen.

| mode | flag | what it does |
|---|---|---|
| reserve | `--n-reserve N` | proposes `N` unused SNs for `--site`/`--prod`/`--batch`, asks for the details of each and creates them |
| CSV | `--csv PATH` | reads `module_sn` or `sn` rows, updates known SNs with `PUT`, creates unknown ones with `POST` |

`--prod` and `--batch` belong to reserve mode and are rejected together with
`--csv`; `--kind` and `--yes` belong to CSV mode.

## Serial numbers in reserve mode

The SN prefix is derived from site, production and batch:
`20WMO<site><prod><batch>`, i.e. eight characters, followed by a six-digit
counter. (`test` uses the leading `99` instead of `20`.)

Existing counters for that prefix are collected, and the recommendation follows
one of two strategies:

| strategy | flag | counters `1, 2, 4` in use, reserve 2 |
|---|---|---|
| fill gaps, then continue *(default)* | *(none)* | `…000003`, `…000005` |
| continue after the highest counter | `--no-fill-holes` | `…000005`, `…000006` |

Counters are human-readable and start at `1`; there is no zero-counting.

For each proposed SN, the script asks for

| field | prompt | empty input |
|---|---|---|
| `name_label` | local nomenclature | re-asks — required |
| `version` | local nomenclature | accepted as empty |
| `comment` | defaults to `--comment` | falls back to the default |

and then shows the complete payload with location, manufacturer and kind of
part already translated to DB IDs, asking for confirmation. Answering anything
but `y` re-asks the three fields **for the current SN only**; values are never
carried over to the next serial number.

## CSV format

The header decides the kind of part:

| SN column | kind of part | behaviour |
|---|---|---|
| `module_sn` | `Module`, implied | never asked |
| `sn` | unknown | asked per row, or taken from `--kind` |

| column | required | meaning |
|---|---|---|
| `module_sn` or `sn` | yes | serial number; rows with an empty SN are skipped |
| `name_label` | yes | must not be empty |
| `version` | no | missing column or empty cell means "not given" |
| `comment` | no | missing column or empty cell means "not given" |

A header containing **both** `module_sn` and `sn` is rejected as ambiguous, as
is a duplicate SN within one file. Header names are matched
case-insensitively and tolerate stray whitespace.

```
module_sn,name_label,version,comment
20WMOMT1000001,MT-01-1,ALTIROCA,some informative comment
20WMOMT1000002,MT-01-2,,
```

**Known SN → `PUT`.** The record is printed with its `part_id` and web view
link, and only the fields given in the CSV are sent. `location`, `manufacturer`,
`kind_of_part` and `barcode` are never part of the update, so an update cannot
move a part.

**Unknown SN → `POST`.** The new part is built from the CSV row, `--site`
(location and manufacturer) and the resolved kind of part. An empty `comment`
cell falls back to `--comment`.

## Command-line parameters

**General**

| flag | required | default | meaning |
|---|---|---|---|
| `--site` | yes | — | site shortname, must be a key of `data.MO_site_id`, at the moment: `ifae`, `ihep`, `ijclab`, `mainz`, `mascir`, `ustc`, `test` |
| `--n-reserve N` | one of the two | — | number of SNs to propose and create |
| `--csv PATH` | one of the two | — | CSV file to read |
| `--comment` | no | `part SN reserved via hgtd-tools` | default comment for created parts |
| `--dryrun` | no | off | print the requests, upload nothing, ask nothing |
| `--local-folder` | no | `~/.hgtd_tools/local_info`, falling back to `./local_info` | folder that `hgtd-tools` uses for the access token |

**Reserve mode**

| flag | required | default | meaning |
|---|---|---|---|
| `--prod` | yes | — | production, must be a key of `data.MO_prod_id`, at the moment: `prod`, `preprod`, `demo`, `test`, `other` |
| `--batch` | yes | — | single alphanumeric character |
| `--no-fill-holes` | no | off | do not reuse skipped counters |

**CSV mode**

| flag | required | default | meaning |
|---|---|---|---|
| `--kind KoP` | no | asked per row | kind of part for a generic `sn` header; currently only `Module` |
| `--yes` | no | off | skip the per-row create/update confirmation |

**Authentication**

| flag | required | default | meaning |
|---|---|---|---|
| `-u`, `--user-name` | yes | — | your CERN user name; also recorded as `record_insertion_user` on creation and `record_lastupdate_user` on update |

## Exit codes

| code | meaning |
|---|---|
| `0` | all parts created/updated (or dry run completed) |
| `1` | runtime or API failure: authentication, reading the SN set, a malformed CSV, or a rejected `POST`/`PUT` |
| `2` | bad usage — invalid flags, missing `--prod`/`--batch` with `--n-reserve`, `--kind` or `--no-fill-holes` in the wrong mode, or an empty user name |

## Examples

```
    # dry run: propose five SNs and print the POST bodies
    SN-reservation -u anstein --site test --n-reserve 2 --prod test --batch 1 --dryrun

    # real run, filling skipped counters
    SN-reservation -u anstein --site test --n-reserve 3 --prod test --batch 2

    # never reuse a skipped counter
    SN-reservation -u anstein --site test --n-reserve 3 --prod test --batch 3
        --no-fill-holes

    # CSV with module_sn: kind of part is Module, no question asked
    SN-reservation -u anstein --site test --csv modules.csv --dryrun

    # CSV with a generic sn column, kind given once, unattended
    SN-reservation -u anstein --site test --csv parts.csv --kind Module --yes
```

## Behaviour notes

!!! warning "Only the targeted kind of part is checked"

    Serial numbers are unique across all kinds of part, but the existence check
    loads only the kind being written (one request per kind, cached for the run).
    A clash with a part of another kind — or with a record created after the run
    started — therefore arrives as a backend error. The script reports it and
    names the duplicate SN as the most likely cause; it does **not** retry.

!!! note "A failure stops the run"

    A rejected `POST`/`PUT` raises, so the remaining rows are not processed and
    the summary is not printed. Check the web view before re-running: a retry
    after a request that actually succeeded would attempt a duplicate.

!!! note "Empty cells mean 'not given', not 'blank it out'"

    An empty `version` or `comment` cell is treated as absent. On update the
    stored value is kept; on creation the version becomes empty and the comment
    falls back to `--comment`. There is currently no way to clear a field via CSV.

!!! tip "`--dryrun` also skips the questions"

    In a dry run no confirmation is asked — the prompt is echoed with a
    `[dryrun: confirmation not asked]` marker and the payload is printed. The
    summary then reports *would be created* / *would be updated*. In reserve mode
    the three detail fields are still asked, because they are what the printed
    payload is built from.

!!! tip "CSV mode is safe to re-run"

    Rows whose SN already exists in the targeted kind become `PUT` updates, so a
    second run over the same file does not create duplicates. It will re-send
    the same updates, which is harmless but visible in the part history.


*Last updated: {{ last_updated }}*

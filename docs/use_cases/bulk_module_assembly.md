# Bulk Module Assembly

`bulk-module-assembly` validates a CSV describing Module → child-part relations,
registers or updates the Modules it mentions, and posts the allowed relations to
the parts-tree endpoint of the HGTD ProdDB.

It is meant for the routine case where a batch of `Module Flex` and `Hybrid`
children need to be attached to a batch of parent Modules at well-defined
positions — typically right after the Module serial numbers were reserved, when
the Modules themselves may not be in the database yet.

Two CSV layouts are accepted:

| layout | header contains | use when |
|---|---|---|
| one row per relation | `parent_kind_of_part,parent_serial_number,…` | you already know exactly which child goes where |
| one row per Module | `module_sn,name_label,version,comment,module_flex_sn,hybrid_hv_sn,hybrid_lv_sn` | you assemble module by module and want the Module details and its three children in one line |

The layout is detected from the header — no flag needed.

The script runs in five phases:

1. **Load** — read the CSV once, detect the layout, expand one-row-per-Module
   input into up to three relation rows.
2. **Module sync** *(one-row-per-Module layout only)* — create Modules that are
   not yet in the DB, update the details of those that are.
3. **Static validation** (offline, no DB traffic).

    - Rule 0: a given `Hybrid` or `Module Flex` child appears at most once across the whole CSV.
    - Rule 1: per parent, exactly one `Module Flex` child at empty position.
    - Rule 2: per parent, exactly two `Hybrid` children at positions `{HV, LV}` (order irrelevant).
    - SN pre-flight: every parent and child serial number satisfies the ATLAS SN convention.

4. **DB checks** — existence of every parent and child SN, plus the DB rules below.
5. **POST** — one `/partstreelist` payload per allowed CSV row, then the report.

The order matters: the sync runs **before** validation, otherwise every Module
this run would create would be reported as "not found in the DB".

## Header handling (both layouts)

Header names are matched **case-insensitively** and tolerate surrounding
whitespace, in both layouts. `Module_SN`, `module_sn` and ` module_sn ` are the
same column.

Two columns whose names differ only in case or whitespace are **rejected** rather
than silently merged — the script aborts with
`duplicate column 'Module_sn' (also given as 'module_sn')`. Empty column names
are rejected as well.

## CSV input — one row per relation

The CSV must have a header row and these columns, in any order:

| column | meaning |
|---|---|
| `parent_kind_of_part` | kind of the parent. Must be `Module`. |
| `parent_serial_number` | parent serial number. |
| `child_kind_of_part` | kind of the child. `Module Flex` or `Hybrid`. |
| `child_serial_number` | child serial number. |
| `position` | position label. `HV` or `LV` for a `Hybrid`, empty for a `Module Flex`. |

## CSV input — one row per Module

```
module_sn,name_label,version,comment,module_flex_sn,hybrid_hv_sn,hybrid_lv_sn
20WMOMAA000001,MM-01-A,v1.2,first batch,20WMFMHAA00001,20WHNNNDA00001,20WHNNNDA00002
20WMOMAA000002,MM-01-B,,,20WMFMHAA00002,20WHNNNDA00003,20WHNNNDA00004
```

| column | required | meaning |
|---|---|---|
| `module_sn` | yes | Module serial number; also the parent of every child in the row |
| `name_label` | for creation | required when the Module does not exist yet; ignored otherwise |
| `version` | no | sent on creation, and on update only if it differs from the stored value |
| `comment` | no | as `version`; falls back to `--comment` on creation |
| `module_flex_sn` | no | Module Flex child, position left empty |
| `hybrid_hv_sn` | no | Hybrid child at position `HV` |
| `hybrid_lv_sn` | no | Hybrid child at position `LV` |

The column names are accepted without the `_sn` suffix as well
(`module_flex`, `hybrid_hv`, `hybrid_lv`). An empty child cell produces no
relation row — the offline rules then report the missing flex or hybrid, exactly
as if the row had been left out of the relation layout. Rows with an empty
`module_sn` are skipped; a `module_sn` appearing twice aborts the run.

The Module row is **expanded** into up to three canonical relation rows, so
everything downstream — validation, DB checks, upload — is identical for both
layouts.

## Kind normalisation

Because `Module Flex` is written in different ways across tools, it gets normalised:
`Module_flex`, `module flex`, `Module-Flex` and `MODULE_FLEX` all map to `Module Flex`.
Other kinds (`Hybrid`, `Module`) are only whitespace-stripped — keep them
spelled exactly as in the DB to avoid surprises.

Whitespace in `position` is treated as empty.

## Rules enforced

**Static (offline)**

- **0.** A given `Hybrid` or `Module Flex` child can appear at most once across the whole CSV.
- **1.** Per parent: exactly one `Module Flex` child, at empty position.
- **2.** Per parent: exactly two `Hybrid` children, with positions `{HV, LV}` (order irrelevant).

**DB (online, layered on top of the static rules)**

- **DB-0.** Every `Hybrid` or `Module Flex` child has zero existing parents.
- **DB-1.** Every parent `Module` has zero existing `Module Flex` children (the CSV adds exactly one).
- **DB-2.** Every parent `Module` has zero existing `Hybrid` children (the CSV adds exactly two).

## Command-line parameters

| flag | required | default | meaning |
|---|---|---|---|
| `-i`, `--input` | yes | — | path to the input CSV |
| `-u`, `--user-name` | yes | — | your CERN user name; stored as `record_insertion_user` on creation and `record_lastupdate_user` on update |
| `--site` | if Modules must be created | — | site shortname used as location and manufacturer for new Modules |
| `--comment` | no | — | default comment for created Modules |
| `--skip-part-sync` | no | off | do not create/update Module parts; only upload relations for Modules that already exist |
| `--local-folder` | no | `~/.hgtd_tools/local_info`, falling back to `./local_info` | folder that `hgtd-tools` uses for the access token |
| `-q`, `--quiet` | no | off | suppress the `OK` summary on success; always prints on failure |
| `--encoding` | no | `utf-8` | encoding used to read the CSV |
| `--dry-run` | no | off | validate, build payloads, print them — never POST or PUT |
| `--skip-upload` | no | off | validate only; never POST even if every check passes |
| `--allow-malformed-sn` | no | off | SN-format failures become warnings rather than blockers, **provided the part exists in the DB** |

`--site` is not mandatory because relation-only runs and the relation layout do
not need it. It becomes mandatory as soon as a Module has to be created, and the
error message names the offending serial number and CSV line.

## Exit codes

| code | meaning |
|---|---|
| `0` | every parent_serial_number passes static + DB rules; if `--skip-upload` is not set, every allowed row was POSTed. |
| `1` | at least one parent_serial_number violated a rule, or rows were blocked because of missing DB serials. The report still lists any partial upload that succeeded. |
| `2` | the CSV could not be read (missing file, unknown `--encoding`, empty file, duplicate or empty column names, unrecognised header, missing columns, no data rows, duplicate `module_sn`). |
| `3` | a DB lookup or the Module sync failed (network/HTTP error, missing `--site`, missing `name_label` for a new Module). |
| `4` | the upload step raised a network/HTTP error mid-run. |

## Examples

Validate only, no POST:

```
bulk-module-assembly -i module_children.csv -u <username> --skip-upload
```

Dry run — build payloads but never POST:

```
bulk-module-assembly -i module_children.csv -u <username> --dry-run
```

**Full upload (default), enforce valid SNs:**

```
bulk-module-assembly -i module_children.csv -u <username>
```

One row per Module, creating the Modules as part of the run:

```
bulk-module-assembly -i modules.csv -u <username> --site mainz --dry-run
bulk-module-assembly -i modules.csv -u <username> --site mainz
```

Modules are maintained elsewhere; only the relations should be uploaded:

```
bulk-module-assembly -i modules.csv -u <username> --skip-part-sync
```

Full upload, allowing malformed SNs as warnings rather than blockers
(useful for DB development with dummy parts):

```
bulk-module-assembly -i module_children.csv -u <username> --allow-malformed-sn
```

## Behaviour notes

!!! note "Partial success is supported"

    If some parents have violations and others don't, the script still POSTs
    the rows whose parent and child are both clean. The report prints the
    `OK: N allowed row(s) were uploaded (partial success; ...)` block followed
    by the `FAIL:` diagnostics for the rest. The exit code is `1` in that case,
    script still fails, but the upload is not silent.

!!! note "Children already wired in the DB are skipped, not failed"

    If a child in the CSV already has a parent in the DB, that row is skipped
    so it does not block other still-unwired parents. The skipped children are
    listed under `NOTE: N child serial(s) already have a parent ...`.

!!! warning "SN pre-flight vs. DB existence"

    With `--allow-malformed-sn`, the SN-format check is a warning only. The DB
    existence check is still enforced: if a serial is not registered in the DB,
    the related rows are blocked.

!!! warning "Only Modules are created or updated"

    The one-row-per-Module layout registers the **Module** parts. A `Module Flex`
    or `Hybrid` that is not yet in the database still blocks its row — register
    those first (e.g. with `SN-reservation`) before uploading the relations.

!!! note "Existing Modules are only updated when something differs"

    The stored record is compared field by field against the CSV row
    (`name_label`, `version`, `comment_description`); unchanged Modules are
    reported as such and not written. Re-running the same file therefore does
    not churn `record_lastupdate_user`.

!!! tip "Check the dry run before creating anything"

    `--dry-run` propagates into the Module sync: you see the `POST` body for each
    new Module and the diff for each changed one. Relation rows whose parent
    would only be created by this run are reported as
    `(parent part_id not resolved: parent does not exist yet)` — they are not
    silently dropped.

!!! tip "Reproducible logs"

    Upload responses are emitted in a deterministic order (sorted by parent SN,
    then child kind, then child SN), so you can diff two reports cleanly.


*Last updated: {{ last_updated }}*

# Bulk Module Assembly

`bulk-module-assembly` validates a CSV of Module -> child-part relations
and posts the allowed rows to the parts-tree endpoint of the HGTD ProdDB.

It is meant for the routine case where a batch of `Module Flex` and `Hybrid`
children need to be attached to a batch of parent Modules at well-defined positions.

The script runs in four phases:

1. **Static validation** (offline, no DB traffic).

    - Rule 0: a given `Hybrid` or `Module Flex` child appears at most once across the whole CSV.
    - Rule 1: per parent, exactly one `Module Flex` child at empty position.
    - Rule 2: per parent, exactly two `Hybrid` children at positions `{HV, LV}` (order irrelevant).
    - SN pre-flight: every parent and child serial number satisfies the ATLAS SN convention.

2. **DB existence check** for every parent and child SN.
3. **POST** — one `/partstreelist` payload per allowed CSV row.
4. **Report** — diagnostics for anything blocked or skipped, plus the per-row upload result.

## CSV input

The CSV must have a header row and these columns, in any order:

| column | meaning |
|---|---|
| `parent_kind_of_part` | kind of the parent. Must be `Module`. |
| `parent_serial_number` | parent serial number. |
| `child_kind_of_part` | kind of the child. `Module Flex` or `Hybrid`. |
| `child_serial_number` | child serial number. |
| `position` | position label. `HV` or `LV` for a `Hybrid`, empty for a `Module Flex`. |

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
| `-u`, `--user-name` | yes | — | your CERN user name |
| `--local-folder` | no | `~/.hgtd_tools/local_info`, falling back to `./local_info` | folder that `hgtd-tools` uses for the access token |
| `-q`, `--quiet` | no | off | suppress the `OK` summary on success; always prints on failure |
| `--encoding` | no | `utf-8` | CSV encoding |
| `--dry-run` | no | off | validate and build payloads but never POST |
| `--skip-upload` | no | off | validate only; never POST even if every check passes |
| `--allow-malformed-sn` | no | off | SN-format failures become warnings rather than blockers, **provided the part exists in the DB** |

## Exit codes

| code | meaning |
|---|---|
| `0` | every parent_serial_number passes static + DB rules; if `--skip-upload` is not set, every allowed row was POSTed. |
| `1` | at least one parent_serial_number violated a rule, or rows were blocked because of missing DB serials. The report still lists any partial upload that succeeded. |
| `2` | the CSV could not be read (missing file, bad encoding, missing columns, no data rows). |
| `3` | a DB lookup failed (network/HTTP error). |
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

!!! tip "Reproducible logs"

    Upload responses are emitted in a deterministic order (sorted by parent SN,
    then child kind, then child SN), so you can diff two reports cleanly.


*Last updated: {{ last_updated }}*

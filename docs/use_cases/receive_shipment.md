# Receive Shipment

`receive-shipment` finds HGTD shipments in the ProdDB and marks the selected
ones as `Received`.

Setting the status to `Received` is what moves every part in a shipment to the
shipment's destination location. It is the only operation that does so —
creating a shipment already marked `Received` leaves the parts at the origin,
which is why `clever-ship` refuses that combination.

The script runs in four phases:

1. **Authentication** against the ProdDB (before any other request).
2. **Selection** — either by exact identifiers, or by search filters followed by
   an interactive choice from the matching table.
3. **Confirmation** — a `y/N` prompt, skipped for `--dry-run`, for
   non-interactive stdin, and for `--yes`.
4. **PUT** — one request per selected shipment, with the optional reception date.

## Two ways in

**Exact identifiers** — acted on directly, no listing, no search filters:

- `SHIPMENT_ID[,SHIPMENT_ID...]` as positional arguments
- `--tracking-number TRK[,TRK...]`

**Search filters** — all matching shipments are printed, then you pick:

| flag | meaning |
|---|---|
| `--search TEXT` | substring match against `shipment_id`, tracking number and EDH link (case-insensitive) |
| `--status STATUS` | filter by status: `Created`, `Shipped`, `Received`, `Cancel` |
| `--company TEXT` | substring match against company name or `company_id` |
| `--date PREFIX` | prefix match on the shipment date: `2026`, `2026-11`, `2026-11-07` |
| `--open-only` | only `Created` and `Shipped` shipments (recommended) |
| `--include-deleted` | also list soft-deleted shipment records |
| `--limit N` | show at most N matches (default 200) |

Filters combine with AND. At least one identifier or one filter is required.

## Command-line parameters

| flag | required | default | meaning |
|---|---|---|---|
| `SHIPMENT_ID[,SHIPMENT_ID...]` | no | — | shipment ids to act on directly |
| `--tracking-number TRK[,TRK...]` | no | — | select by tracking number; costs one GET of all shipments |
| `--search`, `--status`, `--company`, `--date`, `--open-only` | no | — | search filters (see above) |
| `--include-deleted` | no | off | include soft-deleted records |
| `--limit N` | no | `200` | maximum rows in the match table |
| `--reception-date YYYY-MM-DD` | no | not sent | date the parts arrived; when omitted the field keeps its current value |
| `--yes` | no | off | do not ask for confirmation when identifiers were given |
| `--force` | no | off | also PUT shipments that are already `Received` or `Cancel` |
| `--dry-run` | no | off | print what would be PUT without sending it |
| `--quiet` | no | off | suppress the summary on stderr |
| `-u`, `--user-name` | yes | — | your CERN user name; also recorded as `record_lastupdate_user` |
| `--local-folder` | no | `~/.hgtd_tools/local_info`, falling back to `./local_info` | folder that `hgtd-tools` uses for the access token |

`--date` filters on the **shipment date** (when it was sent);
`--reception-date` sets when it **arrived**. They are independent and can be
used in the same command.

## Exit codes

| code | meaning |
|---|---|
| `0` | every selected shipment was received, or the selection was empty |
| `1` | runtime or API failure: authentication, lookup, or at least one PUT |
| `2` | bad usage — unknown status, invalid `--limit`, malformed `--reception-date`, or no identifier and no filter |

## Examples

```
    # exact ids, comma-separated
    receive-shipment 1241,1242 -u yourUsername --dry-run

    # exact tracking numbers, with the arrival date
    receive-shipment --tracking-number trkDHL08193,trkDHL08194
        -u yourUsername --reception-date 2026-11-08

    # search, inspect, then select
    receive-shipment --search DHL --status Created -u yourUsername
    receive-shipment --company dhl --date 2026-11 --open-only -u yourUsername
```

## Behaviour notes

!!! warning "Receiving moves hardware records"

    The `PUT` sets every shipment item's part to the destination location. There
    is no undo beyond a further correction, so `--dry-run` or a listing first is
    the sane habit — especially with `--yes`.

!!! note "Already-received and canceled shipments are skipped"

    `Received` shipments are skipped with a note; `Cancel` shipments are skipped
    with a warning, because the server does not check status before moving
    parts. `--force` overrides both, and should be used deliberately.

!!! note "Selection is validated against the listing"

    When you pick from the match table, the entered ids must be among the rows
    that were printed. A typo cannot receive a shipment you never saw. `all`
    selects every match; an empty answer aborts.

!!! tip "Non-interactive runs"

    Without a terminal, the confirmation prompt is skipped rather than blocking,
    and the selection prompt raises instead of hanging — pass explicit ids or
    `--tracking-number` in cron jobs. `--yes` suppresses the confirmation only;
    it does not suppress the selection prompt.

!!! warning "Reception date is optional"

    `--reception-date` is only sent when given, so an existing value is
    preserved. There is currently no way to clear the field back to empty.


*Last updated: {{ last_updated }}*

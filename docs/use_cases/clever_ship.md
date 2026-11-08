# Clever Ship

`clever-ship` prepares or sends an HGTD shipment for one or more part subtrees.
It resolves the parts from the ProdDB, collects the children recursively, builds
the shipment payload and POSTs it to `/shipment`.

It is meant for the routine case where e.g. a detector unit or module —
together with everything mounted inside it — has to be sent from one institute
to another.

The script runs in five phases:

1. **Authentication** against the ProdDB (before any other request).
2. **Root resolution** — `part_id`s are used as given, `--sn` values are looked
   up per kind of part and converted to `part_id`s.
3. **Traversal** — recursive children are collected breadth-first, deduplicated
   by `part_id`, with each child's position inside its parent recorded.
4. **Payload build** — locations and company are resolved, the shipment date is
   defaulted, and every item's comment is taken from the part's own
   `comment_description`.
5. **POST** — unless `--dry-run` is given, in which case the payload is printed
   and nothing is written.

## Shipment scope

By default a shipment contains **each root plus all of its recursive children**.

| flags | what is shipped |
|---|---|
| *(none)* | each root + all descendants |
| `--without-parent` | all descendants, roots omitted |
| `--no-children` | only the roots |
| `--no-children --without-parent` | rejected — selects nothing |

With several roots, `--without-parent` drops **every** root. Parts reachable
from more than one root are shipped once; the summary reports how many
duplicates were skipped.

## Root selection

Roots may be given as comma-separated `part_id`s, as comma-separated serial
numbers with `--kind`, or as a mix of both.

| flag / argument | meaning |
|---|---|
| `PART_ID[,PART_ID...]` | one or more root `part_id`s, comma-separated |
| `--sn SN[,SN...]` | root serial number(s), comma-separated |
| `--kind KoP` | kind of part the `--sn` roots belong to, e.g. `Detector`. Applies to every SN. Used **only** to resolve the `part_id`. |

`--kind` is deliberately not reused as a traversal filter — a part's
children can never be of same kind of part, so filtering the walk by the same would return
nothing. Use `--child-kind` for that.

## Command-line parameters

**Traversal**

| flag | required | default | meaning |
|---|---|---|---|
| `--child-kind` | no | `all` | only follow children of this kind of part |
| `--max-depth` | no | unlimited | stop N levels below the root |

**Shipment fields**

| flag | required | default | meaning |
|---|---|---|---|
| `--from` | yes | — | origin: shortname, `location_id` or exact `location_name` |
| `--to` | yes | — | destination: shortname, `location_id` or exact `location_name` |
| `--company` | yes | — | shipment company: `company_id` or name (`dhl`, `ups`) |
| `--tracking-number` | no | generated | must be unique — the created record is read back by this value |
| `--date` | no | today | shipment date, `YYYY-MM-DD` |
| `--status` | no | `Created` | `Created`, `Shipped` or `Cancel`. `Received` is refused. |
| `--edh-link` | no | — | EDH link |
| `--no-fetch-part-comments` | no | off | do not fetch `/part/{id}/` for parts lacking `comment_description` |
| `--from-contact`, `--from-contact-email`, `--to-contact`, `--to-contact-email` | no | — | contact fields |

**Output**

| flag | required | default | meaning |
|---|---|---|---|
| `--list` | no | off | print the parts that would be shipped, to stderr |
| `--list-file PATH` | no | — | write the part list (`SN<TAB>part_id N` per line) |
| `--payload-file PATH` | no | — | write the JSON payload |
| `--dry-run` | no | off | do everything except the POST |
| `--quiet` | no | off | suppress the summary on stderr |

**Authentication**

| flag | required | default | meaning |
|---|---|---|---|
| `-u`, `--user-name` | yes | — | your CERN user name; also recorded as `record_insertion_user` |
| `--local-folder` | no | `~/.hgtd_tools/local_info`, falling back to `./local_info` | folder that `hgtd-tools` uses for the access token |

Locations accept the shortnames from `data.relevant_location_IDs_by_shortname`
(`ihep`, `ijclab`, `cern`, `mainz`, `mascir`, `lpnhe`, `ustc`, `test`, `ifae`),
matched case-insensitively, as well as numeric ids and exact location names.

## Exit codes

| code | meaning |
|---|---|
| `0` | shipment created (or dry run completed) |
| `1` | runtime or API failure: authentication, root resolution, traversal, location/company resolution, or the POST itself |
| `2` | bad usage — invalid flags, unparseable `part_id`, malformed date, unknown kind, or an empty selection |

## Examples

```
    # dry run, default scope: root + all descendants
    clever-ship 28833 -u anstein --from ihep --to ijclab --company dhl --dry-run
    clever-ship 28816 -u anstein --from mainz --to test --company ups --dry-run

    # two roots, comma-separated, descendants only
    clever-ship 28833,28834 -u anstein --without-parent
        --from cern --to ihep --company dhl --list --dry-run

    # several serial numbers of the same kind
    clever-ship --sn 20WMO...01,20WMO...02 --kind Module -u anstein
        --from ihep --to ijclab --company dhl --dry-run

    # single part, nothing else
    clever-ship 28833 -u anstein --no-children --from mainz --to test
        --company ups --dry-run

    # actually POST it
    clever-ship 28833,28834 -u anstein --from ihep --to ijclab --company dhl
        --tracking-number trkDHL08193 --date 2026-11-07
```

## Behaviour notes

!!! warning "A new shipment does not move any parts"

    Creating a shipment only stores it. The parts stay at the origin until the
    shipment is received — which is a separate `PUT` performed by
    `receive-shipment`. For that reason `--status Received` is rejected here.

!!! note "Item comments are never typed by hand"

    Each shipment item's comment is taken from the part's own
    `comment_description`. Parts whose record lacks the field are completed from
    `/part/{id}/` — one request per such part, run multi-threaded. Use
    `--no-fetch-part-comments` to skip those requests; the affected items then
    get an empty comment, and the summary reports how many.

!!! note "Tracking numbers must be unique"

    After the POST, `create_shipment` reads the created record back by
    `tracking_number`. A duplicate makes that lookup ambiguous, so the script
    generates `auto-YYYYMMDD-HHMMSS-ffffff` when `--tracking-number` is omitted.

!!! tip "Check the scope line before sending"

    The summary echoes the mode and scope, e.g.
    `[POSTING] 42 part(s) [part + all descendants] from 1 root(s) (28833)`.
    With multi-root runs it also prints per-root counts before deduplication and
    the number of skipped duplicates — the signal that your roots overlap.

!!! warning "Duplicates are shown, not hidden"

    A part mounted under two parents, or a bad parent link, is collected once at
    its shallowest level. Traversal also reports such edges rather than looping.
    Worth a glance before shipping a subtree that contains shared sub-assemblies.


*Last updated: {{ last_updated }}*

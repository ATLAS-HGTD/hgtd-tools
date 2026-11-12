---
icon: lucide/rocket
---

# Welcome to hgtd-tools!

These tools interact with the High-Granularity Timing Detector (HGTD) Production Database (ProdDB) for the Phase-II Upgrade of the ATLAS Experiment at CERN.

This python application comes with API client, GUI, automatic reporting and command-line scripts implementing consistent data uploads as well as their retrieval, analysis, plotting and more complex tasks like running a matching algorithm.

The [internal part of the project](https://gitlab.cern.ch/anstein/hgtd-tools-internal){target="_blank"} performs nightly checks of yields and consistency validation, as documented on the resulting [reports page](https://hgtd-tools-internal.web.cern.ch/){target="_blank"}.

This software follows the [HGTD Detector Naming Conventions for the surface assembly](https://edms.cern.ch/document/3483138/0.1){target="_blank"}, the [HGTD ProdDB Serial Number Note](https://cds.cern.ch/record/2910370/files/ATL-COM-HGTD-2024-026.pdf){target="_blank"} and [HGTD Module QC docs page](https://hgtd-module-qc.docs.cern.ch/){target="_blank"} for nomenclature and specifications.

## Getting started

Please check the [install](getting_started/install.md) guide for installing hgtd-tools the first time or the [update page](getting_started/update.md) when updating it.

## Features

The following overview lists the implemented features of `hgtd-tools` and links to more detailed documentation on specific aspects.

??? success "API (GET / POST / PUT / DELETE)"
    - See the API in action inside the GUI with dynamic, colored progress bar (API request status)
    - Efficient lookup of information in local files (e.g. static Slot table) and fetching of dynamic information via ProdDB API
    - Allows standalone usage of API client. It is used e.g. in [FADAPro](https://gitlab.cern.ch/atlas-hgtd/Electronics/fadapro/-/merge_requests/9){target="_blank"}, documented in the [FADAPro docs on `DB_interface.py`](https://hgtd-fadapro.docs.cern.ch/commandlist/#upload-to-database){target="_blank"}. Its DB implementation is part of the [analysis module](https://gitlab.cern.ch/atlas-hgtd/Electronics/fadapro/-/tree/master/analysis?ref_type=heads){target="_blank"}.

??? success "GUI (Linux / Mac / Windows)"

    Learn more about the [Main GUI for Part-to-Part Relations (Parts Tree)](use_cases/gui_relations.md) with screenshots, walkthrough for different modes etc.

    - clickable canvas to get local coordinates easily, conversion to global coordinates done internally where needed
    - buttons to inspect affected parts
    - GUI Modes
        - Module Assembly (MODULE -> MODULE FLEX, MODULE -> HYBRIDs on HV-side / LV-side)
        - Module Loading (DU -> MODULE)
        - Detector Assembly (CERN): DU (DETECTOR -> DU & multiple SLOT -> MODULE)
        - Detector Assembly (CERN): PEB (DETECTOR -> PEB)
        - Detector Assembly (CERN): FT (SLOT -> FT; includes global to local coordinate conversion via Slot table)
    - Logic
        - new relations can overwrite old ones, if user agrees to do so (implementing replacement of existing relations)
        - for Module Assembly, the above also takes care of two hybrids being allowed per module, but on different sides
        - user can not load / assemble parts that are not allowed to take that spot (implementing constraints for already used positions, and parts not matching the target position by type)
        - if operation requires subsequent operations (e.g. connecting modules to slots when placing a DU on the detector), perform those subsequent operations in one go, for FT this involves connecting to Slot, Module, Detector Unit and PEB in one go
        - query selection before choosing parent / child from full list (e.g. DU type, module manufacturer, child not yet connected or all possible children)

??? success "Additional tools / scripts / automation"
    - Serial Number reservation for module assembly, either by count or from a CSV of serial numbers [with CLI script `SN-reservation`](use_cases/SN_reservation.md)
    - Hybrid matching for module assembly [with CLI script `hybridmatch`](use_cases/hybrid_matching.md)
    - Bulk module assembly relation upload including consistency validation, accepting either one row per relation or one row per Module (with Module registration and serial number reservation) [with CLI script `bulk-module-assembly`](use_cases/bulk_module_assembly.md)
    - IV curve plotting [with CLI script `ivcurve-overlay`](use_cases/ivcurve_plotting.md)
    - Reporting
        - automation with Gitlab CI, using the hgtdbot account
        - runner script producing overviews / reports: [yields with CLI script `report-stats`](reporting/report_stats.md), [relation validation with CLI script `order`](reporting/order.md), [detector parts tree recursive traversal with CLI script `tree`](reporting/tree.md)
        - note: all CI scripts can also be used locally!
    - Flex Tail upload [with CLI script `upload-FlexTail-measurements`](use_cases/FT_upload_instructions.md)
    - Module and SU geometry plotting [with CLI script `plot-MO-SU-geo`](use_cases/module_SU_plotting.md)
    - Shipment preparation with recursive part collection [with CLI script `clever-ship`](use_cases/clever_ship.md)
    - Shipment reception, moving parts to their destination [with CLI script `receive-shipment`](use_cases/receive_shipment.md)

## Quickstart

If you walked through the [install](getting_started/install.md) guide and you activated the your `hgtd` environment, the following tools will be available:

??? tip "Using the `SN-reservation` script to reserve serial numbers or register parts from a CSV"

    When doing module assembly, you may want to reserve serial numbers (e.g. for a new week of module production) that no one else can pick after you reserved them. The script has two mutually exclusive modes: it either **proposes serial numbers for you**, or it **reads a CSV** with the serial numbers and the part details you already have. For more information on both modes, please read [SN Reservation](use_cases/SN_reservation.md).

    *Reserve a number of serial numbers* — `--prod` and `--batch` are required here:

    ```shell
    SN-reservation -u <your-user-name> --site <some-site> --prod <some-prod> --batch <some-batchNr> --n-reserve <how-many-SNs-to-reserve> --dryrun
    ```

    The script lists the serial numbers already in use for that prefix, proposes the next free ones (gaps in the sequence are filled first; pass `--no-fill-holes` to continue right after the highest counter instead), and then asks you for name label, version and comment **per serial number** before showing the payload for confirmation. Nothing is carried over from one SN to the next.

    *Register or update parts from a CSV* — the header decides the kind of part:

    ```shell
    SN-reservation -u <your-user-name> --site <some-site> --csv <path-to-your-csv> --dryrun
    ```

    ```csv
    module_sn,name_label,version,comment
    20WMOMAA000001,MM-01-A,v1.2,first batch
    20WMOMAA000002,MM-01-B,,
    ```

    A `module_sn` header means the parts are Modules and nothing is asked. A generic `sn` header makes the script ask for the kind of part, or you pass it once with `--kind`. Serial numbers already in the database are **updated** with a PUT (never created twice), unknown ones are created.

    `--dryrun` is a plain flag: it prints the requests instead of sending them, and it skips the confirmation questions. Add `--yes` to skip the confirmations in a real run — per CSV row, or per serial number in `--n-reserve` mode; the data prompts are still asked.

    The CSV is read *before* the database login, so a broken file fails immediately instead of after a token round-trip.

??? tip "Using the `hybridmatch` script for hybrid matching"

    When doing module assembly, you may want to get the "optimal" pairing of hybrids (e.g. for a new week of module production) that optimizes the total sum of paired breakdown voltage differences. For more information on the hybrid matching process, please read [Hybrid Matching](use_cases/hybrid_matching.md).

    Execute the following:

    ```shell
    hybridmatch --location <your-site>
    ```

??? tip "Using the `bulk-module-assembly` script for multiple relation upload including validation"

    When doing module assembly, you may have a prefilled csv file with parent-child relations to upload in one go. On the DB website, there was a method to do such a bulk relation upload, but without validation according to this [set of rules](https://hgtd-tools-internal.web.cern.ch/reports/validation/#module-assembly){target="_blank"}. In the HGTD Tools GUI, you get the validation, mistakes are prevented by construction, but you need to go module by module, and connect all children manually. This script is the combination of both - bulk upload, but with built-in consistency check. For more information, please read [Bulk Module Assembly](use_cases/bulk_module_assembly.md).

    Two CSV layouts are accepted, and the layout is detected from the header — no flag needed. Header names are case-insensitive in both.

    *One row per relation* — when you already know exactly which child goes where:

    ```shell
    bulk-module-assembly -i module_children.csv -u <your-username> --dry-run
    ```

    ```csv
    parent_kind_of_part,parent_serial_number,child_kind_of_part,child_serial_number,position
    Module,20WMOMAA000001,Module Flex,20WMFMHAA00001,
    Module,20WMOMAA000001,Hybrid,20WHNNNDA00001,HV
    Module,20WMOMAA000001,Hybrid,20WHNNNDA00002,LV
    ```

    *One row per Module* — when you assemble module by module and want the Module details and its three children in a single line. The Module is **created if missing and updated if its details differ**, then the three relations are uploaded. Leave `module_sn` empty and the script reserves the next free serial number for you, using the same rules as `SN-reservation`:

    ```shell
    bulk-module-assembly -i modules.csv -u <your-username> --site <some-site> --prod <prod> --batch A --dry-run
    ```

    ```csv
    module_sn,name_label,version,comment,module_flex_sn,hybrid_hv_sn,hybrid_lv_sn
    20WMOMAA000001,MM-01-A,v1.2,first batch,20WMFMHAA00001,20WHNNNDA00001,20WHNNNDA00002
    ,MM-01-B,,,20WMFMHAA00002,20WHNNNDA00003,20WHNNNDA00004
    ```

    Both layouts enforce the same rules: one Module Flex per Module at empty position, exactly two Hybrids at `HV` and `LV`, and every child connected to at most one parent — checked offline first and then against the DB. Only the Modules are created/updated; Module Flexes and Hybrids must already be registered. Add `--skip-part-sync` to leave the Module records untouched and upload relations only, `--skip-upload` to validate without writing, and `--allow-malformed-sn` to downgrade the serial-number format check to a warning.

??? tip "Using the `ivcurve-overlay` script for IV curve plotting"

    At module assembly or other stages of production, you may want to inspect and compare various IV curves against each other, possibly not only for one kind of part, but multiple in the same plot (Sensor(s)/Hybrid(s)/Module(s)). For more information on the IV curve plotting process, please read [IV Curve Plotting](use_cases/ivcurve_plotting.md).

    Execute the following (just one example given so you get reminded how to call the script, various combinations possible):

    ```shell
    ivcurve-overlay --hybrid-sns "HybridASerialNumber,HybridBSerialNumber" <check-out-the-different-parameters>
    ```


??? tip "Using the `gui` for Part-to-Part relations, starting from module assembly"

    If you have done some connections between multi-relation parts, like module assembly, module loading, detector assembly with DUs, PEBs or Flex Tails, or you want to get assistance on what to pick, use the GUI of hgtd-tools.

    To open the main window with GUI, execute the following:

    ```shell
    hgtd-tools gui
    ```
    Or the shortcut
    ```shell
    hgtd-tools
    ```

    Closing the application works like you would expect from other applications, e.g. you'll find a red button to close hgtd-tools, you could quit the application with shortcuts of your operating system (e.g. MacOS: cmd+Q), or interrupting the python program from command line with ctrl+c.

    !!! note  "Documentation of typical use cases of the GUI application"

        Checkout the [illustrative showcase of the GUI](use_cases/gui_relations.md) with screenshots, walkthrough for different modes etc.

        Previously, this was hosted on the main ProdDB [documentation page](https://hgtd-database.docs.cern.ch/){target="_blank"}, which contains a [section on hgtd-tools](https://hgtd-database.docs.cern.ch/content/user/parts_tree_hgtd-tools/){target="_blank"} as well.

??? tip "Using the `upload-FlexTail-measurement` script for uploading flex tail measurements"

    After performing all electrical and mechanical measurements of a batch of flex tails, upload the folder containing all measurements to the database. The optional `--dryrun` argument can be useful to test if the upload will succeed or not. For more information on the uploading procedure, please read [FT_upload_instructions](use_cases/FT_upload_instructions.md).

    Execute the following:

    ```shell
    upload-FlexTail-measurement --analysis-folder FT_Measurements --user-name myName --meas_location test --meas_start_date YYYY-MM-DD --meas_end_date YYYY-MM-DD --run_type FT_characterisation_test (--dryrun True)
    ```

??? tip "Using the `plot-MO-SU-geo` script for plotting module positions per quadrant (as in slot table, global reference coordinate system for front and back geometry)"

    For plotting the pre-defined SU-Module map in front/back quadrants and individually for Demonstrator (V1+V2) slices. Needs the references containing the coordinates and mappings from the slot table / flex tail calculation process. This script requires passing the path to the reference files containing the slots and the module references, respectively.
    For more information, please read [Module SU Plotting](use_cases/module_SU_plotting.md).

    Execute the following:

    ```shell
    plot-MO-SU-geo --slot-table-dir <your-path> --module-ref-dir <your-path>
    ```

??? tip "Using the `clever-ship` script to ship a part together with everything inside it"

    When sending parts between institutes, you usually want the whole subtree: a Detector Unit with its Modules, a Module with its Module Flex and both Hybrids. Doing that by hand means walking the tree relation by relation. `clever-ship` walks it for you, resolves locations and the shipment company, and takes each shipment item's comment from the part's own `comment_description` — so nothing has to be typed twice. For more information, please read [clever-ship](use_cases/clever_ship.md).

    Always inspect the payload first:

    ```shell
    clever-ship --sn 20WMO...01,20WMO...02 --kind Module -u <your-username> --from ijclab --to lpnhe --company dhl --list --dry-run
    ```

    Then drop `--dry-run` to POST. A newly created shipment does **not** move any parts — that happens on reception.

??? tip "Using the `receive-shipment` script to receive a shipment and move its parts"

    When a shipment arrives, marking it `Received` is what moves every part in it to the shipment's destination location. `clever-ship` deliberately cannot do this, because creating a shipment already marked `Received` would leave the hardware where it was. For more information, please read [receive-shipment](use_cases/receive_shipment.md).

    Find the shipment first — either directly by id or tracking number, or by search:

    ```shell
    receive-shipment --search DHL --open-only -u <your-username> --dry-run
    receive-shipment 1241,1242 -u <your-username> --reception-date YYYY-MM-DD
    ```

    Without an explicit id or tracking number, the matching shipments are printed as a table and you pick the ones to receive.

## Contributing

If you are planning to contribute, check out the [developer instructions](development/dev.md).

For any problems, do not hesitate to ask on [mattermost](https://mattermost.web.cern.ch/atlas/channels/hgtd-production-database){target="_blank"} or open an [Issue](https://gitlab.cern.ch/anstein/hgtd-tools/-/issues){target="_blank"} after checking the existing issues.

### Open points requiring implementation
New features, bugs, compatibility improvements and other items are collected with the [Issues](https://gitlab.cern.ch/anstein/hgtd-tools/-/issues){target="_blank"} on gitlab.

Some of them are also bound to [Milestones](https://gitlab.cern.ch/anstein/hgtd-tools/-/milestones){target="_blank"}, currently this is preparing major version 4, `Production`.

## Acknowledgements
Thanks to an unknown reddit user who gave me hope when the PyQt6 installation wouldn't want to work with my setup / machine. This [link](https://www.reddit.com/r/Tkinter/comments/snrb1f/comment/hw4bylf/?utm_source=share&utm_medium=web3x&utm_name=web3xcss&utm_term=1&utm_content=share_button){target="_blank"} brought me to [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter){target="_blank"} and the GUI is built on top of the tutorial.

## Zenodo

HGTD Tools is now on Zenodo, with a persistent [Zenodo DOI identifier](https://doi.org/10.5281/zenodo.20774012) which updates with each new version.

```
@software{hgtd_tools,
  author       = {Stein, Annika},
  title        = {HGTD Tools},
  publisher    = {Zenodo},
  doi          = {10.5281/zenodo.20774012},
  url          = {https://doi.org/10.5281/zenodo.20774012},
}
```

*Last updated: {{ last_updated }}*

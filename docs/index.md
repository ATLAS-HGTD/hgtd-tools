---
icon: lucide/rocket
---

# Welcome to hgtd-tools!

These tools interact with the High-Granularity Timing Detector (HGTD) Production Database (ProdDB) for the Phase-II Upgrade of the ATLAS Experiment at CERN.

This python application comes with API client, GUI, automatic reporting and command-line scripts implementing consistent data uploads as well as their retrieval, analysis, plotting and more complex tasks like running a matching algorithm.

The [internal part of the project](https://gitlab.cern.ch/anstein/hgtd-tools-internal){target="_blank"} performs nightly checks of yields and consistency validation, as documented on the resulting [reports page](https://hgtd-tools-internal.web.cern.ch/){target="_blank"}.

## Getting started

Please check the [install](getting_started/install.md) guide for installing hgtd-tools the first time or the [update page](getting_started/update.md) when updating it.

## Features

The following overview lists the implemented features of `hgtd-tools` and links to more detailed documentation on specific aspects.

??? success "API (GET / POST / DELETE)"
    - See the API in action inside the GUI with dynamic progress bar (API request status)
    - Efficient lookup of information in local files (e.g. static Slot table) and fetching of dynamic information via ProdDB API
    - Allows standalone usage of API client (used e.g. in [FADAPro](https://gitlab.cern.ch/atlas-hgtd/Electronics/fadapro/-/merge_requests/9){target="_blank"}, documented in [FADAPro docs on `DB_interface.py`](https://hgtd-fadapro.docs.cern.ch/commandlist/#upload-to-database){target="_blank"})

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
    - Serial Number reservation for module assembly [with CLI script `SN-reservation`](use_cases/SN_reservation.md)
    - Hybrid matching for module assembly [with CLI script `hybridmatch`](use_cases/hybrid_matching.md)
    - IV curve plotting [with CLI script `ivcurve-overlay`](use_cases/ivcurve_plotting.md)
    - Reporting
        - automation with Gitlab CI, using the hgtdbot account
        - runner script producing overviews / reports: yields and relation validation
    - Flex Tail upload [with CLI script `upload-FlexTail-measurements`](use_cases/FT_upload_instructions.md)

## Quickstart

If you walked through the [install](getting_started/install.md) guide and you activated the your `hgtd` environment, the following tools will be available:

??? tip "Using the `SN-reservation` script for module serial number reservation"

    When doing module assembly, you may want to reserve serial numbers (e.g. for a new week of module production) that no one else can pick after you reserved them. For more information on the reservation process, please read [SN Reservation](use_cases/SN_reservation.md).

    Execute the following:

    ```shell
    SN-reservation --user-name <your-user-name> --site <some-site> --prod <some-prod> --batch <some-batchNr> --n-reserve <how-many-SNs-to-reserve> (--dryrun True)
    ```

??? tip "Using the `hybridmatch` script for hybrid matching"

    When doing module assembly, you may want to get the "optimal" pairing of hybrids (e.g. for a new week of module production) that optimizes the total sum of paired breakdown voltage differences. For more information on the hybrid matching process, please read [Hybrid Matching](use_cases/hybrid_matching.md).

    Execute the following:

    ```shell
    hybridmatch --location <your-site>
    ```

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

## Contributing

If you are planning to contribute, check out the [developer instructions](development/dev.md).

For any problems, do not hesitate to ask on [mattermost](https://mattermost.web.cern.ch/atlas/channels/hgtd-production-database){target="_blank"} or open an [Issue](https://gitlab.cern.ch/anstein/hgtd-tools/-/issues){target="_blank"} after checking the existing issues.

### Open points requiring implementation
New features, bugs, compatibility improvements and other items are collected with the [Issues](https://gitlab.cern.ch/anstein/hgtd-tools/-/issues){target="_blank"} on gitlab.

Some of them are also bound to [Milestones](https://gitlab.cern.ch/anstein/hgtd-tools/-/milestones){target="_blank"}, currently entailing `Package refactor` and `Production`.

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

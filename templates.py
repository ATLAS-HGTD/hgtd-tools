def validation_header():
    return f"""---
icon: lucide/link
---

# Validation

!!! info "Automatic reports taken from the HGTD ProdDB"

    Check the CI results of hgtd-tools, run every night or upon request.

    This report was last updated on: {{{{ config.extra.build_time }}}}.

    Every automatically generated result is available on this [cernbox link](https://cernbox.cern.ch/files/spaces/eos/user/a/anstein/www/hgtd-tools-internal/generated){{target="_blank"}}.

## Nightly reports: relations
"""


def module_assembly_intro():
    return f"""### Module Assembly

| Parent KoP | Child KoP | Position |
| ---------- | --------- | -------- |
| Module | Module Flex | empty |
| Module | Hybrid | one of either `HV` or `LV` |

"""


def module_assembly_all(
    all_manus,
    n_valid_parts_all,
    n_valid_connected_parts_all,
    n_invalid_parts_all,
    n_fake_parts_all,
):
    return f"""???+ tip "All validated sites"

    Selected sites: {', '.join(all_manus)}.

    Valid Modules (using latest SN spec, excludes Digital Modules marked with _Digital in Name Label): {n_valid_parts_all}, of which correctly connected with children (MF, HY): {n_valid_connected_parts_all}

    Invalid Modules (not using latest SN spec, and including Digital Modules marked with _Digital in Name Label): {n_invalid_parts_all}

    Fake Modules: {n_fake_parts_all}

    ???+ info "Overview: valid Modules by assembly sites"

        [.png :material-image-search-outline:](https://cernbox.cern.ch/files/spaces/eos/user/a/anstein/www/hgtd-tools-internal/generated/pie_chart_MA_valid_all.png){{ .md-button }}
        [.pdf :material-file-image-outline:](https://cernbox.cern.ch/files/spaces/eos/user/a/anstein/www/hgtd-tools-internal/generated/pie_chart_MA_valid_all.pdf){{ .md-button }}

        ![pie_chart_MA_valid_all.png](../generated/pie_chart_MA_valid_all.png)

    ???+ info "Overview: valid & correctly connected Modules by assembly sites"

        [.png :material-image-search-outline:](https://cernbox.cern.ch/files/spaces/eos/user/a/anstein/www/hgtd-tools-internal/generated/pie_chart_MA_valid_connected_all.png){{ .md-button }}
        [.pdf :material-file-image-outline:](https://cernbox.cern.ch/files/spaces/eos/user/a/anstein/www/hgtd-tools-internal/generated/pie_chart_MA_valid_connected_all.pdf){{ .md-button }}

        ![pie_chart_MA_valid_connected_all.png](../generated/pie_chart_MA_valid_connected_all.png)

"""


def hybridization_intro():
    return f"""### Hybridization

| Parent KoP | Child KoP | Position |
| ---------- | --------- | -------- |
| Hybrid | Sensor | empty |
| Hybrid | ASIC | empty (note: currently not investigated because ASICs are missing in DB) |

"""


def hybridization_all(
    all_manus,
    n_valid_parts_all,
    n_valid_connected_parts_all,
    n_invalid_parts_all,
    n_fake_parts_all,
):
    return f"""???+ tip "All validated sites"

    Selected sites: {', '.join(all_manus)}.

    Valid Hybrids (using latest SN spec): {n_valid_parts_all}, of which correctly connected with children (currently checking only S): {n_valid_connected_parts_all}

    Invalid Hybrids (not using latest SN spec): {n_invalid_parts_all}

    Fake Hybrids: {n_fake_parts_all}

    ???+ info "Overview: valid Hybrids by hybridization sites"

        [.png :material-image-search-outline:](https://cernbox.cern.ch/files/spaces/eos/user/a/anstein/www/hgtd-tools-internal/generated/pie_chart_HY_valid_all.png){{ .md-button }}
        [.pdf :material-file-image-outline:](https://cernbox.cern.ch/files/spaces/eos/user/a/anstein/www/hgtd-tools-internal/generated/pie_chart_HY_valid_all.pdf){{ .md-button }}

        ![pie_chart_HY_valid_all.png](../generated/pie_chart_HY_valid_all.png)

    ???+ info "Overview: valid & correctly connected Hybrids by hybridization sites"

        [.png :material-image-search-outline:](https://cernbox.cern.ch/files/spaces/eos/user/a/anstein/www/hgtd-tools-internal/generated/pie_chart_HY_valid_connected_all.png){{ .md-button }}
        [.pdf :material-file-image-outline:](https://cernbox.cern.ch/files/spaces/eos/user/a/anstein/www/hgtd-tools-internal/generated/pie_chart_HY_valid_connected_all.pdf){{ .md-button }}

        ![pie_chart_HY_valid_connected_all.png](../generated/pie_chart_HY_valid_connected_all.png)

"""


def sensor_par_intro():
    return f"""### Sensor Parents -> (Hybrid, Wafer)

| Parent KoP | Child KoP | Position |
| ---------- | --------- | -------- |
| Hybrid | Sensor | empty |
| Wafer | Sensor | empty (in principle, last two digits of Sensor SN, which is however not stored in position attribute, but as a part attribute of the sensor) |

"""


def sensor_par_all(
    all_manus,
    n_valid_parts_all,
    n_valid_connected_parts_all,
    n_invalid_parts_all,
    n_fake_parts_all,
    n_valid_new_parts_all,
):
    return f"""???+ tip "All validated manufacturers"

    Selected manufacturers: {', '.join(all_manus)}.

    Valid Sensors (using latest SN spec): {n_valid_parts_all}, of which correctly connected with parent HY + W: {n_valid_connected_parts_all}; or of which correctly connected with parent W, but not yet to H: {n_valid_new_parts_all}

    Invalid Sensors (not using latest SN spec): {n_invalid_parts_all}

    Fake Sensors: {n_fake_parts_all}

    ???+ info "Overview: valid Sensors by manufacturer"

        [.png :material-image-search-outline:](https://cernbox.cern.ch/files/spaces/eos/user/a/anstein/www/hgtd-tools-internal/generated/pie_chart_S_valid_all.png){{ .md-button }}
        [.pdf :material-file-image-outline:](https://cernbox.cern.ch/files/spaces/eos/user/a/anstein/www/hgtd-tools-internal/generated/pie_chart_S_valid_all.pdf){{ .md-button }}

        ![pie_chart_S_valid_all.png](../generated/pie_chart_S_valid_all.png)

    ???+ info "Overview: valid & correctly connected Sensors by manufacturer"

        [.png :material-image-search-outline:](https://cernbox.cern.ch/files/spaces/eos/user/a/anstein/www/hgtd-tools-internal/generated/pie_chart_S_valid_connected_all.png){{ .md-button }}
        [.pdf :material-file-image-outline:](https://cernbox.cern.ch/files/spaces/eos/user/a/anstein/www/hgtd-tools-internal/generated/pie_chart_S_valid_connected_all.pdf){{ .md-button }}

        ![pie_chart_S_valid_connected_all.png](../generated/pie_chart_S_valid_connected_all.png)

    ???+ info "Overview: valid & new Sensors (correctly connected to W, not yet to a HY) by manufacturer"

        [.png :material-image-search-outline:](https://cernbox.cern.ch/files/spaces/eos/user/a/anstein/www/hgtd-tools-internal/generated/pie_chart_S_valid_new_all.png){{ .md-button }}
        [.pdf :material-file-image-outline:](https://cernbox.cern.ch/files/spaces/eos/user/a/anstein/www/hgtd-tools-internal/generated/pie_chart_S_valid_new_all.pdf){{ .md-button }}

        ![pie_chart_S_valid_new_all.png](../generated/pie_chart_S_valid_new_all.png)

"""

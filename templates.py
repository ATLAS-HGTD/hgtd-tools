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
    n_valid_parts_all,
    n_valid_connected_parts_all,
    n_invalid_parts_all,
    n_fake_parts_all,
):
    return f"""???+ note "All validated sites"

    Valid Modules: {n_valid_parts_all}, of which correctly connected with children (MF, HY): {n_valid_connected_parts_all}

    Invalid Modules: {n_invalid_parts_all}

    Fake Modules: {n_fake_parts_all}

    ???+ note "Overview: valid Modules by assembly sites"

        [.png :material-image-search-outline:](https://cernbox.cern.ch/files/spaces/eos/user/a/anstein/www/hgtd-tools-internal/generated/pie_chart_MA_valid_all.png){{ .md-button }}
        [.pdf :material-file-image-outline:](https://cernbox.cern.ch/files/spaces/eos/user/a/anstein/www/hgtd-tools-internal/generated/pie_chart_MA_valid_all.pdf){{ .md-button }}

        ![pie_chart_MA_valid_all.png](../generated/pie_chart_MA_valid_all.png)

    ???+ note "Overview: valid & correctly connected Modules by assembly sites"

        [.png :material-image-search-outline:](https://cernbox.cern.ch/files/spaces/eos/user/a/anstein/www/hgtd-tools-internal/generated/pie_chart_MA_valid_connected_all.png){{ .md-button }}
        [.pdf :material-file-image-outline:](https://cernbox.cern.ch/files/spaces/eos/user/a/anstein/www/hgtd-tools-internal/generated/pie_chart_MA_valid_connected_all.pdf){{ .md-button }}

        ![pie_chart_MA_valid_connected_all.png](../generated/pie_chart_MA_valid_connected_all.png)
"""

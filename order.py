from argparse import ArgumentParser

import api
import relation_validation
import util

parser = ArgumentParser("CLI for reporting (parts stats)")
parser.add_argument(
    "--category",
    dest="category",
    help="Kind of part category for which to run validation.",
    default="Module",
)
parser.add_argument(
    "--manufacturer",
    dest="manufacturer",
    help="Manufacturer short name for which to run validation.",
    default="mainz",
)
args = parser.parse_args()

kop_cat = args.category
manufacturer = args.manufacturer

# Find all relevant parts of category under investigation
parts = util.get_relevant_parts(kop_cat)[0]

# (Limit to certain manufacturer first while developing, for quicker feedback)
parts = util.select_parts(parts, manu_shortname=manufacturer)

# Collect stats, and proceed only with valid ones
## how many are valid SNs
valid_parts = util.select_parts(parts, check_valid_SN_latest_spec=True)
## how many are invalid SNs
invalid_parts = util.select_parts(parts, check_invalid_SN_latest_spec=True)
## how many are fake SNs
fake_parts = util.select_parts(parts, check_fake_SN=True)

# Count
n_valid_parts = len(valid_parts)
n_invalid_parts = len(invalid_parts)
n_fake_parts = len(fake_parts)

validation_results = {}

for p in range(len(valid_parts)):
    this_part_id = valid_parts[p]["part_id"]
    validation_results[this_part_id] = relation_validation.validate_module(this_part_id)

# collect stats from validation results and prepare to feed into report template
n_valid_connected_parts = 0

module_relations_template = ""

for p in valid_parts:
    this_part_id = p["part_id"]
    this_part_SN = p["serial_number"]
    if validation_results[this_part_id]["validation_result_overall"] == True:
        n_valid_connected_parts += 1
        module_relations_template += (
            f'\t!!! success "Relation validation OK for {this_part_SN}"\n\n'
        )
    else:
        module_relations_template += f"""\t??? error "Relation validation failed for {this_part_SN}"\n\n
    \tInspect this [part {this_part_SN}]({api.frontendUrlPrefix + f"/viewparts/{this_part_id}"}) in DB.\n\n
    \tDetailed failure reason:\n\n
"""
        if validation_results[this_part_id]["validation_result_MO_chi_MF"] == False:
            module_relations_template += (
                "\t\t"
                + validation_results[this_part_id]["validation_reason_MO_chi_MF"]
                + "\n\n"
            )
        if validation_results[this_part_id]["validation_result_MO_chi_HY"] == False:
            module_relations_template += (
                "\t\t"
                + validation_results[this_part_id]["validation_reason_MO_chi_HY"]
                + "\n\n"
            )

# fill in report into template

validation_template = f"""---
icon: lucide/link
---

# Validation

!!! info "Automatic reports taken from the HGTD ProdDB"

    Check the CI results of hgtd-tools, run every night (started at 2:59 CERN time).

    This report was last updated on: {{{{ config.extra.build_time }}}}.

    Every automatically generated result is available on this [cernbox link](https://cernbox.cern.ch/files/spaces/eos/user/a/anstein/www/hgtd-tools-internal/generated){{target="_blank"}}.

## Nightly reports: relations

### Module Assembly

| Parent KoP | Child KoP | Position |
| ---------- | --------- | -------- |
|  |  |  |
| Module | Module Flex | empty |
| Module | Hybrid | one of either `HV` or `LV` |

???+ note "All sites"

??? note "Mainz"

    Valid Modules: {n_valid_parts}, of which correctly connected with children (MF, HY): {n_valid_connected_parts}

    Invalid Modules: {n_invalid_parts}

    Fake Modules: {n_fake_parts}

    Details:

{module_relations_template}
"""

with open("validation.md", "w") as f:
    f.write(validation_template)

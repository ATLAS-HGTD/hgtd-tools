from argparse import ArgumentParser

import api
import data
import plotter
import relation_validation
import templates
import util

parser = ArgumentParser("CLI for reporting (relation validation)")
parser.add_argument(
    "--mode-alias",
    dest="mode_alias",
    help="Validation mode alias. (Default: %(default)s)",
    default="all",
    choices=["Module Assembly", "Sensor_par_HY", "all"],
)
parser.add_argument(
    "--single-manufacturer",
    dest="single_manufacturer",
    help="[Optional] Single manufacturer short name for which to run validation. Overrides default list associated with mode-alias. Useful during development.",
    default=None,
)
parser.add_argument(
    "--dev",
    dest="dev",
    help="[Optional] Developer mode. Limit number of parts to process.",
    default=False,
)
parser.add_argument(
    "--subtitle",
    dest="subtitle",
    help="[Optional] Add a subtitle with SN validity category and used hgtd-tools commit + date of generation.",
    default=True,
)
parser.add_argument(
    "--custom-text",
    dest="customText",
    help="[Optional] Replace Production Database text in plot label with your custom text (e.g. Preliminary, Internal...).",
    default=None,
)
args = parser.parse_args()

mode_alias = args.mode_alias
single_manufacturer = args.single_manufacturer
dev = util.str2bool(args.dev)
subtitle = util.str2bool(args.subtitle)
exp_text = args.customText if args.customText != None else "Production Database"

if mode_alias == "all":
    # need to run multiple validations in this script
    mode_aliases = ["Module Assembly", "Sensor_par_HY"]
else:
    mode_aliases = [mode_alias]


def prepare_validation_per_subset(parts_subset, mode_alias):
    # Limit to smaller number of parts first while developing, for quicker feedback
    if dev:
        parts_subset = parts_subset[:10]

    # Collect stats from SNs, and proceed only with valid ones
    valid_parts = util.select_parts(parts_subset, check_valid_SN_latest_spec=True)
    invalid_parts = util.select_parts(parts_subset, check_invalid_SN_latest_spec=True)
    fake_parts = util.select_parts(parts_subset, check_fake_SN=True)
    ## Count and prepare dict for relation validation
    if mode_alias == "Module Assembly":
        validation_subset = {
            "n_valid_parts": len(valid_parts),
            "n_invalid_parts": len(invalid_parts),
            "n_fake_parts": len(fake_parts),
            "n_valid_connected_parts": 0,
            "relations_template_good": '\t??? success "Relation validation OK for these parts:"\n\n',
            "relations_template_bad": "",
        }
    elif mode_alias == "Sensor_par_HY":
        validation_subset = {
            "n_valid_parts": len(valid_parts),
            "n_invalid_parts": len(invalid_parts),
            "n_fake_parts": len(fake_parts),
            "n_valid_connected_parts": 0,
            "relations_template_good": '\t??? success "Relation validation OK for these parts:"\n\n',
            "relations_template_new": '\t??? example "These parts are not connected yet:"\n\n',
            "relations_template_bad": "",
        }
    # Collect stats from validation results and prepare to feed into report template
    for p in valid_parts:
        this_part_id = p["part_id"]
        this_part_SN = p["serial_number"]
        if mode_alias == "Module Assembly":
            individual_part_results = relation_validation.validate_module(this_part_id)
        elif mode_alias == "Sensor_par_HY":
            individual_part_results = relation_validation.validate_sensor(this_part_id)

        if individual_part_results["validation_result_overall"] == True:
            # this part only has correct connections, note down its SN / url (every part => new line)
            validation_subset["n_valid_connected_parts"] += 1
            validation_subset[
                "relations_template_good"
            ] += f'\t\t[Part {this_part_SN}]({api.frontendUrlPrefix + f"/viewparts/{this_part_id}"}).\n\n'
        elif individual_part_results["validation_result_overall"] == "new":
            # this part has not been connected yet to parent(s), OK during production (every part => new line)
            validation_subset[
                "relations_template_new"
            ] += f'\t\t[Part {this_part_SN}]({api.frontendUrlPrefix + f"/viewparts/{this_part_id}"}).\n\n'
        else:
            # something is incorrectly connected for this part (every part => new admonition)
            validation_subset[
                "relations_template_bad"
            ] += f"""\t??? failure "Relation validation failed for {this_part_SN}:"\n
\t\tInspect this [part {this_part_SN}]({api.frontendUrlPrefix + f"/viewparts/{this_part_id}"}) in DB.\n
\t\tDetailed failure reason:\n
"""
            # note down the reason(s) individually
            if mode_alias == "Module Assembly":
                if individual_part_results["validation_result_MO_chi_MF"] == False:
                    validation_subset["relations_template_bad"] += (
                        "\t\t"
                        + individual_part_results["validation_reason_MO_chi_MF"]
                        + "\n\n"
                    )
                if individual_part_results["validation_result_MO_chi_HY"] == False:
                    validation_subset["relations_template_bad"] += (
                        "\t\t"
                        + individual_part_results["validation_reason_MO_chi_HY"]
                        + "\n\n"
                    )
            elif mode_alias == "Sensor_par_HY":
                if individual_part_results["validation_result_S_par_HY"] == False:
                    validation_subset["relations_template_bad"] += (
                        "\t\t"
                        + individual_part_results["validation_reason_S_par_HY"]
                        + "\n\n"
                    )
    if validation_subset["n_valid_connected_parts"] == 0:
        validation_subset["relations_template_good"] = (
            '\t!!! warning "Not a single relation validation passed!"\n\n'
        )
    return validation_subset


def prepare_validation_per_mode(mode_alias, manufacturers=None):
    validation_all = {}
    if mode_alias == "Module Assembly":
        # Find all relevant parts of category under investigation
        category = "Module"
        parts = util.get_relevant_parts(category)[0]
        # further split by manufacturer
        for manu in manufacturers:
            parts_per_manu = util.select_parts(parts, manu_shortname=manu)
            validation_all[manu] = prepare_validation_per_subset(
                parts_per_manu, mode_alias
            )

        contributions_valid_all = [
            validation_all[m]["n_valid_parts"] for m in manufacturers
        ]
        contributions_valid_connected_all = [
            validation_all[m]["n_valid_connected_parts"] for m in manufacturers
        ]
        validation_all["all"] = {
            "contributions_valid": [
                validation_all[m]["n_valid_parts"] for m in manufacturers
            ],
            "n_valid_parts": sum(contributions_valid_all),
            "contributions_valid_connected": [
                validation_all[m]["n_valid_connected_parts"] for m in manufacturers
            ],
            "n_valid_connected_parts": sum(contributions_valid_connected_all),
            "n_invalid_parts": sum(
                validation_all[m]["n_invalid_parts"] for m in manufacturers
            ),
            "n_fake_parts": sum(
                validation_all[m]["n_fake_parts"] for m in manufacturers
            ),
        }

        filename_postfix_mode_alias = "MA"
        extra_text_mode_alias = "Module Assembly: Modules"

        # Plot overview pie charts
        ## All valid parts, contributions by manufacturer
        plotter.pie_chart(
            data=validation_all["all"]["contributions_valid"],
            text_labels=manufacturers,
            filename_postfix=filename_postfix_mode_alias + "_valid_all",
            exp_text=exp_text,
            subtitle=subtitle,
            extra_text=extra_text_mode_alias + " (valid). ",
        )
        ## All valid **connected** parts, contributions by manufacturer
        plotter.pie_chart(
            data=validation_all["all"]["contributions_valid_connected"],
            text_labels=manufacturers,
            filename_postfix=filename_postfix_mode_alias + "_valid_connected_all",
            exp_text=exp_text,
            subtitle=subtitle,
            extra_text=extra_text_mode_alias + " (valid & correctly connected). ",
        )
    elif mode_alias == "Sensor_par_HY":
        category = "Sensor"
        parts = util.get_relevant_parts(category)[0]
        # all of them
        validation_all["all"] = prepare_validation_per_subset(parts, mode_alias)
    return validation_all


# fill in report into template
validation_template = templates.validation_header()

for mode_alias in mode_aliases:
    if mode_alias == "Module Assembly":
        manufacturers = data.MA_sites_to_monitor
    else:
        manufacturers = []  # not implemented, but to use same pattern
    if single_manufacturer != None:
        manufacturers = [single_manufacturer]
    validation_all = prepare_validation_per_mode(mode_alias, manufacturers)
    if mode_alias == "Module Assembly":
        validation_template += templates.module_assembly_intro()
        validation_template += templates.module_assembly_all(
            validation_all["all"]["n_valid_parts"],
            validation_all["all"]["n_valid_connected_parts"],
            validation_all["all"]["n_invalid_parts"],
            validation_all["all"]["n_fake_parts"],
        )
        for m in manufacturers:
            validation_template += f"""??? note "{m}"

    Valid Modules: {validation_all[m]["n_valid_parts"]}, of which correctly connected with children (MF, HY): {validation_all[m]["n_valid_connected_parts"]}

    Invalid Modules: {validation_all[m]["n_invalid_parts"]}

    Fake Modules: {validation_all[m]["n_fake_parts"]}

    Details:

{validation_all[m]["relations_template_good"]}
{validation_all[m]["relations_template_bad"]}
"""
    elif mode_alias == "Sensor_par_HY":
        validation_template += templates.sensor_par_HY_intro()
        validation_template += f"""???+ tip "All validated Sensors"

    Valid Sensors: {validation_all["all"]["n_valid_parts"]}, of which correctly connected with parent HY: {validation_all["all"]["n_valid_connected_parts"]}

    Invalid Sensors: {validation_all["all"]["n_invalid_parts"]}

    Fake Sensors: {validation_all["all"]["n_fake_parts"]}

    Details:

{validation_all["all"]["relations_template_good"]}
{validation_all["all"]["relations_template_new"]}
{validation_all["all"]["relations_template_bad"]}
"""

with open("validation.md", "w") as f:
    f.write(validation_template)

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
    choices=["Module Assembly", "Sensor_par", "Hybridization", "all"],
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
    mode_aliases = ["Module Assembly", "Hybridization", "Sensor_par"]
else:
    mode_aliases = [mode_alias]


def prepare_validation_per_subset(parts_subset, mode_alias):
    # Limit to smaller number of parts first while developing, for quicker feedback
    if dev:
        parts_subset = parts_subset[:10]

    # Collect stats from SNs, and proceed only with valid ones
    if mode_alias == "Module Assembly":
        # there are valid modules (in terms of SN), but which are digital modules not to be checked
        valid_SN_parts = util.select_parts(
            parts_subset, check_valid_SN_latest_spec=True
        )
        # filter the valid modules, which are digital modules
        valid_and_DigitalMod_parts = util.select_parts(
            valid_SN_parts, name_label_does_include="_Digital"
        )
        # and the opposite, non-digital (= full) modules
        valid_parts = util.select_parts(
            valid_SN_parts, name_label_does_not_include="_Digital"
        )
        # invalid in terms of SN
        invalid_SN_parts = util.select_parts(
            parts_subset, check_invalid_SN_latest_spec=True
        )
        # add the digital modules on top of the invalid SN modules
        invalid_parts = invalid_SN_parts + valid_and_DigitalMod_parts
    else:
        valid_parts = util.select_parts(parts_subset, check_valid_SN_latest_spec=True)
        invalid_parts = util.select_parts(
            parts_subset, check_invalid_SN_latest_spec=True
        )
    fake_parts = util.select_parts(parts_subset, check_fake_SN=True)
    ## Count and prepare dict for relation validation
    # if the relation validation is of nature parent -> check its children, do not allow unconnected
    if mode_alias in ["Module Assembly", "Hybridization"]:
        validation_subset = {
            "n_valid_parts": len(valid_parts),
            "n_invalid_parts": len(invalid_parts),
            "n_fake_parts": len(fake_parts),
            "n_valid_connected_parts": 0,
            "relations_template_good": '\t??? success "Relation validation OK for these parts:"\n\n',
            "relations_template_bad": "",
        }
    # if the relation validation is of nature child -> check its parents, do track / allow unconnected (new)
    elif mode_alias == "Sensor_par":
        validation_subset = {
            "n_valid_parts": len(valid_parts),
            "n_invalid_parts": len(invalid_parts),
            "n_fake_parts": len(fake_parts),
            "n_valid_connected_parts": 0,
            "n_valid_new_parts": 0,
            "relations_template_good": '\t??? success "Relation validation OK for these parts:"\n\n',
            "relations_template_new": '\t??? example "These parts are not connected yet to a Hybrid:"\n\n',
            "relations_template_bad": "",
        }
    # Collect stats from validation results and prepare to feed into report template
    for p in valid_parts:
        this_part_id = p["part_id"]
        this_part_SN = p["serial_number"]
        if mode_alias == "Module Assembly":
            individual_part_results = relation_validation.validate_module(this_part_id)
        elif mode_alias == "Hybridization":
            individual_part_results = relation_validation.validate_hybrid(this_part_id)
        elif mode_alias == "Sensor_par":
            individual_part_results = relation_validation.validate_sensor(this_part_id)

        if individual_part_results["validation_result_overall"] == True:
            # this part only has correct connections, note down its SN / url (every part => new line)
            validation_subset["n_valid_connected_parts"] += 1
            validation_subset[
                "relations_template_good"
            ] += f'\t\t[Part {this_part_SN}]({api.frontendUrlPrefix + f"/viewparts/{this_part_id}"}).\n\n'
        else:
            if mode_alias == "Sensor_par":
                # Sensors are a special case: there are acceptable failures (sensor not used yet for a Hybrid)
                # but also non-acceptable failures (sensor not connected to parent Wafer, connection to Hybrid truly faulty)
                if individual_part_results["validation_result_S_par_HY"] == "new":
                    # could be acceptable, but need to test also against Wafer
                    if individual_part_results["validation_result_S_par_W"] == True:
                        # connection to parent Wafer is fine, but this part has not been connected yet to HY parent(s), OK during production (every part => new line)
                        validation_subset["n_valid_new_parts"] += 1
                        validation_subset[
                            "relations_template_new"
                        ] += f'\t\t[Part {this_part_SN}]({api.frontendUrlPrefix + f"/viewparts/{this_part_id}"}).\n\n'
                    else:
                        # not yet connected to HY, but no connection to Wafer parent, which is not acceptable
                        validation_subset[
                            "relations_template_bad"
                        ] += f"""\t??? failure "Relation validation failed for {this_part_SN}:"\n
\t\tInspect this [part {this_part_SN}]({api.frontendUrlPrefix + f"/viewparts/{this_part_id}"}) in DB.\n
\t\tDetailed failure reason:\n
"""
                        validation_subset["relations_template_bad"] += (
                            "\t\t"
                            + individual_part_results["validation_reason_S_par_W"]
                            + "\n\n"
                        )
                elif individual_part_results["validation_result_S_par_HY"] == False:
                    # validation failed and at least the connection to Hybrid is truly faulty (wrong position, or more than one connection)
                    validation_subset[
                        "relations_template_bad"
                    ] += f"""\t??? failure "Relation validation failed for {this_part_SN}:"\n
\t\tInspect this [part {this_part_SN}]({api.frontendUrlPrefix + f"/viewparts/{this_part_id}"}) in DB.\n
\t\tDetailed failure reason:\n
"""
                    validation_subset["relations_template_bad"] += (
                        "\t\t"
                        + individual_part_results["validation_reason_S_par_HY"]
                        + "\n\n"
                    )
                    if individual_part_results["validation_result_S_par_W"] == False:
                        validation_subset["relations_template_bad"] += (
                            "\t\t"
                            + individual_part_results["validation_reason_S_par_W"]
                            + "\n\n"
                        )
                elif individual_part_results["validation_result_S_par_HY"] == True:
                    # relation validation to Hybrid is OK, test against Wafer
                    if individual_part_results["validation_result_S_par_W"] == False:
                        validation_subset[
                            "relations_template_bad"
                        ] += f"""\t??? failure "Relation validation failed for {this_part_SN}:"\n
\t\tInspect this [part {this_part_SN}]({api.frontendUrlPrefix + f"/viewparts/{this_part_id}"}) in DB.\n
\t\tDetailed failure reason:\n
"""
                        validation_subset["relations_template_bad"] += (
                            "\t\t"
                            + individual_part_results["validation_reason_S_par_W"]
                            + "\n\n"
                        )
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
                elif mode_alias == "Hybridization":
                    # Currently, only check the 1-1 relation to sensors, in the future, also ASICs!
                    if individual_part_results["validation_result_HY_chi_S"] == False:
                        validation_subset["relations_template_bad"] += (
                            "\t\t"
                            + individual_part_results["validation_reason_HY_chi_S"]
                            + "\n\n"
                        )

    if validation_subset["n_valid_connected_parts"] == 0:
        validation_subset["relations_template_good"] = (
            '\t!!! warning "Not a single relation validation passed!"\n\n'
        )
    if mode_alias == "Sensor_par":
        if validation_subset["n_valid_new_parts"] == 0:
            validation_subset["relations_template_new"] = (
                '\t!!! info "No new Sensors not yet connected to HY."\n\n'
            )
    return validation_subset


def prepare_validation_per_mode(mode_alias, manufacturers=None):
    validation_all = {}
    if mode_alias in ["Module Assembly", "Hybridization", "Sensor_par"]:
        if mode_alias == "Module Assembly":
            category = "Module"
            filename_postfix_mode_alias = "MA"
            extra_text_mode_alias = "Module Assembly: Modules"
        elif mode_alias == "Hybridization":
            category = "Hybrid"
            filename_postfix_mode_alias = "HY"
            extra_text_mode_alias = "Hybridization: Hybrids"
        elif mode_alias == "Sensor_par":
            category = "Sensor"
            filename_postfix_mode_alias = "S"
            extra_text_mode_alias = "Sensors"

        # Find all relevant parts of category under investigation
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
            "contributions_valid": contributions_valid_all,
            "n_valid_parts": sum(contributions_valid_all),
            "contributions_valid_connected": contributions_valid_connected_all,
            "n_valid_connected_parts": sum(contributions_valid_connected_all),
            "n_invalid_parts": sum(
                validation_all[m]["n_invalid_parts"] for m in manufacturers
            ),
            "n_fake_parts": sum(
                validation_all[m]["n_fake_parts"] for m in manufacturers
            ),
        }
        if mode_alias == "Sensor_par":
            contributions_new_all = [
                validation_all[m]["n_valid_new_parts"] for m in manufacturers
            ]
            validation_all["all"]["contributions_valid_new"] = contributions_new_all
            validation_all["all"]["n_valid_new_parts"] = sum(contributions_new_all)
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
        if mode_alias == "Sensor_par":
            ## All **new** parts, contributions by manufacturer
            plotter.pie_chart(
                data=validation_all["all"]["contributions_valid_new"],
                text_labels=manufacturers,
                filename_postfix=filename_postfix_mode_alias + "_valid_new_all",
                exp_text=exp_text,
                subtitle=subtitle,
                extra_text=extra_text_mode_alias
                + " (valid & new, not connected yet to Hybrid, but to Wafer). ",
            )
    return validation_all


# fill in report into template
validation_template = templates.validation_header()

for mode_alias in mode_aliases:
    if mode_alias == "Module Assembly":
        manufacturers = data.MA_sites_to_monitor
    elif mode_alias == "Hybridization":
        manufacturers = data.HY_sites_to_monitor
    elif mode_alias == "Sensor_par":
        manufacturers = data.S_W_manus_to_monitor
    else:
        manufacturers = []  # not implemented, but to use same pattern
    if single_manufacturer != None:
        manufacturers = [single_manufacturer]
    validation_all = prepare_validation_per_mode(mode_alias, manufacturers)
    if mode_alias == "Module Assembly":
        validation_template += templates.module_assembly_intro()
        validation_template += templates.module_assembly_all(
            manufacturers,
            validation_all["all"]["n_valid_parts"],
            validation_all["all"]["n_valid_connected_parts"],
            validation_all["all"]["n_invalid_parts"],
            validation_all["all"]["n_fake_parts"],
        )
        for m in manufacturers:
            validation_template += f"""??? note "{m}"

    Valid Modules (using latest SN spec, excludes Digital Modules marked with _Digital in Name Label): {validation_all[m]["n_valid_parts"]}, of which correctly connected with children (MF, HY): {validation_all[m]["n_valid_connected_parts"]}

    Invalid Modules (not using latest SN spec, and including Digital Modules marked with _Digital in Name Label): {validation_all[m]["n_invalid_parts"]}

    Fake Modules: {validation_all[m]["n_fake_parts"]}

    Details:

{validation_all[m]["relations_template_good"]}
{validation_all[m]["relations_template_bad"]}
"""
    elif mode_alias == "Hybridization":
        validation_template += templates.hybridization_intro()
        validation_template += templates.hybridization_all(
            manufacturers,
            validation_all["all"]["n_valid_parts"],
            validation_all["all"]["n_valid_connected_parts"],
            validation_all["all"]["n_invalid_parts"],
            validation_all["all"]["n_fake_parts"],
        )
        for m in manufacturers:
            validation_template += f"""??? note "{m}"

    Valid Hybrids (using latest SN spec): {validation_all[m]["n_valid_parts"]}, of which correctly connected with children (currently checking only S): {validation_all[m]["n_valid_connected_parts"]}

    Invalid Hybrids (not using latest SN spec): {validation_all[m]["n_invalid_parts"]}

    Fake Hybrids: {validation_all[m]["n_fake_parts"]}

    Details:

{validation_all[m]["relations_template_good"]}
{validation_all[m]["relations_template_bad"]}
"""
    elif mode_alias == "Sensor_par":
        validation_template += templates.sensor_par_intro()
        validation_template += templates.sensor_par_all(
            manufacturers,
            validation_all["all"]["n_valid_parts"],
            validation_all["all"]["n_valid_connected_parts"],
            validation_all["all"]["n_invalid_parts"],
            validation_all["all"]["n_fake_parts"],
            validation_all["all"]["n_valid_new_parts"],
        )
        for m in manufacturers:
            validation_template += f"""??? note "{m}"

    Valid Sensors (using latest SN spec): {validation_all[m]["n_valid_parts"]}, of which correctly connected with parent HY + W: {validation_all[m]["n_valid_connected_parts"]}; or of which correctly connected with parent W, but not yet to HY: {validation_all[m]["n_valid_new_parts"]}

    Invalid Sensors (not using latest SN spec): {validation_all[m]["n_invalid_parts"]}

    Fake Sensors: {validation_all[m]["n_fake_parts"]}

    Details:

{validation_all[m]["relations_template_good"]}
{validation_all[m]["relations_template_new"]}
{validation_all[m]["relations_template_bad"]}
"""

with open("validation.md", "w") as f:
    f.write(validation_template)

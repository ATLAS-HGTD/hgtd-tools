"""CLI for reporting (relation validation) — the "Law & Order" report.

All counting and validation lives in parts_query; this file only turns the
results into the Markdown report, the pie charts and the per-part link lists.
"""

from argparse import ArgumentParser

from hgtd_tools import api, parts_query, plotter, templates, util

# mode alias -> (Kind of Part, filename postfix, plot label prefix)
MODES = {
    "Module Loading": ("Detector Unit", "ML", "Module Loading: Detector Units"),
    "Module Assembly": ("Module", "MA", "Module Assembly: Modules"),
    "Hybridization": ("Hybrid", "HY", "Hybridization: Hybrids"),
    "Sensor_Parents": ("Sensor", "S", "Sensors"),
}

ALL_MODES = list(MODES)

FAILURE_BLOCK = """\t??? failure "Relation validation failed for {sn}:"\n
\t\tInspect this [part {sn}]({link}) in DB.\n
\t\tDetailed failure reason:\n
"""


def part_link(part_id):
    return f"{api.frontendUrlPrefix}/viewparts/{int(part_id)}"


def _reason(result, key):
    return "\t\t" + str(result.get("validation_reason_" + key, "")) + "\n\n"


def build_markdown_subset(valid_parts, invalid_parts, fake_parts, raw, mode_alias):
    """The per-manufacturer dict the report templates expect."""
    if mode_alias in ("Module Loading", "Module Assembly", "Hybridization"):
        subset = {
            "n_valid_parts": len(valid_parts),
            "n_invalid_parts": len(invalid_parts),
            "n_fake_parts": len(fake_parts),
            "n_valid_connected_parts": 0,
            "relations_template_good": '\t??? success "Relation validation OK for these parts:"\n\n',
            "relations_template_bad": "",
        }
    else:
        subset = {
            "n_valid_parts": len(valid_parts),
            "n_invalid_parts": len(invalid_parts),
            "n_fake_parts": len(fake_parts),
            "n_valid_connected_parts": 0,
            "n_valid_new_parts": 0,
            "relations_template_good": '\t??? success "Relation validation OK for these parts:"\n\n',
            "relations_template_new": '\t??? example "These parts are not connected yet to a Hybrid:"\n\n',
            "relations_template_bad": "",
        }

    def bad_block(sn, pid):
        return FAILURE_BLOCK.format(sn=sn, link=part_link(pid))

    for p in valid_parts:
        pid = int(p["part_id"])
        sn = p["serial_number"]
        result = raw.get(pid, {"validation_error": "not validated"})

        if result.get("validation_result_overall"):
            subset["n_valid_connected_parts"] += 1
            subset["relations_template_good"] += f"\t\t[Part {sn}]({part_link(pid)}).\n\n"
            continue

        if mode_alias == "Sensor_Parents":
            to_hy = result.get("validation_result_S_par_HY")
            to_w = result.get("validation_result_S_par_W")
            if to_hy == "new":
                if to_w:
                    # Wafer parent fine, not yet mounted on a Hybrid: acceptable
                    subset["n_valid_new_parts"] += 1
                    subset["relations_template_new"] += f"\t\t[Part {sn}]({part_link(pid)}).\n\n"
                else:
                    subset["relations_template_bad"] += bad_block(sn, pid)
                    subset["relations_template_bad"] += _reason(result, "S_par_W")
            elif not to_hy:
                subset["relations_template_bad"] += bad_block(sn, pid)
                subset["relations_template_bad"] += _reason(result, "S_par_HY")
                if not to_w:
                    subset["relations_template_bad"] += _reason(result, "S_par_W")
            elif to_hy and not to_w:
                subset["relations_template_bad"] += bad_block(sn, pid)
                subset["relations_template_bad"] += _reason(result, "S_par_W")
        else:
            subset["relations_template_bad"] += bad_block(sn, pid)
            for key in parts_query.CHILD_CHECKS[mode_alias]:
                if not result.get("validation_result_" + key):
                    subset["relations_template_bad"] += _reason(result, key)

    if subset["n_valid_connected_parts"] == 0:
        subset["relations_template_good"] = (
            '\t!!! warning "Not a single relation validation passed!"\n\n'
        )
    if mode_alias == "Sensor_Parents" and subset["n_valid_new_parts"] == 0:
        subset["relations_template_new"] = (
            '\t!!! info "No new Sensors not yet connected to HY."\n\n'
        )
    return subset


def prepare_validation_per_mode(
    mode_alias,
    manufacturers,
    max_workers=4,
    dev=False,
    subtitle=True,
    exp_text="Production Database",
):
    """Counts, Markdown subsets and pie charts for one validation mode."""
    category, postfix, extra_text = MODES[mode_alias]

    parts, _ = parts_query.load_parts(category)
    per_site = parts_query.parts_by_site(parts, manufacturers)

    validation_all = {}
    for manu in manufacturers:
        subset_parts = per_site[manu]
        if dev:
            subset_parts = subset_parts[:10]
        valid, invalid, fake = parts_query.split_by_sn(subset_parts, mode_alias)
        raw = parts_query.validate_parts(valid, mode_alias, max_workers=max_workers)
        validation_all[manu] = build_markdown_subset(valid, invalid, fake, raw, mode_alias)

    contributions_valid = [validation_all[m]["n_valid_parts"] for m in manufacturers]
    contributions_connected = [validation_all[m]["n_valid_connected_parts"] for m in manufacturers]
    validation_all["all"] = {
        "contributions_valid": contributions_valid,
        "n_valid_parts": sum(contributions_valid),
        "contributions_valid_connected": contributions_connected,
        "n_valid_connected_parts": sum(contributions_connected),
        "n_invalid_parts": sum(validation_all[m]["n_invalid_parts"] for m in manufacturers),
        "n_fake_parts": sum(validation_all[m]["n_fake_parts"] for m in manufacturers),
    }
    if mode_alias == "Sensor_Parents":
        contributions_new = [validation_all[m]["n_valid_new_parts"] for m in manufacturers]
        validation_all["all"]["contributions_valid_new"] = contributions_new
        validation_all["all"]["n_valid_new_parts"] = sum(contributions_new)

    # pie charts: legend order follows `manufacturers`, so do NOT use build_groups here
    plotter.pie_chart(
        data=validation_all["all"]["contributions_valid"],
        text_labels=manufacturers,
        filename_postfix=postfix + "_valid_all",
        exp_text=exp_text,
        subtitle=subtitle,
        extra_text=extra_text + " (valid). ",
    )
    plotter.pie_chart(
        data=validation_all["all"]["contributions_valid_connected"],
        text_labels=manufacturers,
        filename_postfix=postfix + "_valid_connected_all",
        exp_text=exp_text,
        subtitle=subtitle,
        extra_text=extra_text + " (valid & correctly connected). ",
    )
    if mode_alias == "Sensor_Parents":
        plotter.pie_chart(
            data=validation_all["all"]["contributions_valid_new"],
            text_labels=manufacturers,
            filename_postfix=postfix + "_valid_new_all",
            exp_text=exp_text,
            subtitle=subtitle,
            extra_text=extra_text + " (valid & new, not connected yet to Hybrid, but to Wafer). ",
        )
    return validation_all


def _manufacturers_for(mode_alias, single_manufacturer=None):
    if single_manufacturer is not None:
        return [single_manufacturer]
    return list(parts_query.MONITORED_SITES[mode_alias])


def main():
    parser = ArgumentParser("CLI for reporting (relation validation)")
    parser.add_argument(
        "--mode-alias",
        dest="mode_alias",
        help="Validation mode alias. (Default: %(default)s)",
        default="all",
        choices=ALL_MODES + ["all"],
    )
    parser.add_argument(
        "--single-manufacturer",
        dest="single_manufacturer",
        help="[Optional] Single manufacturer short name for which to run validation. "
        "Overrides default list associated with mode-alias. Useful during development.",
        default=None,
    )
    parser.add_argument(
        "--dev",
        dest="dev",
        help="[Optional] Developer mode. Limit number of parts to process.",
        default=False,
    )
    parser.add_argument(
        "--merge",
        dest="merge",
        help="[Optional] If validation is split into multiple modes, use this to merge "
        "the results into a common md file. You must have run all individual modes "
        "first one-by-one to collect the results.",
        default=False,
    )
    parser.add_argument(
        "--subtitle",
        dest="subtitle",
        help="[Optional] Add a subtitle with SN validity category and used hgtd-tools "
        "commit + date of generation.",
        default=True,
    )
    parser.add_argument(
        "--custom-text",
        dest="customText",
        help="[Optional] Replace Production Database text in plot label with your custom "
        "text (e.g. Preliminary, Internal...).",
        default=None,
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=4,
        metavar="N",
        help="[Optional] Threads for the per-part validation calls. (Default: %(default)s)",
    )
    args = parser.parse_args()

    mode_alias = args.mode_alias
    single_manufacturer = args.single_manufacturer
    dev = util.str2bool(args.dev)
    merge = util.str2bool(args.merge)
    subtitle = util.str2bool(args.subtitle)
    exp_text = args.customText if args.customText is not None else "Production Database"

    if mode_alias == "all":
        mode_aliases = list(ALL_MODES)
    else:
        mode_aliases = [mode_alias]

    # fill in report into template
    if merge:
        validation_template = templates.validation_header()
        for postfix in ("ML", "MA", "HY", "SP"):
            with open(f"validation_{postfix}.md", "r") as pre_computed:
                for line in pre_computed:
                    validation_template += line
        with open("validation.md", "w") as f:
            f.write(validation_template)
        return

    validation_template = templates.validation_header()

    for mode_alias in mode_aliases:
        manufacturers = _manufacturers_for(mode_alias, single_manufacturer)
        validation_all = prepare_validation_per_mode(
            mode_alias,
            manufacturers,
            max_workers=args.max_workers,
            dev=dev,
            subtitle=subtitle,
            exp_text=exp_text,
        )
        single_mode = len(mode_aliases) == 1

        if mode_alias == "Module Loading":
            ML_intro = templates.module_loading_intro()
            validation_template += ML_intro
            if single_mode:
                validation_ML = ML_intro
            ML_all = templates.module_loading_all(
                manufacturers,
                validation_all["all"]["n_valid_parts"],
                validation_all["all"]["n_valid_connected_parts"],
                validation_all["all"]["n_invalid_parts"],
                validation_all["all"]["n_fake_parts"],
            )
            validation_template += ML_all
            if single_mode:
                validation_ML += ML_all
            for m in manufacturers:
                ML_m = f"""??? note "{m}"

    Valid Detector Units (using latest SN spec): {validation_all[m]["n_valid_parts"]}, of which correctly connected with children (Modules at the expected DU positions): {validation_all[m]["n_valid_connected_parts"]}

    Invalid Detector Units (not using latest SN spec): {validation_all[m]["n_invalid_parts"]}

    Fake Detector Units: {validation_all[m]["n_fake_parts"]}

    Details:

{validation_all[m]["relations_template_good"]}
{validation_all[m]["relations_template_bad"]}
"""
                validation_template += ML_m
                if single_mode:
                    validation_ML += ML_m
            if single_mode:
                with open("validation_ML.md", "w") as f:
                    f.write(validation_ML)

        elif mode_alias == "Module Assembly":
            MA_intro = templates.module_assembly_intro()
            validation_template += MA_intro
            if single_mode:
                validation_MA = MA_intro
            MA_all = templates.module_assembly_all(
                manufacturers,
                validation_all["all"]["n_valid_parts"],
                validation_all["all"]["n_valid_connected_parts"],
                validation_all["all"]["n_invalid_parts"],
                validation_all["all"]["n_fake_parts"],
            )
            validation_template += MA_all
            if single_mode:
                validation_MA += MA_all
            for m in manufacturers:
                MA_m = f"""??? note "{m}"

    Valid Modules (using latest SN spec, excludes Digital Modules marked with _Digital in Name Label): {validation_all[m]["n_valid_parts"]}, of which correctly connected with children (MF, HY): {validation_all[m]["n_valid_connected_parts"]}

    Invalid Modules (not using latest SN spec, and including Digital Modules marked with _Digital in Name Label): {validation_all[m]["n_invalid_parts"]}

    Fake Modules: {validation_all[m]["n_fake_parts"]}

    Details:

{validation_all[m]["relations_template_good"]}
{validation_all[m]["relations_template_bad"]}
"""
                validation_template += MA_m
                if single_mode:
                    validation_MA += MA_m
            if single_mode:
                with open("validation_MA.md", "w") as f:
                    f.write(validation_MA)

        elif mode_alias == "Hybridization":
            HY_intro = templates.hybridization_intro()
            validation_template += HY_intro
            if single_mode:
                validation_HY = HY_intro
            HY_all = templates.hybridization_all(
                manufacturers,
                validation_all["all"]["n_valid_parts"],
                validation_all["all"]["n_valid_connected_parts"],
                validation_all["all"]["n_invalid_parts"],
                validation_all["all"]["n_fake_parts"],
            )
            validation_template += HY_all
            if single_mode:
                validation_HY += HY_all
            for m in manufacturers:
                HY_m = f"""??? note "{m}"

    Valid Hybrids (using latest SN spec): {validation_all[m]["n_valid_parts"]}, of which correctly connected with children (currently checking only S): {validation_all[m]["n_valid_connected_parts"]}

    Invalid Hybrids (not using latest SN spec): {validation_all[m]["n_invalid_parts"]}

    Fake Hybrids: {validation_all[m]["n_fake_parts"]}

    Details:

{validation_all[m]["relations_template_good"]}
{validation_all[m]["relations_template_bad"]}
"""
                validation_template += HY_m
                if single_mode:
                    validation_HY += HY_m
            if single_mode:
                with open("validation_HY.md", "w") as f:
                    f.write(validation_HY)

        elif mode_alias == "Sensor_Parents":
            SP_intro = templates.sensor_par_intro()
            validation_template += SP_intro
            if single_mode:
                validation_SP = SP_intro
            SP_all = templates.sensor_par_all(
                manufacturers,
                validation_all["all"]["n_valid_parts"],
                validation_all["all"]["n_valid_connected_parts"],
                validation_all["all"]["n_invalid_parts"],
                validation_all["all"]["n_fake_parts"],
                validation_all["all"]["n_valid_new_parts"],
            )
            validation_template += SP_all
            if single_mode:
                validation_SP += SP_all
            for m in manufacturers:
                SP_m = f"""??? note "{m}"

    Valid Sensors (using latest SN spec): {validation_all[m]["n_valid_parts"]}, of which correctly connected with parent HY + W: {validation_all[m]["n_valid_connected_parts"]}; or of which correctly connected with parent W, but not yet to HY: {validation_all[m]["n_valid_new_parts"]}

    Invalid Sensors (not using latest SN spec): {validation_all[m]["n_invalid_parts"]}

    Fake Sensors: {validation_all[m]["n_fake_parts"]}

    Details:

{validation_all[m]["relations_template_good"]}
{validation_all[m]["relations_template_new"]}
{validation_all[m]["relations_template_bad"]}
"""
                validation_template += SP_m
                if single_mode:
                    validation_SP += SP_m
            if single_mode:
                with open("validation_SP.md", "w") as f:
                    f.write(validation_SP)

    with open("validation.md", "w") as f:
        f.write(validation_template)


if __name__ == "__main__":
    main()

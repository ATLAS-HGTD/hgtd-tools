# standard package imports and default ATLAS style
import json
import os
from argparse import ArgumentParser
from collections import Counter

import numpy as np
import pandas as pd

import data
import plotter
import util


# === CONFIGURATION FOR DATA ACCESS ===
parser = ArgumentParser("CLI for reporting (parts stats)")
parser.add_argument(
    "--categories",
    dest="categories",
    help="[Optional] Use all or a limited set of categories [None, public, test].",
    default=None,
)
parser.add_argument(
    "--skip-data-prep",
    dest="skipDataPrep",
    help="[Optional] Do not run the actual requests to the DB, pick existing data.",
    default=False,
)
parser.add_argument(
    "--subtitle",
    dest="subtitle",
    help="[Optional] Add a subtitle with SN category and commit + date of generation.",
    default=True,
)
parser.add_argument(
    "--custom-text",
    dest="customText",
    help="[Optional] Replace Production Database text in plot label with your custom text (e.g. Preliminary, Internal...).",
    default=None,
)
parser.add_argument(
    "--log-axis",
    dest="logAxis",
    help="[Optional] Use logarithmic y-axis instead of linear.",
    default=False,
)
args = parser.parse_args()

all_cats = [
    "Sensor",
    "Wafer",
    "ASIC",
    "Hybrid",
    "Module Flex",
    "Module",
    "Support Unit",
    "Detector Unit",
    "PEB",
    "PEB_MUX64",
    "Flex Tail",
    "HV_PS",
    "HV_module",
]
public_cats = [
    "Sensor",
    "Wafer",
    # "ASIC", add them back when significant portion is uploaded
    "Hybrid",
    "Module Flex",
    "Module",
    "Support Unit",
    "Detector Unit",
    "PEB",
    # "PEB_MUX64", add them back when significant portion is uploaded
    "Flex Tail",
    "HV_PS",
    "HV_module",
]
test_cats = [
    "HV_PS",
    "HV_module",
]
if args.categories == None:
    categories = all_cats
elif args.categories == "public":
    categories = public_cats
elif args.categories == "test":
    categories = test_cats

skip_data_prep = util.str2bool(args.skipDataPrep)
subtitle = util.str2bool(args.subtitle)
exp_text = args.customText if args.customText != None else "Production Database"
log_axis = util.str2bool(args.logAxis)

interesting_features = [
    "Location",
    "Manufacturer",
    "Uploaded by",
    "Uploaded in YYYY-MM",
]

if not skip_data_prep:
    if os.path.exists("output_invalid.txt"):
        os.remove("output_invalid.txt")
    parts_in_categories = {c: util.get_relevant_parts(c)[0] for c in categories}

    interesting_data_all_cats_invalid = {c: dict() for c in categories}
    interesting_data_all_cats_valid = {c: dict() for c in categories}
    interesting_data_all_cats_fakes = {c: dict() for c in categories}
    for c in categories:
        interesting_data_per_c_invalid = {f: [] for f in interesting_features}
        interesting_data_per_c_valid = {f: [] for f in interesting_features}
        interesting_data_per_c_fakes = {f: [] for f in interesting_features}
        for p in parts_in_categories[c]:
            if str(p["serial_number"][:3]) == "20W":
                check_SN_boolean, check_SN_message = util.check_SN_valid(
                    str(p["serial_number"][:])
                )
                if check_SN_boolean:
                    if "Location" in interesting_features:
                        interesting_data_per_c_valid["Location"].append(
                            p["location"]["location_name"]
                        )
                    if "Manufacturer" in interesting_features:
                        interesting_data_per_c_valid["Manufacturer"].append(
                            p["manufacturer"]["manufacturer_name"]
                        )
                    if "Uploaded by" in interesting_features:
                        interesting_data_per_c_valid["Uploaded by"].append(
                            p["record_insertion_user"]
                        )
                    if "Uploaded in YYYY-MM" in interesting_features:
                        time = p["record_insertion_time"]
                        if time == None:
                            interesting_data_per_c_valid["Uploaded in YYYY-MM"].append(
                                "Unknown"
                            )
                        else:
                            interesting_data_per_c_valid["Uploaded in YYYY-MM"].append(
                                p["record_insertion_time"][:7]
                            )
                else:
                    if "Location" in interesting_features:
                        interesting_data_per_c_invalid["Location"].append(
                            p["location"]["location_name"]
                        )
                    if "Manufacturer" in interesting_features:
                        interesting_data_per_c_invalid["Manufacturer"].append(
                            p["manufacturer"]["manufacturer_name"]
                        )
                    if "Uploaded by" in interesting_features:
                        interesting_data_per_c_invalid["Uploaded by"].append(
                            p["record_insertion_user"]
                        )
                    if "Uploaded in YYYY-MM" in interesting_features:
                        time = p["record_insertion_time"]
                        if time == None:
                            interesting_data_per_c_invalid[
                                "Uploaded in YYYY-MM"
                            ].append("Unknown")
                        else:
                            interesting_data_per_c_invalid[
                                "Uploaded in YYYY-MM"
                            ].append(p["record_insertion_time"][:7])
                    with open("output_invalid.txt", "a") as invalid_txt:
                        invalid_txt.write(
                            str(p["serial_number"][:]) + ": " + check_SN_message + "\n"
                        )
            else:
                if "Location" in interesting_features:
                    interesting_data_per_c_fakes["Location"].append(
                        p["location"]["location_name"]
                    )
                if "Manufacturer" in interesting_features:
                    interesting_data_per_c_fakes["Manufacturer"].append(
                        p["manufacturer"]["manufacturer_name"]
                    )
                if "Uploaded by" in interesting_features:
                    interesting_data_per_c_fakes["Uploaded by"].append(
                        p["record_insertion_user"]
                    )
                if "Uploaded in YYYY-MM" in interesting_features:
                    time = p["record_insertion_time"]
                    if time == None:
                        interesting_data_per_c_fakes["Uploaded in YYYY-MM"].append(
                            "Unknown"
                        )
                    else:
                        interesting_data_per_c_fakes["Uploaded in YYYY-MM"].append(
                            p["record_insertion_time"][:7]
                        )
        interesting_data_all_cats_invalid[c] = interesting_data_per_c_invalid
        interesting_data_all_cats_valid[c] = interesting_data_per_c_valid
        interesting_data_all_cats_fakes[c] = interesting_data_per_c_fakes

    multi_count_dict_invalid = {
        c: {f: dict() for f in interesting_features} for c in categories
    }
    multi_count_dict_valid = {
        c: {f: dict() for f in interesting_features} for c in categories
    }
    multi_count_dict_valid = {
        c: {f: dict() for f in interesting_features} for c in categories
    }
    multi_count_dict_fakes = {
        c: {f: dict() for f in interesting_features} for c in categories
    }
    for c in categories:
        for f in interesting_features:
            multi_count_dict_invalid[c][f] = dict(
                Counter(interesting_data_all_cats_invalid[c][f]).items()
            )
            multi_count_dict_valid[c][f] = dict(
                Counter(interesting_data_all_cats_valid[c][f]).items()
            )
            multi_count_dict_valid[c][f] = dict(
                Counter(interesting_data_all_cats_valid[c][f]).items()
            )
            multi_count_dict_fakes[c][f] = dict(
                Counter(interesting_data_all_cats_fakes[c][f]).items()
            )

    with open("report_stats_invalid.json", "w") as rep_data_f:
        json.dump(multi_count_dict_invalid, rep_data_f)
    with open("report_stats_valid.json", "w") as rep_data_f:
        json.dump(multi_count_dict_valid, rep_data_f)
    with open("report_stats_fakes.json", "w") as rep_data_f:
        json.dump(multi_count_dict_fakes, rep_data_f)
else:
    with open("report_stats_invalid.json") as invalidJson:
        multi_count_dict_invalid = json.load(invalidJson)
    with open("report_stats_valid.json") as validJson:
        multi_count_dict_valid = json.load(validJson)
    with open("report_stats_fakes.json") as fakesJson:
        multi_count_dict_fakes = json.load(fakesJson)


def batch_yield_plot(
    input_dict, postfix="valid", title_prefix="Serial Numbers starting with 20W only. "
):
    """
    Given a multi-dimensional input dictionary (with outer dimension the
    categories, and inner dimension the features), this creates plots for counts
     / fractions.
    """
    for feature_legend_title in interesting_features:
        # merge the legend entries from different categories (i.e. Locations
        # for Sensors, Locations for Modules...)

        all_legend_entries = sorted(
            list(
                set(
                    util.flatten(
                        [
                            list(input_dict[c][feature_legend_title].keys())
                            for c in categories
                        ]
                    )
                )
            )
        )

        # need to fill the set of possible legend entries with new values (old
        # and fill with 0)
        values = []
        fractions = []
        for c in categories:
            values_list_this_c = []
            fractions_list_this_c = []
            for sc in all_legend_entries:
                if sc in input_dict[c][feature_legend_title].keys():
                    values_list_this_c.append(input_dict[c][feature_legend_title][sc])
                    fractions_list_this_c.append(
                        input_dict[c][feature_legend_title][sc]
                        / sum(input_dict[c][feature_legend_title].values())
                    )
                else:
                    values_list_this_c.append(0)
                    fractions_list_this_c.append(0)
            values.append(values_list_this_c)
            fractions.append(fractions_list_this_c)
        values = np.array(values)
        fractions = np.array(fractions)

        plotter.plot_categorical_bar_stack(
            values,
            "counts",
            categories,
            all_legend_entries,
            feature_legend_title,
            exp_text,
            title_prefix,
            subtitle,
            log_axis,
            postfix,
        )
        plotter.plot_categorical_bar_stack(
            fractions,
            "fractions",
            categories,
            all_legend_entries,
            feature_legend_title,
            exp_text,
            title_prefix,
            subtitle,
            log_axis,
            postfix,
        )

        if feature_legend_title == "Uploaded in YYYY-MM":
            # set of sorted months
            if all_legend_entries[-1] == "Unknown":
                consecutive_months = (
                    pd.date_range(
                        all_legend_entries[0], all_legend_entries[-2], freq="MS"
                    )
                    .strftime("%Y-%m")
                    .tolist()
                )
            else:
                consecutive_months = (
                    pd.date_range(
                        all_legend_entries[0], all_legend_entries[-1], freq="MS"
                    )
                    .strftime("%Y-%m")
                    .tolist()
                )

            x_values = []
            newly_uploaded = []
            cumulative_counts = []
            for c in categories:
                x_values_list_this_c = []
                newly_uploaded_list_this_c = []
                # add the number of parts which have unknown entry date first
                # to populate first real entry, then add consecutively on top
                if "Unknown" in list(input_dict[c]["Uploaded in YYYY-MM"].keys()):
                    # extreme edge case for sensors, developed early without
                    # all part details we have nowadays (item without date)
                    cumulative_counts_list_this_c = [
                        input_dict[c]["Uploaded in YYYY-MM"]["Unknown"]
                    ]
                # if all entry dates known, add 0 as first item to which
                # more gets added month by month
                else:
                    cumulative_counts_list_this_c = [0]
                for sc in reversed(input_dict[c]["Uploaded in YYYY-MM"].keys()):
                    if sc in consecutive_months:
                        x_values_list_this_c.append(consecutive_months.index(sc))
                        newly_uploaded_list_this_c.append(
                            input_dict[c]["Uploaded in YYYY-MM"][sc]
                        )
                        cumulative_counts_list_this_c.append(
                            cumulative_counts_list_this_c[-1]
                            + newly_uploaded_list_this_c[-1]
                        )
                x_values.append(x_values_list_this_c)
                newly_uploaded.append(newly_uploaded_list_this_c)
                cumulative_counts.append(cumulative_counts_list_this_c[1:])

            # also create a time trend, as PDF and CDF (i.e. cumulative as well)
            plotter.plot_multi_categorical_time_trend(
                x_values,
                newly_uploaded,
                "newly_uploaded",
                categories,
                consecutive_months,
                exp_text,
                title_prefix + "\n",
                subtitle,
                log_axis,
                postfix,
            )
            plotter.plot_multi_categorical_time_trend(
                x_values,
                cumulative_counts,
                "cumulative_counts",
                categories,
                consecutive_months,
                exp_text,
                title_prefix + "\n",
                subtitle,
                log_axis,
                postfix,
            )


batch_yield_plot(
    input_dict=multi_count_dict_invalid,
    postfix="invalid",
    title_prefix="Serial Numbers starting with 20W, NOT fulfilling the ATLAS convention. ",
)
batch_yield_plot(
    input_dict=multi_count_dict_fakes,
    postfix="fakes",
    title_prefix="Serial Numbers NOT starting with 20W. ",
)
batch_yield_plot(
    input_dict=multi_count_dict_valid,
    postfix="valid",
    title_prefix="Serial Numbers starting with 20W, fulfilling the ATLAS convention. ",
)

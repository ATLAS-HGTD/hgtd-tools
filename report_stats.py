# standard package imports and default ATLAS style
import json
from argparse import ArgumentParser
from collections import Counter
from datetime import datetime

import matplotlib as mpl
import matplotlib.pyplot as plt
import mplhep as hep
import numpy as np
from cycler import cycler

import data
import util

color_sequence1 = [
    "#3f90da",
    "#ffa90e",
    "#bd1f01",
    "#94a4a2",
    "#832db6",
    "#a96b59",
    "#e76300",
    "#b9ac70",
    "#717581",
    "#92dadd",
]
color_sequence2 = [
    "#d55e00",
    "#56b4e9",
    "#e69f00",
    "#f0e442",
    "#009e73",
    "#cc79a7",
    "#0072b2",
]
combination_color_sequence = color_sequence1 + color_sequence2


colors_tab20c = mpl.color_sequences["tab20c"]


# ATLAS plot style
hep.style.use("ATLAS1")
plt.rcParams["axes.axisbelow"] = True
plt.rcParams["axes.prop_cycle"] = cycler(
    "color", colors_tab20c + combination_color_sequence
)


# === CONFIGURATION FOR DATA ACCESS ===
parser = ArgumentParser("CLI for SN reservation, targeted at Module Assembly")
parser.add_argument(
    "--testrun",
    dest="testrun",
    help="[Optional] Only test running with a very limited set of categories.",
    default=False,
)
args = parser.parse_args()
testrun = args.testrun

categories = (
    [
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
    if not testrun
    else [
        "HV_PS",
        "HV_module",
    ]
)
interesting_features = [
    "Location",
    "Manufacturer",
    "Uploaded by",
    "Uploaded in YYYY-MM",
]

parts_in_categories = {c: util.get_relevant_parts(c)[0] for c in categories}

interesting_data_all_cats = {c: dict() for c in categories}
for c in categories:
    interesting_data_per_c = {f: [] for f in interesting_features}
    for p in parts_in_categories[c]:
        if str(p["serial_number"][:3]) != "20W":
            continue
        if "Location" in interesting_features:
            interesting_data_per_c["Location"].append(p["location"]["location_name"])
        if "Manufacturer" in interesting_features:
            interesting_data_per_c["Manufacturer"].append(
                p["manufacturer"]["manufacturer_name"]
            )
        if "Uploaded by" in interesting_features:
            interesting_data_per_c["Uploaded by"].append(p["record_insertion_user"])
        if "Uploaded in YYYY-MM" in interesting_features:
            time = p["record_insertion_time"]
            if time == None:
                interesting_data_per_c["Uploaded in YYYY-MM"].append("Unknown")
            else:
                interesting_data_per_c["Uploaded in YYYY-MM"].append(
                    p["record_insertion_time"][:7]
                )
    interesting_data_all_cats[c] = interesting_data_per_c

multi_count_dict = {c: {f: dict() for f in interesting_features} for c in categories}
for c in categories:
    for f in interesting_features:
        multi_count_dict[c][f] = dict(Counter(interesting_data_all_cats[c][f]).items())

with open("report_stats.json", "w") as rep_data_f:
    json.dump(multi_count_dict, rep_data_f)

for f in interesting_features:
    # merge the legend entries from different categories (i.e. Locations for Sensors, Locations for Modules...)

    all_legend_entries = sorted(
        list(
            set(util.flatten([list(multi_count_dict[c][f].keys()) for c in categories]))
        )
    )

    # need to fill the set of possible legend entries with new values (old and fill with 0)
    values = []
    fractions = []
    for c in categories:
        values_list_this_c = []
        fractions_list_this_c = []
        for sc in all_legend_entries:
            if sc in multi_count_dict[c][f].keys():
                values_list_this_c.append(multi_count_dict[c][f][sc])
                fractions_list_this_c.append(
                    multi_count_dict[c][f][sc] / sum(multi_count_dict[c][f].values())
                )
            else:
                values_list_this_c.append(0)
                fractions_list_this_c.append(0)
        values.append(values_list_this_c)
        fractions.append(fractions_list_this_c)
    values = np.array(values)
    fractions = np.array(fractions)

    # ============

    fig, ax = plt.subplots(figsize=(12, 8))

    bottom_values = np.zeros(len(categories))

    for i, subcategory in enumerate(all_legend_entries):
        ax.bar(
            [i * 0.5 for i in range(len(categories))],
            values[:, i],
            bottom=bottom_values,
            label=subcategory,
            width=0.4,
        )
        bottom_values += values[:, i]
        ax.set_xticks([i * 0.5 for i in range(len(categories))], categories)

    for tick in ax.get_xticklabels():
        tick.set_rotation(90)

    ax.set_ylabel("Number of parts")
    ax.legend(title=f)

    hep.label.exp_text(
        "ATLAS HGTD",
        "Production Database",
        f"Serial Numbers starting with 20W only. Generated with anstein/hgtd-tools~master on {datetime.today().strftime('%Y-%m-%d')}",
        loc=4,
        italic=(True, False, False),
    )
    ax.set_ylim(ax.get_ylim()[0], ax.get_ylim()[-1] * 1.05 * 1.05)
    fig.savefig(f"counts_{f}.pdf", bbox_inches="tight", facecolor="white", dpi=300)
    fig.savefig(f"counts_{f}.png", bbox_inches="tight", facecolor="white", dpi=300)

    # ============

    fig, ax = plt.subplots(figsize=(12, 8))

    bottom_values = np.zeros(len(categories))

    for i, subcategory in enumerate(all_legend_entries):
        ax.bar(
            [i * 0.5 for i in range(len(categories))],
            fractions[:, i],
            bottom=bottom_values,
            label=subcategory,
            width=0.4,
        )
        bottom_values += fractions[:, i]
        ax.set_xticks([i * 0.5 for i in range(len(categories))], categories)

    for tick in ax.get_xticklabels():
        tick.set_rotation(90)

    ax.set_ylabel("Fraction of parts")

    hep.label.exp_text(
        "ATLAS HGTD",
        "Production Database",
        f"Serial Numbers starting with 20W only. Generated with anstein/hgtd-tools~master on {datetime.today().strftime('%Y-%m-%d')}",
        loc=4,
        italic=(True, False, False),
    )
    ax.set_ylim(ax.get_ylim()[0], ax.get_ylim()[-1] * 1.05 * 1.05 * 1.05)
    fig.savefig(f"fractions_{f}.pdf", bbox_inches="tight", facecolor="white", dpi=300)
    fig.savefig(f"fractions_{f}.png", bbox_inches="tight", facecolor="white", dpi=300)

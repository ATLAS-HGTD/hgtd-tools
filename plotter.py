from datetime import datetime

import matplotlib as mpl
import matplotlib.pyplot as plt
import mplhep as hep
import numpy as np
from cycler import cycler
from matplotlib import rcParams

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


def plot_categorical_bar_stack(
    input_array,
    filename_prefix,
    categories,
    legend_entries,
    feature_legend_title,
    exp_text,
    title_prefix,
    subtitle,
    log_axis,
    postfix,
):
    plt.rcParams["axes.prop_cycle"] = cycler(
        "color", colors_tab20c + combination_color_sequence
    )
    n_categories = len(categories)
    fig, ax = plt.subplots(figsize=(12, 8))

    bottom_values = np.zeros(n_categories)

    for i, subcategory in enumerate(legend_entries):
        ax.bar(
            [i * 0.5 for i in range(n_categories)],
            input_array[:, i],
            bottom=bottom_values,
            label=subcategory,
            width=0.4,
        )
        bottom_values += input_array[:, i]
        ax.set_xticks([i * 0.5 for i in range(n_categories)], categories)

    for tick in ax.get_xticklabels():
        tick.set_rotation(90)

    if filename_prefix == "counts":
        ax.set_ylabel("Number of parts")
        if feature_legend_title == "Location":
            ax.legend(
                title=feature_legend_title,
                ncol=2,
                loc="center right",
                fontsize=rcParams["font.size"] / 1.3,
            )
        else:
            ax.legend(
                title=feature_legend_title,
                ncol=2,
                fontsize=rcParams["font.size"] / 1.3,
            )
    elif filename_prefix == "fractions":
        ax.set_ylabel("Fraction of parts")

    hep.label.exp_text(
        "ATLAS HGTD",
        " " + exp_text,
        (
            f"{title_prefix}Generated with anstein/hgtd-tools~master on {datetime.today().strftime('%Y-%m-%d')}"
            if subtitle
            else ""
        ),
        loc=4,
        fontsize=(
            rcParams["font.size"] * 1.3,
            rcParams["font.size"] * 1.3,
            rcParams["font.size"],
            rcParams["font.size"] / 1.7,
        ),
        fontstyle=("italic", "normal", "italic", "normal"),
    )
    if filename_prefix == "counts":
        if log_axis:
            ax.set_yscale("log")
    hep.utils.mpl_magic(ax, soft_fail=True)
    ax.set_xlim(
        ax.get_xlim()[0] - n_categories * 0.025,
        ax.get_xlim()[-1] + n_categories * 0.025,
    )
    fig.savefig(
        f"{filename_prefix}_{feature_legend_title}_{postfix}.pdf",
        bbox_inches="tight",
        facecolor="white",
        dpi=300,
    )
    fig.savefig(
        f"{filename_prefix}_{feature_legend_title}_{postfix}.png",
        bbox_inches="tight",
        facecolor="white",
        dpi=300,
    )
    plt.close()


def plot_multi_categorical_time_trend(
    x_values,
    y_values,
    filename_prefix,
    categories,
    all_months_for_x_axis,
    exp_text,
    title_prefix,
    subtitle,
    log_axis,
    postfix,
):
    plt.rcParams["axes.prop_cycle"] = cycler("color", combination_color_sequence)
    n_all_months_for_x_axis = len(all_months_for_x_axis)
    fig, ax = plt.subplots(figsize=(12, 8))

    for f, feature in enumerate(categories):
        ax.plot(x_values[f], y_values[f], label=feature, linestyle="-", marker="o")
    ax.set_xticks([i for i in range(n_all_months_for_x_axis)], all_months_for_x_axis)
    for tick in ax.get_xticklabels():
        tick.set_rotation(90)

    if filename_prefix == "newly_uploaded":
        ax.set_ylabel("Number of parts uploaded over time")
    elif filename_prefix == "cumulative_counts":
        ax.set_ylabel("Cumulative number of parts over time")
    ax.set_xlabel("Year and Month (YYYY-MM)")
    ax.legend(
        title="Kind of Part",
        ncol=3,
        loc="upper right",
        fontsize=rcParams["font.size"] / 1.3,
    )
    today = datetime.today().strftime("%Y-%m-%d")
    ax.grid(alpha=0.5)
    ax.grid(which="minor", alpha=0.25)
    hep.label.exp_text(
        "ATLAS HGTD",
        " " + exp_text,
        (
            f"{title_prefix}Generated with anstein/hgtd-tools~master on {today}"
            if subtitle
            else ""
        ),
        loc=4,
        fontsize=(
            rcParams["font.size"] * 1.3,
            rcParams["font.size"] * 1.3,
            rcParams["font.size"],
            rcParams["font.size"] / 1.7,
        ),
        fontstyle=("italic", "normal", "italic", "normal"),
    )
    if log_axis:
        ax.set_yscale("log")
    ax.set_ylim(
        8e-1,
        ax.get_ylim()[-1] * 1.05 * 1.05 * 1.05 * 1.05 * 1.05,
    )
    ax.set_xlim(
        -1,
        n_all_months_for_x_axis,
    )
    hep.utils.mpl_magic(ax, soft_fail=True, N=20)
    fig.savefig(
        f"{filename_prefix}_time_trend_by_KoP_{postfix}.pdf",
        bbox_inches="tight",
        facecolor="white",
        dpi=300,
    )
    fig.savefig(
        f"{filename_prefix}_time_trend_by_KoP_{postfix}.png",
        bbox_inches="tight",
        facecolor="white",
        dpi=300,
    )
    plt.close()


def iv_curves_for_sns(
    voltages,
    currents,
    labels,
    KoPs,
    exp_text,
    subtitle,
    postfix,
    lineThreshold,
    spanLabelBackground,
):
    plt.rcParams["axes.prop_cycle"] = cycler("color", combination_color_sequence)
    if len(list(set(KoPs))) > 1:
        KoP_legend = "Serial Numbers"
    else:
        if "Module" in KoPs:
            KoP_legend = "Modules"
        elif "Hybrid" in KoPs:
            KoP_legend = "Hybrids"
        elif "Sensor" in KoPs:
            KoP_legend = "Sensors"

    fig, ax = plt.subplots(figsize=(10, 8))
    for i, label in enumerate(labels):
        ax.plot(voltages[i], currents[i], label=label, linestyle="-", marker="o")

    ax.legend(
        title=KoP_legend,
        fontsize=rcParams["font.size"] / 1.3,
        facecolor="white",
        edgecolor="white",
        framealpha=1,
        frameon=True,
    )
    ax.set_xlabel("Voltage [V]")
    ax.set_ylabel("Current [A]")
    ax.set_yscale("log")
    if lineThreshold:
        ax.axhline(y=5e-5, color="gray", linestyle="-", zorder=0)
    _SNs = "_" + "_".join(labels)
    today = datetime.today().strftime("%Y-%m-%d")
    _postfix = "_" + postfix if postfix != "" else "_" + today
    ax.grid(alpha=0.5)
    ax.grid(which="minor", alpha=0.25)
    hep.label.exp_text(
        "ATLAS HGTD",
        " " + exp_text,
        (f"Generated with anstein/hgtd-tools~master on {today}" if subtitle else ""),
        loc=4,
        fontsize=(
            rcParams["font.size"] * 1.3,
            rcParams["font.size"] * 1.3,
            rcParams["font.size"],
            rcParams["font.size"] / 1.7,
        ),
        fontstyle=("italic", "normal", "italic", "normal"),
    )

    ax.set_ylim(ax.get_ylim()[0], ax.get_ylim()[-1] * 1.05 * 1.05)
    max_x = max([max(v) for v in voltages])
    ax.set_xlim(-10, max_x + 10)
    hep.utils.mpl_magic(ax, soft_fail=True)
    if spanLabelBackground:
        ax.axhspan(
            10
            ** (
                np.log(ax.get_ylim()[-1]) / np.log(10)
                + (
                    np.log(ax.get_ylim()[0]) / np.log(10)
                    - np.log(ax.get_ylim()[-1]) / np.log(10)
                )
                * 0.11
            ),
            ax.get_ylim()[-1],
            alpha=1,
            color="white",
        )
    fig.savefig(
        f"hybrid_ivs{_SNs}{_postfix}.pdf",
        bbox_inches="tight",
        facecolor="white",
        dpi=300,
    )
    fig.savefig(
        f"hybrid_ivs{_SNs}{_postfix}.png",
        bbox_inches="tight",
        facecolor="white",
        dpi=300,
    )
    plt.close()


# def plot_vbd_for_hybrid_sns(input_dict):
#     fig, ax = plt.subplots(figsize=(12, 8))
#
#     labels = input_dict.keys()
#     vbds = [v["VBD"] for v in input_dict.values()]
#
#     bottom_values = np.zeros(len(labels))
#
#     ax.scatter(
#         [i * 0.5 for i in range(len(labels))],
#         vbds
#     )
#     ax.set_xticks([i * 0.5 for i in range(len(labels))], labels)
#
#     for tick in ax.get_xticklabels():
#         tick.set_rotation(90)
#
#     ax.set_ylabel("Breakdown Voltage $V_{bd}$ [V]")
#
#     hep.label.exp_text(
#         "ATLAS HGTD",
#         "Production Database",
#         f"Generated with anstein/hgtd-tools~master on {today}",
#         loc=4,
#         italic=(True, False, False),
#     )
#
#     ax.set_ylim(ax.get_ylim()[0], ax.get_ylim()[-1] * 1.05 * 1.05)
#     # this is just a sanity check (not to be done in the future with all hybrids)
#     #fig.savefig(
#     #    f"hybrid_vbd_{today}.pdf",
#     #    bbox_inches="tight",
#     #    facecolor="white",
#     #    dpi=300,
#     #)
#     #fig.savefig(
#     #    f"hybrid_vbd_{today}.png",
#     #    bbox_inches="tight",
#     #    facecolor="white",
#     #    dpi=300,
#     #)
#
# def plot_vbd_correlation_for_hybrid_sns(input_dict):
#     vbds = [v["VBD"] for v in input_dict.values() if v["sensor_VBD"] != None]
#     sensor_vbds = [v["sensor_VBD"] for v in input_dict.values() if v["sensor_VBD"] != None]
#
#     def _vbd_correlation_for_hybrid_sns(x_min=None,x_max=None,y_min=None,y_max=None):
#         fig, ax = plt.subplots(figsize=(10,10))
#
#         ax.scatter(
#             vbds, sensor_vbds
#         )
#         ax.set_xlabel("Hybrid Breakdown Voltage $V_{bd}$ [V]")
#         ax.set_ylabel("Sensor Average Breakdown Voltage $V_{bd}$ [V]")
#
#         ax.set_xlim([x_min, x_max])
#         ax.set_ylim([y_min, y_max])
#
#         if ((x_min == y_min) or (x_max == y_max)) and ((x_min != None) or (x_max != None)):
#             ax.plot([0,1000],[0,1000],color="black",zorder=0)
#         hep.label.exp_text(
#             "ATLAS HGTD",
#             "Production Database",
#             f"Generated with anstein/hgtd-tools~master on {today}",
#             loc=4,
#             italic=(True, False, False),
#         )
#
#         ax.set_ylim(ax.get_ylim()[0], ax.get_ylim()[-1] * 1.05 * 1.05)
#         # this is just a sanity check (not to be done in the future with all hybrids)
#         #fig.savefig(
#         #    f"hybrid_vbd_{today}.pdf",
#         #    bbox_inches="tight",
#         #    facecolor="white",
#         #    dpi=300,
#         #)
#         #fig.savefig(
#         #    f"hybrid_vbd_{today}.png",
#         #    bbox_inches="tight",
#         #    facecolor="white",
#         #    dpi=300,
#         #)
#     _vbd_correlation_for_hybrid_sns()
#     _vbd_correlation_for_hybrid_sns(x_min=150,y_min=150)

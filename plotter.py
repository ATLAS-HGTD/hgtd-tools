from datetime import datetime

import matplotlib as mpl
import matplotlib.pyplot as plt
import mplhep as hep
import numpy as np
from cycler import cycler
from matplotlib import rcParams

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
    plot_diff_sumHybridIV_moduleIV,
    apply_voltage_correction,
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

    if plot_diff_sumHybridIV_moduleIV:
        fig, (ax, ax_diff) = plt.subplots(
            2,
            1,
            figsize=(12, 10),
            height_ratios=[10, 5],
            sharex=True,
            gridspec_kw={"wspace": 0, "hspace": 0},
        )
    else:
        fig, ax = plt.subplots(figsize=(10, 8))
    for i, label in enumerate(labels):
        ax.plot(voltages[i], currents[i], label=label, linestyle="-", marker="o", ms=5)

    if not plot_diff_sumHybridIV_moduleIV:
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
        ax=ax,
    )

    if not apply_voltage_correction:
        ax.set_ylim(ax.get_ylim()[0], ax.get_ylim()[-1] * 5)
    max_x = max([max(v) for v in voltages])
    ax.set_xlim(-10, max_x + 10)
    if not apply_voltage_correction:
        ax.legend(
            title=KoP_legend,
            fontsize=rcParams["font.size"] / 1.3,
            facecolor="white",
            edgecolor="white",
            framealpha=1,
            frameon=True,
            loc="upper right",
        )
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
    if plot_diff_sumHybridIV_moduleIV:
        minimum_of_maxima = 999
        for i, kop in enumerate(KoPs):
            if kop in ["Hybrid", "Module"]:
                minimum_of_maxima = min(minimum_of_maxima, max(voltages[i]))
        index_minimum_of_maxima = voltages[-1].index(
            minimum_of_maxima
        )  # last allowed index to use for diff plot

        diff_voltages = voltages[-1][:index_minimum_of_maxima]
        diff_currents_measured_module = currents[-1][:index_minimum_of_maxima]
        diff_currents_sum_of_hybrids = currents[-2][:index_minimum_of_maxima]
        diff_currents_to_plot = [
            diff_currents_measured_module[i] - diff_currents_sum_of_hybrids[i]
            for i in range(index_minimum_of_maxima)
        ]
        ax_diff.plot(
            diff_voltages,
            diff_currents_to_plot,
            label="Difference measured Module IV - sum of Hybrid IVs",
            color="#94a4a2",
            linestyle="-",
            marker="o",
            ms=5,
        )
        ax_diff.set_ylabel("Current [A]")
        ax_diff.set_xlabel("Voltage [V]")
        ax_diff.set_yscale("log")
        ax_diff.grid(alpha=0.5)
        ax_diff.grid(which="minor", alpha=0.25)
        if not apply_voltage_correction:
            ax_diff.legend(
                fontsize=rcParams["font.size"] / 1.3,
                facecolor="white",
                edgecolor="white",
                framealpha=1,
                frameon=True,
                loc="upper right",
            )
        _postfix = "_diff" + _postfix
    if apply_voltage_correction:
        ax.plot(
            voltages[-1],
            util.module_voltage_correction(currents[-1], voltages[-1]),
            label="Module with voltage correction",
            color="green",
            linestyle="-",
            marker="o",
            ms=5,
        )
        ax.legend(
            title=KoP_legend,
            fontsize=rcParams["font.size"] / 1.3,
            facecolor="white",
            edgecolor="white",
            framealpha=1,
            frameon=True,
            loc="upper right",
        )
        if plot_diff_sumHybridIV_moduleIV:
            diff_currents_measured_module_corrected = util.module_voltage_correction(
                diff_currents_measured_module, diff_voltages
            )
            diff_corrected_currents_to_plot = [
                diff_currents_measured_module_corrected[i]
                - diff_currents_sum_of_hybrids[i]
                for i in range(index_minimum_of_maxima)
            ]
            # ax_diff.set_ylim(ax_diff.get_ylim()[0], ax_diff.get_ylim()[-1] * 5)
            ax_diff.plot(
                diff_voltages,
                diff_corrected_currents_to_plot,
                label="Difference measured & corrected Module IV - sum of Hybrid IVs",
                color="green",
                linestyle="-",
                marker="o",
                ms=5,
            )
            ax_diff.legend(
                fontsize=rcParams["font.size"] / 1.3,
                facecolor="white",
                edgecolor="white",
                framealpha=1,
                frameon=True,
                loc="upper right",
            )
        _postfix = "_correction" + _postfix
    n_legend_entries = len(ax.get_legend().get_texts())
    if n_legend_entries > 3:
        ax.set_ylim(ax.get_ylim()[0], ax.get_ylim()[-1] * 10)
    _SNs = util.sanitize(_SNs)
    fig.savefig(
        f"ivs_{_SNs}{_postfix}.pdf",
        bbox_inches="tight",
        facecolor="white",
        dpi=300,
    )
    fig.savefig(
        f"ivs_{_SNs}{_postfix}.png",
        bbox_inches="tight",
        facecolor="white",
        dpi=300,
    )
    plt.close()


def pie_chart(
    data,
    text_labels,
    filename_postfix,
    exp_text,
    subtitle,
    extra_text,
):
    plt.rcParams["axes.prop_cycle"] = cycler("color", combination_color_sequence)
    fig, ax = plt.subplots(figsize=(12, 8))
    if sum(data) == 0:
        # all contributions are zero => fill a dummy pie chart
        pie = ax.pie([1], colors=["white"])
        labels = ax.pie_label(pie, "No entries", distance=0.7)
        labels[0].set_color("#111111")
        labels[0].set_weight("bold")
    else:
        # filter to make sure empty contributions are ignored, keeping the color sequence
        filtered_data = []
        filtered_labels = []
        filtered_colors = []
        for i, val in enumerate(data):
            if val > 0:
                filtered_data.append(val)
                filtered_labels.append(text_labels[i])
                filtered_colors.append(
                    combination_color_sequence[i % len(combination_color_sequence)]
                )
        pie = ax.pie(filtered_data, colors=filtered_colors)
        wedges = pie[0]
        labels_outer = ax.pie_label(pie, filtered_labels, distance=1.1)
        labels_frac = ax.pie_label(pie, "{frac:.1%}", distance=0.7)
        labels_abs = ax.pie_label(pie, "{absval:d}", distance=0.4)
        # change the text color depending on wedge color (luminance)
        for i, wedge in enumerate(wedges):
            rgba = wedge.get_facecolor()
            r, g, b = rgba[0], rgba[1], rgba[2]
            # W3C
            luminance = 0.299 * r + 0.587 * g + 0.114 * b
            text_color = "white" if luminance < 0.5 else "#111111"
            labels_frac[i].set_color(text_color)
            labels_frac[i].set_weight("bold")
            labels_abs[i].set_color(text_color)
            labels_abs[i].set_weight("bold")
    hep.label.exp_text(
        "ATLAS HGTD",
        " " + exp_text,
        "",
        loc=0,
        fontsize=(
            rcParams["font.size"] * 1.3,
            rcParams["font.size"] * 1.3,
            rcParams["font.size"],
            rcParams["font.size"] / 1.7,
        ),
        fontstyle=("italic", "normal", "italic", "normal"),
    )
    if subtitle:
        full_subtitle = f"{extra_text}Generated with anstein/hgtd-tools~master on {datetime.today().strftime('%Y-%m-%d')}"
        ax.text(
            0.00,
            0.99,
            full_subtitle,
            transform=ax.transAxes,
            fontsize=rcParams["font.size"] / 1.7,
            fontstyle="normal",
            verticalalignment="top",
            horizontalalignment="left",
        )
    fig.savefig(
        f"pie_chart_{filename_postfix}.pdf",
        bbox_inches="tight",
        facecolor="white",
        dpi=300,
    )
    fig.savefig(
        f"pie_chart_{filename_postfix}.png",
        bbox_inches="tight",
        facecolor="white",
        dpi=300,
    )
    plt.close()


if __name__ == "__main__":
    # test pie chart plotter
    pie_chart(
        [17, 52, 52, 61],
        ["a", "b", "c", "d"],
        "test",
        "Experiment",
        True,
        "Extra text. ",
    )

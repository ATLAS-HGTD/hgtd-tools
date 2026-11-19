import textwrap
from collections import Counter
from datetime import datetime
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import mplhep as hep
import numpy as np
from cycler import cycler
from matplotlib import rcParams

from hgtd_tools import util

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

#: outline colour of every bar segment in the newer plotting functions
EDGE_COLOR = "#1a1a1a"

#: default grey for de-emphasised stack segments; override per segment via `shaded`
SHADED_FACE = "#9aa0a6"

#: horizontal distance (in axes widths) between the frame and an outside legend
LEGEND_X = 1.07


# ATLAS plot style
hep.style.use("ATLAS1")
plt.rcParams["axes.axisbelow"] = True


def _apply_y_scale(ax, scale):
    """
    Apply the requested y-axis scale ('lin' or 'log') to an axis.

    For 'log', a non-positive lower limit (the default for bars starting at 0) is
    replaced by a small fraction of the upper limit so that the axis stays valid.
    """
    if scale != "log":
        ax.set_yscale("linear")
        return
    ax.set_yscale("log")
    lower, upper = ax.get_ylim()
    if lower <= 0:
        top = upper if upper > 0 else 1.0
        ax.set_ylim(top * 1e-4, top)


def _apply_x_scale(ax, scale):
    """x-axis counterpart of _apply_y_scale."""
    if scale != "log":
        ax.set_xscale("linear")
        return
    ax.set_xscale("log")
    lower, upper = ax.get_xlim()
    if lower <= 0:
        top = upper if upper > 0 else 1.0
        ax.set_xlim(top * 1e-4, top)


def _exp_label(ax, exp_text, title_prefix="", subtitle=False, loc=4):
    """'ATLAS HGTD | <exp_text>' label with the optional generation line.

    `loc` is mplhep's placement code (0 = best, 1 = upper right, 2 = upper left,
    3 = lower left, 4 = lower right); the label always stays inside the frame.
    """
    hep.label.exp_text(
        "ATLAS HGTD",
        " " + exp_text,
        (
            f"{title_prefix}Generated with anstein/hgtd-tools~master on "
            f"{datetime.today().strftime('%Y-%m-%d')}"
            if subtitle
            else ""
        ),
        loc=loc,
        fontsize=(
            rcParams["font.size"] * 1.3,
            rcParams["font.size"] * 1.3,
            rcParams["font.size"],
            rcParams["font.size"] / 1.7,
        ),
        fontstyle=("italic", "normal", "italic", "normal"),
        ax=ax,
    )


def _selection_text(selection_lines, width=64):
    """Wrapped corner text from a list of free-text lines."""
    if not selection_lines:
        return None
    return "\n".join(
        line for chunk in selection_lines for line in textwrap.fill(chunk, width=width).split("\n")
    )


def _draw_selection(fig, selection_lines, width=64):
    """Print the active selection into the lower left corner of a figure.

    Shrinks the axes first, so the text can never overlap the tick labels or
    the axis title. The 0.45 cap stops a very long selection from eating the
    plot; shorten the text instead if you hit it.
    """
    text = _selection_text(selection_lines, width=width)
    if not text:
        return
    fontsize = rcParams["font.size"] / 1.9
    n_lines = text.count("\n") + 1
    height_in = fig.get_size_inches()[1]
    needed = (n_lines * fontsize * 1.4 + 10) / (height_in * 72) if height_in else 0.0
    bottom = min(0.45, max(fig.subplotpars.bottom, needed + 0.08))
    if bottom > fig.subplotpars.bottom:
        fig.subplots_adjust(bottom=bottom)
    fig.text(
        0.01,
        0.01,
        text,
        ha="left",
        va="bottom",
        fontsize=fontsize,
        color="#333333",
        linespacing=1.4,
    )


def _stem(filename_prefix, postfix, scale, variant=None):
    """File stem; the normalisation variant is part of the name so that the
    counts and the fractions figure of one call cannot overwrite each other."""
    parts = [filename_prefix]
    if postfix:
        parts.append(postfix)
    parts.append(scale)
    if variant and variant != "none":
        parts.append(variant)
    return "_".join(parts)


def _save(fig, stem, outdir=None):
    """Write pdf + png, creating `outdir` if needed. Returns the stem written."""
    target = Path(outdir) / stem if outdir else Path(stem)
    if outdir:
        target.parent.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(f"{target}.{ext}", bbox_inches="tight", facecolor="white", dpi=300)
    plt.close(fig)
    return str(target)


def _outside_legend_kwargs(legend_title, legend_kwargs=None):
    """Legend to the right of the frame, vertically centred on the axes."""
    kwargs = {
        "title": legend_title,
        "ncol": 1,
        "fontsize": rcParams["font.size"] / 1.3,
        "facecolor": "white",
        "edgecolor": "white",
        "framealpha": 1,
        "frameon": True,
        "loc": "center left",
        "bbox_to_anchor": (LEGEND_X, 0.5),
        "borderaxespad": 0.0,
    }
    kwargs.update(legend_kwargs or {})
    return kwargs


def plot_categorical_bar_stack(
    input_array,
    filename_prefix,
    categories,
    legend_entries,
    feature_legend_title,
    exp_text,
    title_prefix,
    subtitle,
    scale,
    postfix,
):
    if not legend_entries:
        return
    plt.rcParams["axes.prop_cycle"] = cycler("color", colors_tab20c + combination_color_sequence)
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
    _apply_y_scale(ax, scale)
    hep.utils.mpl_magic(ax, soft_fail=True)
    ax.set_xlim(
        ax.get_xlim()[0] - n_categories * 0.025,
        ax.get_xlim()[-1] + n_categories * 0.025,
    )
    for ext in ("pdf", "png"):
        fig.savefig(
            f"{filename_prefix}_{feature_legend_title}_{postfix}_{scale}.{ext}",
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
    scale,
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
        (f"{title_prefix}Generated with anstein/hgtd-tools~master on {today}" if subtitle else ""),
        loc=4,
        fontsize=(
            rcParams["font.size"] * 1.3,
            rcParams["font.size"] * 1.3,
            rcParams["font.size"],
            rcParams["font.size"] / 1.7,
        ),
        fontstyle=("italic", "normal", "italic", "normal"),
    )
    _apply_y_scale(ax, scale)
    if scale == "log":
        ax.set_ylim(8e-1, ax.get_ylim()[-1] * 1.05 * 1.05 * 1.05 * 1.05 * 1.05)
    else:
        ax.set_ylim(0, ax.get_ylim()[-1] * 1.1)
    ax.set_xlim(
        -1,
        n_all_months_for_x_axis,
    )
    hep.utils.mpl_magic(ax, soft_fail=True, N=20)
    for ext in ("pdf", "png"):
        fig.savefig(
            f"{filename_prefix}_time_trend_by_KoP_{postfix}_{scale}.{ext}",
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
    legend_title,
):
    plt.rcParams["axes.prop_cycle"] = cycler("color", combination_color_sequence)
    if legend_title == "default":
        if len(list(set(KoPs))) > 1:
            KoP_legend = "Serial Numbers"
        else:
            if "Module" in KoPs:
                KoP_legend = "Modules"
            elif "Hybrid" in KoPs:
                KoP_legend = "Hybrids"
            elif "Sensor" in KoPs:
                KoP_legend = "Sensors"
    else:
        KoP_legend = legend_title
        if legend_title == "None":
            KoP_legend = None

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
                + (np.log(ax.get_ylim()[0]) / np.log(10) - np.log(ax.get_ylim()[-1]) / np.log(10))
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
                diff_currents_measured_module_corrected[i] - diff_currents_sum_of_hybrids[i]
                for i in range(index_minimum_of_maxima)
            ]
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
    if n_legend_entries > 5:
        leg = ax.get_legend()
        leg.set_loc("lower right")
        ax.set_ylim(ax.get_ylim()[0], ax.get_ylim()[-1] / 10)
    if KoP_legend is not None:
        if n_legend_entries > 4:
            leg = ax.get_legend()
            leg.set_loc("lower right")
            ax.set_ylim(ax.get_ylim()[0], ax.get_ylim()[-1] / 10)
        else:
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
        _ = ax.pie_label(pie, filtered_labels, distance=1.1)
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


# ------------------------------------------------------------------
# Generic stacked bars / category counts
# ------------------------------------------------------------------


def plot_stacked_bar_by_category(
    input_array,
    categories,
    legend_entries,
    filename_prefix,
    legend_title,
    exp_text,
    title_prefix="",
    subtitle=False,
    scale="lin",
    postfix="",
    normalize="none",
    shaded=None,
    xlabel=None,
    ylabel=None,
    horizontal=False,
    annotations=None,
    annotate_totals=True,
    rotate_xticks=90,
    selection_lines=None,
    figsize=(12, 8),
    labels_outside=False,
    exp_text_loc=4,
    legend_kwargs=None,
    outdir=None,
):
    """Stacked bars with one bar per category and one segment per legend entry.

    Parameters:
        input_array: shape (len(categories), len(legend_entries)); rows are
            bars, columns are stack segments.
        categories: bar labels (one per row).
        legend_entries: segment labels (one per column), in stack order.
        filename_prefix: file names become
            ``{filename_prefix}_{postfix}_{scale}[_{normalize}].{pdf,png}``
        normalize: "none" keeps counts, "row" divides each row by its sum so
            the bars show fractions (empty rows stay at zero).
        shaded: {segment: {"alpha": float, "hatch": str, "color": str}} for
            segments that should read as a de-emphasised group (grey with
            increasing alpha and different hatches). Segments not listed use
            the module colour cycle.
        annotations: optional text per bar, drawn at the end of the stack.
        annotate_totals: label each stack with its total when `annotations`
            is None.
        horizontal: bars grow to the right instead of upwards; `scale` then
            applies to the x axis. For horizontal bars the stack offset is
            passed as `left`, for vertical ones as `bottom`.
        labels_outside: put the legend to the right of the axes (see
            `LEGEND_X`), so it does not cover the bars.
        exp_text_loc: where the 'ATLAS HGTD' label goes; 0 puts it above the
            axes, any other value is forwarded to mplhep (4 = lower right).
        selection_lines: free-text lines printed in the lower left corner.
        outdir: directory for the output files; created if missing.

    The category axis is pinned to the bars and the value axis is set *after*
    mpl_magic, so neither padding nor the annotations can drift.
    Returns the file stem that was written, or None when there is nothing to
    draw. Colours follow ``colors_tab20c + combination_color_sequence``.
    """
    array = np.asarray(input_array, dtype=float)
    if array.ndim != 2 or not array.size:
        return None
    if array.shape != (len(categories), len(legend_entries)):
        raise ValueError(
            f"input_array has shape {array.shape}, expected "
            f"({len(categories)}, {len(legend_entries)})"
        )
    if not array.any():
        return None

    totals = array.sum(axis=1)
    plotted = array
    if normalize == "row":
        safe = np.where(totals > 0, totals, 1.0)
        plotted = array / safe[:, None]

    palette = list(colors_tab20c) + list(combination_color_sequence)
    shaded = shaded or {}
    plain_entries = [e for e in legend_entries if e not in shaded]

    plt.rcParams["axes.prop_cycle"] = cycler("color", palette)
    fig, ax = plt.subplots(figsize=figsize)

    positions = np.arange(len(categories))

    left = np.zeros(len(categories))
    for j, entry in enumerate(legend_entries):
        values = plotted[:, j]
        if not values.any():
            continue
        style = shaded.get(entry)
        kwargs = dict(
            edgecolor=EDGE_COLOR,
            linewidth=0.8,
            label=entry,
            zorder=2,
        )
        if style:
            kwargs.update(
                color=style.get("color", SHADED_FACE),
                alpha=style.get("alpha", 0.4),
                hatch=style.get("hatch"),
            )
        else:
            kwargs["color"] = palette[plain_entries.index(entry) % len(palette)]
        # ax.barh stacks with `left=`, ax.bar with `bottom=`. Passing the wrong
        # one reaches Rectangle.set() and raises AttributeError.
        if horizontal:
            ax.barh(positions, values, left=left, height=0.6, **kwargs)
        else:
            ax.bar(positions, values, bottom=left, width=0.6, **kwargs)
        left = left + values

    if annotations is None and annotate_totals:
        annotations = [f"{t:.1%}" if normalize == "row" else f"{t:.0f}" for t in totals]
    if annotations is not None:
        pad = (plotted.max() if plotted.size else 0.0) * 0.012 or 0.01
        for i, (end, text) in enumerate(zip(left, annotations)):
            if horizontal:
                # bars grow to the right: label just past the stack tip
                ax.text(
                    end + pad,
                    positions[i],
                    " " + str(text),
                    va="center",
                    ha="left",
                    fontsize=rcParams["font.size"] / 1.3,
                )
            else:
                # bars grow upwards: label above the bar, centred on it
                ax.text(
                    positions[i],
                    end + pad,
                    str(text),
                    va="bottom",
                    ha="center",
                    fontsize=rcParams["font.size"] / 1.3,
                )

    if horizontal:
        ax.set_yticks(positions, categories)
        ax.set_ylabel(ylabel or "Category")
        ax.set_xlabel(xlabel or ("Fraction" if normalize == "row" else "Number"))
        ax.grid(axis="x", alpha=0.5)
        ax.grid(axis="x", which="minor", alpha=0.25)
    else:
        ax.set_xticks(positions, categories)
        ax.set_xlabel(xlabel or "Category")
        ax.set_ylabel(ylabel or ("Fraction" if normalize == "row" else "Number"))
        for tick in ax.get_xticklabels():
            tick.set_rotation(rotate_xticks)
        ax.grid(axis="y", alpha=0.5)
        ax.grid(axis="y", which="minor", alpha=0.25)
    ax.set_axisbelow(True)

    if labels_outside:
        ax.legend(**_outside_legend_kwargs(legend_title, legend_kwargs))
    else:
        kwargs = {
            "title": legend_title,
            "ncol": 2,
            "fontsize": rcParams["font.size"] / 1.3,
            "facecolor": "white",
            "edgecolor": "white",
            "framealpha": 1,
            "frameon": True,
        }
        kwargs.update(legend_kwargs or {})
        ax.legend(**kwargs)

    _exp_label(ax, exp_text, title_prefix, subtitle, loc=exp_text_loc)

    _draw_selection(fig, selection_lines)
    hep.utils.mpl_magic(ax, soft_fail=True)

    # limits last: mpl_magic must not re-introduce padding around the bars
    upper = float(left.max()) if left.max() > 0 else 1.0
    if horizontal:
        _apply_x_scale(ax, scale)
        ax.set_xlim(ax.get_xlim()[0] if scale == "log" else 0, upper * 1.10)
        ax.set_ylim(-0.5, len(categories) - 0.5)
    else:
        _apply_y_scale(ax, scale)
        ax.set_ylim(ax.get_ylim()[0] if scale == "log" else 0, upper * 1.10)
        ax.set_xlim(-0.5, len(categories) - 0.5)

    return _save(fig, _stem(filename_prefix, postfix, scale, normalize), outdir=outdir)


def plot_stacked_bars_from_counts(
    counts_by_category,
    filename_prefix,
    legend_title,
    exp_text,
    segment_order=None,
    category_order=None,
    segment_totals=None,
    title_prefix="",
    subtitle=False,
    scale="lin",
    postfix="",
    shaded=None,
    xlabel=None,
    ylabel=None,
    horizontal=False,
    rotate_xticks=90,
    annotations=None,
    selection_lines=None,
    legend_kwargs=None,
    outdir=None,
    normalize=("none",),
    figsize=(12, 8),
    labels_outside=False,
    exp_text_loc=4,
):
    """Draw one stacked bar per category from nested count dicts.

    Takes the shape the CLIs actually have — ``{category: {segment: count}}`` —
    builds the matrix, orders both axes and writes the requested variants, so a
    caller never assembles a numpy array by hand.

    Parameters:
        counts_by_category: {category: {segment: count}}. Missing segments are
            zero; missing categories are skipped.
        segment_order / category_order: explicit orders. None sorts by total,
            descending, ties alphabetically.
        segment_totals: optional {segment: total} used only for ordering, e.g.
            segments known from another figure.
        normalize: variants to write; "none" (counts) and "row" (fractions
            within each bar). Each variant gets its own file name.
        labels_outside / exp_text_loc / figsize: forwarded to
            plot_stacked_bar_by_category.
        All other parameters are forwarded to plot_stacked_bar_by_category.

    Returns the list of file stems written (empty when there is nothing to draw).
    """
    counts_by_category = {
        category: dict(counts) for category, counts in (counts_by_category or {}).items()
    }
    if not counts_by_category:
        return []

    categories = list(category_order or [])
    if not categories:
        totals = Counter({cat: sum(counts.values()) for cat, counts in counts_by_category.items()})
        categories = sorted(totals, key=lambda c: (-totals[c], c))
    if not categories:
        return []

    if segment_order is not None:
        segments = list(segment_order)
    else:
        totals = Counter()
        for counts in counts_by_category.values():
            totals.update(counts)
        if segment_totals:
            totals.update(segment_totals)
        segments = sorted(totals, key=lambda s: (-totals[s], s))
    if not segments:
        return []

    matrix = np.zeros((len(categories), len(segments)))
    for i, category in enumerate(categories):
        counts = counts_by_category.get(category) or {}
        for j, segment in enumerate(segments):
            matrix[i, j] = counts.get(segment, 0)
    if not matrix.any():
        return []

    written = []
    for variant in normalize:
        stem = plot_stacked_bar_by_category(
            matrix,
            categories,
            segments,
            filename_prefix,
            legend_title,
            exp_text,
            title_prefix=title_prefix,
            subtitle=subtitle,
            scale=scale,
            postfix=postfix,
            normalize=variant,
            shaded=shaded,
            xlabel=xlabel,
            ylabel=ylabel,
            horizontal=horizontal,
            annotations=annotations,
            rotate_xticks=rotate_xticks,
            selection_lines=selection_lines,
            legend_kwargs=legend_kwargs,
            figsize=figsize,
            labels_outside=labels_outside,
            exp_text_loc=exp_text_loc,
            outdir=outdir,
        )
        if stem:
            written.append(stem)
    return written


def plot_grouped_stacked_bars(
    input_array,
    categories,
    group_labels,
    legend_entries,
    filename_prefix,
    legend_title,
    exp_text,
    title_prefix="",
    subtitle=False,
    scale="lin",
    postfix="",
    normalize="none",
    shaded=None,
    xlabel=None,
    ylabel=None,
    annotations=None,
    bar_height=0.42,
    group_gap=0.02,
    site_spacing=1.35,
    separators=True,
    exp_text_loc=0,
    selection_lines=None,
    figsize=(12, 8),
    legend_kwargs=None,
    color_keys=None,
    outdir=None,
):
    """Two (or more) stacked bars per category, drawn side by side.

    Used when the same category (a site) carries two populations that should be
    compared visually — e.g. modules produced there vs hybrids stored there —
    without merging them into a single stack.

    Parameters:
        input_array: shape (len(categories), len(group_labels), len(legend_entries)).
            Rows are categories, the middle axis selects the bar inside the
            group, the last axis is the stack segment.
        categories: bar-group labels (one per row), used as y tick labels.
        group_labels: labels of the bars inside a group, bottom to top.
        legend_entries: segment labels (one per column), in stack order.
        normalize: "none" keeps counts, "row" normalises each bar to itself.
        shaded: {segment: {"alpha": float, "hatch": str, "color": str}} for
            de-emphasised segments (grey, increasing alpha, distinct hatches).
        annotations: per-bar text, shape (len(categories), len(group_labels)).
        bar_height / group_gap: thickness of one bar and the gap between the
            bars of one group; a small `group_gap` keeps the pair together.
        site_spacing: distance between categories. Raising it (or lowering
            `bar_height`) widens the gap between sites relative to the gap
            inside a pair.
        separators: draw a faint line between consecutive categories.
        exp_text_loc: 0 (default) puts the 'ATLAS HGTD' label above the axes.
        selection_lines: free-text lines printed in the lower left corner.
        color_keys: one colour key per legend entry; entries sharing a key share
            a colour. Defaults to the labels themselves.
        outdir: directory for the output files; created if missing.

    The legend always sits outside, to the right of the frame. Every segment is
    outlined in `EDGE_COLOR`, in both bars.
    Returns the file stem written, or None when there is nothing to draw.
    """
    array = np.asarray(input_array, dtype=float)
    if array.ndim != 3 or not array.size:
        return None
    if array.shape != (len(categories), len(group_labels), len(legend_entries)):
        raise ValueError(
            f"input_array has shape {array.shape}, expected "
            f"({len(categories)}, {len(group_labels)}, {len(legend_entries)})"
        )
    if not array.any():
        return None

    totals = array.sum(axis=2)  # (n_categories, n_groups)
    plotted = array
    if normalize == "row":
        safe = np.where(totals > 0, totals, 1.0)
        plotted = array / safe[..., None]

    palette = list(colors_tab20c) + list(combination_color_sequence)
    shaded = shaded or {}

    if color_keys is None:
        color_keys = list(legend_entries)
    if len(color_keys) != len(legend_entries):
        raise ValueError(
            f"color_keys has {len(color_keys)} entries, expected {len(legend_entries)}"
        )
    key_weights = {}
    for j, key in enumerate(color_keys):
        key_weights[key] = key_weights.get(key, 0.0) + float(array[:, :, j].sum())
    ordered_keys = sorted(key_weights, key=lambda k: (-key_weights[k], str(k)))
    color_of = {key: palette[i % len(palette)] for i, key in enumerate(ordered_keys)}

    plt.rcParams["axes.prop_cycle"] = cycler("color", palette)
    fig, ax = plt.subplots(figsize=figsize)

    positions = np.arange(len(categories)) * site_spacing
    n_groups = len(group_labels)
    spacing = bar_height + group_gap
    offsets = (np.arange(n_groups) - (n_groups - 1) / 2.0) * spacing

    left = np.zeros((len(categories), n_groups))
    labeled = set()
    for j, entry in enumerate(legend_entries):
        shade = shaded.get(entry)
        for g in range(n_groups):
            values = plotted[:, g, j]
            if not values.any():
                continue
            kwargs = dict(
                height=bar_height,
                left=left[:, g],  # horizontal bars: the stack offset is `left`
                label=entry if entry not in labeled else None,
                edgecolor=EDGE_COLOR,
                linewidth=0.8,
                zorder=2,
            )
            if shade:
                kwargs.update(
                    color=shade.get("color", SHADED_FACE),
                    alpha=shade.get("alpha", 0.4),
                    hatch=shade.get("hatch"),
                )
            else:
                kwargs["color"] = color_of[color_keys[j]]
            ax.barh(positions + offsets[g], values, **kwargs)
            labeled.add(entry)
            left[:, g] = left[:, g] + values

    if annotations is None:
        annotations = [
            [
                f"{group_labels[g]}: {totals[i, g]:.1%}"
                if normalize == "row"
                else f"{group_labels[g]}: {totals[i, g]:.0f}"
                for g in range(n_groups)
            ]
            for i in range(len(categories))
        ]
    # pad relative to the data range, so fractions (max 1.0) get a visible gap too
    pad = (plotted.max() if plotted.size else 0.0) * 0.015 or 0.01
    for i in range(len(categories)):
        for g in range(n_groups):
            ax.text(
                left[i, g] + pad,
                positions[i] + offsets[g],
                str(annotations[i][g]),
                va="center",
                ha="left",
                fontsize=rcParams["font.size"] / 1.5,
            )

    if separators and len(categories) > 1:
        for i in range(len(categories) - 1):
            ax.axhline(
                positions[i] + site_spacing / 2.0,
                color="0.85",
                linewidth=0.6,
                zorder=1,
            )

    ax.set_yticks(positions, categories)
    ax.set_ylim(
        positions[0] - site_spacing / 2.0,
        positions[-1] + site_spacing / 2.0,
    )
    ax.set_ylabel(ylabel or "Site")
    ax.set_xlabel(xlabel or ("Fraction" if normalize == "row" else "Number"))
    ax.grid(axis="x", alpha=0.5)
    ax.grid(axis="x", which="minor", alpha=0.25)
    ax.set_axisbelow(True)

    ax.legend(**_outside_legend_kwargs(legend_title, legend_kwargs))

    _exp_label(ax, exp_text, title_prefix, subtitle, loc=exp_text_loc)

    _draw_selection(fig, selection_lines)
    hep.utils.mpl_magic(ax, soft_fail=True)

    # limits last, same reason as in plot_stacked_bar_by_category
    upper = float(left.max()) if left.max() > 0 else 1.0
    _apply_x_scale(ax, scale)
    ax.set_xlim(ax.get_xlim()[0] if scale == "log" else 0, upper * 1.15)
    ax.set_ylim(
        positions[0] - site_spacing / 2.0,
        positions[-1] + site_spacing / 2.0,
    )

    return _save(fig, _stem(filename_prefix, postfix, scale, normalize), outdir=outdir)


def plot_category_counts(
    labels,
    values,
    filename_prefix,
    exp_text,
    xlabel=None,
    ylabel=None,
    title_prefix="",
    subtitle=False,
    scale="lin",
    postfix="",
    color=None,
    annotate=True,
    rotate_xticks=90,
    selection_lines=None,
    figsize=(12, 8),
    exp_text_loc=4,
    outdir=None,
):
    """Single-colour bar chart of one number per label.

    Used for "which categories exist, and how many of each" — the caller decides
    the labels (SN prefixes, kinds of part, ...) and their order.
    Returns the file stem that was written, or None when there is nothing to draw.
    """
    if not len(labels):
        return None

    plt.rcParams["axes.prop_cycle"] = cycler("color", combination_color_sequence)
    fig, ax = plt.subplots(figsize=figsize)
    ax.bar(
        list(labels),
        list(values),
        color=color or color_sequence1[0],
        edgecolor=EDGE_COLOR,
        linewidth=0.8,
        zorder=2,
    )
    if annotate:
        for x, value in enumerate(values):
            ax.text(
                x,
                value,
                str(value),
                ha="center",
                va="bottom",
                fontsize=rcParams["font.size"] / 1.3,
            )

    ax.set_xlabel(xlabel or "Category")
    ax.set_ylabel(ylabel or "Number of parts")
    for tick in ax.get_xticklabels():
        tick.set_rotation(rotate_xticks)
    ax.grid(axis="y", alpha=0.5)
    ax.grid(axis="y", which="minor", alpha=0.25)
    ax.set_axisbelow(True)

    _exp_label(ax, exp_text, title_prefix, subtitle, loc=exp_text_loc)
    _draw_selection(fig, selection_lines)
    hep.utils.mpl_magic(ax, soft_fail=True)

    # limits last, and only enough headroom for the annotations
    _apply_y_scale(ax, scale)
    top = max(values) if len(values) and max(values) > 0 else 1.0
    if scale == "log":
        ax.set_ylim(max(ax.get_ylim()[0], 0.8), top * 1.20)
    else:
        ax.set_ylim(0, top * 1.12)

    return _save(fig, _stem(filename_prefix, postfix, scale), outdir=outdir)


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
    # test grouped stacked bars with shaded segments
    plot_grouped_stacked_bars(
        [
            [[10, 2, 1], [4, 0, 2]],
            [[5, 5, 0], [3, 1, 0]],
            [[1, 0, 0], [0, 0, 1]],
        ],
        ["site_a", "site_b", "site_c"],
        ["modules", "hybrids at location"],
        ["20WHNNC", "20WHNND", "0 hybrids"],
        "test",
        "Hybrid SN prefix",
        "Internal",
        postfix="test",
        shaded={"0 hybrids": {"alpha": 0.25, "hatch": "//"}},
        selection_lines=["sites: monitored", 'version contains: "ALTIROC A"'],
    )
    # test the counts-dict wrapper (vertical bars, both variants)
    plot_stacked_bars_from_counts(
        {
            "20WHNNC": {"ihep": 12, "mainz": 3},
            "20WHNND": {"ihep": 4, "cern": 9},
            "20WHNMI": {"mainz": 7},
        },
        "test_locations",
        "Hybrid location",
        "Internal",
        normalize=("none", "row"),
        labels_outside=True,
        exp_text_loc=0,
        postfix="test",
    )
    plot_category_counts(
        ["20WHNNC", "20WHNDC", "20WHNMI"],
        [120, 80, 5],
        "test_prefixes",
        "Internal",
        exp_text_loc=0,
        postfix="test",
    )

from argparse import ArgumentParser
from datetime import datetime
from datetime import UTC

import numpy as np

import plotter
import util

parser = ArgumentParser("IV curve plotting wrapper")
parser.add_argument(
    "--mode-alias",
    dest="mode_alias",
    help="Plotting mode. (Default: %(default)s)",
    default="Individual_overlay",
    choices=[
        "Individual_overlay",  # default: provide SN of parts to plot into same frame
        # NotImplemented yet "Get_Module_and_children_HY_IVs",  # only need SN of module parent, get values for children from DB
    ],
)
parser.add_argument(
    "--sensor_sns",
    dest="sensor_sns",
    help="One or multiple SNs of Sensors to plot (summed) IV curve(s) for; if multiple, comma-separated.",
    default=None,
)
parser.add_argument(
    "--hybrid_sns",
    dest="hybrid_sns",
    help="One or multiple SNs of Hybrids to plot IV curve(s) for; if multiple, comma-separated.",
    default=None,
)
parser.add_argument(
    "--module_sns",
    dest="module_sns",
    help="One or multiple SNs of Modules to plot IV curve(s) for; if multiple, comma-separated.",
    default=None,
)
parser.add_argument(
    "--apply_voltage_correction",
    dest="apply_voltage_correction",
    help="Correct Module IV by shifting the set voltage by correction term related to resistor on MF (adds additinoal curve).",
    default=False,
)
parser.add_argument(
    "--sum_sensorIV",
    dest="sum_sensorIV",
    help="Whether to plot the sum of both summed Sensor IVs.",
    default=False,
)
parser.add_argument(
    "--sum_hybridIV",
    dest="sum_hybridIV",
    help="Whether to plot the sum of both Hybrid IVs.",
    default=False,
)
parser.add_argument(
    "--diff_sumHybridIV_moduleIV",
    dest="diff_sumHybridIV_moduleIV",
    help="Whether to plot the difference between sum of both Hybrid IVs and actual Module IV.",
    default=False,
)
parser.add_argument(
    "--custom_labels",
    dest="custom_labels",
    help="One or multiple custom labels; if multiple, comma-separated.",
    default=None,
)
parser.add_argument(
    "--exp_text",
    dest="exp_text",
    help="Which kind of plot: Preliminary, Internal (default).",
    default="Internal",
)
parser.add_argument(
    "--legend_title",
    dest="legend_title",
    help="Custom legend title.",
    default="default",
)
parser.add_argument(
    "--output_postfix",
    dest="output_postfix",
    help="Postfix to append to filename.",
    default="",
)
args = parser.parse_args()

mode_alias = args.mode_alias
sensor_sns = args.sensor_sns
hybrid_sns = args.hybrid_sns
module_sns = args.module_sns
apply_voltage_correction = util.str2bool(args.apply_voltage_correction)
plot_sum_hybridIV = util.str2bool(args.sum_hybridIV)
plot_diff_sumHybridIV_moduleIV = util.str2bool(args.diff_sumHybridIV_moduleIV)
custom_labels = args.custom_labels
exp_text = args.exp_text
legend_title = args.legend_title
output_postfix = args.output_postfix

if __name__ == "__main__":
    voltages = []
    currents = []
    KoPs = []
    labels = []
    if sensor_sns != None:
        sensor_sns = [sensor_sns] if "," not in sensor_sns else sensor_sns.split(",")
        all_sensor_ivs_to_plot = []
        for sn in sensor_sns:
            iv, _ = util.get_sum_iv_for_sensor(sn, ivs_per_pad=None)
            KoPs.append("Sensor")
            labels.append(sn)
            all_sensor_ivs_to_plot.append(iv)
            currents.append(iv[0])
            voltages.append(iv[1])
    if hybrid_sns != None:
        hybrid_sns = [hybrid_sns] if "," not in hybrid_sns else hybrid_sns.split(",")
        all_hybrid_ivs_to_plot = []
        all_hybrid_ivs = util.get_all_hybrid_ivs()
        if plot_sum_hybridIV:
            sum_hybrid_ivs_to_plot = []
        for sn in hybrid_sns:
            iv, _ = util.get_iv_for_hybrid_or_module(
                sn, all_ivs=all_hybrid_ivs, KoP="Hybrid"
            )
            KoPs.append("Hybrid")
            labels.append(sn)
            all_hybrid_ivs_to_plot.append(iv)
            currents.append(iv[0])
            voltages.append(iv[1])
            if plot_sum_hybridIV:
                sum_hybrid_ivs_to_plot.append(iv)
        if plot_sum_hybridIV:
            sum_currents = [
                sum(x)
                for x in zip(sum_hybrid_ivs_to_plot[0][0], sum_hybrid_ivs_to_plot[1][0])
            ]
            currents.append(sum_currents)
            voltages.append(sum_hybrid_ivs_to_plot[1][1])
            KoPs.append("Hybrid")
            labels.append("Sum of Hybrid IVs")
    if module_sns != None:
        module_sns = [module_sns] if "," not in module_sns else module_sns.split(",")
        all_module_ivs_to_plot = []
        all_module_ivs = util.get_all_module_ivs()
        for sn in module_sns:
            iv, _ = util.get_iv_for_hybrid_or_module(
                sn, all_ivs=all_module_ivs, KoP="Module"
            )
            KoPs.append("Module")
            labels.append(sn)
            all_module_ivs_to_plot.append(iv)
            currents.append(iv[0])
            voltages.append(iv[1])

    if custom_labels != None:
        labels = (
            [custom_labels] if "," not in custom_labels else custom_labels.split(",")
        )
    plotter.iv_curves_for_sns(
        voltages,
        currents,
        labels,
        KoPs,
        exp_text=exp_text,
        subtitle=False,
        postfix=output_postfix,
        lineThreshold=False,
        spanLabelBackground=False,
        plot_diff_sumHybridIV_moduleIV=plot_diff_sumHybridIV_moduleIV,
        apply_voltage_correction=apply_voltage_correction,
        legend_title=legend_title,
    )

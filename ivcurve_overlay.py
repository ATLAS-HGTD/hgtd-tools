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
    "--custom_labels",
    dest="custom_labels",
    help="One or multiple custom labels; if multiple, comma-separated.",
    default=None,
)
args = parser.parse_args()

mode_alias = args.mode_alias
hybrid_sns = args.hybrid_sns
module_sns = args.module_sns
custom_labels = args.custom_labels

if __name__ == "__main__":
    voltages = []
    currents = []
    KoPs = []
    labels = []
    if hybrid_sns != None:
        hybrid_sns = [hybrid_sns] if "," not in hybrid_sns else hybrid_sns.split(",")
        all_hybrid_ivs_to_plot = []
        all_hybrid_ivs = util.get_all_hybrid_ivs()
        for sn in hybrid_sns:
            iv, _ = util.get_iv_for_hybrid_or_module(
                sn, all_ivs=all_hybrid_ivs, KoP="Hybrid"
            )
            KoPs.append("Hybrid")
            labels.append(sn)
            all_hybrid_ivs_to_plot.append(iv)
            currents.append(iv[0])
            voltages.append(iv[1])
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
        exp_text="Preliminary",
        subtitle=False,
        postfix="test_overlay",
        lineThreshold=False,
        spanLabelBackground=False,
    )

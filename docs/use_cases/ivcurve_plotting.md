# IV Curve Plotting

## Data sources

Endpoints storing IV curves are available for Sensors (per pad, or combining them manually into a sum - which is done in hgtd-tools), Hybrids, Modules.

## Using the `ivcuve_overlay.py` script for curve plotting

You can combine an arbitrary number of serial numbers with customizable plotting style / labels.

Execute the following from the hgtd-tools directory (using either Anaconda Prompt or your preferred shell with which you installed miniconda or any environment with the required packages). You do not need to provide all Kinds of Parts for plotting, just one out of Sensor/Hybrid/Module is enough, but indeed you can combine them arbitrarily:

```shell
conda activate hgtd
python ivcurve_overlay.py --sensor_sns "comma-separated,list,of,Sensor,SNs" --hybrid_sns "comma-separated,list,of,Hybrid,SNs" --module_sns "comma-separated,list,of,Module,SNs"
```

This generates (if all data sources could be found) matplotlib / mplhep figures using the pattern `ivs_{custom_strings_depending_on_config}.pdf` and similar in `.png`.

Check out the additional parameters, i.e. here is the current help:

```shell
usage: IV curve plotting wrapper [-h] [--mode-alias {Individual_overlay}] [--sensor_sns SENSOR_SNS] [--hybrid_sns HYBRID_SNS] [--module_sns MODULE_SNS]
                                 [--apply_voltage_correction APPLY_VOLTAGE_CORRECTION] [--sum_hybridIV SUM_HYBRIDIV]
                                 [--diff_sumHybridIV_moduleIV DIFF_SUMHYBRIDIV_MODULEIV] [--custom_labels CUSTOM_LABELS] [--exp_text EXP_TEXT]
                                 [--legend_title LEGEND_TITLE] [--output_postfix OUTPUT_POSTFIX]

options:
  -h, --help            show this help message and exit
  --mode-alias {Individual_overlay}
                        Plotting mode. (Default: Individual_overlay)
  --sensor_sns SENSOR_SNS
                        One or multiple SNs of Sensors to plot (summed) IV curve(s) for; if multiple, comma-separated.
  --hybrid_sns HYBRID_SNS
                        One or multiple SNs of Hybrids to plot IV curve(s) for; if multiple, comma-separated.
  --module_sns MODULE_SNS
                        One or multiple SNs of Modules to plot IV curve(s) for; if multiple, comma-separated.
  --apply_voltage_correction APPLY_VOLTAGE_CORRECTION
                        Correct Module IV by shifting the set voltage by correction term related to resistor on MF (adds additinoal curve).
  --sum_hybridIV SUM_HYBRIDIV
                        Whether to plot the sum of both Hybrid IVs.
  --diff_sumHybridIV_moduleIV DIFF_SUMHYBRIDIV_MODULEIV
                        Whether to plot the difference between sum of both Hybrid IVs and actual Module IV.
  --custom_labels CUSTOM_LABELS
                        One or multiple custom labels; if multiple, comma-separated.
  --exp_text EXP_TEXT   Which kind of plot: Preliminary, Internal (default).
  --legend_title LEGEND_TITLE
                        Custom legend title.
  --output_postfix OUTPUT_POSTFIX
                        Postfix to append to filename.
```

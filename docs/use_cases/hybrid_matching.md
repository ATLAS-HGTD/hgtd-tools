# Hybrid Matching

## Data sources

We restrict to Hybrids

- at a given site (checking the Location field in DB!),
- not yet connected to a Module.

For these, in the present implementation, the connection to Sensors (and to Wafer) is checked to obtain data for matching

- Hybrids not connected to Sensors can not be paired.
- Hybrids connected to Sensors, where the Sensor **is** connected to Wafer, may be paired, if there is `VBD` information available that is stored for that Wafer-Sensor relation.
- Hybrids connected to Sensors, where the Sensor **is not** connected to Wafer, may be paired, if sufficient IV curve information for every Sensor pad is available to determine an overall score.

For the algorithm in the current implementation, we pair by `VBD` of the Sensor. We do not use IV curve information of Hybrids, as there is nearly no data of that kind available to begin with. The data source can be either:

- `VBD_AVERAGE` as entered to the `VBD` table, if the connection to Wafer-Sensor exists, and the value exists for the given Sensor.
  - We use the latest upload, if there are multiple uploads, a higher `RUN_END_TIMESTAMP` or a higher `RUN_NUMBER` wins.
- Average over all individual `VBD` values by manually calculating them for all pads, if these values exist. The method to calculate these values follows the interpolation technique, and uses the per-pad threshold current of $5\cdot10^{-7}\,\mathrm{A}$.
  - Because IV information for Sensors comes in different "flavors" aka `RUN_TYPE`, an assumption had to be made which values to use for the algorithm. `15X15` takes precedence over `15x15`, over `15X1`, over `15x1`, over `1X1`, over `1x1`. Any other run type is not considered.
  - We use the latest upload, if there are multiple uploads, a higher `RUN_END_TIMESTAMP` or a higher `RUN_NUMBER` wins.
- Hybrids for which neither of these techniques yield a score, have to be ignored for the pairing algorithm.

## Using the `hybridmatch.py` script for module assembly

When performing module assembly, you can pair Hybrids that are available for your use case.

Execute the following from the hgtd-tools directory (using either Anaconda Prompt or your preferred shell with which you installed miniconda or any environment with the required packages):

```shell
conda activate hgtd
python hybridmatch.py --location <your-site>
```

This shows the pairing algorithm results in the CLI, but also stores a report for further use as markdown document using the pattern `pairings_Only_Sensor_VBD_closest_{location}.md`.

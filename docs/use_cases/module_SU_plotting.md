# Module SU Plotting

`plot-MO-SU-geo` plots modules into quadrants, given reference csv files containing
the coordinates (module reference points, at the long edge cloest to the IP).

## CSV input

HGTD Group members can get the relevant files from [GitLab (anstein/slotsflextailspreproduction)](https://gitlab.cern.ch/anstein/slotsflextailspreproduction/-/tree/master/SlotTable?ref_type=heads){target="_blank"}.

The names of the csv files are expected to be
`fullBackQuadrant.csv`, `fullFrontQuadrant.csv`
for the slots,
and `Back-Back_to_plot_module_reference.csv`, `Front-Front_to_plot_module_reference.csv`
for the module references.

```shell
    plot-MO-SU-geo --slot-table-dir <your-path> --module-ref-dir <your-path>
```

*Last updated: {{ last_updated }}*

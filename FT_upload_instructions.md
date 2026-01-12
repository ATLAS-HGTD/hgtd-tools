# Flex Tail Measurement Upload

To ensure a proper upload of flex tail measurements to the database first make sure the the data you want to upload are structured such that the database accepts them. For this reason, please have a look at the required structure

|- <measurement_dir>
|   |- IBERT
|   |   |- <serial_number_of_measured_FT1>
|   |   |- <serial_number_of_measured_FT2>
|   |   |- <serial_number_of_measured_FT3>
|   |   |- ...
|   |   |- BERmeasurements.csv
|   |- TDR
|   |   |- <serial_number_of_measured_FT1>
|   |   |- <serial_number_of_measured_FT2>
|   |   |- <serial_number_of_measured_FT3>
|   |   |- ...
|   |   |- Impedances.csv
|   |- Thickness
|   |   |- <serial_number_of_measured_FT1>
|   |   |- <serial_number_of_measured_FT2>
|   |   |- <serial_number_of_measured_FT3>
|   |   |- ...
|   |   |- Thicknesses.csv
|   |- VD
|   |   |- <serial_number_of_measured_FT1>
|   |   |- <serial_number_of_measured_FT2>
|   |   |- <serial_number_of_measured_FT3>
|   |   |- ...
|   |   |- VDmeta.yaml
|   |- flags.csv


## Note

The respective .csv- and .yaml-files are needed, else the upload fails!


If the measurement data are properly set up for upload, please run the corresponding script `upload_FlexTail_measurement.py` for upload. The script iterates over the full content of the <measurement_dir> directory, enters the directory of each measurement type (IBERT, TDR, Thickness, VD) and creates .tar-archives of for each flex tail measurement for upload <serial_number_of_measured_FTx>. Finally, also the .tar-archive of <measurement_dir> is created and the data is uploaded.
An example of how to execute this script is here:

`python upload_FlexTail_measurement.py --analysis-folder FT_Measurements --user-name myName --meas_location test --meas_start_date YYYY-MM-DD --meas_end_date YYYY-MM-DD --run_type FT_characterisation_test --dryrun True`

To break this down:
* `--analysis-folder` defines the path to the folder containing analysis results
* `--user-name` requires your CERN user name for authentication
* `--meas_location` defines the location of measurement
* `--meas_start_date` sets a start date of measurement
* `--meas_end_date` sets an end date of measurement
* `--run_type` sets a custom run type specifying the flex tail measurement
* `--dryrun` defines a test running until the last very step, but does not perform upload

More options for the command line argument parsing are defined in `upload_FlexTail_measurement.py`.

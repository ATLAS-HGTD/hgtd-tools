#!/usr/bin/env python3
import os.path
import shutil
import tarfile
import time
from argparse import ArgumentParser
from pprint import pprint

import requests

import api
import data
import util


INFO = "[INFO] : "
WARNING = util.bcolors.WARNING + "[WARNING] : " + util.bcolors.ENDC
ERROR = util.bcolors.FAIL + "[ERROR] : " + util.bcolors.ENDC


parser = ArgumentParser("CLI for DB Interface")
parser.add_argument(
    "--analysis-folder",
    dest="analysisFolder",
    help="Path to the folder containing analysis results. "
    "Example: if there is a dir FT_Measurements/FT_Measurement_test, you "
    "should put --analysis-folder test for DB upload.",
    default="../FT_Measurements/",
    required=True,
)
parser.add_argument(
    "--user-name",
    dest="userName",
    help="Your CERN user name.",
    default=None,
    required=True,
)
parser.add_argument(
    "--local-folder",
    dest="localFolder",
    help="Path to the folder that will hold temporary DB "
    "data for uploading, including a token for the user. "
    "Set this from where you are calling this script.",
    default="local_info",
)
parser.add_argument(
    "--run_type",
    dest="runType",
    help="Set a custom run type specifying the " "flex tail measurement.",
    default=None,
)
parser.add_argument(
    "--meas_location",
    dest="measurementLocation",
    help="Set a measurement location.",
    default=None,
)
parser.add_argument(
    "--meas_start_date",
    dest="measurementStartDate",
    help="Set a start date of measurement (format: YYYY-MM-DD)",
    default=None,
    required=True,
)
parser.add_argument(
    "--meas_end_date",
    dest="measurementEndDate",
    help="Set an end date of measurement (format: YYYY-MM-DD)",
    default=None,
    required=True,
)
parser.add_argument(
    "--comment", dest="comment", help="[Optional] Set a comment.", default=None
)
parser.add_argument(
    "--dryrun",
    dest="dryrun",
    help="[Optional] Only test running until the last very step, but do not perform upload.",
    default=False,
)
args = parser.parse_args()


def check_existing(sn):
    for ft in existing_flextails:
        if str(ft["serial_number"]) == str(sn):
            return True
    else:
        return False


def prep_tar(analysisInputFolder):
    with tarfile.open(
        localFolder + "/temporary_tar_output.tar", "w", format=tarfile.GNU_FORMAT
    ) as tar:
        tar.add(analysisInputFolder)


def upload(
    data_payload,
    files_payload,
    token,
    dryRun=False,
    endpoint_flextail_bulk_meas="/flex_tail_measurements_new",
):
    last_responseText = api.post_information(
        endpoint_flextail_bulk_meas,
        data_payload,
        dryrun=dryRun,
        content_type="multipart/form-data",
        files_payload=files_payload,
        existing_token=token,
    )
    return last_responseText


# read the arguments submitted from user by CLI
# analysisFolder is supposed to live in a parallel directory ../FT_Measurements/
analysisFolder, localFolder, username, comment = (
    f"../FT_Measurements/{args.analysisFolder}",
    args.localFolder,
    args.userName,
    args.comment,
)
runType, measurementLocation, measurementStartDate, measurementEndDate = (
    args.runType,
    args.measurementLocation,
    args.measurementStartDate,
    args.measurementEndDate,
)
dryrun = args.dryrun


# disentangle user auth from DB token, always get a new DB one
api.user_auth_cli(username, local_folder)
myToken = api.get_access_token()


# create a directory with all measurements as .tar-archives
measurementDirs = [
    name
    for name in os.listdir(analysisFolder)
    if os.path.isdir(os.path.join(analysisFolder, name))
]
# get the current directory and then navigate into the directory where the measurements are stored
os.chdir(f"{analysisFolder}")
# iterate over all different measurement types (IBERT, TDR, Thickness, VD)
for meas_dir in measurementDirs:
    # enter the directory specifying the measurement type and get the subdirectories
    os.chdir(os.path.join(os.getcwd(), f"{os.getcwd()}/{meas_dir}"))
    subpath = os.getcwd()
    subdirs = [
        name
        for name in os.listdir(subpath)
        if os.path.isdir(os.path.join(subpath, name))
    ]
    # iterate over all flex tails stored in separate directories, create a tar archive, navigate back and then delete the directory
    for subdir in subdirs:
        os.chdir(os.path.join(subpath, subdir))
        subsubpath = os.getcwd()
        with tarfile.open(f"{subsubpath}.tgz", "w:gz") as tar:
            tar.add(subsubpath, arcname=f"{subdir}")
        os.chdir("..")
        shutil.rmtree(subdir)
    # get back to the directory to be able to navigate to the next measurement type
    os.chdir("..")

# return back to the hgtd-tools directory
os.chdir(os.path.dirname(__file__))

# for a correct upload of the measurement directory it needs to contain
# the directories VD/ with at least VDmeta.yaml, Thickness/ with at least
# Thicknesses.csv, TDR/ with at least Impedances.csv as well as
# IBERT/ with at least BERmeasurement.csv
if not os.path.isdir(analysisFolder):
    print(
        ERROR
        + f"The analysis folder you want to upload does not exist. "
        + "Please make sure you upload the correct directory."
    )
else:
    if not os.path.isdir(os.path.join(analysisFolder, "VD")):
        print(
            ERROR
            + f"The analysis folder you want to upload is not complete for upload. "
            + "Please make sure the voltage drop measurements are included."
        )
    if not os.path.isdir(os.path.join(analysisFolder, "TDR")):
        print(
            ERROR
            + f"The analysis folder you want to upload is not complete for upload. "
            + "Please make sure the impedance measurements are included."
        )
    if not os.path.isdir(os.path.join(analysisFolder, "Thickness")):
        print(
            ERROR
            + f"The analysis folder you want to upload is not complete for upload. "
            + "Please make sure the thickness measurements are included."
        )
    if not os.path.isdir(os.path.join(analysisFolder, "IBERT")):
        print(
            ERROR
            + f"The analysis folder you want to upload is not complete for upload. "
            + "Please make sure the bit-error-rate measurements are included."
        )
    if not os.path.isfile(os.path.join(analysisFolder, "flags.csv")):
        print(
            ERROR
            + f"The analysis folder you want to upload is not complete for upload. "
            + "Please make sure flags.csv is included."
        )
    else:
        if not os.path.isfile(os.path.join(analysisFolder, "VD/VDmeta.yaml")):
            print(
                ERROR
                + f"The analysis folder you want to upload is not complete for upload. "
                + "Please make sure the VDmeta.yaml is included."
            )
        if not os.path.isfile(os.path.join(analysisFolder, "TDR/Impedances.csv")):
            print(
                ERROR
                + f"The analysis folder you want to upload is not complete for upload. "
                + "Please make sure the Impedances.csv is included."
            )
        if not os.path.isfile(
            os.path.join(analysisFolder, "IBERT/BERmeasurements.csv")
        ):
            print(
                ERROR
                + f"The analysis folder you want to upload is not complete for upload. "
                + "Please make sure the BERmeasurements.csv is included."
            )
        if not os.path.isfile(
            os.path.join(analysisFolder, "Thickness/Thicknesses.csv")
        ):
            print(
                ERROR
                + f"The analysis folder you want to upload is not complete for upload. "
                + "Please make sure the Thicknesses.csv is included."
            )


def find_SN_in_meta(metaFile):
    # enter the metadata file and cheeck for all flex tails to be uploaded
    measured_SNs = []
    with open(metaFile) as metaFile:
        sn = metaFile.readlines()[1:]
        for nth in range(len(sn)):
            # the serial number is defined with a length of 14
            measured_SNs.append(sn[nth][:14])

    return measured_SNs


# all measured flex tails for upload are summarised in flags.csv
measured_SNs = find_SN_in_meta(f"{analysisFolder}/flags.csv")
existing_flextails, last_responseText = util.get_relevant_parts("Flex Tail")


# check if the serial number(s) already exist(s) in the DB
SNs_exist = [check_existing(serial) for serial in measured_SNs]
m_part_ids = [
    m["part_id"] for m in existing_flextails if str(m["serial_number"]) in measured_SNs
]
existing_locations = [
    m["location"]["location_id"]
    for m in existing_flextails
    if str(m["serial_number"]) in measured_SNs
]


if sum(SNs_exist) == len(SNs_exist):
    # first build a new tar (temporary file that will only be used for upload,
    # and deleted afterwards)
    prep_tar(analysisFolder)

    # first find the location ids (defined in data.py) where the flex tail currently are
    current_locs = []
    for sn in measured_SNs:
        current_locs.append(
            [
                ft["location"]["location_id"]
                for ft in existing_flextails
                if str(ft["serial_number"]) == f"{sn}"
            ][0]
        )
    # rename location ids to be compatible with human readable location names
    mapping = {
        1481: "mainz",
        1581: "mascir",
        1541: "cern",
        1521: "test",
    }
    current_locs = [mapping.get(loc, loc) for loc in current_locs]

    possible_locs = ["mainz", "mascir", "cern", "test"]
    if measurementLocation != None:
        if measurementLocation not in possible_locs:
            print(
                WARNING
                + f"Your analysis folder does contain a measurement location: {measurementLocation} that is not allowed. "
                + "You now need to give this information via the command line."
            )
            print(INFO + "Allowed locations: mainz, mascir, cern, test")
            good_loc = False
            while good_loc == False:
                measurementLocation = input(
                    "Type measurement location, choose any of the allowed locations from the list. Example: mainz. "
                    "Confirm with [Enter]: "
                )
                if measurementLocation in possible_locs:
                    # check whether all flex tails used for upload are at the location
                    # specified for measurement location
                    for location, sn in zip(current_locs, measured_SNs):
                        if location != f"{measurementLocation}":
                            print(
                                ERROR
                                + f"The location specified for measurement: {measurementLocation} is not similar to the location: {location} where flex tail: {sn} is currently stored. "
                                "Please make sure the location in the database is up to date."
                            )
                            raise RuntimeError("Location synchronisation failed")
                        else:
                            good_loc = True
                else:
                    print(
                        WARNING
                        + f"Your custom input via command line does contain a measurement location: {measurementLocation} that is not allowed. "
                        + "Please try again."
                    )
        else:
            # check whether all flex tails used for upload are at the location
            # specified for measurement location
            for location, sn in zip(current_locs, measured_SNs):
                if location != f"{measurementLocation}":
                    print(
                        ERROR
                        + f"The location specified for measurement: {measurementLocation} is not similar to the location: {location} where flex tail: {sn} is currently stored. "
                        "Please make sure the location in the database is up to date."
                    )
                    raise RuntimeError("Location synchronisation failed")
    else:
        print(
            WARNING
            + "Your analysis folder does not contain a measurement location. "
            + "You now need to give this information via the command line."
        )
        print(INFO + "Allowed locations: mainz, mascir, cern, test")
        good_loc = False
        while good_loc == False:
            measurementLocation = input(
                "Type measurement location, choose any of the allowed locations from the list. Example: mainz. "
                "Confirm with [Enter]: "
            )
            if measurementLocation in possible_locs:
                # check whether all flex tails used for upload are at the location
                # specified for measurement location
                for location, sn in zip(current_locs, measured_SNs):
                    if location != f"{measurementLocation}":
                        print(
                            ERROR
                            + f"The location specified for measurement: {measurementLocation} is not similar to the location: {location} where flex tail: {sn} is currently stored. "
                            "Please make sure the location in the database is up to date."
                        )
                        raise RuntimeError("Location synchronisation failed")
                    else:
                        good_loc = True
            else:
                print(
                    WARNING
                    + f"Your custom input via command line does contain a measurement location: {measurementLocation} that is not allowed. "
                    + "Please try again."
                )
    # at this point, we should definitely have a valid loc
    loc_id_for_DB = data.relevant_location_IDs_by_shortname[measurementLocation]

    if comment == None:
        comment = ""

    allowedRunTypes = [
        "FT_characterisation_mainz",
        "FT_characterisation_mainz_irradiated",
        "FT_characterisation_morocco",
        "FT_characterisation_morocco_irradiated",
        "FT_characterisation_cern",
        "FT_characterisation_cern_irradiated",
        "FT_characterisation_test",
        "FT_characterisation_test_irradiated",
    ]
    if runType == None:
        print(
            ERROR + f"You need to specify the run type! "
            "Please choose from the list of allowed run types. "
            "Allowed run types are: FT_characterisation_mainz, FT_characterisation_mainz_irradiated, FT_characterisation_morocco, FT_characterisation_morocco_irradiated, FT_characterisation_cern, FT_characterisation_cern_irradiated, FT_characterisation_test, FT_characterisation_test_irradiated."
        )
        good_runType = False
        while good_runType == False:
            runType = input(
                "Give a run type, choose any of the allowed run types from the list. Example: FT_characterisation_mainz. "
                "Confirm with [Enter]: "
            )
            if runType in allowedRunTypes:
                if runType.split("_")[2] == measurementLocation:
                    good_runType = True
                else:
                    print(
                        WARNING
                        + f"Your custom input via command line does contain a valid run type: {runType} that does not correspond to the measurement location: {measurementLocation}. "
                        + "Please try again."
                    )
            else:
                print(
                    WARNING
                    + f"Your custom input via command line does not contain a valid run type: {runType} that is allowed. "
                    + "Please try again."
                )
    if runType != None:
        if runType not in allowedRunTypes:
            print(
                WARNING + f"The run type you chose {runType} is not allowed! "
                "Please choose from the list of allowed run types. "
                "Allowed run types are: FT_characterisation_mainz, FT_characterisation_mainz_irradiated, FT_characterisation_morocco, FT_characterisation_morocco_irradiated, FT_characterisation_cern, FT_characterisation_cern_irradiated, FT_characterisation_test, FT_characterisation_test_irradiated."
            )
            good_runType = False
            while good_runType == False:
                runType = input(
                    "Give a run type, choose any of the allowed run types from the list. Example: FT_characterisation_mainz. "
                    "Confirm with [Enter]: "
                )
                if runType in allowedRunTypes:
                    if runType.split("_")[2] == measurementLocation:
                        good_runType = True
                    else:
                        print(
                            WARNING
                            + f"Your custom input via command line does contain a valid run type: {runType} that does not correspond to the measurement location: {measurementLocation}. "
                            + "Please try again."
                        )
                else:
                    print(
                        WARNING
                        + f"Your custom input via command line does contain a valid run type: {runType} that is not allowed. "
                        + "Please try again."
                    )

    files_payload = {
        "data_file": (
            "temporary_tar_output.tar",
            open(localFolder + "/temporary_tar_output.tar", "rb"),
        )
    }
    data_payload = {
        "is_record_deleted": "F",  # we want to record this as something that is not "deleted", so we put "F"
        "location": loc_id_for_DB,  # measurement site / location (could be your institute location)
        "run_type": runType,  # measurement type, e.g. after irradiation etc.
        "run_begin_timestamp": measurementStartDate,  # begin of measurement data, usual time and date format
        "run_end_timestamp": measurementEndDate,  # end of measurement data, usual time and date format
        "comment_description": comment,  # comment
        "record_insertion_user": username,
    }  # to store who did this upload in the database

    print(INFO + "These are the data to be uploaded, please check:")
    pprint(data_payload)
    if not dryrun:
        upload_response = upload(data_payload, files_payload, myToken)
        if upload_response[:2] != "20":
            print(
                ERROR
                + "Data was not uploaded successfully. "
                + "Inspect the content of the temporary tar file for potential mistakes and check if the SN exists in the DB."
                + f"\n{last_responseText}"
            )
            raise RuntimeError("Upload failed")
        else:
            print(
                INFO + "Data successfully uploaded, deleting temporary tar archive now."
            )
            os.remove(localFolder + "/temporary_tar_output.tar")
    else:
        print(INFO + "Concluding dryrun without uploading.")
else:
    for existance_i in range(len(SNs_exist)):
        if not SNs_exist[existance_i]:
            print(
                ERROR
                + f"The serial number {measured_SNs[existance_i]} of your flex tail does not exist in the ProdDB parts list. "
                + "You need to add this serial number first via https://nginx-hgtddb.app.cern.ch/parts "
                + "before you can upload measurements for this part or correct the SN in your config."
            )
    raise RuntimeError("SN existance check failed for at least one SN")

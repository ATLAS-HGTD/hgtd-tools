import json
import textwrap
import webbrowser

import numpy as np
import requests

import api
import data

# === Helper for argparse

# Source - https://stackoverflow.com/a/43357954
# Posted by Maxim, modified by community. See post 'Timeline' for change history
# Retrieved 2026-02-04, License - CC BY-SA 4.0


def str2bool(v):
    if isinstance(v, bool):
        return v
    if v.lower() in ("yes", "true", "t", "y", "1"):
        return True
    elif v.lower() in ("no", "false", "f", "n", "0"):
        return False
    else:
        raise argparse.ArgumentTypeError("Boolean value expected.")


# from : https://svn.blender.org/svnroot/bf-blender/trunk/blender/build_files/scons/tools/bcolors.py
class bcolors:
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"


# === Operations with standard objects (lists, dicts, strings etc.)
def flatten(xss):
    return [x for xs in xss for x in xs]


def get_sorted_list_of_lists_by_Nth_column(unsorted_list, column):
    sortList = unsorted_list.copy()
    sortList.sort(key=lambda x: x[column])
    return sortList


def get_relevant_SNs_and_partIDs(partsList):
    these_SNs_and_partIDs = get_sorted_list_of_lists_by_Nth_column(
        [[pL["serial_number"], pL["part_id"]] for pL in partsList], 0
    )
    return these_SNs_and_partIDs


# https://stackoverflow.com/a/45287550
class CustomTextWrapper(textwrap.TextWrapper):
    def wrap(self, text):
        split_text = text.split("\n")
        lines = [
            line
            for para in split_text
            for line in textwrap.TextWrapper.wrap(self, para)
        ]
        return lines


### function to get the first 8 chars of MO SNs
def get_MO_SN_prefix(site, prod, batch):
    if site not in data.MO_site_id.keys():
        raise RuntimeError(f"Provided site {site} is invalid")
    if prod not in data.MO_prod_id.keys():
        raise RuntimeError(f"Provided prod {prod} is invalid")

    if site == "test":
        leading = "99"
    else:
        leading = "20"

    k = data.MO_site_id[site.lower()]
    p = data.MO_prod_id[prod.lower()]
    b = str(batch)
    if len(b) > 1:
        raise RuntimeError(
            f"SN : batch should be a single character but you passed {b}"
        )
    if not b.isalnum():
        raise RuntimeError(f"SN : batch should be alphanumeric but you passed {b}")
    snprefix = f"{leading}WMO{k}{p}{b}"
    return snprefix.upper()


# === Operations with canvas objects
def isInSlot(rect, x, y):
    isInSlot = False
    left = rect["x"]
    right = rect["x"] + rect["w"]
    top = rect["y"]
    bottom = rect["y"] + rect["h"]
    if right >= x and left <= x and bottom >= y and top <= y:
        isInSlot = True
    return isInSlot


# === Operations with API or Browser
def open_webbrowser_with_url(url, debug=False, noExtraPrefix=False):
    if noExtraPrefix:
        if debug:
            print(f">>> Opening {url} in webbrowser...")
        webbrowser.open_new_tab(url)
    else:
        if debug:
            print(f">>> Opening {api.frontendUrlPrefix + url} in webbrowser...")
        webbrowser.open_new_tab(api.frontendUrlPrefix + url)


def delete_children(par_partID, onlyNonDeleted=True, ofKind="all", dryrun=False):
    try:
        partstree, responseText = api.fetch_information(f"/childrenlist/{par_partID}/")
        if onlyNonDeleted:
            interesting_partstree = []
            for p in partstree:
                if str(p["is_record_deleted"]) == "F":
                    if ofKind == "all" or str(
                        data.KoPID_from_partKoPName[ofKind]
                    ) == str(p["part"]["kind_of_part"]["kind_of_part_id"]):
                        interesting_partstree.append(p)
        else:
            interesting_partstree = partstree
            del partstree
        for ip in interesting_partstree:
            responseText = api.delete_information(
                f"/partstreedelete/{ip['record_id']}/", dryrun=dryrun
            )
        return responseText
    except (
        requests.exceptions.HTTPError,
        requests.exceptions.ConnectionError,
        requests.exceptions.Timeout,
        requests.exceptions.RequestException,
    ) as e:
        raise e
    except ValueError as e:
        raise e


def delete_parents(chi_partID, onlyNonDeleted=True, ofKind="all", dryrun=False):
    try:
        partstree, responseText = api.fetch_information(f"/parentslist/{chi_partID}/")
        if onlyNonDeleted:
            interesting_partstree = []
            for p in partstree:
                if str(p["is_record_deleted"]) == "F":
                    if ofKind == "all" or str(
                        data.KoPID_from_partKoPName[ofKind]
                    ) == str(p["part_parent"]["kind_of_part"]["kind_of_part_id"]):
                        interesting_partstree.append(p)
        else:
            interesting_partstree = partstree
            del partstree
        for ip in interesting_partstree:
            responseText = api.delete_information(
                f"/partstreedelete/{ip['record_id']}/", dryrun=dryrun
            )
        return responseText
    except (
        requests.exceptions.HTTPError,
        requests.exceptions.ConnectionError,
        requests.exceptions.Timeout,
        requests.exceptions.RequestException,
    ) as e:
        raise e
    except ValueError as e:
        raise e


def get_info_of_part_id(part_id):
    try:
        details, responseText = api.fetch_information(f"/part/{part_id}/")
        return details, responseText
    except (
        requests.exceptions.HTTPError,
        requests.exceptions.ConnectionError,
        requests.exceptions.Timeout,
        requests.exceptions.RequestException,
    ) as e:
        raise e
    except ValueError as e:
        raise e


def get_attributes_of_part_id(part_id):
    try:
        attributes, responseText = api.fetch_information(f"/partattrlist/{part_id}/")
        return attributes, responseText
    except (
        requests.exceptions.HTTPError,
        requests.exceptions.ConnectionError,
        requests.exceptions.Timeout,
        requests.exceptions.RequestException,
    ) as e:
        raise e
    except ValueError as e:
        raise e


def get_measurement_types_of_module_SN(part_SN):
    try:
        measurements, responseText = api.fetch_information(
            f"/module_threshold_run_type?serial_number={part_SN}"
        )
        return measurements, responseText
    except (
        requests.exceptions.HTTPError,
        requests.exceptions.ConnectionError,
        requests.exceptions.Timeout,
        requests.exceptions.RequestException,
    ) as e:
        raise e
    except ValueError as e:
        raise e


def get_SN_of_parts(parts):
    return [part["serial_number"] for part in parts]


def select_parts(
    parts,
    location_shortname=None,
    location_name=None,
    location_id=None,
    manu_shortname=None,
    manu_name=None,
    manu_id=None,
    sn_does_include=None,
    name_label_does_include=None,  # case-insensitive
    name_label_does_not_include=None,  # case-insensitive
    check_valid_SN_latest_spec=False,
    check_invalid_SN_latest_spec=False,
    check_fake_SN=False,
    no_parents_ofKind=None,
    no_children_ofKind=None,
    has_parents_ofKind=None,
    has_children_ofKind=None,
):
    if location_shortname != None:
        parts = [
            iP
            for iP in parts
            if str(iP["location"]["location_id"])
            == str(data.relevant_location_IDs_by_shortname[location_shortname])
        ]
    if location_name != None:
        parts = [
            iP
            for iP in parts
            if str(iP["location"]["location_name"]) == str(location_name)
        ]
    if location_id != None:
        parts = [
            iP for iP in parts if str(iP["location"]["location_id"]) == str(location_id)
        ]
    if manu_shortname != None:
        parts = [
            iP
            for iP in parts
            if str(iP["manufacturer"]["manufacturer_id"])
            == str(data.relevant_manufacturer_IDs_by_shortname[manu_shortname])
        ]
    if manu_name != None:
        parts = [
            iP
            for iP in parts
            if str(iP["manufacturer"]["manufacturer_name"]) == str(manu_name)
        ]
    if manu_id != None:
        parts = [
            iP
            for iP in parts
            if str(iP["manufacturer"]["manufacturer_id"]) == str(manu_id)
        ]
    if sn_does_include != None:
        parts = [
            iP for iP in parts if str(sn_does_not_include) in str(iP["serial_number"])
        ]
    if name_label_does_include != None:  # case-insensitive
        parts = [
            iP
            for iP in parts
            if str(name_label_does_not_include).lower() in str(iP["name_label"]).lower()
        ]
    if name_label_does_not_include != None:  # case-insensitive
        parts = [
            iP
            for iP in parts
            if str(name_label_does_not_include).lower()
            not in str(iP["name_label"]).lower()
        ]
    if check_valid_SN_latest_spec == True:
        parts = [
            iP for iP in parts if check_SN_valid(str(iP["serial_number"]))[0] == True
        ]
    if check_invalid_SN_latest_spec == True:
        parts = [
            iP
            for iP in parts
            if (str(iP["serial_number"])[:3] == "20W")
            and check_SN_valid(str(iP["serial_number"]))[0] == False
        ]
    if check_fake_SN == True:
        parts = [iP for iP in parts if (str(iP["serial_number"])[:3] != "20W")]
    if no_parents_ofKind != None:
        parts = [
            iP
            for iP in parts
            if get_parents(iP["part_id"], ofKind=no_parents_ofKind)[0] == []
        ]
    if no_children_ofKind != None:
        parts = [
            iP
            for iP in parts
            if get_children(iP["part_id"], ofKind=no_children_ofKind)[0] == []
        ]
    if has_parents_ofKind != None:
        parts = [
            iP
            for iP in parts
            if len(get_parents(iP["part_id"], ofKind=has_parents_ofKind)[0]) > 0
        ]
    if has_children_ofKind != None:
        parts = [
            iP
            for iP in parts
            if len(get_children(iP["part_id"], ofKind=has_children_ofKind)[0]) > 0
        ]
    return parts


def get_relevant_parts(
    partKoP_shortname, onlyNonDeleted=True, getFullAttributes=False, useLocal=False
):
    KoP_ID = data.KoPID_from_partKoPName[partKoP_shortname]
    retrieve = "partattributelistbykop" if getFullAttributes else "partslistbykop"
    try:
        if not useLocal:
            if partKoP_shortname == "Slot":
                slots, responseText = api.fetch_information(
                    f"/partslistbykop/{KoP_ID}/"
                )
                these_parts, responseText = api.fetch_information(
                    f"/partattributelistbykop/{KoP_ID}/"
                )
                with open("./local/all_slots.json", "w") as f:
                    json.dump(these_parts, f)
                with open("./local/slots.json", "w") as f:
                    json.dump(slots, f)
                for alSl in these_parts:
                    for s in slots:
                        if str(alSl["part_serial_number"]) == str(s["serial_number"]):
                            alSl["part_id"] = s["part_id"]

            else:
                these_parts, responseText = api.fetch_information(
                    f"/{retrieve}/{KoP_ID}/"
                )
                if retrieve != "partattributelistbykop":
                    these_parts = [
                        tP for tP in these_parts if tP["is_record_deleted"] == "F"
                    ]
        else:
            # slot table is the one table that basically only acts as a static lookup;
            # contains the various location definitions (local & global) but during
            # the lifetime of the detector, the Slot table itself stays constant
            # => can be stored as a local file, don't need to load it freshly each time
            # (at least that's my understanding now during R&D of the database tools)

            # the following two files result from dumping the API-accessed files
            """
            with open('./local/all_slots.json') as allSlotsJson:
                these_parts, responseText = json.load(allSlotsJson), '200: Local File'
            with open('./local/slots.json') as slotsJson:
                slots, responseText = json.load(slotsJson), '200: Local File'

            for alSl in these_parts:
                for s in slots:
                    if alSl['part_serial_number'] == s['serial_number']:
                        alSl['part_id'] = s['part_id']
            """

            # the following two files result from manually downloading, exporting and converting them
            # this was done because the API endpoint above results in OOMKilled errors!
            with open(
                "./local/Slot_Table_fullNovember2025_demoV1V2_module0.json"
            ) as allSlotsJson:
                these_parts, responseText = json.load(allSlotsJson), "200: Local File"
            with open(
                "./local/Slot_fullNovember2025_demoV1V2_module0.json"
            ) as slotsJson:
                slots, responseText = json.load(slotsJson), "200: Local File"

            for alSl in these_parts:
                for s in slots:
                    if str(alSl["part_serial_number"]) == str(s["Serial #"]):
                        alSl["part_id"] = s["Part ID"]
        return these_parts, responseText
    except (
        requests.exceptions.HTTPError,
        requests.exceptions.ConnectionError,
        requests.exceptions.Timeout,
        requests.exceptions.RequestException,
    ) as e:
        raise e
    except ValueError as e:
        raise e


def get_parents(chi_partID, onlyNonDeleted=True, ofKind="all"):
    try:
        partstree, responseText = api.fetch_information(f"/parentslist/{chi_partID}/")
        if onlyNonDeleted:
            interesting_partstree = []
            for p in partstree:
                if str(p["is_record_deleted"]) == "F":
                    if ofKind == "all" or str(
                        data.KoPID_from_partKoPName[ofKind]
                    ) == str(p["part_parent"]["kind_of_part"]["kind_of_part_id"]):
                        interesting_partstree.append(p)
            return interesting_partstree, responseText
        else:
            return partstree, responseText
    except (
        requests.exceptions.HTTPError,
        requests.exceptions.ConnectionError,
        requests.exceptions.Timeout,
        requests.exceptions.RequestException,
    ) as e:
        raise e
    except ValueError as e:
        raise e


# this is quicker (a bit) because it only reads the children of the given parent
def get_children(par_partID, onlyNonDeleted=True, ofKind="all"):
    try:
        partstree, responseText = api.fetch_information(f"/childslist/{par_partID}/")
        if onlyNonDeleted:
            interesting_partstree = []
            for p in partstree:
                if str(p["is_record_deleted"]) == "F":
                    if ofKind == "all" or str(
                        data.KoPID_from_partKoPName[ofKind]
                    ) == str(p["part"]["kind_of_part"]["kind_of_part_id"]):
                        interesting_partstree.append(p)
            return interesting_partstree, responseText
        else:
            return partstree, responseText
    except (
        requests.exceptions.HTTPError,
        requests.exceptions.ConnectionError,
        requests.exceptions.Timeout,
        requests.exceptions.RequestException,
    ) as e:
        raise e
    except ValueError as e:
        raise e


def get_locations(onlyNonDeleted=True):
    try:
        locations, responseText = api.fetch_information(f"/locations")
        if onlyNonDeleted:
            interesting_locations = []
            for m in locations:
                if str(m["is_record_deleted"]) == "F":
                    interesting_locations.append(m)
            return interesting_locations, responseText
        else:
            return locations, responseText
    except (
        requests.exceptions.HTTPError,
        requests.exceptions.ConnectionError,
        requests.exceptions.Timeout,
        requests.exceptions.RequestException,
    ) as e:
        raise e
    except ValueError as e:
        raise e


def get_manufacturers(onlyNonDeleted=True):
    try:
        manufacturers, responseText = api.fetch_information(f"/manufacturers")
        if onlyNonDeleted:
            interesting_manufacturers = []
            for m in manufacturers:
                if str(m["is_record_deleted"]) == "F":
                    interesting_manufacturers.append(m)
            return interesting_manufacturers, responseText
        else:
            return manufacturers, responseText
    except (
        requests.exceptions.HTTPError,
        requests.exceptions.ConnectionError,
        requests.exceptions.Timeout,
        requests.exceptions.RequestException,
    ) as e:
        raise e
    except ValueError as e:
        raise e


# this loads the full partstree, quite slow (and big!)
def load_partstree(onlyNonDeleted=True, useLocal=False):
    try:
        if not useLocal:
            partstree, responseText = api.fetch_information(f"/partstreelist")
            with open("./local/partstreelist.json", "w") as f:
                json.dump(partstree, f)
        else:
            # WARNING: relations OTOH are dynamic in nature and should not be accidentally
            # picked up from possibly outdated local files!!!
            # Please use for testing purposes only, you should now not need this anymore.
            with open("./local/partstreelist.json") as partstreeJson:
                partstree, responseText = json.load(partstreeJson), "200: Local File"
        interesting_partstree = []
        for p in partstree:
            if str(p["is_record_deleted"]) == "F":
                if (
                    p["part"]["kind_of_part"]["kind_of_part_id"] == 1005
                    and p["part_parent"]["kind_of_part"]["kind_of_part_id"] == 2407
                ):
                    interesting_partstree.append(p)
        return interesting_partstree, responseText
    except (
        requests.exceptions.HTTPError,
        requests.exceptions.ConnectionError,
        requests.exceptions.Timeout,
        requests.exceptions.RequestException,
    ) as e:
        raise e
    except ValueError as e:
        raise e


# this checks if a SN is valid, i.e. fulfills the ATLAS convention
def check_SN_valid(snIn):
    messageOut = "Invalid Serial Number"
    lengthMessageOut = ""
    propertiesOut = ""
    if (snIn[:3] == "99W") or (snIn[:3] == "98W"):
        messageOut = "This is a test SN only / dummy placeholder for DB development."
        return False, messageOut
    elif snIn[:3] == "20W":
        messageOut = "Attempting to decode ATLAS SN"
        if len(snIn) < 14:
            lengthMessageOut = "ATLAS SN must have 14 digits. Found too few."
            return False, lengthMessageOut
        elif len(snIn) > 14:
            lengthMessageOut = "ATLAS SN must have 14 digits. Found too many."
            return False, lengthMessageOut
        else:
            # check for Sensor (sensor is special, it has only one digit for its component type)
            # first make sure to not get a Support Unit (SU) which also starts with S
            if (snIn[3] == "S") and (snIn[4] != "U"):
                # either Sensor or Sensor Wafer
                if snIn[4] == "0":
                    # Wafer
                    messageOut = "Attempting to decode Wafer SN"
                    try:
                        # note, every variable that is called somethingExplainer
                        # is just for human-readable decoding with a meaning
                        # not necessary to be stored in the DB
                        # (component groups should complain if they should be stored)
                        manu = snIn[5]
                        if manu == "0":
                            manuExplainer = "IHEP-IME"
                        elif manu == "1":
                            manuExplainer = "USTC-IME"
                        else:
                            manuExplainer = "Unknown Manufacturer / Vendor attribute!"
                            return False, manuExplainer
                    except:
                        messageOut = "Failed to decode Wafer SN, check if you used this pattern: 20WS0MPBBONNNN"
                        return False, messageOut
                else:
                    # Sensor
                    try:
                        manu = snIn[4]
                        if manu == "1":
                            manuExplainer = "IHEP-IME Pre-production"
                        elif manu == "2":
                            manuExplainer = "IHEP-IME Production"
                        elif manu == "3":
                            manuExplainer = "USTC-IME Pre-production"
                        elif manu == "4":
                            manuExplainer = "USTC-IME Production"
                        else:
                            manuExplainer = "Unknown Sensor type attribute!"
                            return False, manuExplainer
                        stype = snIn[5]
                        if stype == "0":
                            stypeExplainer = "main sensor"
                        elif stype == "1":
                            stypeExplainer = "QC-TS of main sensor"
                        elif stype == "2":
                            stypeExplainer = "main partial sensor"
                        elif stype == "3":
                            stypeExplainer = "QC-TS of main partial sensor"
                        else:
                            stypeExplainer = "Unknown Sensor type attribute!"
                            return False, stypeExplainer
                        batchn = f"{snIn[6]}{snIn[7]}"
                        wafern = f"{snIn[8]}{snIn[9]}{snIn[10]}{snIn[11]}"
                        locInWaf = f"{snIn[12]}{snIn[13]}"
                        if int(locInWaf) <= 52:
                            locInWafExplainer = "main sensor"
                        elif int(locInWaf) >= 61:
                            locInWafExplainer = "partial sensor"
                        else:
                            locInWafExplainer = "Unknown Location in wafer attribute!"
                            return False, locInWafExplainer
                        propertiesOut = (
                            f"Manufacturer / Vendor: {manu} ({manuExplainer}), Sensor type: {stype} ({stypeExplainer}), "
                            f"Batch number: {batchn}, Wafer number: {wafern}, Location in wafer: {locInWaf} ({locInWafExplainer})"
                        )
                        if lengthMessageOut == "":
                            messageOut = "Successfully decoded Sensor SN"
                        else:
                            messageOut = ""
                    except Exception:
                        messageOut = "Failed to decode Sensor SN, check if you used this pattern: 20WSMEBBNNNNXY"
                        return False, messageOut
            elif snIn[3] == "F" and snIn[4] == "T":
                messageOut = "Attempting to decode Flex Tail SN"
                try:
                    manu = snIn[5]
                    snGeneration = 2  # 0: pre 24052023, 1: post 24052023 but pre 2025, 1.2: new demonstrator order 2024/2025, 2 (default): from 2025 for (pre-)production
                    if manu == "G":
                        manuExplainer = "Germany"
                    elif manu == "C":
                        manuExplainer = "China"
                    elif manu == "S":
                        manuExplainer = "Slovenia"
                    elif manu == "M":
                        manuExplainer = "Morocco"
                    elif manu == "1":
                        snGeneration = 0
                        manuExplainer = "Germany"
                    elif manu == "2":
                        snGeneration = 0
                        manuExplainer = "China"
                    elif manu == "3":
                        snGeneration = 0
                        manuExplainer = "Slovenia"
                    else:
                        manuExplainer = "Unknown Vendor attribute!"
                        return False, manuExplainer
                    digitSeven = snIn[6]
                    digitEight = snIn[7]
                    if digitEight == "D" and int(digitSeven) <= 2:
                        snGeneration = 1
                        messageOut = "Recognize old Flex Tail SN definition, used for demonstrator from 24.05.2023 until 2024"
                        prodExplainer = "demonstrator"
                    elif digitEight == "1" and digitSeven == "1":
                        snGeneration = 1
                        messageOut = "Recognize old Flex Tail SN definition, used for demonstrator from 24.05.2023 until 2024"
                        prodExplainer = "demonstrator"
                    elif digitEight == "2" and digitSeven == "1":
                        snGeneration = 1.2
                        messageOut = "Recognize old Flex Tail SN definition, used for new demonstrator order 2024/2025"
                        prodExplainer = "demonstrator"
                    else:
                        if snGeneration == 2:
                            messageOut = "Recognize newest Flex Tail SN definition, used from 2025 for (pre-)production as documented in ATL-COM-HGTD-2024-026"
                        else:
                            messageOut = "Recognize old Flex Tail SN definition, used for demonstrator until 24.05.2023"
                    readout = f"{snIn[8]}"
                    if readout == "R":
                        readoutExplainer = "single readout"
                    elif readout == "F":
                        readoutExplainer = "full readout"
                    else:
                        readoutExplainer = "Unknown Readout attribute!"
                        return False, readoutExplainer
                    fttype = f"{snIn[9]}{snIn[10]}"  # what they mean is different for each generation
                    fttypeExplainer = "Small length type: long cable, conversion to mm found in Slot table for vessel D (demonstrator) or A/C (production), work in progress"
                    ftcounter = f"{snIn[11]}{snIn[12]}{snIn[13]}"
                    # now we know the SN generation, we can proceed
                    if snGeneration == 2:
                        prod = digitSeven
                        if prod == "M":
                            prodExplainer = "Main production"
                        elif prod == "P":
                            prodExplainer = "Pre-production"
                        elif prod == "D":
                            prodExplainer = "demonstrator"
                        elif prod == "T":
                            prodExplainer = "test"
                        elif prod == "O":
                            prodExplainer = "other"
                        else:
                            prodExplainer = "Unknown Production attribute!"
                            return False, prodExplainer
                        batchn = digitEight
                    elif snGeneration == 1.2:
                        prod = digitSeven
                        # prodExplainer already known above
                        batchn = digitEight
                    elif snGeneration == 1:
                        prod = digitEight
                        # prodExplainer already known above
                        batchn = digitSeven
                    else:
                        prod = digitEight
                        if prod == "0":
                            prodExplainer = "Main production"
                        elif prod == "1":
                            prodExplainer = "demonstrator"
                        elif prod == "2":
                            prodExplainer = "test"
                        elif prod == "3":
                            prodExplainer = "other"
                        else:
                            prodExplainer = "Unknown Production attribute!"
                            return False, prodExplainer
                        batchn = digitSeven
                    propertiesOut = f"Manufacturer / Vendor: {manu} ({manuExplainer}), Production: {prod} ({prodExplainer}), Batch number: {batchn}, Readout: {readout}, Type: {fttype} ({fttypeExplainer}), Counter: {ftcounter}"
                    if lengthMessageOut == "":
                        if snGeneration == 2:
                            messageOut = "Successfully decoded newest Flex Tail SN definition, used from 2025 for (pre-)production as documented in ATL-COM-HGTD-2024-026"
                        elif snGeneration == 1.2:
                            messageOut = "Successfully decoded old Flex Tail SN definition, used for new demonstrator order 2024/2025"
                        elif snGeneration == 1:
                            messageOut = "Successfully decoded old Flex Tail SN definition, used for demonstrator from 24.05.2023 until 2024"
                        else:
                            messageOut = "Successfully decoded old Flex Tail SN definition, used for demonstrator until 24.05.2023"
                    else:
                        messageOut = ""
                except:
                    messageOut = "Failed to decode FT SN, check if you used this pattern: 20WFTMBPQTTNNN (or an older SN pattern for the demonstrator)"
                    return False, messageOut
            elif snIn[3] == "M" and snIn[4] == "O":
                messageOut = "Attempting to decode Module SN"
                try:
                    as_ = snIn[5]
                    if as_ == "F":
                        asExplainer = "IFAE"
                    elif as_ == "H":
                        asExplainer = "IHEP"
                    elif as_ == "J":
                        asExplainer = "IJCLab"
                    elif as_ == "M":
                        asExplainer = "Mainz"
                    elif as_ == "A":
                        asExplainer = "MAScIR"
                    elif as_ == "U":
                        asExplainer = "USTC"
                    else:
                        asExplainer = "Unknown Assembly site attribute!"
                        return False, asExplainer
                    prod = snIn[6]
                    if prod == "M":
                        prodExplainer = "Main production"
                    elif prod == "P":
                        prodExplainer = "Pre-production"
                    elif prod == "D":
                        prodExplainer = "demonstrator"
                    elif prod == "T":
                        prodExplainer = "test"
                    elif prod == "O":
                        prodExplainer = "other"
                    else:
                        prodExplainer = "Unknown Production attribute!"
                        return False, prodExplainer
                    batchn = snIn[7]
                    counter = "".join(snIn[8:14])
                    propertiesOut = f"Assembly site: {as_} ({asExplainer}), Production: {prod} ({prodExplainer}), Batch number: {batchn}, Counter: {counter}"
                    if lengthMessageOut == "":
                        messageOut = "Successfully decoded Module SN"
                    else:
                        messageOut = ""
                except Exception:
                    messageOut = "Failed to decode Module SN, check if you used this pattern: 20WMOKPBNNNNNN"
                    return False, messageOut
            elif snIn[3] == "H":
                messageOut = "Attempting to decode Hybrid SN"
                try:
                    manu_step2 = snIn[4]
                    if manu_step2 == "N":
                        manu_step2Explainer = "NCAP"
                    elif manu_step2 == "P":
                        manu_step2Explainer = "Patech"
                    else:
                        manu_step2Explainer = (
                            "Unknown Assembly site attribute for Step 2!"
                        )
                        return False, manu_step2Explainer
                    manu_step3 = snIn[5]
                    if manu_step3 == "N":
                        manu_step3Explainer = "NCAP"
                    elif manu_step3 == "D":
                        manu_step3Explainer = "Disco"
                    elif manu_step3 == "M":
                        manu_step3Explainer = "micropack"
                    else:
                        manu_step3Explainer = (
                            "Unknown Assembly site attribute for Step 3!"
                        )
                        return False, manu_step3Explainer
                    manu_step4 = snIn[6]
                    if manu_step4 == "N":
                        manu_step4Explainer = "NCAP"
                    elif manu_step4 == "I":
                        manu_step4Explainer = "IFAE"
                    elif manu_step4 == "C":
                        manu_step4Explainer = "CNM"
                    else:
                        manu_step4Explainer = (
                            "Unknown Assembly site attribute for Step 4!"
                        )
                        return False, manu_step4Explainer
                    prod = snIn[7]
                    if prod == "M" or prod == "0":
                        prodExplainer = "Main production"
                    elif prod == "P":
                        prodExplainer = "Pre-production"
                    elif prod == "D" or prod == "1":
                        prodExplainer = "demonstrator"
                    elif prod == "T" or prod == "2":
                        prodExplainer = "test"
                    elif prod == "O" or prod == "3":
                        prodExplainer = "other"
                    else:
                        prodExplainer = "Unknown Production attribute!"
                        return False, prodExplainer
                    batchn = f"{snIn[8]}{snIn[9]}"
                    counter = "".join(snIn[10:14])
                    propertiesOut = f"Manufacturer / Vendor (Step 2): {manu_step2} ({manu_step2Explainer}), Manufacturer / Vendor (Step 3): {manu_step3} ({manu_step3Explainer}), Manufacturer / Vendor (Step 4): {manu_step4} ({manu_step4Explainer}), Production: {prod} ({prodExplainer}), Batch number: {batchn}, Counter: {counter}"
                    if lengthMessageOut == "":
                        messageOut = "Successfully decoded Hybrid SN"
                    else:
                        messageOut = ""
                except Exception:
                    messageOut = "Failed to decode Hybrid SN, check if you used this pattern: 20WHMMMPBBNNNN"
                    return False, messageOut
            elif snIn[3] == "A" and snIn[4] == "S":
                messageOut = "Attempting to decode ASIC SN"
                try:
                    tests = snIn[5]
                    if tests == "H":
                        testsExplainer = "IHEP"
                    elif tests == "J":
                        testsExplainer = "IJCLab"
                    else:
                        testsExplainer = "Unknown Assembly site attribute!"
                        return False, testsExplainer
                    prod = snIn[6]
                    if prod in ("M"):
                        prodExplainer = "Main production"
                    elif prod == "P":
                        prodExplainer = "Pre-production"
                    else:
                        prodExplainer = "Unknown Production attribute!"
                        return False, prodExplainer
                    waferID = "".join(snIn[7:14])
                    waferNr = "".join(snIn[7:11])
                    chipID = "".join(snIn[11:14])
                    propertiesOut = f"Test site: {tests} ({testsExplainer}), Production: {prod} ({prodExplainer}), Wafer_ID: {waferID}, Wafer_Nr: {waferNr}, Chip_ID: {chipID}"
                    if lengthMessageOut == "":
                        messageOut = "Successfully decoded ASIC SN"
                    else:
                        messageOut = ""
                except Exception:
                    messageOut = "Failed to decode ASIC SN, check if you used this pattern: 20WASVPDDDDCCC"
                    return False, messageOut
            elif snIn[3] == "M" and snIn[4] == "F":
                messageOut = "Attempting to decode Module Flex SN"
                try:
                    manu = snIn[5]
                    if manu == "H":
                        manuExplainer = "IHEP"
                    else:
                        manuExplainer = "Unknown Assembly site attribute!"
                        return False, manuExplainer
                    prod = snIn[6]
                    if prod in ("M", "0"):
                        prodExplainer = "Main production"
                    elif prod == "P":
                        prodExplainer = "Pre-production"
                    elif prod in ("D", "1"):
                        prodExplainer = "demonstrator"
                    elif prod in ("T", "2"):
                        prodExplainer = "test"
                    elif prod in ("O", "3"):
                        prodExplainer = "other"
                    else:
                        prodExplainer = "Unknown Production attribute!"
                        return False, prodExplainer
                    batchn = snIn[7]
                    grounding = snIn[8]
                    counter = "".join(snIn[9:14])
                    propertiesOut = f"Manufacturer / Vendor: {manu} ({manuExplainer}), Production: {prod} ({prodExplainer}), Batch number: {batchn}, Grounding scheme: {grounding}, Counter: {counter}"
                    if lengthMessageOut == "":
                        messageOut = "Successfully decoded Module Flex SN"
                    else:
                        messageOut = ""
                except:
                    messageOut = "Failed to decode Module Flex SN, check if you used this pattern: 20WMFMPBJNNNNN"
                    return False, messageOut
            elif snIn[3] == "S" and snIn[4] == "U":
                messageOut = "Attempting to decode Support Unit SN"
                try:
                    manu = snIn[5]
                    if manu == "C":
                        manuExplainer = "China"
                    else:
                        manuExplainer = "Unknown Vendor attribute!"
                        return False, manuExplainer
                    prod = snIn[6]
                    if prod in ["M", "0"]:
                        prodExplainer = "Main production"
                        sn_meta_gen = "new"
                    elif prod == "P":
                        prodExplainer = "Pre-production"
                        sn_meta_gen = "new"
                    elif prod in ["D", "1"]:
                        prodExplainer = "demonstrator"
                        sn_meta_gen = "old"
                    elif prod in ["T", "2"]:
                        prodExplainer = "test"
                        sn_meta_gen = "old"
                    elif prod in ["O", "3"]:
                        prodExplainer = "other"
                        sn_meta_gen = "old"
                    else:
                        prodExplainer = "Unknown Production attribute!"
                        return False, prodExplainer
                    if sn_meta_gen == "new":
                        batchn = str(snIn[7])
                        side = str(snIn[8])
                        if side == "F":
                            sideExplainer = "F"
                        elif side == "B":
                            sideExplainer = "B"
                        else:
                            sideExplainer = "Unknown F or B type attribute!"
                            return False, stdExplainer
                        ring = str(snIn[9])
                        if ring == "I":
                            ringExplainer = "inner"
                        elif ring == "M":
                            ringExplainer = "middle"
                        elif ring == "O":
                            ringExplainer = "outer"
                        else:
                            ringExplainer = "Unknown Ring attribute!"
                            return False, ringExplainer
                        numerictype = str(snIn[10]) + str(snIn[11])
                        counter = str(snIn[12]) + str(snIn[13])
                        propertiesOut = f"Manufacturer / Vendor: {manu} ({manuExplainer}), Production: {prod} ({prodExplainer}), Batch number: {batchn}, F or B type: {side} ({sideExplainer}), Ring: {ring} ({ringExplainer}), Type: {numerictype}, Counter: {counter}"
                        if lengthMessageOut == "":
                            messageOut = "Successfully decoded new-gen Support Unit SN"
                        else:
                            messageOut = ""
                    else:
                        side = str(snIn[7])
                        if side == "F":
                            sideExplainer = "F"
                        elif side == "B":
                            sideExplainer = "B"
                        else:
                            sideExplainer = "Unknown F or B type attribute!"
                            return False, stdExplainer
                        ring = str(snIn[8])
                        if ring == "I":
                            ringExplainer = "inner"
                        elif ring == "M":
                            ringExplainer = "middle"
                        elif ring == "O":
                            ringExplainer = "outer"
                        else:
                            ringExplainer = "Unknown Ring attribute!"
                            return False, ringExplainer
                        numerictype = str(snIn[9]) + str(snIn[10])
                        counter = str(snIn[11]) + str(snIn[12]) + str(snIn[13])
                        propertiesOut = f"Manufacturer / Vendor: {manu} ({manuExplainer}), Production: {prod} ({prodExplainer}), F or B type: {side} ({sideExplainer}), Ring: {ring} ({ringExplainer}), Type: {numerictype}, Counter: {counter}"
                        if lengthMessageOut == "":
                            messageOut = "Successfully decoded old-gen Support Unit SN"
                        else:
                            messageOut = ""
                except:
                    messageOut = "Failed to decode Support Unit SN, check if you used this pattern: 20WSUMPBZRTTNN"
                    return False, messageOut
            elif snIn[3] == "D" and snIn[4] == "U":
                messageOut = "Attempting to decode Detector Unit SN"
                try:
                    manu = snIn[5]
                    if manu == "F" or manu == "1":
                        manuExplainer = "IFAE"
                    elif manu == "H" or manu == "2":
                        manuExplainer = "IHEP"
                    elif manu == "P" or manu == "3":
                        manuExplainer = "LPNHE"
                    elif manu == "M" or manu == "4":
                        manuExplainer = "Mainz"
                    elif manu == "A" or manu == "5":
                        manuExplainer = "MAScIR"
                    elif manu == "U" or manu == "6":
                        manuExplainer = "USTC"
                    else:
                        manuExplainer = "Unknown Site attribute!"
                        return False, manuExplainer
                    prod = snIn[6]
                    if prod == "M" or prod == "0":
                        prodExplainer = "Main production"
                        sn_meta_gen = "new"
                    elif prod == "P":
                        prodExplainer = "Pre-production"
                        sn_meta_gen = "new"
                    elif prod == "D" or prod == "1":
                        prodExplainer = "demonstrator"
                        sn_meta_gen = "old"
                    elif prod == "T" or prod == "2":
                        prodExplainer = "test"
                        sn_meta_gen = "old"
                    elif prod == "O" or prod == "3":
                        prodExplainer = "other"
                        sn_meta_gen = "old"
                    else:
                        prodExplainer = "Unknown Production attribute!"
                        return False, prodExplainer
                    if sn_meta_gen == "new":
                        batchn = str(snIn[7])
                        side = str(snIn[8])
                        if side == "F":
                            sideExplainer = "F"
                        elif side == "B":
                            sideExplainer = "B"
                        else:
                            sideExplainer = "Unknown F or B type attribute!"
                            return False, sideExplainer
                        ring = str(snIn[9])
                        if ring == "I":
                            ringExplainer = "inner"
                        elif ring == "M":
                            ringExplainer = "middle"
                        elif ring == "O":
                            ringExplainer = "outer"
                        else:
                            ringExplainer = "Unknown Ring attribute!"
                            return False, ringExplainer
                        numerictype = str(snIn[10]) + str(snIn[11])
                        counter = str(snIn[12]) + str(snIn[13])
                        propertiesOut = f"Sites that install modules on SU: {manu} ({manuExplainer}), Production: {prod} ({prodExplainer}), Batch number: {batchn}, F or B type: {side} ({sideExplainer}), Ring: {ring} ({ringExplainer}), Type: {numerictype}, Counter: {counter}"
                        if lengthMessageOut == "":
                            messageOut = "Successfully decoded new-gen Detector Unit SN"
                        else:
                            messageOut = ""
                    else:
                        side = str(snIn[7])
                        if side == "F":
                            sideExplainer = "F"
                        elif side == "B":
                            sideExplainer = "B"
                        else:
                            sideExplainer = "Unknown F or B type attribute!"
                            return False, sideExplainer
                        ring = str(snIn[8])
                        if ring == "I":
                            ringExplainer = "inner"
                        elif ring == "M":
                            ringExplainer = "middle"
                        elif ring == "O":
                            ringExplainer = "outer"
                        else:
                            ringExplainer = "Unknown Ring attribute!"
                            return False, ringExplainer
                        numerictype = str(snIn[9]) + str(snIn[10])
                        counter = str(snIn[11]) + str(snIn[12]) + str(snIn[13])
                        propertiesOut = f"Sites that install modules on SU: {manu} ({manuExplainer}), Production: {prod} ({prodExplainer}), F or B type: {side} ({sideExplainer}), Ring: {ring} ({ringExplainer}), Type: {numerictype}, Counter: {counter}"
                        if lengthMessageOut == "":
                            messageOut = "Successfully decoded old-gen Detector Unit SN"
                        else:
                            messageOut = ""
                except:
                    messageOut = "Failed to decode Detector Unit SN, check if you used this pattern: 20WDUKPBZRTTNN"
                    return False, messageOut
            elif snIn[3] == "G" and snIn[4] == "L":
                messageOut = "Attempting to decode Glue SN"
                try:
                    manu = snIn[5]
                    if manu in ("F", "1"):
                        manuExplainer = "IFAE"
                    elif manu in ("H", "2"):
                        manuExplainer = "IHEP"
                    elif manu in ("J", "3"):
                        manuExplainer = "IJCLab"
                    elif manu in ("M", "4"):
                        manuExplainer = "Mainz"
                    elif manu in ("A", "5"):
                        manuExplainer = "MAScIR"
                    elif manu in ("U", "6"):
                        manuExplainer = "USTC"
                    else:
                        manuExplainer = "Unknown Site attribute!"
                        return False, manuExplainer
                    prod = snIn[6]
                    if prod in ("M", "0"):
                        prodExplainer = "Main production"
                    elif prod == "P":
                        prodExplainer = "Pre-production"
                    elif prod in ("D", "1"):
                        prodExplainer = "demonstrator"
                    elif prod in ("T", "2"):
                        prodExplainer = "test"
                    elif prod in ("O", "3"):
                        prodExplainer = "other"
                    else:
                        prodExplainer = "Unknown Production attribute!"
                        return False, prodExplainer
                    counter = "".join(snIn[7:14])
                    propertiesOut = f"Manufacturer / Vendor: {manu} ({manuExplainer}), Production: {prod} ({prodExplainer}), Counter: {counter}"
                    if lengthMessageOut == "":
                        messageOut = "Successfully decoded Glue SN"
                    else:
                        messageOut = ""
                except:
                    messageOut = "Failed to decode Glue SN, check if you used this pattern: 20WGLMPNNNNNNN"
                    return False, messageOut
            elif snIn[3] == "P" and snIn[4] == "E":
                messageOut = "Attempting to decode PEB SN"
                try:
                    manu = snIn[5]
                    if manu == "H":
                        manuExplainer = "IHEP"
                    elif manu == "N":
                        manuExplainer = "NJU"
                    else:
                        manuExplainer = "Unknown Manufacturer / Vendor attribute!"
                        return False, manuExplainer
                    prod = snIn[6]
                    if prod == "M" or prod == "0":
                        prodExplainer = "Main production"
                    elif prod == "P":
                        prodExplainer = "Pre-production"
                    elif prod == "D" or prod == "1":
                        prodExplainer = "demonstrator"
                    elif prod == "T" or prod == "2":
                        prodExplainer = "test"
                    elif prod == "O" or prod == "3":
                        prodExplainer = "other"
                    else:
                        prodExplainer = "Unknown Production attribute!"
                        return False, prodExplainer
                    batchn = str(snIn[7])
                    grounding = str(snIn[8])
                    numerictype = str(snIn[9]) + str(snIn[10])
                    counter = str(snIn[11]) + str(snIn[12]) + str(snIn[13])
                    propertiesOut = f"Manufacturer / Vendor: {manu} ({manuExplainer}), Production: {prod} ({prodExplainer}), Batch number: {batchn}, Grounding scheme: {grounding}, Type: {numerictype}, Counter: {counter}"
                    if lengthMessageOut == "":
                        messageOut = "Successfully decoded PEB SN"
                    else:
                        messageOut = ""
                except Exception:
                    messageOut = "Failed to decode PEB SN, check if you used this pattern: 20WPEMPBJNNNNN"
                    return False, messageOut
            elif snIn[3] == "C" and snIn[4] == "S":
                messageOut = "Attempting to decode HV Power Supply Crate SN"
                try:
                    manu = f"{snIn[5]}{snIn[6]}"
                    if manu == "P0":
                        manuExplainer = "IHEP-SDU Pre-production"
                    elif manu == "P1":
                        manuExplainer = "IHEP-SDU Production"
                    else:
                        manuExplainer = "Unknown Manufacturer / Vendor attribute!"
                        return False, manuExplainer
                    prod = f"{snIn[7]}{snIn[8]}{snIn[9]}{snIn[10]}"
                    batchn = f"{snIn[11]}{snIn[12]}{snIn[13]}"
                    propertiesOut = f"Manufacturer / Vendor: {manu} ({manuExplainer}), Production time YYMM: {prod}, Batch number: {batchn}"
                    if lengthMessageOut == "":
                        messageOut = "Successfully decoded HV Power Supply Crate SN"
                    else:
                        messageOut = ""
                except:
                    messageOut = "Failed to decode HV Power Supply Crate SN, check if you used this pattern: 20WTPMMYYMMBBB"
                    return False, messageOut
            elif snIn[3] == "M" and snIn[4] == "D":
                messageOut = "Attempting to decode HV Module SN"
                try:
                    manu = f"{snIn[5]}{snIn[6]}"
                    if manu == "P0":
                        manuExplainer = "IHEP-SDU Pre-production"
                    elif manu == "P1":
                        manuExplainer = "IHEP-SDU Production"
                    else:
                        manuExplainer = "Unknown Manufacturer / Vendor attribute!"
                        return False, manuExplainer
                    prod = f"{snIn[7]}{snIn[8]}{snIn[9]}{snIn[10]}"
                    batchn = f"{snIn[11]}{snIn[12]}{snIn[13]}"
                    propertiesOut = f"Manufacturer / Vendor: {manu} ({manuExplainer}), Production time YYMM: {prod}, Batch number: {batchn}"
                    if lengthMessageOut == "":
                        messageOut = "Successfully decoded HV Module SN"
                    else:
                        messageOut = ""
                except:
                    messageOut = "Failed to decode HV Module SN, check if you used this pattern: 20WTPMMYYMMBBB"
                    return False, messageOut
            else:
                messageOut = "Invalid or incomplete Serial Number"
                return False, messageOut
    elif snIn[0] == "V":
        messageOut = "Attempting to decode Slot SN"
        if len(snIn) < 14:
            lengthMessageOut = "Slot SN must have at least 14 digits. Found too few."
            return False, lengthmessageOut
        elif len(snIn) > 16:
            lengthMessageOut = "Slot SN must have at most 16 digits. Found too many."
            return False, lengthmessageOut
        else:
            lengthMessageOut = ""
        try:
            vessel = snIn[1]
            layer = snIn[4]
            quadrant = snIn[7]
            row = snIn.split("R")[-1].split(":")[0]
            mod = snIn.split("M")[1]
            propertiesOut = f"Vessel: {vessel}, Layer: {layer}, Quadrant: {quadrant}, Row: {row}, Module: {mod}"
            if lengthMessageOut == "":
                messageOut = "Successfully decoded Slot SN"
            else:
                messageOut = ""
        except:
            messageOut = "Failed to decode Slot SN, check if you used this pattern: Vx:Lx:Qx:Rx:Mx"
            return False, messageOut
    else:
        messageOut = "Invalid Serial Number"
        return False, messageOut
    return True, ""


def get_vbd_for_sensor_via_wafer(sensor_SN, wafer_SN, metric="VBD_AVERAGE"):
    vbd, _ = api.fetch_information(f"/sensorvbdv2view?serial_number={wafer_SN}")
    available_vbd_meas_per_sensor = []
    for s in vbd:
        if s["SERIAL_NUMBER"] == sensor_SN:
            available_vbd_meas_per_sensor.append(s)
    if len(available_vbd_meas_per_sensor) > 0:
        return (
            float(
                sorted(
                    available_vbd_meas_per_sensor,
                    key=lambda d: d["RUN_END_TIMESTAMP"],
                    reverse=True,
                )[0][metric]
            ),
            "",
        )
    else:
        return (
            -999999,
            f"Could not retrieve VBD via /sensorvbdv2view for Sensor {sensor_SN} and Wafer {wafer_SN}",
        )


def get_vbd_from_iv(
    i, v, method="interpolate_linear", debug=False, threshold_in_A=5e-5
):
    """
    Determine Vbd for a given IV curve with measured currents per voltage (needs two lists as input)

    interpolate_linear: find the V-range between which the threshold for BD was exceeded and interpolate linearly between them
    first_to_exceed: the first V-value for which the threshold for BD was exceeded

    threshold in A, take 500nA=5e-7 from sensor paper for sensor, but 100*500nA=5e-5 for hybrid

    behavior: if multiple passes cross the threshold, return only the first (lowest V)

    Algorithm discussed at February 26 HGTD Week, Annika + Stefano
    """

    # convert the list into numpy array and continue with absolute values
    i = np.abs(np.array(i))
    v = np.abs(np.array(v))

    if debug:
        print(i >= threshold_in_A)

    if np.all(i < threshold_in_A):
        # if during the entire measurement range, the threshold was never exceeded, we have not seen Vbd
        # output a reasonable dummy value that coincides with the worst-case (BD could happen at next 5V step)
        # this is to make sure the average determination has good inputs to work with,
        # but different handling is possible (e.g. excluding such a value from AVG, if it comes from a single pad)
        return 205

    # index in array for which current (I) first exceeds threshold
    first_pass_index = np.where(i >= threshold_in_A)[0][0]

    # use this index to get the corresponding V, I and the last values just before this
    first_v_above_threshold = v[first_pass_index]
    if method == "first_to_exceed":
        return first_v_above_threshold
    else:
        # linear interpolation between two points (just below, just above threshold)
        last_v_below_threshold = v[first_pass_index - 1]
        first_i_above_threshold = i[first_pass_index]
        last_i_below_threshold = i[first_pass_index - 1]

        # relative amount of current between consecutive measured points covered to exceed threshold
        estimated_path_fraction = (threshold_in_A - last_i_below_threshold) / (
            first_i_above_threshold - last_i_below_threshold
        )
        # this fraction of covered voltage between consecutive steps to estimate the interpolated Vbd
        return last_v_below_threshold + estimated_path_fraction * (
            first_v_above_threshold - last_v_below_threshold
        )


def get_i_v_from_iv_pad_str(iv_long_formatted_string):
    string_as_json = json.loads(iv_long_formatted_string)
    i_strings = string_as_json["I"]
    v_strings = string_as_json["V"]
    I = [float(i) for i in i_strings]
    V = [float(v) for v in v_strings]
    return I, V


def get_ivs_for_all_pads_of_sensor(sensor_SN):
    ivs, _ = api.fetch_information(f"/sensorivview?serial_number={sensor_SN}")
    types = []
    for iv in ivs:
        if str(iv["RUN_TYPE"]) == "15x15":
            types.append("15x15")
        elif str(iv["RUN_TYPE"]) == "15X15":
            types.append("15X15")
        elif str(iv["RUN_TYPE"]) == "15x1":
            types.append("15x1")
        elif str(iv["RUN_TYPE"]) == "15X1":
            types.append("15X1")
        elif str(iv["RUN_TYPE"]) == "1x1":
            types.append("1x1")
        elif str(iv["RUN_TYPE"]) == "1X1":
            types.append("1X1")
    if len(types) == 0:
        return (
            {},
            f"Could not retrieve IV via /sensorivview for Sensor {sensor_SN}",
        )

    # there could be different types, just pick one of them in hierarchy
    if "15x15" in types:
        ivs, _ = api.fetch_information(
            f"/sensorivview?serial_number={sensor_SN}&run_type=15x15"
        )
    else:
        if "15X15" in types:
            ivs, _ = api.fetch_information(
                f"/sensorivview?serial_number={sensor_SN}&run_type=15X15"
            )
        else:
            if "15x1" in types:
                ivs, _ = api.fetch_information(
                    f"/sensorivview?serial_number={sensor_SN}&run_type=15x1"
                )
            else:
                if "15X1" in types:
                    ivs, _ = api.fetch_information(
                        f"/sensorivview?serial_number={sensor_SN}&run_type=15X1"
                    )
                else:
                    if "1x1" in types:
                        ivs, _ = api.fetch_information(
                            f"/sensorivview?serial_number={sensor_SN}&run_type=1x1"
                        )
                    else:
                        if "1X1" in types:
                            ivs, _ = api.fetch_information(
                                f"/sensorivview?serial_number={sensor_SN}&run_type=1X1"
                            )
                        else:
                            return (
                                -999999,
                                f"Could not retrieve IV via /sensorivview for Sensor {sensor_SN}, unknown run types only {", ".join(types)}",
                            )
    if len(ivs) == 0:
        print("Len of 15x15 output is zero, does not exist.")
        ivs, _ = api.fetch_information(
            f"/sensorivview?serial_number={sensor_SN}&run_type=15X1"
        )
        if len(ivs) == 0:
            print("Len of 15X1 output is also zero, does not exist.")
            ivs, _ = api.fetch_information(
                f"/sensorivview?serial_number={sensor_SN}&run_type=1X1"
            )
            if len(ivs) == 0:
                print("Len of 1X1 output is also zero, does not exist.")
                return (
                    {},
                    f"Could not retrieve IV via /sensorivview for Sensor {sensor_SN}",
                )
    ivs_per_pad = {}
    for curve in ivs:
        pad_loc = int(curve["PAD_LOCATION"])
        if pad_loc in list(range(1, 256)):
            if str(curve["GUARD_RING"]) == "" and str(curve["IV_GUARD_RING"]) == "":
                if pad_loc not in ivs_per_pad.keys():
                    ivs_per_pad[pad_loc] = curve["IV_PAD"]
                else:
                    if ivs_per_pad[pad_loc]["RUN_END_TIMESTAMP"] < curve[pad_loc][
                        "RUN_END_TIMESTAMP"
                    ] or int(ivs_per_pad[pad_loc]["RUN_NUMBER"]) < int(
                        curve[pad_loc]["RUN_NUMBER"]
                    ):
                        # current curve is newer than previously stored one
                        ivs_per_pad[pad_loc] = curve["IV_PAD"]
    return ivs_per_pad, ""


def get_sum_iv_for_sensor(sensor_SN, ivs_per_pad=None):
    if ivs_per_pad == None:
        ivs_per_pad, ivs_response = get_ivs_for_all_pads_of_sensor(sensor_SN)
        if ivs_per_pad == {}:
            return [], ivs_response
    sum_I = []
    V = []
    for pad in ivs_per_pad.keys():
        I, V = get_i_v_from_iv_pad_str(ivs_per_pad[pad])
        if sum_I == []:
            sum_I = I
        else:
            sum_I = [a + b for a, b in zip(sum_I, I)]
    return [sum_I, V], ""


def get_vbd_for_sensor_via_iv(sensor_SN, threshold_in_A=5e-7, ivs_per_pad=None):
    if ivs_per_pad == None:
        ivs_per_pad, ivs_response = get_ivs_for_all_pads_of_sensor(sensor_SN)
        if ivs_per_pad == {}:
            return [], ivs_response
    # after all ivs, for each pad, are collected, calculate VBD for each of them using 500nA as threshold
    vbd_per_pad = {}
    for pad in ivs_per_pad.keys():
        i, v = get_i_v_from_iv_pad_str(ivs_per_pad[pad])
        vbd_per_pad[pad] = float(get_vbd_from_iv(i, v, threshold_in_A=threshold_in_A))
    return sum(vbd_per_pad.values()) / len(vbd_per_pad.keys()), ""


def get_all_hybrid_ivs():
    ivs, _ = api.fetch_information("/hybridivview")
    return ivs


def get_all_module_ivs():
    ivs, _ = api.fetch_information("/moduleivview")
    return ivs


def get_iv_for_hybrid_or_module(part_SN, all_ivs=None, KoP=None):
    """
    Returns up to one Hybrid (Module) IV for a given Hybrid (Module) SN.
    If multiple are found, pick the one with less None currents.
    If the evaluated curves share the same number of None currents,
    pick the one with larger SR_NO (counts through curves).
    Ignore curves with I = V (data entry errors).

    Parameters:
        part_SN: serial number of Hybrid (Module) to get IV curve for
        all_ivs: list of Hybrid (Module) IVs, or None, if they still need to be obtained from API
        KoP: choices "Module" or "Hybrid", default: "Hybrid", only necessary if all_ivs = None

    Returns:
        List of two lists ([list of currents, list of voltages]), if a valid curve was found, else empty list
        Empty string if IV returned, or reason why no IV returned
    """
    if all_ivs == None:
        if KoP == "Hybrid":
            all_ivs = get_all_hybrid_ivs()
        elif KoP == "Module":
            all_ivs = get_all_module_ivs()
        else:
            return (
                [],
                "You need to provide a KoP out of Hybrid or Module to proceed. "
                "There was no list of IV curves provided.",
            )
    designated_iv_curve_for_part_SN = None
    for ivcurve in all_ivs:
        eval_ivcurve = eval("{" + ivcurve["IV"][1:-1] + "}")
        if eval_ivcurve != {}:
            if eval_ivcurve["I"] != eval_ivcurve["V"]:
                if part_SN == str(ivcurve["SERIAL_NUMBER"]):
                    if designated_iv_curve_for_part_SN == None:
                        designated_iv_curve_for_part_SN = {
                            "IV": eval_ivcurve,
                            "SR_NO": ivcurve["SR_NO"],
                        }
                    else:
                        # more than one found
                        # next modifications necessary because many HY/MO IVs do not come with any way to distinguish them (time / user / site etc.)
                        counting_None_inDesignated = len(
                            [
                                i
                                for i in designated_iv_curve_for_part_SN["IV"]["I"]
                                if i == "None"
                            ]
                        )
                        counting_None_inCurrent = len(
                            [i for i in eval_ivcurve["I"] if i == "None"]
                        )
                        if counting_None_inDesignated > counting_None_inCurrent:
                            # replace with another curve with fewer None currents
                            designated_iv_curve_for_part_SN = {
                                "IV": eval_ivcurve,
                                "SR_NO": ivcurve["SR_NO"],
                            }
                        elif counting_None_inDesignated == counting_None_inCurrent:
                            if int(designated_iv_curve_for_part_SN["SR_NO"]) < int(
                                ivcurve["SR_NO"]
                            ):
                                # replace with another curve with higher SR_NO (later upload)
                                designated_iv_curve_for_part_SN = {
                                    "IV": eval_ivcurve,
                                    "SR_NO": ivcurve["SR_NO"],
                                }
    if designated_iv_curve_for_part_SN != None:
        i = [float(i) for i in designated_iv_curve_for_part_SN["IV"]["I"]]
        v = [float(v) for v in designated_iv_curve_for_part_SN["IV"]["V"]]
        return [i, v], ""
    else:
        return [], f"No valid IV curve found for {part_SN}."


def get_vbd_for_hybrid_or_module_via_iv(
    part_SN, all_ivs=None, KoP=None, threshold_in_A=None
):
    if threshold_in_A == None:
        if KoP == "Hybrid":
            threshold_in_A = 5e-5  # to check
        elif KoP == "Module":
            threshold_in_A = 2 * 5e-5  # to check, just guessing here
        else:
            return (
                -999999,
                "You need to provide a KoP out of Hybrid or Module to proceed. "
                "Threshold current could not be inferred. Pass a KoP, or alternatively the threshold in A.",
            )
    iv, response = get_iv_for_hybrid_or_module(part_SN, all_ivs, KoP)
    if response != "":
        return -999999, response
    else:
        return float(get_vbd_from_iv(iv[0], iv[1], threshold_in_A=threshold_in_A))

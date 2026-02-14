import os.path
import time
from argparse import ArgumentParser
from pprint import pprint

import requests
import yaml

import api
import data
import util

manus = data.relevant_manufacturer_IDs_by_shortname
locs = data.relevant_location_IDs_by_shortname
KoPs = data.KoPID_from_partKoPName

parser = ArgumentParser("CLI for SN reservation, targeted at Module Assembly")
parser.add_argument(
    "--user-name",
    dest="userName",
    help="Your CERN user name.",
    default=None,
    required=True,
)
parser.add_argument(
    "--site",
    dest="site",
    help=f"Site. Must be one of {','.join(data.MO_site_id.keys())}",
    default=None,
    required=True,
)
parser.add_argument(
    "--prod",
    dest="prod",
    help=f"Production. Must be one of {','.join(data.MO_prod_id.keys())}",
    default=None,
    required=True,
)
parser.add_argument(
    "--batch",
    dest="batch",
    help=f"Batch. Must be alphanumerical",
    default=None,
    required=True,
)
parser.add_argument(
    "--n-reserve",
    dest="nToReserve",
    help=f"Number of SNs to reserve. Must be an integer",
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
    "--comment", dest="comment", help="[Optional] Set a comment.", default=None
)
parser.add_argument(
    "--dryrun",
    dest="dryrun",
    help="[Optional] Only test running until the last very step, but do not perform upload.",
    default=False,
)
args = parser.parse_args()

# read the arguments submitted from user by CLI
# required fields
username, my_site, my_prod, my_batch, how_many_to_reserve = (
    args.userName,
    args.site,
    args.prod,
    args.batch,
    int(args.nToReserve),
)
# optional fields
comment, local_folder = args.comment, args.localFolder
# boolean flag
dryrun = util.str2bool(args.dryrun)

if comment == None:
    comment = "part SN reserved via hgtd-tools"


# disentangle user auth from DB token, always get a new DB one later on
api.user_auth_cli(username, local_folder)
myToken = api.get_access_token()

modules, last_responseText = util.get_relevant_parts("Module")
module_SNs = util.get_SN_of_parts(modules)
my_prefix = util.get_MO_SN_prefix(my_site, my_prod, my_batch)


def find_matching_SNs(prefix, existing_SNs):
    return [ex for ex in existing_SNs if str(ex[:8]) == str(prefix)]


def find_matching_sorted_counters(matching_SN_list):
    return sorted([SN[8:] for SN in matching_SN_list])


def change_counter_digits_to_ints(counters):
    return [int(c) for c in counters]


def find_max(my_list):
    return max(my_list) if len(my_list) > 0 else 0


def collect_possible_holes(counters_as_INT, max_match):
    holes = []
    # we do not apply zero-counting, because these are human-readable counters starting from 1
    for i in range(1, max_match + 1):
        if i not in counters_as_INT:
            holes.append(i)
    return holes


def build_recommended_SNs(N_to_reserve, holes_to_use, max_so_far, prefix):
    n_holes_to_use = len(holes_to_use)
    if n_holes_to_use >= N_to_reserve:
        recom_counters = holes_to_use[:N_to_reserve]
    else:
        still_to_build = N_to_reserve - n_holes_to_use
        recom_counters = holes_to_use + [
            new_ones
            for new_ones in range(max_so_far + 1, max_so_far + 1 + still_to_build)
        ]

    return [f"{prefix}{counter:06}" for counter in recom_counters]


my_matching_SNs = find_matching_SNs(my_prefix, module_SNs)
matched_sorted_counters = find_matching_sorted_counters(my_matching_SNs)
matched_sorted_counters_as_INT = change_counter_digits_to_ints(matched_sorted_counters)
max_matched = find_max(matched_sorted_counters_as_INT)
holes_in_matched = collect_possible_holes(matched_sorted_counters_as_INT, max_matched)
recommended_SNs = build_recommended_SNs(
    how_many_to_reserve, holes_in_matched, max_matched, my_prefix
)

if len(my_matching_SNs) > 0:
    print(
        f"hgtd-tools found the following SNs matching your prefix criteria on site/prod/batch: {my_prefix}"
    )
    pprint(my_matching_SNs)
    print(
        "hgtd-tools will now recommend unused SNs, attempting to fill any skipped SNs and continuing with the next ones."
    )
else:
    print(
        f"hgtd-tools will recommend suitable SNs to you, starting from the prefix: {my_prefix}"
    )
for i in range(how_many_to_reserve):
    print(
        f"\n\nYou are about to introduce the following Serial Number in the database: {recommended_SNs[i]}"
    )
    user_not_yet_happy = True
    while user_not_yet_happy:
        print("hgtd-tools needs more detail information for your new part.\n")
        name_label = input(
            "Type Name Label of this part. Use the local nomenclature that is known in your lab. "
            "Confirm with [Enter]: "
        )
        version = input(
            "Type Version of this part. Use the local nomenclature that is known in your lab and recommended for your component group. "
            "Confirm with [Enter]: "
        )
        comment_confirm = input(
            f'The currently used comment string is "{comment}". Are you fine with it (just confirm with [Enter]) or do you want to change it (type e.g. "N")? '
        )
        if comment_confirm != "":
            comment = input(
                "You want to change the comment for this part, type it in. Confirm with [Enter]: "
            )

        part_to_upload = {
            "barcode": "",
            "serial_number": recommended_SNs[i],
            "is_record_deleted": "F",
            "version": version,
            "name_label": name_label,
            "comment_description": comment,
            "kind_of_part": str(KoPs["Module"]),
            "location": str(locs[my_site]),
            "manufacturer": str(manus[my_site]),
            "record_insertion_user": username,
        }

        print(
            "This is what would be uploaded for this part, with human-readable location, manufacturer and Kind Of Part already translated to DB IDs:"
        )
        pprint(part_to_upload)
        happy = input(
            'Are you happy with this? Type in "Y" or "y" to confirm that this should be uploaded, any other input to modify again before uploading. '
        )
        if happy.lower() == "y":
            user_not_yet_happy = False

    if dryrun:
        last_responseText = api.post_information(
            "/partslist", part_to_upload, dryrun=True, existing_token=myToken
        )
        print("Concluding dryrun without uploading.")

    else:
        last_responseText = api.post_information(
            "/partslist", part_to_upload, dryrun=False, existing_token=myToken
        )
        if last_responseText[:2] != "20":
            print("Data was not uploaded successfully." + f"\n{last_responseText}")
            raise RuntimeError("Upload failed")
        else:
            print("Data successfully uploaded.")

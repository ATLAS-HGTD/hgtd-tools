import api
import datetime
import os, os.path
import getpass, requests
import tarfile
from argparse import ArgumentParser
from msg_style import bcolors

INFO = '[INFO] : '
WARNING = bcolors.WARNING + '[WARNING] : ' + bcolors.ENDC
ERROR = bcolors.FAIL + '[ERROR] : ' + bcolors.ENDC


parser = ArgumentParser('CLI for DB Interface')
parser.add_argument('--analysis-folder', dest='analysisFolder',
                    help='Path to the folder containing analysis results. '
                    'Specify the parent directory that contains all scans. ' 
                    'Example: if there is a dir testSource/sourceScan, you '
                    'should put --analysis-folder testSource for DB upload.',
                    default=None, required=True)
parser.add_argument('--user-name', dest='userName',
                    help='Your CERN user name.',
                    default=None, required=True)
parser.add_argument('--db-folder', dest='dbFolder',
                    help='Path to the folder that will hold temporary DB '
                    'data for uploading, including a token for the user.',
                    default='analysis/db_data')
args = parser.parse_args()

def authenticate(u_name, pw, totp, dbFolder_path):
    try:
        auth_user, last_responseText = api.get_user(u_name, pw, totp)
    except (requests.exceptions.HTTPError,
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
            requests.exceptions.RequestException) as e:
        last_responseText = str(e)
    except ValueError as e:
        last_responseText = str(e)

    if last_responseText[:2] != '20':
        print(ERROR + 'New user could not be authenticated.' +
              f'\n{last_responseText}')
        raise RuntimeError('User authentication failed')
    else:
        print(INFO + 'User authenticated.' +
              '\nPreparing an access token, valid for the next 20 minutes.')
        token = api.get_access_token()
        # write token and valid user name to dbFolder,
        # this overwrites if a previous one existed
        with open(dbFolder_path + '/' + u_name, 'w') as outfile:
            outfile.write(token)

def test_for_existing_token_file(username):
    if os.path.isfile(dbFolder + '/' + username):
        if datetime.datetime.now() - datetime.datetime.fromtimestamp(os.path.getmtime(dbFolder + '/' + username)) < datetime.timedelta(minutes=19):
            return True
        else:
            return False
    return False

def check_existing():
    pass

def prep_tar(analysisInputFolder):
    with tarfile.open(dbFolder + '/temporary_tar_output.tar', "w", format=tarfile.GNU_FORMAT) as tar:
        tar.add(analysisInputFolder)

def download(token, endpoint_to_fetch = '/partattrlist/6573/'):
    downloaded_content, last_responseText = api.fetch_information(endpoint_to_fetch, existing_token = token)
    return downloaded_content, last_responseText

def upload(data_payload, files_payload, token, dryRun = False,
           endpoint_module_bulk_meas = '/module_threshold_measurements_many'):
    last_responseText = api.post_information(endpoint_module_bulk_meas, 
                                             data_payload,
                                             dryrun = dryRun,
                                             content_type = 'multipart/form-data',
                                             files_payload = files_payload,
                                             existing_token = token)
    return last_responseText

# read the arguments submitted from user by CLI
analysisFolder, dbFolder, username = args.analysisFolder, args.dbFolder, args.userName

# get existing token, search through the db folder to get file with username as filename
# ToDo
# if existing token found, check validity, otherwise let user re-auth
if not test_for_existing_token_file(username):
    # authenticate user, request input from CLI
    password = getpass.getpass('Type password, confirm with [Enter]: ')
    sixdigit = input('Type 6-digit verification code if you have 2FA setup. '
                     'Confirm with [Enter]: ')

    authenticate(username, password, sixdigit, dbFolder)

# after this step, we definitely have a valid token stored
with open(dbFolder + '/' + username, 'r') as tokenFile:
    myToken = tokenFile.readlines()[0]

# upload if new data
# check if the data is already there
# ToDo

# first build a new tar (temporary file that will only be used for upload,
# and deleted afterwards)
prep_tar(analysisFolder)

# ToDo read such info from FADAPro analysis output instead of requesting via CLI from user input
# ToDo agree on what shall be allowed here or not and how to get the most up-to-date list
run_type = input('Type measurement type, including the step and possibly more detailed tag'
                 ' for irradiation, thermal cycling etc. '
                 'Confirm with [Enter]: ')
# ToDo agree on what shall be allowed here or not and how to get the most up-to-date list
meas_loc = input('Type measurement location, choose any of the allowed locations from the list. Example: 1521. '
                 'Confirm with [Enter]: ')
run_start = input('Type start date of measurement (format: YYYY-MM-DD). '
                 'Confirm with [Enter]: ')
run_end = input('Type end date of measurement (format: YYYY-MM-DD). '
                 'Confirm with [Enter]: ')
comment = input('[Optional] Type comment, or leave empty. '
                 'Confirm with [Enter]: ')

files_payload = {'data_file': ('temporary_tar_output.tar', open(dbFolder + '/temporary_tar_output.tar','rb'))}
data_payload = {'is_record_deleted': 'F', # we want to record this as something that is not "deleted", so we put "F"
                'location': meas_loc, # measurement site / location (could be your institute location, cern, clean room etc.) - we need to hardcode somewhere or retrieve the list of locations to choose from, because again this needs an ID
                'run_type': run_type, # measurement type, e.g. the full name of the step (assembly_<insititute>, loading_<after some TCs> etc.)
                'run_begin_timestamp': run_start, # begin of measurement data, usual time and date format
                'run_end_timestamp': run_end, # end of measurement data, usual time and date format
                'comment_description': comment, # comment
                'record_insertion_user': username} # to store who did this upload in the database

upload_response = upload(data_payload, files_payload, myToken)
# ToDo: check the successful upload by attempting to download the data again. And test for existing SN must happen before!!!
if upload_response[:2] != '20':
    print(ERROR + 'Data was not uploaded successfully.' +
          ' Inspect the content of the temporary tar file for potential mistakes and check if the SN exists in the DB.' +
          f'\n{last_responseText}')
    raise RuntimeError('Upload failed')
else:
    print(INFO + 'Data successfully uploaded, deleting temporary tar archive now.')
    os.remove(dbFolder + '/temporary_tar_output.tar')

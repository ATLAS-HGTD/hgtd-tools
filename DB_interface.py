import api, util
import datetime
import os, os.path
import getpass, requests
import tarfile
import time, yaml
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
parser.add_argument('--overwrite_run_type', dest='overwriteRunType',
                    help='[Optional] Set a custom run type, not taking the one from '
                    'existing metadata upload file.',
                    default=None)
parser.add_argument('--overwrite_start_date', dest='overwriteStartDate',
                    help='[Optional] Set a custom start date of measurement (format: YYYY-MM-DD), not taking the one from '
                    'existing metadata upload file.',
                    default=None)
parser.add_argument('--overwrite_end_date', dest='overwriteEndDate',
                    help='[Optional] Set a custom end date of measurement (format: YYYY-MM-DD), not taking the one from '
                    'existing metadata upload file.',
                    default=None)
parser.add_argument('--comment', dest='comment',
                    help='[Optional] Set a comment.',
                    default=None)
parser.add_argument('--dryrun', dest='dryrun',
                    help='[Optional] Only test running until the last very step, but do not perform upload.',
                    default=False)
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
    """ check the existance of token file and that its last modification was not too long ago 
    conservative timedelta of 18min because submission of the tar and cross-check of user might take a minute or two
    """
    if os.path.isfile(dbFolder + '/' + username):
        if datetime.datetime.now() - datetime.datetime.fromtimestamp(os.path.getmtime(dbFolder + '/' + username)) < datetime.timedelta(minutes=18):
            return True
        else:
            return False
    return False

def check_existing(sn):
    existing_modules, last_responseText = util.get_relevant_parts('Module')
    for mod in existing_modules:
        if str(mod['serial_number']) == str(sn):
            return True
    else:
        return False

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
overwriteRunType, overwriteStartDate, overwriteEndDate, comment = args.overwriteRunType, args.overwriteStartDate, args.overwriteEndDate, args.comment
dryrun = args.dryrun

# get existing token, search through the db folder to get file with username as filename
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

# this function taken from FADAPro
# ToDo for MR this must be replaced by a call to an imported IO module
def find_last_recursively(start_dir, search_for='meas_parameters.yaml', this_depth = 0, max_depth = 10, dir_to_skip = [], skip_subdir_names = ['last_vthc','.ipynb_checkpoints']):
    """ find the last folder, recursively, starting from start_dir and navigating subfolders until the file search_for is found.
    Return None if no folder is found
    
    Will not navigate to search in any folder contained in dir_to_skip .
    Note : this may cause the automatic search to fail if the only subdirectory of the last top directory is vetoed.
    E.g. if in order of time the sequence is:
        /path/to/folder/f1
        /path/to/folder/f2
        /path/to/another_folder/f1
        and dir_to_skip = ['/path/to/another_folder/f1'], then the finder will get stuck at '/path/to/another_folder'

    skip_subdir_names = subdirectory called like this will be ignored
    """

    # max limit reached
    if this_depth > max_depth:
        print('... last folder search : stopping for max depth at', start_dir)
        return None

    # file found
    if os.path.isfile(os.path.join(start_dir, search_for)):
        return start_dir

    # search for last subdir
    all_subdirs = [os.path.join(start_dir, d) for d in os.listdir(start_dir) if os.path.isdir(os.path.join(start_dir, d))]

    # prune directories to skip
    dir_to_skip = [os.path.normpath(p) for p in dir_to_skip]
    all_subdirs = [d for d in all_subdirs if os.path.normpath(d) not in dir_to_skip]
    is_in_list  = lambda sd : any(sn in os.path.basename(sd) == sn for sn in skip_subdir_names)
    all_subdirs = [d for d in all_subdirs if not is_in_list(d)]

    # no subdirs found
    if len(all_subdirs) == 0 :
        print('... last folder search : no subdirs found in', start_dir)
        return None
    
    last_sub = max(all_subdirs, key=os.path.getmtime)
    return find_last_recursively(start_dir=last_sub, search_for=search_for, this_depth=this_depth+1, max_depth=max_depth, dir_to_skip=dir_to_skip, skip_subdir_names=skip_subdir_names)

def find_SN_in_analysisFolder(analysisFolder):
    first_sn_File = find_last_recursively(analysisFolder, search_for='SN.txt')
    # from the first sn file, we know where to look for others
    parent_of_first_sn_file = os.path.dirname(first_sn_File)
    module_dirs = [os.path.join(parent_of_first_sn_file, d) for d in os.listdir(parent_of_first_sn_file) if os.path.isdir(os.path.join(parent_of_first_sn_file, d))]
    measured_SNs = []
    for mod_dir in module_dirs:
        if os.path.isfile(os.path.join(mod_dir, 'SN.txt')):
            # found a SN file
            with open(os.path.join(mod_dir, 'SN.txt'), 'r') as snFile:
                # sanitize the SN, no line break chars if there are any
                sn = snFile.readlines()[0].replace('\n', '').replace('\r', '')
                measured_SNs.append(sn)
    return measured_SNs

measured_SNs = find_SN_in_analysisFolder(analysisFolder)

# check if the serial number(s) already exist(s) in the DB
SNs_exist = [check_existing(serial) for serial in measured_SNs]

if sum(SNs_exist) == len(SNs_exist):
    print(INFO + 'The serial number(s) of your module(s) were successfully found in the ProdDB parts list.')
    # upload if new data
    # check if the data is already there
    # ToDo
    
    # first build a new tar (temporary file that will only be used for upload,
    # and deleted afterwards)
    prep_tar(analysisFolder)
    
    # ToDo read such info from FADAPro analysis output instead of requesting via CLI from user input
    DB_upload_info_Folder = find_last_recursively(analysisFolder, search_for='DB_upload_info.yaml')
    print(DB_upload_info_Folder)
    
    with open(os.path.join(DB_upload_info_Folder, 'DB_upload_info.yaml')) as yamlfile:
        meas_upload_info = yaml.safe_load(yamlfile)
        meas_step = meas_upload_info.get('meas_step') # aka run_type
        # the meas_type like sourceScan is taken from the directory structure on the backend-level
        # timestamp serves as run_start and run_end
        #datetime_obj = datetime.datetime.strptime(meas_upload_info.get('timestamp'),"%d/%m/%Y %H:%M:%S")
        #unix_timestamp = datetime_obj.timestamp()
        #timestamp = datetime.datetime.utcfromtimestamp(unix_timestamp).strftime('%Y-%m-%dT%H:%M:%SZ')
        #timestamp_date = datetime.datetime.strptime(meas_upload_info.get('timestamp'),"%d/%m/%Y %H:%M:%S")
        meas_date = meas_upload_info.get('timestamp').split(' ')[0] # just the date
        meas_date_y, meas_date_m, meas_date_d = meas_date[6:10], meas_date[3:5], meas_date[0:2]
        timestamp = f'{meas_date_y}-{meas_date_m}-{meas_date_d}'
        print('meas_step from yaml:',meas_step)
        print('timestamp from yaml:',timestamp)

    run_type = meas_step
    run_start, run_end = timestamp, timestamp
    
    '''
    meas_folder: B_None_On_all_Inj_none_N_100000_Vth_380_Q_12
    meas_step: assembly
    meas_type: sourceScan
    timestamp: 26/08/2025 16:35:56
    '''
    # ToDo agree on what shall be allowed here or not and how to get the most up-to-date list
    #run_type = input('Type measurement type, including the step and possibly more detailed tag'
    #                 ' for irradiation, thermal cycling etc. '
    #                 'Confirm with [Enter]: ')
    # ToDo agree on what shall be allowed here or not and how to get the most up-to-date list
    meas_loc = input('Type measurement location, choose any of the allowed locations from the list. Example: 1521. '
                     'Confirm with [Enter]: ')
    #run_start = input('Type start date of measurement (format: YYYY-MM-DD). '
    #                 'Confirm with [Enter]: ')
    #run_end = input('Type end date of measurement (format: YYYY-MM-DD). '
    #                 'Confirm with [Enter]: ')
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

    if not dryrun:
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
    else:
        print(INFO + 'Concluding dryrun without uploading.')
else:
    for existance_i in range(len(SNs_exist)):
        if not SNs_exist[existance_i]:
            print(ERROR + f'The serial number {measured_SNs[existance_i]} of your module does not exist in the ProdDB parts list.' +
                  ' You need to add this serial number first via https://nginx-hgtddb.app.cern.ch/parts' +
                  ' before you can upload measurements for this part or correct the SN in your config.')
    raise RuntimeError('SN existance check failed for at least one SN')
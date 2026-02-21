import datetime
import getpass
import json
import os
from pprint import pprint

import requests

# === To open links in browser
# Redirect to new frontend
frontendUrlPrefix = "https://nginx-hgtddb.app.cern.ch"

# === Interaction with hgtd-proddb REST API
# This was the "old" backend, now retired, without SSO
apiUrlPrefix = "https://backend-hgtddb.app.cern.ch/hgtddb"
# New backend API with protection (e.g. access token, oidc)
protectedApiUrlPrefix = "https://hgtddb-api.web.cern.ch/hgtddb"
# CERN endpoint to receive API access tokens (e.g. for new backend),
# method client_credentials
access_token_url = "https://auth.cern.ch/auth/realms/cern/api-access/token"

# === For user authentication via OpenID (CERN SSO)
# Used to write usernames that are different from the default "None"
# which would result in the default user ATLAS_HGTD_PROD
kc_server = "https://auth.cern.ch"
client_id = "public-client"
client_secret = ""
keycloak_endpoint = kc_server + "/auth/realms/cern/protocol/openid-connect/token"
userinfo_endpoint = kc_server + "/auth/realms/cern/protocol/openid-connect/userinfo"

# === For checking against latest version
hgtd_tools_version_endpoint = "https://cernbox.cern.ch/remote.php/dav/public-files/lFlRlPYl6EO4J3N/hgtd-tools-version"


def get_version(debug=False):
    try:
        request = requests.get(hgtd_tools_version_endpoint)
        request.raise_for_status()
        if debug:
            print(">> GET response:", request.status_code, request.reason)
        return request.text, f"{request.status_code}, {request.reason}"
    except requests.exceptions.HTTPError as errh:
        if debug:
            print("Http Error:", errh)
        raise requests.exceptions.HTTPError("Http Error:", errh)
    except requests.exceptions.ConnectionError as errc:
        if debug:
            print("Error Connecting:", errc)
        raise requests.exceptions.ConnectionError("Error Connecting:", errc)
    except requests.exceptions.Timeout as errt:
        if debug:
            print("Timeout Error:", errt)
        raise requests.exceptions.Timeout("Timeout Error:", errt)
    except requests.exceptions.RequestException as err:
        if debug:
            print("OOps: Something Else", err)
        raise requests.exceptions.RequestException("OOps: Something Else", err)


def get_user(us, pw, to, debug=False):
    try:
        # get an access token
        request = requests.post(
            keycloak_endpoint,
            data={
                "grant_type": "password",
                "scope": "openid",
                "client_id": client_id,
                "client_secret": client_secret,
                "password": pw,
                "username": us,
                "totp": to,
            },
        )
        request.raise_for_status()
        access_token = request.json()["access_token"]
        # use access token to talk to userinfo endpoint
        request = requests.post(userinfo_endpoint, data={"access_token": access_token})
        request.raise_for_status()
        if debug:
            print(request.text)
        return request.json()["cern_upn"], f"{request.status_code}, {request.reason}"
    except requests.exceptions.HTTPError as errh:
        if debug:
            print("Http Error:", errh)
        raise requests.exceptions.HTTPError("Http Error:", errh)
    except requests.exceptions.ConnectionError as errc:
        if debug:
            print("Error Connecting:", errc)
        raise requests.exceptions.ConnectionError("Error Connecting:", errc)
    except requests.exceptions.Timeout as errt:
        if debug:
            print("Timeout Error:", errt)
        raise requests.exceptions.Timeout("Timeout Error:", errt)
    except requests.exceptions.RequestException as err:
        if debug:
            print("OOps: Something Else", err)
        raise requests.exceptions.RequestException("OOps: Something Else", err)


def authenticate(u_name, pw, totp, local_folder):
    try:
        auth_user, last_responseText = get_user(u_name, pw, totp)
    except (
        requests.exceptions.HTTPError,
        requests.exceptions.ConnectionError,
        requests.exceptions.Timeout,
        requests.exceptions.RequestException,
    ) as e:
        last_responseText = str(e)
    except ValueError as e:
        last_responseText = str(e)

    if last_responseText[:2] != "20":
        print("[ERROR] New user could not be authenticated." + f"\n{last_responseText}")
        raise RuntimeError("User authentication failed")
    else:
        print(
            "[INFO]"
            + "User authenticated."
            + "\nPreparing an access token, valid for the next 480 minutes."
        )
        token = get_access_token()
        # write token and valid user name to localFolder,
        # this overwrites if a previous one existed
        with open(local_folder + "/" + u_name, "w") as outfile:
            outfile.write(token)


def test_for_existing_token_file(username, local_folder):
    """check the existance of token file and that its last modification was not too long ago
    not strictly respecting actual lifetime of token, but timedelta of 480min (one work day)
    """
    if os.path.isfile(local_folder + "/" + username):
        if datetime.datetime.now() - datetime.datetime.fromtimestamp(
            os.path.getmtime(local_folder + "/" + username)
        ) < datetime.timedelta(minutes=480):
            return True
        else:
            return False
    return False


def user_auth_cli(username, local_folder):
    # get existing token, search through the db folder to get file with username as filename
    # if existing user file found, get DB token, otherwise let user re-auth
    if not test_for_existing_token_file(username, local_folder):
        # authenticate user, request input from CLI
        password = getpass.getpass("Type password, confirm with [Enter]: ")
        sixdigit = input(
            "Type 6-digit verification code if you have 2FA setup. "
            "Confirm with [Enter]: "
        )

        authenticate(username, password, sixdigit, local_folder)


def get_access_token(grant_type="client_credentials", debug=False):
    applicationDetails = {}
    applicationDetails["grant_type"] = (None, grant_type)
    if grant_type == "client_credentials":
        applicationDetails["client_id"] = (None, "hgtd-api-client")
        with open(
            os.path.dirname(os.path.realpath(__file__)) + "/config_api"
        ) as config_api:
            applicationDetails["client_secret"] = (
                None,
                config_api.readline().strip(),
            )
        applicationDetails["audience"] = (None, "webframeworks-paas-hgtddb")
        url_to_use = access_token_url
    else:
        raise NotImplementedError(
            "Error: hgtddb-api does only accept grant_type = 'client_credentials'"
        )
    headers = {"content-type": "application/x-www-form-urlencoded"}

    try:
        request = requests.post(url_to_use, data=applicationDetails, headers=headers)
        request.raise_for_status()
        if debug:
            print(request.text)
        return json.loads(request.text)["access_token"]
    except requests.exceptions.HTTPError as errh:
        if debug:
            print("Http Error:", errh)
        raise requests.exceptions.HTTPError("Http Error:", errh)
    except requests.exceptions.ConnectionError as errc:
        if debug:
            print("Error Connecting:", errc)
        raise requests.exceptions.ConnectionError("Error Connecting:", errc)
    except requests.exceptions.Timeout as errt:
        if debug:
            print("Timeout Error:", errt)
        raise requests.exceptions.Timeout("Timeout Error:", errt)
    except requests.exceptions.RequestException as err:
        if debug:
            print("OOps: Something Else", err)
        raise requests.exceptions.RequestException("OOps: Something Else", err)


def fetch_information(endpoint, authorized=True, debug=False, existing_token=None):
    # https://stackoverflow.com/a/47007419
    try:
        if authorized:
            access_token = (
                get_access_token() if existing_token == None else existing_token
            )
            authorization = "Bearer " + access_token
            headers = {
                "Authorization": authorization,
                "content-type": "application/json",
            }
            request = requests.get(
                protectedApiUrlPrefix + endpoint, timeout=600, headers=headers
            )
        else:
            request = requests.get(apiUrlPrefix + endpoint, timeout=600)
        request.raise_for_status()
        if debug:
            print(">> GET response:", request.status_code, request.reason)
        return json.loads(request.text), f"{request.status_code}, {request.reason}"
    except requests.exceptions.HTTPError as errh:
        if debug:
            print("Http Error:", errh)
        raise requests.exceptions.HTTPError("Http Error:", errh)
    except requests.exceptions.ConnectionError as errc:
        if debug:
            print("Error Connecting:", errc)
        raise requests.exceptions.ConnectionError("Error Connecting:", errc)
    except requests.exceptions.Timeout as errt:
        if debug:
            print("Timeout Error:", errt)
        raise requests.exceptions.Timeout("Timeout Error:", errt)
    except requests.exceptions.RequestException as err:
        if debug:
            print("OOps: Something Else", err)
        raise requests.exceptions.RequestException("OOps: Something Else", err)


def post_information(
    endpoint,
    payload,
    authorized=True,
    debug=False,
    dryrun=False,
    content_type="application/json",
    files_payload={},
    existing_token=None,
):
    if debug:
        pprint(payload)
    if not dryrun:
        try:
            if authorized:
                access_token = (
                    get_access_token() if existing_token == None else existing_token
                )
                authorization = "Bearer " + access_token
                if content_type == "application/json":
                    headers = {
                        "Authorization": authorization,
                        "content-type": "application/json",
                    }
                    response = requests.post(
                        protectedApiUrlPrefix + endpoint,
                        data=json.dumps(payload),
                        headers=headers,
                    )
                elif content_type == "multipart/form-data":
                    # we don't need to add , 'content-type': 'multipart/form-data' because it is used implicitly
                    headers = {"Authorization": authorization}
                    response = requests.post(
                        protectedApiUrlPrefix + endpoint,
                        files=files_payload,
                        data=payload,
                        headers=headers,
                    )
                else:
                    raise NotImplementedError("This content-type is not implemented.")
            else:
                if content_type == "application/json":
                    headers = {"content-type": "application/json"}
                    response = requests.post(
                        apiUrlPrefix + endpoint,
                        data=json.dumps(payload),
                        headers=headers,
                    )
                else:
                    raise NotImplementedError("This content-type is not implemented.")
            response.raise_for_status()
            if debug:
                print(">> PATCH response:", response.status_code, response.reason)
            return f"{response.status_code}, {response.reason}"
        except requests.exceptions.HTTPError as errh:
            if debug:
                print("Http Error:", errh)
            raise requests.exceptions.HTTPError("Http Error:", errh)
        except requests.exceptions.ConnectionError as errc:
            if debug:
                print("Error Connecting:", errc)
            raise requests.exceptions.ConnectionError("Error Connecting:", errc)
        except requests.exceptions.Timeout as errt:
            if debug:
                print("Timeout Error:", errt)
            raise requests.exceptions.Timeout("Timeout Error:", errt)
        except requests.exceptions.RequestException as err:
            if debug:
                print("OOps: Something Else", err)
            raise requests.exceptions.RequestException("OOps: Something Else", err)
    else:
        print(">>> Dryrun post operation with endpoint", endpoint)
        print(">>> and payload", payload)


def delete_information(
    endpoint, authorized=True, debug=False, dryrun=False, existing_token=None
):
    if not dryrun:
        try:
            if authorized:
                access_token = (
                    get_access_token() if existing_token == None else existing_token
                )
                authorization = "Bearer " + access_token
                headers = {
                    "Authorization": authorization,
                    "content-type": "application/json",
                }
                response = requests.delete(
                    protectedApiUrlPrefix + endpoint, headers=headers
                )
            else:
                response = requests.delete(apiUrlPrefix + endpoint)
            response.raise_for_status()
            if debug:
                print(">> DELETE response:", response.status_code, response.reason)
            return f"{response.status_code}, {response.reason}"
        except requests.exceptions.HTTPError as errh:
            if debug:
                print("Http Error:", errh)
            raise requests.exceptions.HTTPError("Http Error:", errh)
        except requests.exceptions.ConnectionError as errc:
            if debug:
                print("Error Connecting:", errc)
            raise requests.exceptions.ConnectionError("Error Connecting:", errc)
        except requests.exceptions.Timeout as errt:
            if debug:
                print("Timeout Error:", errt)
            raise requests.exceptions.Timeout("Timeout Error:", errt)
        except requests.exceptions.RequestException as err:
            if debug:
                print("OOps: Something Else", err)
            raise requests.exceptions.RequestException("OOps: Something Else", err)
    else:
        print(">>> Dryrun delete operation with endpoint", endpoint)

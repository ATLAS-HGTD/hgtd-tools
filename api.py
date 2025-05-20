import getpass, json, requests
from pprint import pprint

# === To open links in browser
# Redirect to new frontend
frontendUrlPrefix = 'https://nginx-hgtddb.app.cern.ch'

# === Interaction with hgtd-proddb REST API
# This was the "old" backend, now retired, without SSO
apiUrlPrefix = 'https://backend-hgtddb.app.cern.ch/hgtddb'
# New backend API with protection (e.g. access token, oidc)
protectedApiUrlPrefix = 'https://hgtddb-api.web.cern.ch/hgtddb'
# CERN endpoint to receive API access tokens (e.g. for new backend),
# method client_credentials
access_token_url = 'https://auth.cern.ch/auth/realms/cern/api-access/token'
# We do not yet use password grant_type method to talk to the hgtd-api
#password_token_url = 'https://auth.cern.ch/auth/realms/cern/protocol/openid-connect/token'

# === For user authentication via OpenID (CERN SSO)
# Used to write usernames that are different from the default "None"
# which would result in the default user ATLAS_HGTD_PROD
kc_server= "https://auth.cern.ch"
client_id = "public-client"
client_secret = ""
keycloak_endpoint = kc_server+"/auth/realms/cern/protocol/openid-connect/token"
userinfo_endpoint = kc_server+"/auth/realms/cern/protocol/openid-connect/userinfo"

def get_user(us,pw,to, debug=False):   
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
                "totp": to
                }
        )
        request.raise_for_status()
        access_token = request.json()['access_token']
        # use access token to talk to userinfo endpoint
        request = requests.post(
            userinfo_endpoint,
            data={"access_token": access_token}
        )
        request.raise_for_status()
        if debug:
            print(request.text)
        return request.json()['cern_upn'], f'{request.status_code}, {request.reason}'
    except requests.exceptions.HTTPError as errh:
        if debug:
            print("Http Error:",errh)
        raise requests.exceptions.HTTPError("Http Error:",errh)
    except requests.exceptions.ConnectionError as errc:
        if debug:
            print("Error Connecting:",errc)
        raise requests.exceptions.ConnectionError("Error Connecting:",errc)
    except requests.exceptions.Timeout as errt:
        if debug:
            print("Timeout Error:",errt)
        raise requests.exceptions.Timeout("Timeout Error:",errt)
    except requests.exceptions.RequestException as err:
        if debug:
            print("OOps: Something Else",err)
        raise requests.exceptions.RequestException("OOps: Something Else",err)

def get_access_token(grant_type = 'client_credentials', debug = False):
    applicationDetails = {}    
    applicationDetails['grant_type'] = (None, grant_type)
    if grant_type == 'client_credentials':
        applicationDetails['client_id'] = (None, 'hgtd-api-client')
        applicationDetails['client_secret'] = (None, 'tfMW775EPllKczpWh3uZaE3VQ2aOHUnr')
        applicationDetails['audience'] = (None, 'webframeworks-paas-hgtddb')
        url_to_use = access_token_url
    '''    
    # not yet implemented
    elif grant_type == 'password':
        username = input('Enter username: ')
        password = getpass.getpass('Enter password: ')
        sixdigit = input('Enter 6-digit verification code: ')

        applicationDetails['scope'] = (None, 'openid')
        applicationDetails['username'] = (None, username)
        applicationDetails['password'] = (None, password)
        applicationDetails['totp'] = (None, sixdigit)
        applicationDetails['client_id'] = (None, 'public-client')
        applicationDetails['client_secret'] = (None, '')
        url_to_use = password_token_url
    '''
    headers = {'content-type': 'application/x-www-form-urlencoded'}

    try:
        request = requests.post(url_to_use, data=applicationDetails, headers=headers)
        request.raise_for_status()
        if debug:
            print(request.text)
        return json.loads(request.text)['access_token']
    except requests.exceptions.HTTPError as errh:
        if debug:
            print("Http Error:",errh)
        raise requests.exceptions.HTTPError("Http Error:",errh)
    except requests.exceptions.ConnectionError as errc:
        if debug:
            print("Error Connecting:",errc)
        raise requests.exceptions.ConnectionError("Error Connecting:",errc)
    except requests.exceptions.Timeout as errt:
        if debug:
            print("Timeout Error:",errt)
        raise requests.exceptions.Timeout("Timeout Error:",errt)
    except requests.exceptions.RequestException as err:
        if debug:
            print("OOps: Something Else",err)
        raise requests.exceptions.RequestException("OOps: Something Else",err)

def fetch_information(endpoint, authorized = True, debug = False):
    # https://stackoverflow.com/a/47007419
    try:
        if authorized:
            access_token = get_access_token()
            authorization = 'Bearer ' + access_token
            headers = {'Authorization': authorization, 'content-type': 'application/json'}
            request = requests.get(protectedApiUrlPrefix + endpoint, timeout=600, headers=headers)
        else:
            request = requests.get(apiUrlPrefix + endpoint, timeout=600)
        request.raise_for_status()
        if debug:
            print('>> GET response:', request.status_code, request.reason)
        return json.loads(request.text), f'{request.status_code}, {request.reason}'
    except requests.exceptions.HTTPError as errh:
        if debug:
            print("Http Error:",errh)
        raise requests.exceptions.HTTPError("Http Error:",errh)
    except requests.exceptions.ConnectionError as errc:
        if debug:
            print("Error Connecting:",errc)
        raise requests.exceptions.ConnectionError("Error Connecting:",errc)
    except requests.exceptions.Timeout as errt:
        if debug:
            print("Timeout Error:",errt)
        raise requests.exceptions.Timeout("Timeout Error:",errt)
    except requests.exceptions.RequestException as err:
        if debug:
            print("OOps: Something Else",err)
        raise requests.exceptions.RequestException("OOps: Something Else",err)

def post_information(endpoint, payload, authorized = True, debug = False, dryrun = False):
    headers = {'content-type': 'application/json'}
    if debug:
        pprint(payload)
    if not dryrun:
        try:
            if authorized:
                access_token = get_access_token()
                authorization = 'Bearer ' + access_token
                headers = {'Authorization': authorization, 'content-type': 'application/json'}
                response = requests.post(protectedApiUrlPrefix + endpoint, data=json.dumps(payload), headers=headers)
            else:
                response = requests.post(apiUrlPrefix + endpoint, data=json.dumps(payload), headers=headers)
            response.raise_for_status()
            if debug:
                print('>> PATCH response:', response.status_code, response.reason)
            return f'{response.status_code}, {response.reason}'
        except requests.exceptions.HTTPError as errh:
            if debug:
                print("Http Error:",errh)
            raise requests.exceptions.HTTPError("Http Error:",errh)
        except requests.exceptions.ConnectionError as errc:
            if debug:
                print("Error Connecting:",errc)
            raise requests.exceptions.ConnectionError("Error Connecting:",errc)
        except requests.exceptions.Timeout as errt:
            if debug:
                print("Timeout Error:",errt)
            raise requests.exceptions.Timeout("Timeout Error:",errt)
        except requests.exceptions.RequestException as err:
            if debug:
                print("OOps: Something Else",err)
            raise requests.exceptions.RequestException("OOps: Something Else",err)
    else:
        print('>>> Dryrun post operation with endpoint', endpoint)
        print('>>> and payload', payload)

def delete_information(endpoint, authorized = True, debug = False, dryrun = False):
    if not dryrun:
        try:
            if authorized:
                access_token = get_access_token()
                authorization = 'Bearer ' + access_token
                headers = {'Authorization': authorization, 'content-type': 'application/json'}
                response = requests.delete(protectedApiUrlPrefix + endpoint, headers=headers)
            else:
                response = requests.delete(apiUrlPrefix + endpoint)
            response.raise_for_status()
            if debug:
                print('>> DELETE response:', response.status_code, response.reason)
            return f'{response.status_code}, {response.reason}'
        except requests.exceptions.HTTPError as errh:
            if debug:
                print("Http Error:",errh)
            raise requests.exceptions.HTTPError("Http Error:",errh)
        except requests.exceptions.ConnectionError as errc:
            if debug:
                print("Error Connecting:",errc)
            raise requests.exceptions.ConnectionError("Error Connecting:",errc)
        except requests.exceptions.Timeout as errt:
            if debug:
                print("Timeout Error:",errt)
            raise requests.exceptions.Timeout("Timeout Error:",errt)
        except requests.exceptions.RequestException as err:
            if debug:
                print("OOps: Something Else",err)
            raise requests.exceptions.RequestException("OOps: Something Else",err)
    else:
        print('>>> Dryrun delete operation with endpoint', endpoint)

import json, requests
from pprint import pprint

# Interaction with hgtd-proddb REST API
# The requests are all made against the "old" backend
apiUrlPrefix = 'https://backend-hgtddb.app.cern.ch/hgtddb'

def fetch_information(endpoint, debug = False):
    request = requests.get(apiUrlPrefix + endpoint)
    # https://stackoverflow.com/a/47007419
    try:
        request = requests.get(apiUrlPrefix + endpoint,timeout=600)
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

def post_information(endpoint, payload, debug = False, dryrun = False):
    headers = {'content-type': 'application/json'}
    if debug:
        pprint(payload)
    if not dryrun:
        try:
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

def delete_information(endpoint, debug = False, dryrun = False):
    if not dryrun:
        try:
            response = requests.delete(apiUrlPrefix + endpoint)
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
        print('>>> Dryrun delete operation with endpoint', endpoint)

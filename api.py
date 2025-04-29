import json, requests
from pprint import pprint

# Interaction with hgtd-proddb REST API
# The requests are all made against the "old" backend
apiUrlPrefix = 'https://backend-hgtddb.app.cern.ch/hgtddb'

def fetch_information(endpoint, debug = False):
    request = requests.get(apiUrlPrefix + endpoint)
    if debug:
        print('>> GET response:', request.status_code, request.reason)
    return json.loads(request.text)

def patch_information(endpoint, payload, debug = False):
    headers = {'content-type': 'application/json'}
    if debug:
        pprint(payload)
    response = requests.patch(apiUrlPrefix + endpoint, data=json.dumps(payload), headers=headers)
    if debug:
        print('>> PATCH response:', response.status_code, response.reason)

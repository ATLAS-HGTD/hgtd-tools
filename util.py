import json
import requests
import textwrap
import webbrowser

import api
import data

# === Operations with standard objects (lists, dicts, strings etc.)
def get_sorted_list_of_lists_by_Nth_column(unsorted_list, column):
    sortList = unsorted_list.copy()
    sortList.sort(key=lambda x: x[column])
    return sortList

def get_relevant_SNs_and_partIDs(partsList):
    these_SNs_and_partIDs = get_sorted_list_of_lists_by_Nth_column([[pL['serial_number'],pL['part_id']] for pL in partsList], 0)
    return these_SNs_and_partIDs

# https://stackoverflow.com/a/45287550
class CustomTextWrapper(textwrap.TextWrapper):
    def wrap(self, text):
        split_text = text.split('\n')
        lines = [line for para in split_text for line in textwrap.TextWrapper.wrap(self, para)]
        return lines

# === Operations with canvas objects
def isInSlot(rect, x, y):
    isInSlot = False
    left = rect['x']
    right = rect['x']+rect['w']
    top = rect['y']
    bottom = rect['y']+rect['h']
    if (right >= x
        and left <= x
        and bottom >= y
        and top <= y):
        isInSlot = True
    return isInSlot

# === Operations with API or Browser
def open_webbrowser_with_url(url, debug = False, noExtraPrefix = False):
    if noExtraPrefix:
        if debug:
            print(f'>>> Opening {url} in webbrowser...')
        webbrowser.open_new_tab(url)
    else:
        if debug:
            print(f'>>> Opening {api.frontendUrlPrefix + url} in webbrowser...')
        webbrowser.open_new_tab(api.frontendUrlPrefix + url)

def delete_parents(chi_partID, onlyNonDeleted = True):
    try:
        partstree, responseText = api.fetch_information(f'/parentslist/{chi_partID}/')
        if onlyNonDeleted:
            interesting_partstree = []
            for p in partstree:
                if p['is_record_deleted'] == 'F':
                    interesting_partstree.append(p)
        else:
            interesting_partstree = partstree
            del partstree
        for ip in interesting_partstree:
            responseText = api.delete_information(f'/partstreedelete/{ip['record_id']}/')
        return responseText
    except (requests.exceptions.HTTPError, requests.exceptions.ConnectionError, requests.exceptions.Timeout, requests.exceptions.RequestException) as e:
        raise e
    except ValueError as e:
        raise e

def get_relevant_parts(partKoP_shortname, onlyNonDeleted = True, getFullAttributes = False, useLocal = False):
    KoP_ID = data.KoPID_from_partKoPName[partKoP_shortname]
    retrieve = 'partattributelistbykop' if getFullAttributes else 'partslistbykop'
    try:
        if not useLocal:
            if partKoP_shortname == 'Slot':
                these_parts, responseText = api.fetch_information(f'/partattributelistbykop/{KoP_ID}/')
                with open('./local/all_slots.json', 'w') as f:
                    json.dump(these_parts, f)
                slots, responseText = api.fetch_information(f'/partslistbykop/{KoP_ID}/')
                with open('./local/slots.json', 'w') as f:
                    json.dump(slots, f)
                for alSl in these_parts:
                    for s in slots:
                        if alSl['part_serial_number'] == s['serial_number']:
                            alSl['part_id'] = s['part_id']

            # == OLD ==: had to load PEB attributes to get PEB type in the past, now not necessary anymore
            # because NEW: PEB type is part of PEB SN
            #elif partKoP_shortname == 'PEB':
            #    these_parts, responseText = api.fetch_information(f'/partattributelistbykop/{KoP_ID}/')
            #    with open('./local/all_pebs.json', 'w') as f:
            #        json.dump(these_parts, f)
            #    pebs, responseText = api.fetch_information(f'/partslistbykop/{KoP_ID}/')
            #    with open('./local/pebs.json', 'w') as f:
            #        json.dump(pebs, f)
            #    for alPeb in these_parts:
            #        for p in pebs:
            #            if alPeb['part_serial_number'] == p['serial_number']:
            #                alPeb['part_id'] = p['part_id']
            #                alPeb['serial_number'] = p['serial_number']

            else:
                these_parts, responseText = api.fetch_information(f'/{retrieve}/{KoP_ID}/')
                if retrieve != 'partattributelistbykop':
                    these_parts = [tP for tP in these_parts if tP['is_record_deleted'] == 'F']
        else:
            # slot table is the one table that basically only acts as a static lookup;
            # contains the various location definitions (local & global) but during
            # the lifetime of the detector, the Slot table itself stays constant
            # => can be stored as a local file, don't need to load it freshly each time
            # (at least that's my understanding now during R&D of the database tools)

            # the following two files result from dumping the API-accessed files
            '''
            with open('./local/all_slots.json') as allSlotsJson:
                these_parts, responseText = json.load(allSlotsJson), '200: Local File'
            with open('./local/slots.json') as slotsJson:
                slots, responseText = json.load(slotsJson), '200: Local File'
                
            for alSl in these_parts:
                for s in slots:
                    if alSl['part_serial_number'] == s['serial_number']:
                        alSl['part_id'] = s['part_id']
            '''

            # the following two files result from manually downloading, exporting and converting them
            # this was done because the API endpoint above results in OOMKilled errors!
            with open('./local/Slot_Table_fullJune2025_demo54mod.json') as allSlotsJson:
                these_parts, responseText = json.load(allSlotsJson), '200: Local File'
            with open('./local/Slot_fullJune2025_demo54mod.json') as slotsJson:
                slots, responseText = json.load(slotsJson), '200: Local File'
                
            for alSl in these_parts:
                for s in slots:
                    if alSl['part_serial_number'] == s['Serial #']:
                        alSl['part_id'] = s['Part ID']
        return these_parts, responseText
    except (requests.exceptions.HTTPError, requests.exceptions.ConnectionError, requests.exceptions.Timeout, requests.exceptions.RequestException) as e:
        raise e
    except ValueError as e:
        raise e

def get_parents(chi_partID, onlyNonDeleted = True, ofKind = 'all'):
    try:
        partstree, responseText = api.fetch_information(f'/parentslist/{chi_partID}/')
        if onlyNonDeleted:
            interesting_partstree = []
            for p in partstree:
                if p['is_record_deleted'] == 'F':
                    if ofKind == 'all' or str(data.KoPID_from_partKoPName[ofKind]) == str(p['part_parent']['kind_of_part']['kind_of_part_id']):
                        interesting_partstree.append(p)
            return interesting_partstree, responseText
        else:
            return partstree, responseText
    except (requests.exceptions.HTTPError, requests.exceptions.ConnectionError, requests.exceptions.Timeout, requests.exceptions.RequestException) as e:
        raise e
    except ValueError as e:
        raise e

# this is quicker (a bit) because it only reads the children of the given parent
def get_children(par_partID, onlyNonDeleted = True, ofKind = 'all'):
    try:
        partstree, responseText = api.fetch_information(f'/childslist/{par_partID}/')
        if onlyNonDeleted:
            interesting_partstree = []
            for p in partstree:
                if p['is_record_deleted'] == 'F':
                    if ofKind == 'all' or str(data.KoPID_from_partKoPName[ofKind]) == str(p['part']['kind_of_part']['kind_of_part_id']):
                        interesting_partstree.append(p)
            return interesting_partstree, responseText
        else:
            return partstree, responseText
    except (requests.exceptions.HTTPError, requests.exceptions.ConnectionError, requests.exceptions.Timeout, requests.exceptions.RequestException) as e:
        raise e
    except ValueError as e:
        raise e

def get_manufacturers(onlyNonDeleted = True):
    try:
        manufacturers, responseText = api.fetch_information(f'/manufacturers')
        if onlyNonDeleted:
            interesting_manufacturers = []
            for m in manufacturers:
                if m['is_record_deleted'] == 'F':
                    interesting_manufacturers.append(m)
            return interesting_manufacturers, responseText
        else:
            return manufacturers, responseText
    except (requests.exceptions.HTTPError, requests.exceptions.ConnectionError, requests.exceptions.Timeout, requests.exceptions.RequestException) as e:
        raise e
    except ValueError as e:
        raise e

# this loads the full partstree, quite slow (and big!)
def load_partstree(onlyNonDeleted = True, useLocal = False):
    try:
        if not useLocal:
            partstree, responseText = api.fetch_information(f'/partstreelist')
            with open('./local/partstreelist.json', 'w') as f:
                json.dump(partstree, f)
        else:
            # WARNING: relations OTOH are dynamic in nature and should not be accidentally
            # picked up from possibly outdated local files!!!
            # Please use for testing purposes only, you should now not need this anymore.
            with open('./local/partstreelist.json') as partstreeJson:
                partstree, responseText = json.load(partstreeJson), '200: Local File'
        interesting_partstree = []
        for p in partstree:
            if p['is_record_deleted'] == 'F':
                if p['part']['kind_of_part']['kind_of_part_id'] == 1005 and p['part_parent']['kind_of_part']['kind_of_part_id'] == 2407:
                    interesting_partstree.append(p)
        return interesting_partstree, responseText
    except (requests.exceptions.HTTPError, requests.exceptions.ConnectionError, requests.exceptions.Timeout, requests.exceptions.RequestException) as e:
        raise e
    except ValueError as e:
        raise e

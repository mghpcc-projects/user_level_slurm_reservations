"""
MassOpenCloud / Hardware Isolation Layer (HIL)
User Level Slurm Reservations (ULSR)

Infiniband Link Management - Database Interface

Uses (pre-existing) Serverless interface to AWS 
Lambda and DynamoDB to save and retrieve IB port state

March 2018, Tim Donahue    tdonahue@mit.edu
"""

import json
import requests
from urlparse import urljoin
from ulsr_settings import (IB_DB_URL, IB_DB_KEY, IB_DB_CONTENT_TYPE, 
                           IB_DB_GET_TIMEOUT)
from ulsr_logging import log_info, log_debug, log_error


def read_ib_db(resname, debug=False):
    '''
    Read IB port state for the named reservation using a REST GET
    interface
    '''
    try:
        resp = requests.get(urljoin(IB_DB_URL, resname), headers={'X-Api-Key': IB_DB_KEY},
                            timeout=IB_DB_GET_TIMEOUT)
    except Exception as e:
        log_error('GET failed: %s' % e)
        return {}

    if not resp.ok:
        log_error('GET failed: `[%s] %s`' % (resp.status_code, resp.reason))
        return {}

    # A miss will return 200 OK, so check the content length
    if (int(resp.headers['Content-Length']) == 0):
        log_error('No port state data found for `%s`' % resname)
        return {}

    # Decode the response:
    #   Step 1: JSON => {'ibSplist': Switch port dict string}
    #   Step 2: Switch port dict string => {Switch port dict}

    rdict = resp.json()
    if (rdict['resId'] != resname):
        log_error('Reservation name mismatch (`%s`)' % rdict['resID'])
        return {}

    return json.loads(rdict['ibSplist'])


def write_ib_db(resname, switch_ports, debug=False):
    '''
    Write IB port state information for the named reservation using 
    a REST POST interface

    switch_ports is a dict of the form:
    {switch1_GUID: {port1_no: 'up' | 'down', ...}, switch2_GUID: {...}, ...}

    The passed port state data is modified to include {resid: <resname>}, which 
    forms the DB key, and {'ib_splist':[switch_port_dict]}.
    '''
    status = True
    headers = {'X-Api-Key': IB_DB_KEY, 'Content-Type': IB_DB_CONTENT_TYPE}
    resdata = {}
    resdata['resid'] = resname
    resdata['ib_splist'] = switch_ports

    if debug:
        log_debug('Updating IB state for `%s' % resname)
        log_debug('  %s' % json.dumps(resdata))

    resp = requests.post(IB_DB_URL, headers=headers, data=json.dumps(resdata))
    if not resp.ok:
        log_error('POST failed: `[%s]: %s`' % (resp.status_code, resp.reason))
        log_error('  %s' % resp.headers)
        status = False

    return status

# EOF

if False:
    write_ib_db('flexalloc_moc_cc_1000_test1', 
                {'0x1000200030004000': {'1': 'up', '2': 'down'}, 
                 '0x1000200030004001': {'3': 'down', '2': 'up'}}, debug=True)
    switch_ports = read_ib_db('flexalloc_moc_cc_1000_test1', debug=True)
    print switch_ports

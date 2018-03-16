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
from ulsr_settings import IB_DB_URL, IB_DB_KEY, IB_DB_CONTENT_TYPE
from ulsr_logging import log_info, log_debug, log_error


def _decode_list(data):
    rv = []
    for item in data:
        if isinstance(item, unicode):
            item = item.encode('utf-8')
        elif isinstance(item, list):
            item = _decode_list(item)
        elif isinstance(item, dict):
            item = _decode_dict(item)
        rv.append(item)
    return rv

def _decode_dict(data):
    rv = {}
    for key, value in data.iteritems():
        if isinstance(key, unicode):
            key = key.encode('utf-8')
        if isinstance(value, unicode):
            value = value.encode('utf-8')
        elif isinstance(value, list):
            value = _decode_list(value)
        elif isinstance(value, dict):
            value = _decode_dict(value)
        rv[key] = value
    return rv


def read_ib_db(resname, debug=False):
    '''
    Read IB port state for the named reservation using a REST GET
    interface
    '''

# $$$    NEEDS TIMEOUT

    resp = requests.get(urljoin(IB_DB_URL, resname), headers={'X-Api-Key': IB_DB_KEY})
    if not resp.ok:
        log_error('GET failed: `[%s] %s`' % (resp.status_code, resp.reason))
        return {}

    # A miss will return 200 OK, so check the content length
    if (int(resp.headers['Content-Length']) == 0):
        log_error('No port state data found for `%s`' % resname)
        return {}

    # Convert Unicode to ASCII and validate the reservation name
    switch_ports = resp.json()['ibSplist']
    print type(switch_ports)
    return

    if (rdict['resId'] != resname):
        log_error('Reservation name mismatch (`%s`)' % rdict['resID'])
        return {}

    del rdict['resId']
    if 'foo' in rdict:
        del rdict['foo']

    print json.loads(rdict['ibSplist'])
    return rdict


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
    resdata['ib_splist'] = [switch_ports]

    if True:
        log_debug('Updating IB state for `%s' % resname)
        log_debug('  %s' % json.dumps(resdata))

    resp = requests.post(IB_DB_URL, headers=headers, data=json.dumps(resdata))
    if not resp.ok:
        log_error('POST failed: `[%s]: %s`' % (resp.status_code, resp.reason))
        log_error('  %s' % resp.headers)
        status = False

    return status

# EOF

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


def read_ib_db(resname, debug=False):
    '''
    Read IB port state for the named reservation using a REST GET
    interface
    '''
    rdict = {}

    resp = requests.get(urljoin(IB_DB_URL, resname), headers={'X-Api-Key': IB_DB_KEY})
    if resp.ok:
        # A miss will return 200 OK, so check the content length
        if (int(resp.headers['Content-Length']) != 0):
            rdict = resp.json()
        else:
            log_error('No port state data found for `%s`' % resname)
    else:
        log_error('GET failed: `[%s] %s`' % (resp.status_code, resp.reason))

    return rdict


def write_ib_db(resname, switch_ports, debug=False):
    '''
    Write IB port state information for the named reservation using 
    a REST POST interface

    switch_ports is a dict of the form:
    {switch1_GUID: {port_no: 'up' | 'down', ...}, switch2_GUID: {...}, ...}

    The passed port state data is modified to include {resid: <resname>}, which 
    forms the DB key.
    '''
    status = True
    headers = {'X-Api-Key': IB_DB_KEY, 'Content-Type': IB_DB_CONTENT_TYPE}
    switch_ports['resid'] = resname
    if debug:
        log_debug('Updating IB state for `%s' % resname)
        log_debug('  %s' % json.dumps(switch_ports))

    resp = requests.post(IB_DB_URL, headers=headers, data=json.dumps(switch_ports))
    if not resp.ok:
        log_error('POST failed: `[%s]: %s`' % (resp.status_code, resp.reason))
        log_error('  %s' % resp.headers)
        status = False

    return status

# EOF

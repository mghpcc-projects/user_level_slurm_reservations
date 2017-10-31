"""
MassOpenCloud / Hardware Isolation Layer (MOC/HIL)

HIL Client Interface

August 2017, Tim Donahue	tpd001@gmail.com
"""

import urllib

from hil.client.client import Client, RequestsHTTPClient
from hil.client.base import FailedAPICallException
from hil_slurm_logging import log_info, log_debug, log_error
from hil_slurm_settings import HIL_ENDPOINT, HIL_USER, HIL_PW


def hil_client_connect(endpoint_ip, name, pw):
    '''
    Connect to the HIL server and return a HIL Client instance
    '''
    hil_http_client = RequestsHTTPClient()
    if not hil_http_client:
        log_error('Unable to create HIL HTTP Client')
        return None

    hil_http_client.auth = (name, pw)

    return Client(endpoint_ip, hil_http_client)


def check_hil_interface():
    hil_client = hil_init()


def hil_reserve_nodes(nodelist, from_project, hil_client=None):
    '''
    Cause HIL nodes to move from the 'from' project to the HIL free pool.
    Typically, the 'from' project is the Slurm loaner project.

    This methods first powers off the nodes, then disconnects all networks,
    then moves the node from the 'from' project to the free pool.

    We power off the nodes before removing the networks because the IPMI
    network is also controlled by HIL. If we removed all networks, then we will
    not be able to perform any IPMI operations on nodes.
    '''
    status = True

    if not hil_client:
        hil_client = hil_init()

    for node in nodelist:
        # get information from node
        try:
            node_info = hil_client.node.show(node)
        except:
            log_error('HIL reservation failure: HIL node info unavailable, node `%s`' % node)
            status = False
            continue

        project = node_info['project']
        if (project != from_project):
            log_error('HIL reservation failure: Node `%s` (in project `%s`) not in `%s` project' % (node, project, from_project))
            status = False
            continue

    for node in nodelist:
        # prep and move the node from the Slurm project to the HIL free pool
        try:
            hil_client.node.power_off(node)
        except:
            log_error('HIL reservation failure: Unable to power off node `%s`' % node)
            status = False
            continue

    for node in nodelist:
        if not _remove_all_networks(node, hil_client):
            status = False
            continue

    for node in nodelist:
        try:
            hil_client.project.detach(from_project, node)
        except:
            log_error('HIL reservation failure: Unable to detach node `%s` from project `%s`' % (node, from_project))
            status = False
            continue

    return status


def hil_free_nodes(nodelist, to_project, hil_client=None):
    '''
    Cause HIL nodes to move the HIL free pool to the 'to' project.
    Typically, the 'to' project is the Slurm loaner project.

    This method first powers off the nodes, then disconnects all networks,
    then moves the node from the free pool to the 'to' project.

    We power off the nodes before removing the networks because the IPMI
    network is also controlled by HIL. If we removed all networks, then we will
    not be able to perform any IPMI operations on nodes.
    '''
    status = True

    if not hil_client:
        hil_client = hil_init()

    for node in nodelist:
        # get information from node
        try:
            node_info = hil_client.node.show(node)
        except:
            log_error('HIL release failure: HIL node info unavailable, node `%s`' % node)
            status = False
            continue

        # If the node is in the Slurm project now, skip further processing, but don't indicate
        # failure.
        project = node_info['project']
        if (project == to_project):
            log_info('HIL release: Node `%s` already in `%s` project, skipping' % (node, to_project))
            continue

        # prep and move the node from the HIL free pool to the Slurm project
        try:
            hil_client.node.power_off(node)
        except:
            log_error('HIL release failure: Unable to power off node `%s`' % node)
            status = False
            continue

        if not _remove_all_networks(node, hil_client):
            status = False
            continue

        try:
            hil_client.project.connect(to_project, node)
        except:
            log_error('HIL reservation failure: Unable to connect node `%s` to project `%s`' % (node, to_project))
            status = False
            continue

    return status


def hil_init():
    return hil_client_connect(HIL_ENDPOINT, HIL_USER, HIL_PW)


def _remove_all_networks(node, hil_client):
    '''
    Disconnect all networks from all of the node's NICs
    '''
    try:
        node_info = hil_client.node.show(node)
    except:
        log_error('Failed to retrieve info for HIL node `%s`' % node)
        return False

    status = True

    # get node information and then iterate on the nics
    for nic in node_info['nics']:
        # get the port and switch to which the nics are connected to
        port = nic['port']
        switch = nic['switch']
        if port and switch:
            try:
                hil_client.port.port_revert(switch, port)
            except:
                log_error('Failed to revert port `%s` on node `%s` switch `%s`' % (port, node, switch))
                status = False
                continue

    return status

# EOF

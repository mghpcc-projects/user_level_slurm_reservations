"""
MassOpenCloud / Hardware Isolation Layer (MOC/HIL)

HIL Client Interface

August 2017, Tim Donahue	tpd001@gmail.com
"""

import urllib

from hil.client.client import Client, RequestsHTTPClient
from hil.client.base import FailedAPICallException
from hil_slurm_logging import log_info, log_debug, log_error
from hil_slurm_settings import HIL_ENDPOINT, HIL_USER, HIL_PW, HIL_SLURM_PROJECT


# Place holder -> need to assert that the node's Slurm proj matches this
SLURM_PROJECT = HIL_SLURM_PROJECT


def hil_client_connect(endpoint_ip, name, pw):
    '''
    '''
    hil_http_client = RequestsHTTPClient()
    if not hil_http_client:
        log_error('Unable to create HIL HTTP Client')
        return None

    hil_http_client.auth = (name, pw)

    return Client(endpoint_ip, hil_http_client)


def check_hil_interface():
    hil_client = hil_init()


def hil_reserve_nodes(hil_client, nodelist):
    '''
    Cause HIL nodes to move from the Slurm loaner project to the HIL free pool.

    This methods first powers off the nodes, then disconnects all networks and
    then moves the node from the Slurm project to the free pool.

    We power off the nodes before removing the networks because the ipmi
    network is also controlled by HIL. If we removed all networks, then we will
    not be able to perform any ipmi operations on nodes.
    '''
    status = True

    if not hil_client:
        hil_client = hil_init()

    for node in nodelist:
        # get information from node
        try:
            node_info = hil_client.node.show(node)
        except:
            log_error('HIL reservation failure: HIL node info unavailable')
            return False

        project = node_info['project']
        if (project != SLURM_PROJECT):
            log_error('HIL reservation failure: Node %s (project %s) not in %s project' % (node, project, SLURM_PROJECT))
            status = False
            continue

        # prep and move the node to free pool
        try:
            hil_client.node.power_off(node)
        except:
            log_error('HIL reservation failure: Unable to power off node %s' % node)
            status = False
            continue

        _remove_all_networks(node, hil_client)

        try:
            hil_client.project.detach(project, node)
        except:
            log_error('HIL reservation failure: Unable detach node %s from project %s' % (node, project))
            status = False
            continue

    return status


def hil_free_nodes(nodelist):
    '''
    Cause HIL nodes to move from the HIL free pool to the Slurm loaner project.

    This methods first powers off the nodes, then disconnects all networks and
    then moves the node from the free pool to the Slurm project.

    We power off the nodes before removing the networks because the ipmi
    network is also controlled by HIL. If we removed all networks, then we will
    not be able to perform any ipmi operations on nodes.
    '''
    hil_client = hil_init()
    for node in nodelist:
        # get information from node
        node_info = hil_client.node.show(node)
        project = node_info['project']
        # check that the node is not in Slurm already
        assert project != slurm_project
        # prep and return node to Slurm
        hil_client.node.power_off(node)
        _remove_all_networks(node, hil_client)
        hil_client.project.connect(slurm_project, node)


def hil_init():
    hil_client = hil_client_connect(HIL_ENDPOINT, HIL_USER, HIL_PW)
    return hil_client


def _remove_all_networks(node, hil_client):
    """remove all networks from a node's nics"""
    node_info = hil_client.node.show(node)
    # get node information and then iterate on the nics
    for nic in node_info['nics']:
        # get the port and switch to which the nics are connected to
        port = nic['port']
        switch = nic['switch']
        if port and switch:
            hil_client.port.port_revert(switch, port)

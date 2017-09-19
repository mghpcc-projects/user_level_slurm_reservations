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



def hil_client_connect(endpoint_ip, name, pw):
    '''
    '''
    hil_http_client = RequestsHTTPClient()
    hil_http_client.auth = (name, pw)

    return Client(endpoint_ip, hil_http_client)


def check_hil_interface():
    hil_client = hil_init()


def hil_reserve_nodes(nodelist, dest_project):
    '''
    Cause HIL nodes to move from the Slurm loaner project to a new HIL project.

    This methods first powers off the nodes, then disconnects all networks and
    then moves the node from the Slurm project to the free pool.

    We power off the nodes before removing the networks because the ipmi
    network is also controlled by HIL. If we removed all networks, then we will
    not be able to perform any ipmi operations on nodes.
    '''
    hil_client = hil_init()
    for node in nodelist:
        # get information from node
        node_info = hil_client.node.show(node)
        project = node_info['project']
        # check that the correct project is stored
        assert project == HIL_SLURM_PROJECT
        # prep and move the node to free pool
        hil_client.node.power_off(node)
        _remove_all_networks(node, hil_client)
        hil_client.project.detach(project, node)
        hil_client.project.connect(dest_project, node)


def hil_free_nodes(nodelist, dest_project):
    '''
    Cause HIL nodes to move from a HIL project to the Slurm loaner project.

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
        assert project != HIL_SLURM_PROJECT
        # prep and return node to Slurm
        hil_client.node.power_off(node)
        _remove_all_networks(node, hil_client)
        hil_client.project.connect(HIL_SLURM_PROJECT, node)


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

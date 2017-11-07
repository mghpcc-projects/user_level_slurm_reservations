"""
MassOpenCloud / Hardware Isolation Layer (MOC/HIL)

HIL Client Interface

August 2017, Tim Donahue	tpd001@gmail.com
"""

import urllib

import time

from hil.client.client import Client, RequestsHTTPClient
from hil.client.base import FailedAPICallException
from hil_slurm_logging import log_info, log_debug, log_error
from hil_slurm_settings import HIL_ENDPOINT, HIL_USER, HIL_PW

# timeout ensures that networking actions are completed in a resonable time.
HIL_TIMEOUT = 13


class HILClientFailure(Exception):
    """Exception indicating that the HIL client failed"""


class ProjectMismatchError(Exception):
    """Raised when projects don't match"""


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
    if not hil_client:
        hil_client = hil_init()

    # Get information from node and ensure that the node is actually connected
    # to <from_project> before proceeding.
    for node in nodelist:
        node_info = show_node(hil_client, node)

        project = node_info['project']
        if (project != from_project):
            log_error('HIL reservation failure: Node `%s` (in project `%s`) not in `%s` project' % (node, project, from_project))
            raise ProjectMismatchError()

    # Power off all nodes.
    for node in nodelist:
        power_off_node(hil_client, node)

    # Remove all networks from nodes.
    for node in nodelist:
        _remove_all_networks(hil_client, node)

    # Finally, remove node from project.
    for node in nodelist:
        remove_node_from_project(hil_client, node, from_project)


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

    if not hil_client:
        hil_client = hil_init()

    # Get information from node and ensure that the node is actually connected
    # to <from_project> before proceeding.
    for node in nodelist:
        node_info = show_node(hil_client, node)

        # If the node is in the Slurm project now, skip further processing, but don't indicate
        # failure.
        project = node_info['project']
        if (project == to_project):
            log_info('HIL release: Node `%s` already in `%s` project, skipping' % (node, to_project))
            nodelist.remove(node)

    # Power off all nodes.
    for node in nodelist:
        power_off_node(hil_client, node)

    # Remove all networks from nodes.
    for node in nodelist:
        _remove_all_networks(hil_client, node)

    # Finally, connect node to <to_project>
    for node in nodelist:
        try:
            hil_client.project.connect(to_project, node)
            log_info('Node `%s` connected to project `%s`' % (node, to_project))
        except FailedAPICallException, ConnectionError:
            log_error('HIL reservation failure: Unable to connect node `%s` to project `%s`' % (node, to_project))
            raise HILClientFailure()


def hil_init():
    return hil_client_connect(HIL_ENDPOINT, HIL_USER, HIL_PW)


def _remove_all_networks(hil_client, node):
    '''
    Disconnect all networks from all of the node's NICs
    '''
    node_info = show_node(hil_client, node)

    # get node information and then iterate on the nics
    for nic in node_info['nics']:
        # get the port and switch to which the nics are connected to
        port = nic['port']
        switch = nic['switch']
        if port and switch:
            try:
                hil_client.port.port_revert(switch, port)
                log_info('Removed all networks from node `%s`' % node)
            except FailedAPICallException, ConnectionError:
                log_error('Failed to revert port `%s` on node `%s` switch `%s`' % (port, node, switch))
                raise HILClientFailure()


def _ensure_no_networks(hil_client, node):
    """Polls on the output of show node to check if networks have been removed.
    It will timeout and raise an exception if it's taking too long.
    """
    connected_to_network = True
    end_time = time.time() + HIL_TIMEOUT
    while connected_to_network:
        if time.time() > end_time:
            raise HILClientFailure('Networks not removed from node in reasonable time')
        node_info = show_node(hil_client, node)
        for nic in node_info['nics']:
            if nic['networks']:
                connected_to_network = True
                break
            else:
                connected_to_network = False
        # don't tight loop.
        time.sleep(1)
    return


def remove_node_from_project(hil_client, node, from_project):
    """Remove node from <from_project>
    Handles the case when there's an active networking action on the nic
    """
    try:
        _ensure_no_networks(hil_client, node)
        hil_client.project.detach(from_project, node)
        log_info('Node `%s` removed from project `%s`' % (node, from_project))
    except FailedAPICallException as ex:
        # check what the type of error it is and retry until network actions
        # are taken care of.
        if ex.message == 'Node has pending network actions':
            remove_node_from_project(hil_client, node, from_project)
            return
        log_error('HIL reservation failure: Unable to detach node `%s` from project `%s`' % (node, from_project))
        raise HILClientFailure()


def show_node(hil_client, node):
    """Returns node information and takes care of handling exceptions"""
    try:
        node_info = hil_client.node.show(node)
        return node_info
    except FailedAPICallException, ConnectionError:
        # log a note for the admins, and the exact exception before raising
        # an error.
        log_error('HIL reservation failure: HIL node info unavailable, node `%s`' % node)
        raise HILClientFailure()


def power_off_node(hil_client, node):
    try:
        hil_client.node.power_off(node)
        log_info('Node `%s` succesfully powered off' % node)
    except FailedAPICallException, ConnectionError:
        log_error('HIL reservation failure: Unable to power off node `%s`' % node)
        raise HILClientFailure()

"""
MassOpenCloud / Hardware Isolation Layer (MOC/HIL)

HIL Client Interface

August 2017, Tim Donahue	tdonahue@mit.edu
             Naved Ansari   naved001@bu.edu
"""

import time

from hil.client.client import Client, RequestsHTTPClient
from hil.client.base import FailedAPICallException
from ulsr_logging import log_info, log_debug, log_error
from ulsr_settings import HIL_ENDPOINT, HIL_USER, HIL_PW, OBM_NIC, \
 OBM_NETWORK, MAINTENANCE_PROJECT
from ulsr_helpers import is_hil_available
from requests import ConnectionError

# timeout ensures that networking actions are completed in a resonable time.
HIL_TIMEOUT = 20


class HILClientFailure(Exception):
    """Exception indicating that the HIL client failed"""


class ProjectMismatchError(Exception):
    """Raised when projects don't match"""


def _hil_client_connect(endpoint_ip, name, pw):
    '''
    Connect to the HIL server and return a HIL Client instance
    Note this call will succeed if the API server is running, but the network server is down           '''
    hil_http_client = RequestsHTTPClient()
    if not hil_http_client:
        log_error('Unable to create HIL HTTP client (1)')
        return None

    hil_http_client.auth = (name, pw)
    c = Client(endpoint_ip, hil_http_client)
    if not c:
        log_error('Unable to create HIL client (2)')

    return c


def hil_init():
    '''
    '''
    if is_hil_available():
        status =_hil_client_connect(HIL_ENDPOINT, HIL_USER, HIL_PW)
    else:
        log_info('HIL unavailable, all HIL operations will appear to succeed')
        status = True
    return status


def check_hil_interface():
    hil_client = hil_init()


def hil_reserve_nodes(nodelist, from_project, hil_client=None):
    '''
    Cause HIL nodes to move from the 'from' project to the HIL free pool.
    Typically, the 'from' project is the Slurm loaner project.

    This method does some state checking and corrections before proceeding:

    1. If a node is already in the free pool, it skips processing it.
    2. If the node is not in the from_project, them a project mismatch error
    is raised. Though, a node can be in the maintenance project.
    3. The nodes are connected to the obm_network, and powered off.
    4. Then the obm_networks are removed.
    5. Finally, the nodes are moved to the HIL free pool. At this stage, all nodes
    are powered off.

    '''
    if not is_hil_available():
        return

    if not hil_client:
        hil_client = hil_init()

    # Get information from node and ensure that the node is actually connected
    # to <from_project> before proceeding.
    # iterate over a copy of nodelist, otherwise we can't modify it.

    for node in nodelist[:]:

        node_info = show_node(hil_client, node)
        project = node_info['project']

        # if node already in the free pool, skip any processing.
        if project is None:
            log_info('HIL release: Node `%s` already in the free pool, skipping' % node)
            nodelist.remove(node)

        elif project != from_project and project != MAINTENANCE_PROJECT:
            log_error('HIL reservation failure: Node `%s` (in project `%s`) not in `%s` project' % (node, project, from_project))
            raise ProjectMismatchError()

    # Power off all nodes.
    # Check if the obm network is connected, if not, connect it.
    for node in nodelist:
        if not _is_network_connected(hil_client, node, OBM_NETWORK, 'vlan/native'):
            hil_client.node.connect_network(node, OBM_NIC, OBM_NETWORK, 'vlan/native')
        _ensure_network_connected(hil_client, node, OBM_NETWORK, 'vlan/native')
        power_off_node(hil_client, node)

    # Remove all networks from nodes.
    for node in nodelist:
        _remove_all_networks(hil_client, node)

    # Finally, remove node from `from_project` and MAINTENANCE-PROJECT.
    for node in nodelist:

        # this call will check multiple times before raising an error.
        _ensure_no_networks(hil_client, node)
        remove_node_from_project(hil_client, node, from_project)

        node_info = show_node(hil_client, node)
        project = node_info['project']

        if project == MAINTENANCE_PROJECT:
            remove_node_from_project(hil_client, node, MAINTENANCE_PROJECT)


def hil_free_nodes(nodelist, to_project, hil_client=None):
    '''
    Cause HIL nodes to move from the HIL free pool and maintenance-project
    to the 'to' project. Typically, the 'to' project is the Slurm loaner project.

    This method does some state checking and corrections before proceeding:

    1. If the ndoe is already in the to_project, skip any processing.
    2. if the node doesn't belong to the free pool, and is not in the maintenance
    pool, then we *forcibly* remove it from that project and put it in the maintenance project.
    3. For nodes, that are in the free pool, put them in the maintenance project.
    4. When all nodes are in the maintennace project. Do the the following:
        * Connect them to the OBM_network.
        * Power off the nodes.
        * Remove the obm network
        * Remove the nodes from the maintenance project.
    5. Connect the nodes to the to_project.

     '''

    if not is_hil_available():
        return

    if not hil_client:
        hil_client = hil_init()

    # Get information from node and ensure that the node is actually connected
    # to <from_project> before proceeding.
    # iterate over a copy of nodelist, otherwise we can't modify it.
    for node in nodelist[:]:
        node_info = show_node(hil_client, node)

        # If the node is in the Slurm project now, skip further processing, but don't indicate
        # failure.

        project = node_info['project']

        if (project == to_project):
            log_info('HIL release: Node `%s` already in `%s` project, skipping' % (node, to_project))
            nodelist.remove(node)
        elif (project is not None and project != MAINTENANCE_PROJECT):
            # if a node was not in the free pool or the maintenance project.
            # we remove it from that project, which puts it in the maintenance pool.
            log_info('Node %s is not in the free pool' % node)
            _remove_all_networks(hil_client, node)
            _ensure_no_networks(hil_client, node)
            remove_node_from_project(hil_client, node, project)
        else:
            # if the node was in the free pool, then put it in the
            # maintenance project
            connect_node_to_project(hil_client, node, MAINTENANCE_PROJECT)

    for node in nodelist:
        # now that nodes are in maintenance project. connect the obm_network and
        # poweroff the nodes.
        hil_client.node.connect_network(node, OBM_NIC, OBM_NETWORK, 'vlan/native')
        _ensure_network_connected(hil_client, node, OBM_NETWORK, 'vlan/native')
        power_off_node(hil_client, node)
        hil_client.node.detach_network(node, OBM_NIC, OBM_NETWORK)
        _ensure_no_networks(hil_client, node)
        hil_client.project.detach(MAINTENANCE_PROJECT, node)

    # Finally, connect node to <to_project>
    for node in nodelist:
        connect_node_to_project(hil_client, node, to_project)


# BUNCH OF HELPER METHODS

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
            except FailedAPICallException as e:
                log_error('Failed to revert port `%s` on node `%s` switch `%s`' % (port, node, switch))
                raise HILClientFailure(e)
            except ConnectionError as e:
                log_error("_remove_all_networks: Couldn't connect to HIL server.")
                raise HILClientFailure(e)



def _ensure_no_networks(hil_client, node):
    """Polls on the output of show node to check if networks have been removed.
    It will timeout and raise an exception if it's taking too long.

    This method will be updated to use the show_networking_action API once
    hil v0.3 is released
    """
    end_time = time.time() + HIL_TIMEOUT
    while time.time() < end_time:
        node_info = show_node(hil_client, node)
        for nic in node_info['nics']:
            if nic['networks']:
                break
        # don't tight loop.
        time.sleep(0.5)
    raise HILClientFailure('Networks not removed from node %s in reasonable time', node)


def _ensure_network_connected(hil_client, node, network, channel):
    """Polls on the output of show node to check if the specified network
    was connected or not.

    This method will be updated to use the show_networking_action API once
    hil v0.3 is released
    """
    end_time = time.time() + HIL_TIMEOUT
    while time.time() < end_time:
        if _is_network_connected(hil_client, node, network, channel):
            return
        # don't tight loop.
        time.sleep(0.5)
    raise HILClientFailure('%s is not connected', network)


def _is_network_connected(hil_client, node, network, channel):
    """Returns a boolean indicating whether <network> is connected to <node>
    or not"""
    node_info = show_node(hil_client, node)
    for nic in node_info['nics']:
        try:
            if nic['networks'][channel] == network:
                return True
        except KeyError:
            pass
    return False


def show_node(hil_client, node):
    """Returns node information and takes care of handling exceptions"""
    try:
        node_info = hil_client.node.show(node)
        return node_info
    except FailedAPICallException as e:
        log_error('show_node for %s failed', node)
        raise HILClientFailure(e)
    except ConnectionError as e:
        log_error("Show Node: Couldn't connect to HIL server.")
        raise HILClientFailure(e)


def power_off_node(hil_client, node):
    try:
        hil_client.node.power_off(node)
        log_info('Node `%s` succesfully powered off' % node)
    except FailedAPICallExceptionas e:
        log_error('Unable to power off node `%s`' % node)
        raise HILClientFailure(e)
    except ConnectionError as e:
        log_error("power_off_node: Couldn't connect to HIL server.")
        raise HILClientFailure(e)


def remove_node_from_project(hil_client, node, project):
    try:
        hil_client.project.detach(project, node)
        log_info('Node `%s` removed from project `%s`' % (node, project))
    except FailedAPICallException as e:
        log_error('Unable to detach node `%s` from project `%s`' % (node, project))
        raise HILClientFailure(e)
    except ConnectionError as e:
        log_error("remove_node_from_project: Couldn't connect to HIL server.")
        raise HILClientFailure(e)


def connect_node_to_project(hil_client, node, project):
    try:
        hil_client.project.connect(project, node)
        log_info('Node `%s` connected to project `%s`' % (node, project))
    except FailedAPICallException as e:
        log_error('Unable to connect node `%s` to project `%s`' % (node, project))
        raise HILClientFailure(e)
    except ConnectionError as e:
        log_error("connect_node_to_project: Couldn't connect to HIL server.")
        raise HILClientFailure(e)

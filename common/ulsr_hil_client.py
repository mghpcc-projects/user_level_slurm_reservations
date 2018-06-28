"""
MassOpenCloud / Hardware Isolation Layer (MOC/HIL)

HIL Client Interface

August 2017, Tim Donahue    tdonahue@mit.edu
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


def hil_client_object(endpoint_ip, name, pw):
    """"Returns a HIL client object"""
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
        status = hil_client_object(HIL_ENDPOINT, HIL_USER, HIL_PW)
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
            log_info(
                'HIL release: Node `%s` already in the free pool, skipping' % node)
            nodelist.remove(node)
        elif project != from_project and project != MAINTENANCE_PROJECT:
            log_error('HIL reservation failure: Node `%s` (in project `%s`) not in `%s` project' % (
                node, project, from_project))
            raise ProjectMismatchError()

    # Power off all nodes.
    # Check if the obm network is connected, if not, connect it.
    for node in nodelist:
        if not _is_network_connected(hil_client, node, OBM_NETWORK, 'vlan/native'):
            status_id = connect_network(hil_client, node, OBM_NIC,
                                        OBM_NETWORK, 'vlan/native')
            assert_network_operation_success(hil_client, status_id)
        power_off_node(hil_client, node)

    # Queue the network operations to remove all networks from all nodes, but
    # don't check the success of the operations just yet.
    status_ids = []
    for node in nodelist:
        status_ids.extend(remove_all_networks(hil_client, node))

    # Check the status of the networking actions after we have queued all
    # operations in the previous step.
    for status_id in status_ids:
        assert_network_operation_success(hil_client, status_id)

    # Finally, remove node from `from_project` and MAINTENANCE_PROJECT.
    for node in nodelist:
        node_info = show_node(hil_client, node)
        project = node_info['project']

        if project == from_project:
            remove_node_from_project(hil_client, node, from_project)

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
            log_info('HIL release: Node `%s` already in `%s` project, skipping' % (
                node, to_project))
            nodelist.remove(node)
        elif (project is not None and project != MAINTENANCE_PROJECT):
            # if a node was not in the free pool or the maintenance project.
            # we remove it from that project, which puts it in the maintenance pool.
            log_info('Node %s is not in the free pool' % node)

            status_ids = remove_all_networks(hil_client, node)
            for status_id in status_ids:
                assert_network_operation_success(hil_client, status_id)
            remove_node_from_project(hil_client, node, project)
        elif project is None:
            # if the node was in the free pool, then put it in the
            # maintenance project
            connect_node_to_project(hil_client, node, MAINTENANCE_PROJECT)

    for node in nodelist:
        # now that nodes are in maintenance project. connect the obm_network and
        # poweroff the nodes.
        status_id = connect_network(hil_client,
                                    node, OBM_NIC, OBM_NETWORK, 'vlan/native')
        assert_network_operation_success(hil_client, status_id)
        power_off_node(hil_client, node)

        status_id = remove_network(hil_client, node, OBM_NIC, OBM_NETWORK)
        assert_network_operation_success(hil_client, status_id)
        remove_node_from_project(hil_client, node, MAINTENANCE_PROJECT)

    # Finally, connect node to <to_project>
    for node in nodelist:
        connect_node_to_project(hil_client, node, to_project)


# BUNCH OF HELPER METHODS
# These methods make regular hil_client calls and check for errors.

def remove_all_networks(hil_client, node):
    '''
    Disconnect all networks from all of the node's NICs.

    Returns a list of network operation status ids.
    '''
    node_info = show_node(hil_client, node)

    # we could be operating on multiple nics, so we need to store all status_ids
    status_ids = []

    # get node information and then iterate on the nics
    for nic in node_info['nics']:
        # get the port and switch to which the nics are connected to
        port = nic['port']
        switch = nic['switch']
        if port and switch:
            try:
                response = hil_client.port.port_revert(switch, port)
                status_ids.append(response['status_id'])
                log_info('Removing all networks from node: `%s`' % node)
            except FailedAPICallException as e:
                log_error('Failed to revert port `%s` on node `%s` switch `%s`' % (
                    port, node, switch))
                raise HILClientFailure(e)
            except ConnectionError as e:
                log_error(
                    "remove_all_networks: Couldn't connect to HIL server.")
                raise HILClientFailure(e)
    return status_ids


def assert_network_operation_success(hil_client, status_id):
    """This asserts that a networking operation with an id <status_id>
    completes successfully in a reasonable time.
    """
    end_time = time.time() + HIL_TIMEOUT
    status = "PENDING"
    while status == "PENDING" and time.time() < end_time:
        response = hil_client.node.show_networking_action(status_id)
        status = response['status']
        if status == "DONE":
            return
        elif status == "PENDING":
            continue
        elif status == "ERROR":
            raise HILClientFailure(
                'HIL networking operation failed. %s is not connected.', network)
        else:
            raise HILClientFailure(
                "Unknown networking status returned by HIL server: %s", status)

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
    except FailedAPICallException as e:
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
        log_error('Unable to detach node `%s` from project `%s`' %
                  (node, project))
        raise HILClientFailure(e)
    except ConnectionError as e:
        log_error("remove_node_from_project: Couldn't connect to HIL server.")
        raise HILClientFailure(e)


def connect_node_to_project(hil_client, node, project):
    try:
        hil_client.project.connect(project, node)
        log_info('Node `%s` connected to project `%s`' % (node, project))
    except FailedAPICallException as e:
        log_error('Unable to connect node `%s` to project `%s`' %
                  (node, project))
        raise HILClientFailure(e)
    except ConnectionError as e:
        log_error("connect_node_to_project: Couldn't connect to HIL server.")
        raise HILClientFailure(e)


def connect_network(hil_client, node, nic, network, channel):
    """
    Connects a single network to specified nic on node.

    Returns a status_id to poll on
    """
    try:
        response = hil_client.node.connect_network(
            node, nic, network, 'vlan/native')
        status_id = response['status_id']
        log_info('Node `%s` succesfully connected to network `%s`' %
                 (node, network))
        return status_id
    except FailedAPICallException as e:
        log_error('Unable to connect `%s` to network `%s`' % (node, network))
        raise HILClientFailure(e)
    except ConnectionError as e:
        log_error("connect_network: Couldn't connect to HIL server.")
        raise HILClientFailure(e)


def remove_network(hil_client, node, nic, network):
    """
    Removes a single network from a nic on a node.

    Returns a status_id to poll on
    """
    try:
        response = hil_client.node.detach_network(
            node, nic, network)
        status_id = response['status_id']
        log_info('Node `%s` succesfully connected to network `%s`' %
                 (node, network))
        return status_id
    except FailedAPICallException as e:
        log_error('Unable to remove network `%s` from `%s`' % (node, network))
        raise HILClientFailure(e)
    except ConnectionError as e:
        log_error("remove_network: Couldn't connect to HIL server.")
        raise HILClientFailure(e)

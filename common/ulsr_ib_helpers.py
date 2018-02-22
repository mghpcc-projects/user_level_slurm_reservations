"""
MassOpenCloud / Hardware Isolation Layer (HIL)
User Level Slurm Reservations (ULSR)

Infiniband Link Management Support Routines

December 2017, Tim Donahue	tdonahue@mit.edu
"""
import errno
import glob
import logging
import stat
import sys

import ulsr_importpath

from ulsr_settings import (IB_UMAD_DEVICE_NAME_PREFIX,
                           IBLINKINFO_CMD, IBPORTSTATE_CMD, IBSTAT_CMD,
                           SS_LINKINFO_CMD, SS_PORTSTATE_CMD)
from ulsr_logging import log_info, log_warning, log_error, log_debug


def _check_ib_umad_access():
    '''
    Check if we have RW access to all local UMAD devices.
    If so, return True, else return False
    '''
    umad_name_match_pattern = IB_UMAD_NAME_PREFIX + '*'
    umad_list = glob.glob(umad_name_match_pattern)

    if (len(umad_list) == 0):
        log_error('No Infiniband UMAD devices matching `%s` found' % umad_name_match_pattern)
        return False

    for umad in umad_list:
        if not os.access(umad, (os.R_OK | os.W_OK)):
            log_debug('IB UMAD devices not directly accessible')
            return False

    return True


def check_ib_file_access(permit_cfgfile, ib_ctrl_program):
    '''
    Verify the IB switch & link permit file, the IB link control
    '''
    if not permit_file:
        log_error('Switch and link permit file not specified, exiting')
        return False, errno.EINVAL

    ow_mode = stat.S_IRWXG | stat.S_IRWXO

    this_filename = os.path.abspath(__file__)
    this_dirname = os.path.dirname(this_filename)

    file_paths = [this_dirname, this_filename, permit_file, ib_ctrl_program]

    for path in file_paths:
        try:
            st = os.stat(path)
            if (st.st_mode & ow_mode):
                log_error('Path `%s` permissions (%s) too open, exiting' %
                          (path, oct(st.st_mode)))
                return False, errno.EPERM
        except:
            log_error('File or directory `%s` not found, exiting' % path)
            return False, errno.ENOENT

    # Verify IB port control program exists
    try:
        st = os.stat(ib_ctrl_program)
    except:
        log_error('Infiniband port control program not found, exiting')
        return False, errno.ENOENT

    return True, 0


def parse_ib_permit_file(permit_cfgfile, debug=False):
    '''
    Read and parse the switch and port permit file.
    Return a dict of the form {guid: [port, port, ...], ...} and
    a 'permit any' indication
    '''
    permit_any = False
    permitted_link_dict = {}

    with open(permit_cfgfile) as fp:
        n = 1
        line = fp.readline()
        while line:
            line = line.strip()

            if line.startswith('#'):
                continue

            if ' any ' in line.lower():
                permit_any = True
                continue

            tokens = line.split()
            if (len(tokens) < 2):
                log_error('Permit config file `%s`: Malformed line %s' % (permit_cfgfile, n))
                continue

            guid = tokens[0]
            port = tokens[1]

            if not guid.startswith('0x') or (len(guid) != 18):
                log_error('Permit config file `%s`: Malformed line %s' % (permit_cfgfile, n))
                continue

            if guid in permitted_link_dict:
                permitted_link_dict[guid].append(port)
            else:
                permitted_link_dict[guid] = [port]

            line = fp.readline()
            n += 1

    return permit_any, permitted_link_dict


def _parse_iblinkinfo_line(node, line):
    '''
    Parse one 'iblinkinfo -l' HCA output line.
    If the link is LinkUp, return remote GUID and port number.
    If the link is not LinkUp, return None, None.

    Assumed iblinkinfo output line format:

    0xf452140300f55051 "              ib-test-7 mlx4_0"     37    1[  ] ==\
    ( 4X       14.0625 Gbps Active/  LinkUp)==>  \
    0xf45214030067c630      5   16[  ] "MF0;switch-e1be74:SX6036/U1" ( )

    Note that command 'iblinkinfo -l -D 1' run on a host with multiple IB links does
    not return information for all of the links.
    '''
    lhs, _, peer_guid_token = line.partition('==>')

    if 'LinkUp' not in lhs:
        log_error('Down IB link found on %s' % node)
        return None, None

    peer_guid = peer_guid_token.lstrip()[:18]
    port_number_token, _, _ = peer_guid_token.rpartition('[')
    port_number = port_number_token.split()[2].strip()

    return peer_guid, port_number


def _get_node_ib_ports_direct(nodelist, user, debug=False):
    '''
    Via SSH, issue a remote, UN-privileged IB management command to
    each node in the nodelist. Obtain the number of IB ports and
    the GUIDs of those ports.
    '''
    status = True
    node_ib_ports = {node: [] for node in nodelist}

    ibstat_cmd_template = generate_remote_cmd_template(IBSTAT_CMD)

    for node in nodelist:
        remote_cmd = ibstat_cmd_template.format(node)

        stdout_data = ''
        stderr_data = ''
        stdout_data, stderr_data = exec_subprocess_cmd(shlex.split(remote_cmd))
        if len(stderr_data):
            log_error('Unable to retrieve IB port info from `%s`, aborting' % (node))
            status = False
            break

        # Parse 'ibstat -p' command output and find the GUID of each port on
        # the current node, add to the list of ports for this node.
        for line in stdout_data.split('\n'):
            port_guid = line.strip()
            if port_guid:
                node_ib_ports[node].append(port_guid)

    if status:
        return node_ib_ports
    else:
        return {}


def _get_switch_ports_direct(nodelist, user, debug=False):
    '''
    Via SSH, issue remote IB management command to each node in the nodelist and
    obtain the GUIDs of the peer switches, and the port numbers of the peer switch
    ports.

    Return a dict containing the nodes, the switch GUIDs, and the port numbers:
    {node1: {switch1_guid: [ports], switch2_guid: [ports]}, node2: ...}

    RESTRICTIONS:
      1. Works for a single HCA per host
      2. Returns an empty set if a Down IB link is found on any remote host
      3. May only work on simple (e.g., single hub-and-spoke) IB network topologies
    '''
    status = True

    # Get the GUIDs for the IB ports on each node in the node list
    # The length of the port list is the number of ports, which
    # impacts the formatting of the iblinkinfo command

    node_ib_ports = _get_node_ib_ports_direct(nodelist, user, debug=False)
    if not node_ib_ports:
        return {}

    # {node: {switch1_guid: [port_number, ...], switch2_guid: [], ...}}
    switch_ports = {node: {} for node in nodelist}

    ib_cmd_template = generate_ssh_remote_cmd_template(IBLINKINFO_CMD)

    for node in nodelist:

        nports = len(node_ib_ports[node])

        # Iterate over this node's ports and retrieve peer switch ID and port number
        # for each
        for host_port in range(nports, 0, -1):
            remote_cmd = ib_cmd_template.format(node) + ' {}'.format(host_port)
            stdout_data = ''
            stderr_data = ''
            stdout_data, stderr_data = exec_subprocess_cmd(shlex.split(remote_cmd))
            if len(stderr_data):
                log_error('Failed to retrieve peer switch port info from `%s` port %s, aborting' %
                          (node, host_port))
                status = False
                break

            switch_guid, switch_port = _parse_iblinkinfo_line(node, stdout_data.split('\n')[0])
            if not switch_guid:
                status = False
                break

            if switch_guid in switch_ports[node]:
                switch_ports[node][switch_guid].append(switch_port)
            else:
                switch_ports[node] = {switch_guid: [switch_port]}

        if not status:
            switch_ports = {}
            break

    # {node: {switch1_guid: [port_number, ...], switch2_guid: [...], ...}, node2: {}}
    return switch_ports


def _control_switch_ports_direct(switch_ports, user, just_check=True,
                                 enable=False, disable=False, debug=False):
    '''
    Enable or disable, or just perform a 'dry run' (no change), of IB
    switch ports listed in the switch_ports dictionary.
    Use ibportstate(8) issued locally to perform the work.
    '''
    status = True

    if enable and disable:
        log_error('Invalid link control operation, either enable or disable, not both')
        return False

    verb = 'enable' if enable else ('disable' if disable else '')

    # switch_ports dict format:
    # {node: {switch1_guid: [port_number, ...], switch2_guid: [...], ...}, node2: {}}

    for node in switch_ports:
        for switch_guid in switch_ports[node]:

            # ibportstate -G <switch_guid> <switch_port> <verb>
            ib_cmd_template = IBPORTSTATE_CMD + '-G {}'.format(guid) + ' {}' + ' {}'.format(verb)

            for port in switch_ports[node][switch_guid]:
                remote_cmd = ib_cmd_template.format(port)
                stdout_data = ''
                stderr_data = ''
                if not just_check:
                    stdout_data, stderr_data = exec_subprocess_cmd(shlex.split(remote_cmd))
                    if len(stderr_data):
                        status = False
                        break
                else:
                    log_debug('IB link control cmd: `%s`' % remote_cmd)

    return status


def _get_switch_ports_via_ss(nodelist, user, debug=False):
    '''
    Via SSH, issue a remote privileged command to each node in the nodelist
    and obtain the GUID of the peer switch, and the port number of the peer
    switch port.

    Return a dict containing the nodes, the switch GUID, and the port number:
    {node1: {switch1_guid: [ports], switch2_guid: [ports]}, node2: ...}

    RESTRICTIONS:
      1. Works for a single interface, and single HCA per host
    '''
    status = True
    ss_cmd_template = generate_ssh_remote_cmd_template(SS_LINKINFO_CMD)

    switch_ports = {node: {} for node in nodelist}

    for node in nodelist:
        remote_cmd = ss_cmd_template.format(node)
        stdout_data = ''
        stderr_data = ''
        stdout_data, stderr_data = exec_subprocess_cmd(shlex.split(remote_cmd))
        if len(stderr_data):
            log_error('Failed to retrieve peer switch port info from `%s` port %s, aborting' %
                      (node, host_port))
            status = False
            break

        for line in stdout_data.split('\n'):
            line = line.strip()
            if line:
                switch_guid, switch_port = _parse_iblinkinfo_line(node, line)
                if not switch_guid:
                    status = False
                    break

            if switch_guid in switch_ports[node]:
                switch_ports[node][switch_guid].append(switch_port)
            else:
                switch_ports[node] = {switch_guid: [switch_port]}

        if not status:
            switch_ports = {}
            break

    # {node: {switch1_guid: [port_number, ...], switch2_guid: [...], ...}, node2: {}}
    return switch_ports


def _control_switch_ports_via_ss(switch_ports, user, just_check=True,
                                 enable=False, disable=False, debug=False):
    '''
    Enable or disable, or just perform a 'dry run' (no change) of IB switch
    ports listed in the switch_ports directory.
    Use the privileged (sudo) shell script to perform the work.
    '''
    if enable and disable:
        log_error('Invalid link control operation, either enable or disable, not both')
        return False

    verb = '' if just_check else ('enable' if enable else ('disable' if disable else ''))

    if just_check:
        log_info('Check mode, swich port state should not change')

    # switch_ports dict format:
    # {node: {switch1_guid: [port_number, ...], switch2_guid: [...], ...}, node2: {}}

    for node in switch_ports:
        for switch_guid in switch_ports[node]:
            for port in switch_ports[node][switch_guid]:
                cmd_input += '{} {} {}\n'.format(switch_guid, port, verb)

    cmd = SS_PORTSTATE_CMD

    log_info('IB link control command: \n  %s %s' % (cmd, cmd_input))

    stdout_data, stderr_data = exec_subprocess_cmd(shlex.split(remote_cmd), input=cmd_input)
    if len(stderr_data):
        log_error('Failed to update switch ports')
        return False

    return True


def update_ib_links(nodelist, user, priv_mode=False, just_check=True, 
                    enable=False, disable=False, debug=False):
    '''
    '''
    if priv_mode and _check_ib_umad_access():
        log_info('Privileged mode enabled and UMADs accessible, using direct controls')

        switch_ports = _get_switch_ports_direct(nodelist, user, debug=debug)
        status = _control_switch_ports_direct(switch_ports, user, just_check=just_check,
                                              enable=True, disable=False, debug=debug)
    else:
        log_debug('Using privileged shell scripts for link control')

        switch_ports = _get_switch_ports_via_ss(nodelist, user, debug=debug)
        status = control_switch_ports_via_ss(switch_ports, user, just_check=just_check,
                                             enable=True, disable=False, debug=debug)


# EOF

"""
MassOpenCloud / Hardware Isolation Layer (HIL)
User Level Slurm Reservations (ULSR)

Infiniband Link Management Support Routines

December 2017, Tim Donahue	tdonahue@mit.edu
"""

import errno
import glob
import logging
import os
import shlex
import stat
import sys

import ulsr_importpath

from ulsr_helpers import (generate_ssh_remote_cmd_template, exec_subprocess_cmd,
                          is_ib_available)
from ulsr_constants import IbAction
from ulsr_ib_db import read_ib_db, write_ib_db
from ulsr_settings import (IB_UMAD_DEVICE_NAME_PREFIX,
                           IBLINKINFO_CMD, IBPORTSTATE_CMD, IBSTAT_CMD,
                           SS_LINKINFO_CMD, SS_PORTSTATE_CMD)
from ulsr_logging import log_info, log_warning, log_error, log_debug


def _check_ib_umad_access():
    '''
    Check if we have RW access to all local UMAD devices.
    If so, return True, else return False
    '''
    umad_name_match_pattern = IB_UMAD_DEVICE_NAME_PREFIX + '*'
    umad_list = glob.glob(umad_name_match_pattern)

    if (len(umad_list) == 0):
        log_info('No Infiniband UMAD devices matching `%s` found' % umad_name_match_pattern)
        return False

    for umad in umad_list:
        if not os.access(umad, (os.R_OK | os.W_OK)):
            log_debug('IB UMAD devices not directly accessible')
            return False

    return True


def _check_ib_file_access(permit_cfgfile, ib_ctrl_program):
    '''
    Verify permissions on the the IB switch GUID & port permit file
    Verify the IB link control program exists
    '''
    if not permit_cfgfile:
        log_error('IB permit config file not specified, exiting')
        return False, errno.EINVAL

    this_filename = os.path.abspath(__file__)
    this_dirname = os.path.dirname(this_filename)
    permit_cfgfile_dir = os.path.dirname(os.path.abspath(permit_cfgfile))

    file_paths = [this_dirname, this_filename, permit_cfgfile, permit_cfgfile_dir,
                  ib_ctrl_program]

    for path in file_paths:
        try:
            st = os.stat(path)
            if (st.st_mode & stat.S_IWOTH):
                log_error('Path `%s` permissions (%s) too open' %
                          (path, oct(st.st_mode)))
                return False
        except:
            log_error('File or directory `%s` not found' % path)
            return False

    return True


def _parse_ib_permit_file(args):
    '''
    Read and parse the switch and port permit file.
    Return a dict of the form {guid: [port, port, ...], ...} and
    a 'permit any' indication
    '''
    permit_any = False
    permitted_port_dict = {}
    n = 0
    fname = args.ib_permitfile

    if args.debug:
        log_debug('Parsing IB permit config file `%s`' % fname)

    with open(fname) as fp:
        while True:
            n += 1
            line = fp.readline()
            if not line:
                break
            line = line.strip()
            if not len(line):
                continue

            if line.startswith('#'):
                continue

            if line.lower().startswith('any'):
                permit_any = True
                continue

            tokens = line.split()
            if (len(tokens) < 2):
                log_error('Permit config file `%s`: Malformed line %s' % (fname, n))
                continue

            guid = tokens[0]
            port = tokens[1]

            # Strip leading zeros from port number
            while (port[0] == '0'):
                port = port[1:]

            if not guid.startswith('0x') or (len(guid) != 18):
                log_error('Permit config file `%s`: Malformed line %s' % (fname, n))
                continue

            if guid in permitted_port_dict:
                permitted_port_dict[guid].append(port)
            else:
                permitted_port_dict[guid] = [port]

            n += 1

    return permit_any, permitted_port_dict


def _check_ib_ports_permitted(switch_ports, permitted_ports):
    '''
    Compare the switch GUIDs and port numbers found on the far
    end of each node's IB links against the list of GUIDs and port
    numbers we are permitted to operate on. If any impermissible links
    are found return false.

    switch_ports: {node: {switch_guid1: [port, ...], guid2: [port, ...]}}
    permitted_ports: {{switch_guid1: [port, ...], guid2: [port, ...]}
    '''
    for node, switch_ports in switch_ports.iteritems():
        for guid, port_list in switch_ports.iteritems():
            if guid not in permitted_ports:
                log_error('Switch GUID %s not among permitted switches' % guid)
                return False

            for port in port_list:
                if port not in permitted_ports[guid]:
                    log_error('Switch GUID %s port %s not among permitted ports' % (guid, port))
                    return False
    return True


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
#   print 'Line is %s' % line
    lhs, _, peer_guid_token = line.partition('==>')

    port_state = 'up' if 'LinkUp' in lhs else 'down'

    peer_guid = peer_guid_token.lstrip()[:18]
#   print 'Peer GUID token %s' % peer_guid_token
    port_number_token, _, _ = peer_guid_token.rpartition('[')
#   print 'Port number token %s' % port_number_token
    port_number = port_number_token.split()[2].strip()

    return peer_guid, port_number, port_state


def _add_port_to_switch_ports(node, line, switch_port_dict):
    '''
    Add switch GUID, port number, and port state to the
    switch port dictionary
    '''
    switch_guid, port_no, port_state = _parse_iblinkinfo_line(node, line)
    if not switch_guid:
        log_error('No switch GUID')
        return False

    if port_state is 'down':
        log_error('Down IB link found on node `%s`' % node)
        return False

    if switch_guid in switch_port_dict[node]:
        if port_no in switch_port_dict[node][switch_guid]:
            log_error('Duplicate port (%s) node `%s` switch %s' % (port_no, node, switch_guid))
            return False
        else:
            switch_port_dict[node][switch_guid][port_no] = port_state
    else:
        switch_port_dict[node][switch_guid] = {port_no: port_state}

    return True


def _log_ib_network_stats(switch_ports):
    '''
    '''
    nports = 0
    nnodes = len(switch_ports)
    nswitches = sum(len(node) for node in switch_ports.values())
    for node in switch_ports.values():
        nports += sum(len(switch) for switch in node.values())

    log_info('Collected IB link info (%s node%s, %s switch%s, %s port%s)' %
             (nnodes, 's'[nnodes==1:], nswitches, ['','es'][nswitches != 1],
              nports, 's'[nports==1:]))


def _retrieve_ib_port_state(resname, debug=False):
    '''
    Retrieve previously-stored IB port state information for the
    named reservation

    Should return a dict of the form
    {switch1_GUID: {port1_no: 'up' | 'down', ...}, switch2_GUID: {...}, ...}
    '''
    return read_ib_db(resname, debug=debug)


def _archive_ib_port_state(resname, switch_ports, debug=False):
    '''
    Store IB port state information for the named reservation
    in the database
    '''
    return write_ib_db(resname, switch_ports, debug=debug)


def _ss_perror_string(cmd, exit_code):
    '''
    Convert the nonzero exit code of ibendis.sh or bash to a string, 
    which may then be returned as stderr data
    '''
    IBENDIS_EXIT_CODE_MAP = {1: 'Invalid GUID format',
                             2: 'Invalid port number format',
                             3: 'Invalid port action',
                             4: 'Invalid input line',
                             5: 'Failed GUID / port combination check',
                             6: 'File checks failed'}

    BASH_EXIT_CODE_MAP = {126: 'bash: Command not executable',
                          127: 'bash: Command not found'}
    
    if exit_code in IBENDIS_EXIT_CODE_MAP:
        perror_string = '%s (%s)' % (IBENDIS_EXIT_CODE_MAP[exit_code], exit_code)
    elif exit_code in BASH_EXIT_CODE_MAP:
        perror_string = '%s (%s)' % (BASH_EXIT_CODE_MAP[exit_code], exit_code)
    else:
        perror_string = '%s Unknown error (%s)' % (cmd, exit_code)

    return perror_string


def _get_node_ib_ports_direct(nodelist, args):
    '''
    Via SSH, issue a remote, UN-privileged IB management command to
    each node in the nodelist. Obtain the number of IB ports and
    the GUIDs of those ports.
    '''
    status = True
    node_ib_ports = {node: [] for node in nodelist}

    ibstat_cmd_template = generate_ssh_remote_cmd_template(args.ssh_user, IBSTAT_CMD)

    for node in nodelist:
        remote_cmd = ibstat_cmd_template.format(node)
        stdout_data, stderr_data = '', ''
        stdout_data, stderr_data = exec_subprocess_cmd(shlex.split(remote_cmd), 
                                                       perror_fn=_ss_perror_string,
                                                       debug=args.debug)
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


def _get_switch_ports_direct(nodelist, args):
    '''
    Via SSH, issue remote IB management command to each node in the nodelist and
    obtain the GUIDs of the peer switches, and the port numbers of the peer switch
    ports.

    Return a dict containing the nodes, the switch GUIDs, the port numbers, and
    the port states:
    {node1: {switch1_guid: {port1: state, port2: state, ...},
             switch2_guid: {port1: state, ...}},
     node2: {switch1_guid: {port1: state, port2: state, ...},
             switch2_guid: {port1: state, ...}},
     ...}

    RESTRICTIONS:
      1. Works for a single HCA per host
      2. Returns an empty set if a Down IB link is found on any remote host
      3. May only work on simple (e.g., single hub-and-spoke) IB network topologies
    '''
    status = True

    # Get the GUIDs for the IB ports on each node in the node list
    # The length of the port list is the number of ports, which
    # impacts the formatting of the iblinkinfo command

    node_ib_ports = _get_node_ib_ports_direct(nodelist, args)
    if not node_ib_ports:
        return False, {}

    # So far as we know, iblinkinfo accepts a single (GUID, port) tuple
    # Loop over the set of GUIDs and ports and issue one command per (GUID, port)
    #
    # Output switch_ports dict format:
    # {node1: {switch1_guid: {port_number: 'up' | 'down', port_number: 'up' | 'down'],
    #          switch2_guid: {...}, ...},
    #  node2: {switch1_guid: {port_number: 'up' | 'down', port_number: 'up' | 'down'],
    #          switch2_guid: {...}, ...

    switch_ports = {node: {} for node in nodelist}

    ib_cmd_template = generate_ssh_remote_cmd_template(args.ssh_user, IBLINKINFO_CMD)

    for node in nodelist:

        nports = len(node_ib_ports[node])

        # Iterate over this node's ports and retrieve peer switch ID and port number
        # for each
        for host_port in range(nports, 0, -1):
            remote_cmd = ib_cmd_template.format(node) + ' {}'.format(host_port)
            stdout_data, stderr_data = '', ''
            stdout_data, stderr_data = exec_subprocess_cmd(shlex.split(remote_cmd), 
                                                           perror_fn=_ss_perror_string,
                                                           debug=args.debug)
            if len(stderr_data):
                log_error('Failed to retrieve peer IB switch port info from `%s` port %s, aborting' %
                          (node, host_port))
                status = False
                break

            status = _add_port_to_switch_ports(node, stdout_data.split('\n')[0], switch_ports)
            if not status:
                break

        if not status:
            switch_ports = {}
            break

    # {node1: {switch1_guid: {port1: <state>, ...}, switch2_guid: {port: <state>, ...}},
    #  node2: {switch1_guid: {port1: <state>, ...}, ...}}

    return status, switch_ports


def _control_switch_ports_direct(switch_ports, args, action=IbAction.IB_NONE):
    '''
    If action is IB_NONE, just perform a 'dry run' (no change), of IB
    switch ports listed in the switch_ports dictionary.
    
    Use ibportstate(8) issued locally to perform the work.
    '''
    status = True

    # switch_ports dict format:
    #
    # {node1: {switch1_guid: {port1: state, port2: state, ...}, 
    #          switch2_guid: {port1: state, port2: state, ...}},
    # {node2: {switch1_guid: {port1: state, port2: state, ...}, 
    #          switch2_guid: {port1: state, port2: state, ...}}, ...}

    for node in switch_ports:
        for switch_guid in switch_ports[node]:

            # ibportstate -G <switch_guid> <switch_port> <action>
            ib_cmd_template = IBPORTSTATE_CMD + ' -G {}'.format(switch_guid)
            ib_cmd_template += ' {}' + ' {}'.format(action)

            for port in switch_ports[node][switch_guid]:
                remote_cmd = ib_cmd_template.format(port)
                stdout_data, stderr_data = '', ''
                if not args.just_check:
                    stdout_data, stderr_data = exec_subprocess_cmd(shlex.split(remote_cmd),
                                                                   perror_fn=_ss_perror_string,
                                                                   debug=args.debug)
                    if len(stderr_data):
                        status = False
                        break
                else:
                    log_info('IB link control cmd: `%s`' % remote_cmd)

    return status


def _get_switch_ports_via_ss(nodelist, args):
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
    ss_cmd_template = generate_ssh_remote_cmd_template(args.ssh_user, SS_LINKINFO_CMD)

    switch_ports = {node: {} for node in nodelist}

    for node in nodelist:
        remote_cmd = ss_cmd_template.format(node)
        stdout_data, stderr_data = '', ''
        stdout_data, stderr_data = exec_subprocess_cmd(shlex.split(remote_cmd), 
                                                       perror_fn=_ss_perror_string,
                                                       debug=args.debug)

        if len(stderr_data):
            log_error('Failed to retrieve peer IB switch port info from `%s`, aborting' % node)
            log_error('  %s' % stderr_data)
            status = False
            break

        for line in stdout_data.split('\n'):
            line = line.strip()
            if not line:
                continue
#            else:
#                print 'Line %s' % line
            status = _add_port_to_switch_ports(node, line, switch_ports)
            if not status:
                break

        # All lines processed, check status, return empty dict if error

        if not status:
            switch_ports = {}
            break

    # {node: {switch1_guid: [port_number, ...], switch2_guid: [...], ...}, node2: {}}

    return status, switch_ports


def _control_switch_ports_via_ss(switch_ports, args, action=IbAction.IB_NONE):
    '''
    Enable or disable, or just perform a 'dry run' (no change) of IB switch
    ports listed in the switch_ports directory.
    Use the privileged (sudo) shell script to perform the work.
    '''
    # Construct the string of (GUID, port, action, \n) tuples passed to the shell script
    # via stdin
    #
    # switch_ports dict format:
    # {node: {switch1_guid: [port_number, ...], switch2_guid: [...], ...}, node2: {}}
    cmd_input = []
    for node in switch_ports:
        for switch_guid in switch_ports[node]:
            for port, state in switch_ports[node][switch_guid].iteritems():
                cmd_input.append('{} {} {}\n'.format(switch_guid, port, action))

    local_cmd = SS_PORTSTATE_CMD

    if args.debug:
        log_debug('IB link control command: `%s`' % shlex.split(local_cmd)[0])
        log_debug('Standard input:')
        for i in cmd_input:
            log_debug('    %s' % i.strip())

    stdout_data, stderr_data = exec_subprocess_cmd(local_cmd, input=cmd_input,
                                                   perror_fn=_ss_perror_string,
                                                   debug=args.debug)
    if len(stderr_data):
        # The port state control command returned an error, but may also
        # have written to stdout.
        log_error('Failed to update IB switch ports (%s)' % stderr_data)
        if args.debug:
            if stdout_data:
                for line in stdout_data.split('#'):
                    log_debug('  Stdout: %s' % line.strip(), separator=False)
        return False

    return True


def update_ib_links(resname, nodelist, args, action):
    '''
    Update any Infiniband links found to be LinkUp on the nodes in
    the reservation.

    Actions:
      IB_NONE: Survey links but take no action
      IB_DISABLE: Survey links and disable any which are LinkUp,
                  record prior state in DB
      IB_RESTORE: Retrieve state from DB, restore any links
                  which were previously LinkUp

      Reservation information remains in DB.
    '''
    status = True

    # Check if IB subsystem is present

    if not is_ib_available():
        log_info('Infiniband unavailable, all IB operations will appear to succeed')
        return status

    # Check if we have direct UMAD access and direct access is selected (-p)

    direct_ib_access = True if (args.priv_ib_access and _check_ib_umad_access()) else False

    # Select IB network survey and control functions

    if direct_ib_access:
        log_info('Privileged mode (`-p`), UMADs accessible, using direct IB access')
        _survey_fn = _get_switch_ports_direct
        _control_fn = _control_switch_ports_direct
    else:
        log_info('Using privileged shell scripts for IB access')
        _survey_fn = _get_switch_ports_via_ss
        _control_fn = _control_switch_ports_via_ss

    # Normally, we disable links when creating a reservation and
    # restore them during reservation deletion.
    #
    # After disabling links, save their initial state to a DB
    # Before restoring links, retrieve their prior state from the DB
    # Set control prolog / epilog functions appropriately
    #
    # Parse the IB permit file before links are disabled or restored

    _restore_prolog_fn, _disable_epilog_fn = None, None

    if (action == IbAction.IB_NONE):
        permit_any = False

    elif (action == IbAction.IB_DISABLE):
        permit_any, permitted_ports = _parse_ib_permit_file(args)
        _disable_epilog_fn = _archive_ib_port_state

    elif (action == IbAction.IB_RESTORE):
        permit_any, permitted_ports = _parse_ib_permit_file(args)
        _restore_prolog_fn = _retrieve_ib_port_state

    else:
        log_error('Invalid IB control operation selected')
        return False

    # For each node in the reservation, collect the peer switch GUID, port number,
    # and link state
    #
    # $$$ May want to do this only when IB_DISABLE
    #
    status, switch_ports = _survey_fn(nodelist, args)
    if not status:
        return status

    _log_ib_network_stats(switch_ports)

    # Check switch and port operations permissions.
    #
    # First check if ANY was found in the permit file.
    #
    # If ANY was not found, and direct IB access allowed, compare the switches
    # and ports found against the list we are permitted to work on
    #
    # If direct IB access not allowed, leave the permission check to the
    # privileged shell script

    if permit_any:
        log_info('Permit file (`%s`) contains `ANY`,' % args.ib_permitfile)
        log_info('  any switch port may be modified')

    elif direct_ib_access:
        if not _check_ib_ports_permitted(switch_ports, permitted_ports):
            return False
    else:
        pass

    # Call the link control prolog, if required, to:
    #   Retrieve IB port state information for this reservation

    if _restore_prolog_fn:
        prior_switch_ports_state = _restore_prolog_fn(resname, switch_ports)
        if not prior_switch_ports_state:
            return False
        else:
            switch_ports = prior_switch_ports_state

    if not _control_fn(switch_ports, args, action):
        return False

    # Call the epilog, if required, passing the surveyed network state

    if _disable_epilog_fn:
        status = _disable_epilog_fn(resname, switch_ports)

    return status

# EOF

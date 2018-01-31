"""
MassOpenCloud / Hardware Isolation Layer (HIL)
User Level Slurm Reservations (ULSR)

Infiniband Link Management 

December 2017, Tim Donahue	tdonahue@mit.edu
"""

import argparse
import errno
import hostlist
import logging
import shlex
import sys
import xml.etree.ElementTree as ET

import ulsr_importpath
from ulsr_helpers import (exec_subprocess_cmd, get_reservation_data, is_ulsr_reservation,
                          get_nodelist_from_resdata)
from ulsr_settings import ULSR_IB_MGMT_LOGFILE
from ulsr_logging import log_init, log_info, log_debug, log_error

IBLINKINFO_CMD = 'iblinkinfo.sh'
IBPORTSTATE_CMD = 'ibportstate.sh'
ULSR_IBLINK_CFGFILE = 'iblink_conf.xml'
DEBUG = True


def _validate_switch_id(guid):
    '''
    Perform appropriate switch ID validation here
    '''
    if guid is None:
        return False
    else:
        return True


def _validate_port_number(port_number):
    '''
    Validate the switch port number
    '''
    if port_number is None:
        return False
    else:
        return True


def _dump_parsed_config_file(filename, nodelist, switch_dict):
    '''
    Display the results of the config file parse
    '''
    print '\nConfig File: %s' % filename
    print '\nNodes'
    for nodename in nodelist:
        print '  %s' % nodename

    print '\nSwitches'
    for guid, port_list in switch_dict.iteritems():
        print '  %s' % guid
        for port in sorted(port_list):
            print '    Port %s' % port


def parse_iblink_cfgfile(cfgfile, debug=False):
    '''
    Parse the XML file containing the list of switches and port numbers 
    we are authorized to work on.

    Return a list of nodenames, switch GUIDs, and port numbers

    Note that while the association between node names and switches present
    in the XML is not currently maintained, it would be straightforward to 
    do so.
    '''
    tree = ET.parse(cfgfile)
    root = tree.getroot()

    nodelist = []
    switch_dict = {}

    for node in root.findall('node'):
        nodename = node.get('name')

        if nodename is None:
            log_error('Missing node name', separator=False)
            continue

        if nodename not in nodelist:
            # New node, add to list of nodes
            nodelist.append(nodename)
            if debug:
                print 'Node %s has been added' % nodename

        for switch in node.findall('switch'):
            guid = switch.get('guid')
            if not _validate_switch_id(guid):
                log_error('Node %s: Invalid switch ID (%s)' % (nodename, guid), 
                          separator=False)
                continue

            if guid not in switch_dict:
                # New switch, add an empty port list
                switch_dict[guid] = []
                if debug:
                    print 'Switch %s added' % guid

            for port in switch.findall('port'):
                port_number = port.get('number')
                if not _validate_port_number(port_number):
                    log_error('Node %s switch %s - Invalid port (%s)' % 
                              (nodename, guid, port_number), separator=False)
                    continue

                if port_number in switch_dict[guid]:
                    log_error('Node %s switch %s: Duplicate port (%s)' % 
                              (nodename, guid, port_number), separator=False)
                    continue
                else:
                    switch_dict[guid].append(port_number)
                    if debug:
                        print('  Port %s added' % port_number)
        
    if DEBUG:
        _dump_parsed_config_file(cfgfile, nodelist, switch_dict)

    return nodelist, switch_dict


def _control_iblinks(switch_dict, disable=False, enable=False, debug=False):
    '''
    Perform IB control operation on all the switch ports in the dictionary
    '''
    status = 0

    if enable and disable:
        log_error('Conflicting IB link controls, ignoring', separator=False)
        return False

    ibportstate_cmd_fmt = 'ibportstate -G {} {} {}'

    if enable:
        verb = 'enable'
    elif disable:
        verb = 'disable'

    # Loop through the switch GUIDs, then over the list of ports on each switch

    for guid, port_list in switch_dict.iteritems():

        for port in port_list:

            ibportstate_cmd = ibportstate_cmd_fmt.format(guid, port, verb)
            stdout_data, stderr_data = exec_subprocess_cmd(shlex.split(ibportstate_cmd))

            if (len(stderr_data) != 0):
                log_error('Failed to %s port %s on switch %s`' % (verb, port, guid))
                log_debug('  %s' % stderr_data)
                status = errno.EIO
            else:
                log_info('Switch %s  Port %s:  %sd' % (guid, port, verb))

    return status


def _parse_arguments():
    '''
    '''
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--debug', action='store_true', dest='debug',
                        help='Display debug information')
    parser.add_argument('-r', '--reservation', dest='resname', required=True,
                        metavar='RESERVATION', help='ULSR reservation name')
    parser.add_argument('-c', '--configfile', dest='cfgfile',
                        metavar='FILE', help='Config file name')
    return parser.parse_args()


def main(argv=[]):
    '''
    Arguments:
    -d / --debug:  Output debug info
    -h / --help:  Output help
    -r / --reservation <name>: ULSR reservation name
    '''
    log_init('ULSR_Infiniband_mgmt', ULSR_IB_MGMT_LOGFILE, logging.DEBUG)

    log_info('ULSR Infiniband Management', separator=True)
    log_info('Using config file `%s`' % ULSR_IBLINK_CFGFILE)
    log_debug('')

    args = _parse_arguments()

    # Parse the topology / allowed operations config file

    cfgfile = ULSR_IBLINK_CFGFILE
    permit_nodelist, switch_dict = parse_iblink_cfgfile(cfgfile)

    # Validate the passed reservation, get list of nodes in reservation

    if not is_ulsr_reservation(args.resname, None):
        log_error('Reservation `%s` not a ULSR reservation, exiting' % args.resname)
        sys.exit(errno.EINVAL)

    resdata_dict_list = get_reservation_data(args.resname)
    if not resdata_dict_list:
        log_error('Reservation data for `%s` not found, exiting' % args.resname)
        sys.exit(errno.ENXIO)

    reservation_nodelist = get_nodelist_from_resdata(resdata_dict_list[0])

    # Verify reservation nodes are in the IB link control permit list

    for node in reservation_nodelist:
        if node not in permit_nodelist:
            log_error('Reservation node `%s` not in configured permit list, exiting' % node)
            sys.exit(errno.EPERM)

    # Issue Infiniband management commands to control switch ports

    status = _control_iblinks(switch_dict, enable=True, debug=True)

    sys.exit(status)


if __name__ == '__main__':
    main(sys.argv[1:])
    exit(0)

# EOF

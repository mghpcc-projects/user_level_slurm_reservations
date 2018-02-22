"""
MassOpenCloud / Hardware Isolation Layer (HIL)
User Level Slurm Reservations (ULSR)

Infiniband Link Management

December 2017, Tim Donahue	tdonahue@mit.edu
"""

import argparse
import errno
import glob
import hostlist
import logging
import os
import shlex
import stat
import sys
import xml.etree.ElementTree as ET

import ulsr_importpath
from ulsr_helpers import (exec_subprocess_cmd, get_reservation_data, is_ulsr_reservation,
                          get_nodelist_from_resdata)
from ulsr_settings import (ULSR_IB_MGMT_LOGFILE, ULSR_IBLINK_CFGFILE, 
                           IBPORTSTATE_CMD, IBLINKINFO_CMD, IBSTATUS_CMD, IBSTAT_CMD,
                           CNH_SSS_LINKINFO_CMD, CNH_SSS_PORTSTATE_CMD,
                           SSH_OPTIONS, IB_DEVICE_NAME_PREFIX)
from ulsr_logging import log_init, log_info, log_warning, log_error, log_debug


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
    Perform appropriate port number validation here
    '''
    if port_number is None:
        return False
    else:
        return True


def _dump_parsed_config_file(cfgfile, node_dict, control_dict=None):
    '''
    Display the results of the config file parse
    '''
    print '\nConfig File: %s' % cfgfile
    print '\nNodes'
    for nodename in node_dict.keys():
        print '  %s' % nodename

    print '\nSwitches'
    for nodename, switch_dict in node_dict.iteritems():
        for guid, port_list in switch_dict.iteritems():
            print '  %s' % guid
            for port in sorted(port_list):
                print '    Port %s' % port


    if control_dict:
        pass


def _parse_iblink_cfgfile(cfgfile, debug=False):
    '''
    Parse the XML file containing the list of switches and port numbers
    we are authorized to work on.

    Return a list of nodenames, switch GUIDs, and port numbers

    {nodename: {switch_guid: [port_number, port_number]}, ...}

    Note that while the association between node names and switches present
    in the XML is not currently maintained, it would be straightforward to
    do so.
    '''
    tree = ET.parse(cfgfile)
    root = tree.getroot()

    node_dict = {}
    switch_dict = {}

    # Process control elements
    permit_any = False
    link_disable = False

    for ctrl in root.findall('control'):
        if 'permit' in ctrl.attrib:
            permit_any = True if (ctrl.get('permit') == 'Any') else False
        elif 'link_disable' in ctrl.attrib:
            link_disable = True if (ctrl.get('link_disable') == 'True') else False

    if permit_any:
        log_warning('Configuration allows access to any IB switch and link', separator=False)
    if link_disable:
        log_warning('Configuration allows disabling IB links', separator=False)

    # Process node elements

    for node in root.findall('node'):
        nodename = node.get('name')
        if nodename is None:
            log_error('IB config file: Missing node name', separator=False)
            continue

        # If the node is not in the set, add it, else print a diagnostic
        # Nodes may appear in the file twice
        if nodename not in node_dict:
            node_dict[nodename] = {}
        else:
            log_info('IB config file: Duplicate node entry for node `%s`, processing' %
                     nodename)

        for switch in node.findall('switch'):
            guid = switch.get('guid')
            if not _validate_switch_id(guid):
                log_error('IB config file: Node `%s` has invalid switch ID (%s)' %
                          (nodename, guid), separator=False)
                continue

            switch_dict = node_dict[nodename]
            if guid not in switch_dict:
                # New switch, add an empty port list
                switch_dict[guid] = []

            for port in switch.findall('port'):
                port_number = port.get('number')
                if not _validate_port_number(port_number):
                    log_error('IB config file: Node `%s` switch %s has invalid port (%s)' %
                              (nodename, guid, port_number), separator=False)
                    continue

                if port_number in switch_dict[guid]:
                    log_error('IB config file: Node `%s` switch %s has duplicate port (%s)' %
                              (nodename, guid, port_number), separator=False)
                    continue
                else:
                    switch_dict[guid].append(port_number)
    if debug:
        _dump_parsed_config_file(cfgfile, node_dict)

    return node_dict


def _parse_arguments():
    '''
    '''
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--check', action='store_true', dest='just_check',
                        help='Do not modify IB network', default=False)
    parser.add_argument('-d', '--debug', action='store_true', dest='debug',
                        help='Display debug information')
    parser.add_argument('-r', '--reservation', dest='resname', required=True,
                        metavar='RESERVATION', help='ULSR reservation name')
    parser.add_argument('-f', '--file', dest='cfgfile',
                        metavar='FILE', help='Config file name',
                        default=ULSR_IBLINK_CFGFILE)
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

    args = _parse_arguments()
    if args.just_check:
        log_info('Check mode (-c) specified, IB network will not be modified')

    log_info('Processing reservation `%s`' % args.resname)
    log_info('Using IB network config file `%s`' % args.cfgfile)
    log_debug('')

    # Verify restrictive permissions on this file, this dir, and config file
    # Verify IB port state command exists

    if _validate_files(args.cfgfile, IBPORTSTATE_CMD):
        sys.exit(errno.EPERM)

    # Parse the topology / allowed operations config file

    node_dict = _parse_iblink_cfgfile(args.cfgfile, args.debug)

    # Validate the passed reservation, get list of nodes in reservation

    if not is_ulsr_reservation(args.resname, None):
        log_error('Reservation `%s` not a ULSR reservation, exiting' % args.resname)
        sys.exit(errno.EINVAL)

    resdata_dict_list = get_reservation_data(args.resname)
    if not resdata_dict_list:
        log_error('Reservation data for `%s` not found, exiting' % args.resname)
        sys.exit(errno.ENXIO)

    reservation_nodelist = get_nodelist_from_resdata(resdata_dict_list[0])
#   print 'reservation nodelist is %s' % reservation_nodelist

    # Verify reservation nodes are in the IB link control permit list,
    # and build a dict which may be acted upon
    node_action_dict = {}
    permit_nodelist = node_dict.keys()
    for reserved_node in reservation_nodelist:
        if reserved_node in permit_nodelist:
            node_action_dict[reserved_node] = node_dict[reserved_node]
        else:
            log_error('Reservation node `%s` not in configured permit list, exiting' %
                      reserved_node)
            sys.exit(errno.EPERM)

    # Check if we have local Infiniband UMAD access
    ibdev_access = _check_ib_access()
                                          
    # Get switch IDs and port numbers for IB links connecting to servers
    user = 'cc'
    iblink_dict = _get_iblink_list(reservation_nodelist, user, ibdev_access)

    # Issue Infiniband management commands to control switch ports
#    status = _control_iblinks(node_action_dict, just_check=args.just_check,
#                              enable=True, debug=True)
    status = 0
    sys.exit(status)


if __name__ == '__main__':
    main(sys.argv[1:])
    exit(0)

# EOF

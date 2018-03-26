"""
MassOpenCloud / Hardware Isolation Layer (HIL)
User Level Slurm Reservations (ULSR)

Periodic Reservation Monitor

May 2017, Tim Donahue	tdonahue@mit.edu
"""

import argparse
import getpass
import logging
import sys
from time import time, gmtime, mktime, strptime, strftime

import ulsr_importpath

from ulsr_hil_client import hil_init, hil_reserve_nodes, hil_free_nodes
from ulsr_settings import (ULSR_MONITOR_LOGFILE, HIL_ENDPOINT, HIL_SLURM_PROJECT,
                           DEFAULT_IB_PERMIT_CFGFILE)
from ulsr_constants import (SHOW_OBJ_TIME_FMT, ULSR_RESERVE, ULSR_RELEASE,
                            RES_CREATE_FLAGS, RES_CREATE_HIL_FEATURES,
                            RES_CREATE_TIME_FMT, IbAction)
from ulsr_helpers import (exec_scontrol_show_cmd, parse_ulsr_reservation_name, 
                          create_slurm_reservation, delete_slurm_reservation,
                          get_ulsr_reservations, log_ulsr_reservation,
                          get_nodelist_from_resdata)
from ulsr_ib_helpers import update_ib_links
from ulsr_logging import log_init, log_info, log_debug, log_error


def _get_reserve_resname(release_resname, res_dict):
    '''
    '''
    return release_resname.replace(ULSR_RELEASE, ULSR_RESERVE, 1)


def _get_release_resname(reserve_resname, res_dict):
    '''
    Construct a release reservation name from the passed
    reserve reservation name.  Return release reservation name,
    reservation start time, and reservation end time

    To prevent the release reservation from timing out, set the 
    end_time_s to None, which should force 'Duration=Unlimited'
    '''
    release_resname = reserve_resname.replace(ULSR_RESERVE, ULSR_RELEASE, 1)

    t_start_s = strftime(RES_CREATE_TIME_FMT, gmtime(time()))
    t_end_s = None

    return release_resname, t_start_s, t_end_s


def _process_ulsr_reservations(hil_client, res_dict_list, restype, args):
    '''
    Process ULSR reserve or release reservations.
    Common processing:
        Determine IB port operation (none, disable, restore)
    Reserve reservations (restype == ULSR_RESERVE):
        Reserve nodes via HIL, disable IB links, create release reservation
    Release reservations (restype == ULSR_RELEASE):
        Free nodes via HIL, restore IB links, delete release reservation
    '''
    n = 0

    if (restype == ULSR_RESERVE):
        ib_action = IbAction.IB_DISABLE
        hil_fn, hil_op = hil_reserve_nodes, 'reserve'
    elif (restype == ULSR_RELEASE):
        ib_action = IbAction.IB_RESTORE
        hil_fn, hil_op = hil_free_nodes, 'free'
    else:
        log_error('Invalid reservation type (`%s`)' % restype)
        return

    # Process each reservation dict in the list of reservation dicts

    for res_dict in res_dict_list:
        resname = res_dict['ReservationName']
        nodelist = get_nodelist_from_resdata(res_dict)

        # Invoke HIL client to reserve or free nodes in HIL
        # If this fails, stop processing this reservation,
        #  and continue with the next reservation
        try:
            hil_fn(nodelist, HIL_SLURM_PROJECT, hil_client)
        except Exception as e:
            log_error('HIL %s operation failed for `%s`', (hil_op, resname))
            log_debug('  %s' % e)
            continue

        # Update IB links
        # Disable if reserve reservation, restore if release reservation

        ib_resname = (resname if (restype == ULSR_RESERVE) else 
                      _get_reserve_resname(resname, res_dict))

        if not update_ib_links(ib_resname, nodelist, args, ib_action):
            log_error('Infiniband update failed for `%s`' % resname)
            continue

        # If processing a reserve reservation, create the release reservation.
        
        if (restype == ULSR_RESERVE):
            release_resname, t_start_s, t_end_s = _get_release_resname(resname, res_dict)
            stdout_data, stderr_data = create_slurm_reservation(release_resname,
                                                                res_dict['Users'],
                                                                t_start_s, t_end_s,
                                                                nodes=res_dict['Nodes'],
                                                                flags=RES_CREATE_FLAGS,
                                                                features=RES_CREATE_HIL_FEATURES,
                                                                debug=args.debug)
            log_ulsr_reservation(release_resname, stderr_data, t_start_s, t_end_s)
            n += 1

        else: 	# restype == ULSR_RELEASE

            # If processing a release reservation, delete the release reservation.

            stdout_data, stderr_data = delete_slurm_reservation(resname, debug=args.debug)
            if (len(stderr_data) == 0):
                log_info('Deleted ULSR release reservation `%s`' % resname)
                n += 1
            else:
                log_error('Error deleting ULSR release reservation `%s`' % resname)
                log_error(stderr_data)

    # Return the number of reservations processed
    return n


def _find_ulsr_singleton_reservations(ulsr_reservations_dict, singleton_type):
    '''
    Find all reserve or release reservations which do not have a pair
    release or reserve reservation.  These singleton reservations exist
    during the ULSR reservation creation and release processes, respectively.
    '''
    singleton_reservation_dict_list = []

    # Select the pair type based on the reservation type of interest

    if (singleton_type == ULSR_RESERVE):
        pair_type = ULSR_RELEASE
    elif (singleton_type == ULSR_RELEASE):
        pair_type = ULSR_RESERVE
    else:
        log_error('Invalid reservation type (`%s`)' % pair_type)
        return singleton_reservation_dict_list

    # Look for reservations which have a pair member.
    # If any singleton reservations found, add them to the list

    for resname, resdata_dict in ulsr_reservations_dict.iteritems():
        _, restype, _, _, _ = parse_ulsr_reservation_name(resname)
        if (restype == singleton_type):
            # Check for matching reservation.
            # If found, continue. Else add the singleton to the list.
            if resname.replace(singleton_type, pair_type, 1) in ulsr_reservations_dict:
                continue
            else:
                singleton_reservation_dict_list.append(resdata_dict)

    return singleton_reservation_dict_list


def _parse_arguments():

    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--check', action='store_true', dest='just_check',
                        default=False, help='Do not modify IB network')
    parser.add_argument('-d', '--debug', action='store_true',
                         default=False, help='Display debug information')
    parser.add_argument('-f', '--file', dest='ib_permitfile', type=str,
                        default=DEFAULT_IB_PERMIT_CFGFILE, help='Permit file for IB operations')
    parser.add_argument('-p', '--priv_ib_access', action='store_true', default=False,
                        help='Privileged mode, uses direct IB network access if possible')
    parser.add_argument('-u', '--user',  type=str, dest='ssh_user', default= getpass.getuser(),
                        help='Username for local and SSH remote cmd execution')
    return parser.parse_args()


def main(argv=[]):

    log_init('ulsr_monitor', ULSR_MONITOR_LOGFILE, logging.DEBUG)

    args = _parse_arguments()

    log_info('ULSR Reservation Monitor', separator=True)
    log_debug('')

    # Look for ULSR reservations.  If none found, return

    ulsr_reservation_dict_list = get_ulsr_reservations(debug=args.debug)
    if not len(ulsr_reservation_dict_list):
        if args.debug:
            log_debug('No ULSR reservations found, nothing to do')
        return

    if args.ssh_user:
        log_info('Remote commands will be run as user `%s`' % args.ssh_user)
    if args.just_check:
        log_info('Check mode (`-c`) specified, IB network will not be modified')

    # Construct a dictionary of ULSR reservation data, keyed by reservation name.
    # Values are reservation data dictionaries

    all_ulsr_reservations_dict = {}

    for resdata_dict in ulsr_reservation_dict_list:
        resname = resdata_dict['ReservationName']
        all_ulsr_reservations_dict[resname] = resdata_dict

    # Find singleton RESERVE and RELEASE reservations
    # If none found, there's nothing to do
    reserve_res_dict_list = _find_ulsr_singleton_reservations(all_ulsr_reservations_dict, 
                                                              ULSR_RESERVE)
    release_res_dict_list = _find_ulsr_singleton_reservations(all_ulsr_reservations_dict, 
                                                              ULSR_RELEASE)
    if not len(reserve_res_dict_list) and not len(release_res_dict_list):
        if args.debug:
            log_debug('No singleton ULSR reserve or release reservations found')
        return

    # Attempt to connect to the HIL server.
    # On failure, exit, leaving singleton reservations in place

    hil_client = hil_init()
    if not hil_client:
        log_error('Unable to connect to HIL server `%s` to process HIL reservations' % HIL_ENDPOINT)
        return

    # Process reserve and release reservations

    n_released = _process_ulsr_reservations(hil_client, release_res_dict_list, ULSR_RELEASE, args)
    n_reserved = _process_ulsr_reservations(hil_client, reserve_res_dict_list, ULSR_RESERVE, args)
    if n_released:
        log_info('ULSR monitor: Processed %s release reservations' % n_released)
    if n_reserved:
        log_info('ULSR monitor: Processed %s reserve reservations' % n_reserved)
    return


if __name__ == '__main__':
    main(sys.argv[1:])
    exit(0)

# EOF

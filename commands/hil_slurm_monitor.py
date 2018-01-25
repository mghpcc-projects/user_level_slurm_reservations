"""
MassOpenCloud / Hardware Isolation Layer (HIL)
User Level Slurm Reservations (ULSR)

Periodic Reservation Monitor

May 2017, Tim Donahue	tdonahue@mit.edu
"""

import hostlist
import inspect
import logging
from os import listdir
from os.path import realpath, dirname, isfile, join
import sys
from time import time, gmtime, mktime, strptime, strftime

libdir = realpath(join(dirname(inspect.getfile(inspect.currentframe())), '../common'))
sys.path.append(libdir)

from hil_slurm_client import hil_init, hil_reserve_nodes, hil_free_nodes
from hil_slurm_settings import HIL_MONITOR_LOGFILE, HIL_ENDPOINT, HIL_SLURM_PROJECT
from hil_slurm_constants import (SHOW_OBJ_TIME_FMT, HIL_RESERVE, HIL_RELEASE,
                                 RES_CREATE_FLAGS, RES_CREATE_HIL_FEATURES,
                                 RES_CREATE_TIME_FMT)
from hil_slurm_helpers import (exec_scontrol_show_cmd, is_hil_reservation,
                               parse_hil_reservation_name,
                               create_slurm_reservation, delete_slurm_reservation,
                               get_hil_reservations, log_hil_reservation)
from hil_slurm_logging import log_init, log_info, log_debug, log_error


def _process_reserve_reservations(hil_client, reserve_res_dict_list):
    '''
    Move nodes reserved in HIL reserve reservation from the HIL Slurm (loaner) project
    to the HIL free pool.
    If successful, create the associated Slurm HIL reserve reservation
    '''
    n = 0
    for reserve_res_dict in reserve_res_dict_list:
        nodelist = hostlist.expand_hostlist(reserve_res_dict['Nodes'])
        resname = reserve_res_dict['ReservationName']

        try:
            hil_reserve_nodes(nodelist, HIL_SLURM_PROJECT, hil_client)
            release_resname = resname.replace(HIL_RESERVE, HIL_RELEASE, 1)

            t_start_s = strftime(RES_CREATE_TIME_FMT, gmtime(time()))
            t_end_s = reserve_res_dict['EndTime']
            if t_start_s >= t_end_s:
                t_end_s = strftime(RES_CREATE_TIME_FMT, 
                                   gmtime(time() + HIL_RESERVATION_DEFAULT_DURATION))

            # $$$ May want to check for pre-existing reservation with same name
            stdout_data, stderr_data = create_slurm_reservation(release_resname,
                                                                reserve_res_dict['Users'],
                                                                t_start_s, t_end_s,
                                                                nodes=reserve_res_dict['Nodes'],
                                                                flags=RES_CREATE_FLAGS,
                                                                features=RES_CREATE_HIL_FEATURES,
                                                                debug=False)
            log_hil_reservation(release_resname, stderr_data, t_start_s, t_end_s)
            n += 1
        except:
            log_error('Failed to reserve nodes in HIL reservation `%s`' % resname)

    return n


def _process_release_reservations(hil_client, release_res_dict_list):
    '''
    Move nodes reserved in HIL release reservations back to the HIL Slurm (loaner) project,
    then deleted the associated Slurm HIL release reservation
    '''
    n = 0

    for release_res_dict in release_res_dict_list:
        nodelist = hostlist.expand_hostlist(release_res_dict['Nodes'])

        # Attempt to move the node back to the Slurm loaner project
        # If successful, delete the Slurm (HIL release) reservation
        try:
            hil_free_nodes(nodelist, HIL_SLURM_PROJECT, hil_client)

            release_resname = release_res_dict['ReservationName']

            stdout_data, stderr_data = delete_slurm_reservation(release_resname, debug=False)
            if (len(stderr_data) == 0):
                log_info('Deleted HIL release reservation `%s`' % release_resname)
                n += 1
            else:
                log_error('Error deleting HIL release reservation `%s`' % release_resname)
                log_error(stderr_data)
        except:
            log_error('Exception deleting HIL release reservation `%s`' % release_resname)

    return n


def _find_hil_singleton_reservations(hil_reservations_dict, singleton_type):
    '''
    Find all reserve or release reservations which do not have a pair
    release or reserve reservation.  These singleton reservations exist
    during the HIL reservation creation and release processes, respectively.
    '''
    singleton_reservation_dict_list = []

    # Select the pair type based on the reservation type of interest

    if (singleton_type == HIL_RESERVE):
        pair_type = HIL_RELEASE
    elif (singleton_type == HIL_RELEASE):
        pair_type = HIL_RESERVE
    else:
        log_error('Invalid reservation type (`%s`)' % pair_type)
        return singleton_reservation_dict_list

    # Look for reservations which have a pair member.
    # If any singleton reservations found, add them to the list

    for resname, resdata_dict in hil_reservations_dict.iteritems():
        _, restype, _, _, _ = parse_hil_reservation_name(resname)
        if (restype == singleton_type):
            # Check for matching reservation.
            # If found, continue. Else add the singleton to the list.
            if resname.replace(singleton_type, pair_type, 1) in hil_reservations_dict:
                continue
            else:
                singleton_reservation_dict_list.append(resdata_dict)

    return singleton_reservation_dict_list


def main(argv=[]):
    '''
    '''
    log_init('hil_monitor', HIL_MONITOR_LOGFILE, logging.DEBUG)

    # Look for HIL ULSR reservations.
    # If none found, return
    hil_reservation_dict_list = get_hil_reservations()
    if not len(hil_reservation_dict_list):
        return

    log_info('HIL Reservation Monitor', separator=True)
    log_debug('')

    # Construct a dictionary of HIL reservation data, keyed by reservation name.
    # Values are reservation data dictionaries

    all_hil_reservations_dict = {}

    for resdata_dict in hil_reservation_dict_list:
        resname = resdata_dict['ReservationName']
        all_hil_reservations_dict[resname] = resdata_dict

    if not len(all_hil_reservations_dict):
        return

    # Find singleton RESERVE and RELEASE reservations
    # If none found, there's nothing to do

    reserve_res_dict_list = _find_hil_singleton_reservations(all_hil_reservations_dict, HIL_RESERVE)
    release_res_dict_list = _find_hil_singleton_reservations(all_hil_reservations_dict, HIL_RELEASE)
    if not len(reserve_res_dict_list) and not len(release_res_dict_list):
        return

    # Attempt to connect to the HIL server.
    # On failure, exit, leaving singleton reservations in place

    hil_client = hil_init()
    if not hil_client:
        log_error('Unable to connect to HIL server `%s` to process HIL reservations' % HIL_ENDPOINT)
        return

    n_released = _process_release_reservations(hil_client, release_res_dict_list)
    n_reserved = _process_reserve_reservations(hil_client, reserve_res_dict_list)

    if n_released:
        log_info('HIL monitor: Processed %s release reservations' % n_released)
    if n_reserved:
        log_info('HIL monitor: Processed %s reserve reservations' % n_reserved)
    return


if __name__ == '__main__':
    main(sys.argv[1:])
    exit(0)

# EOF

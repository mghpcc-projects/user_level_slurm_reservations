"""
MassOpenCloud / Hardware Isolation Layer (HIL)

Slurm / HIL Reservation Monitor

May 2017, Tim Donahue	tpd001@gmail.com
"""

import fileinput
import hostlist
import inspect
import logging
from os import listdir
from os.path import realpath, dirname, isfile, join
import sys
from time import time, mktime, strptime

libdir = realpath(join(dirname(inspect.getfile(inspect.currentframe())), '../common'))
sys.path.append(libdir)

from hil_slurm_client import hil_init, hil_free_nodes
from hil_slurm_settings import HIL_MONITOR_LOGFILE, HIL_ENDPOINT
from hil_slurm_constants import SHOW_OBJ_TIME_FMT, HIL_RESERVE, HIL_RELEASE
from hil_slurm_helpers import (exec_scontrol_show_cmd, is_hil_reservation, 
                               parse_hil_reservation_name, delete_slurm_reservation)
from hil_slurm_logging import log_init, log_info, log_debug, log_error


def _find_hil_release_reservations(resdata_dict_list):
    '''
    Traverse the passed list of HIL reservation data
    Find release reservations which do not have reserve reservations
    Returns a list of release reservations which should be deleted
    '''
    all_reservations = {}
    delete_reservation_dict_list = []

    for resdata_dict in resdata_dict_list:
        resname = resdata_dict['ReservationName']
        all_reservations[resname] = resdata_dict

    # Look for reserve reservations with matching release reservations
    # If any singleton release reservations found, add them to the list
    for resname, resdata_dict in all_reservations.iteritems():
        _, restype, _, _, _ = parse_hil_reservation_name(resname)
        if restype == HIL_RELEASE:
            # Check for matching reserve reservation
            if resname.replace(HIL_RELEASE, HIL_RESERVE, 1) not in all_reservations:
                delete_reservation_dict_list.append(resdata_dict)

    return delete_reservation_dict_list

    
def _get_hil_reservations():
    '''
    Return a dictionary of all HIL reservations extant in the system
    '''
    resdata_dict_list, stdout_data, stderr_data = exec_scontrol_show_cmd('reservation', None)
#    print 'All reservations'
#    print resdata_dict_list

    for resdata_dict in resdata_dict_list:
        if is_hil_reservation(resdata_dict['ReservationName'], None):
            continue
        else:
            resdata_dict_list.remove(resdata_dict)

    return resdata_dict_list


def _return_nodes_to_slurm(nodelist):
    '''
    Return the passed list of nodes from a HIL project to the 'Slurm' (loaner) project
    '''
    

def main(argv=[]):
    '''
    '''
    log_init('hil_monitor', HIL_MONITOR_LOGFILE, logging.DEBUG)

    # Look for HIL ULSR reservations.
    # If none found, return
    all_res_dict_list = _get_hil_reservations()
    if not len(all_res_dict_list):
        return

    log_info('HIL Reservation Monitor', separator=True)
    log_debug('')

    # Find HIL ULSR release reservations among all reservations.  
    # If none found, return
    release_res_dict_list = _find_hil_release_reservations(all_res_dict_list)
    if not len(release_res_dict_list):
        return

    # Process release reservations.
    # Establish communications with HIL server
    hil_client = hil_init()
    if not hil_client:
        log_error('Unable to connect to HIL server `%s` to return nodes' % HIL_ENDPOINT)
        return False

    # Move loaned nodes from HIL free pool back to Slurm project
    # If successful, delete the release reservation
    for release_res_dict in release_res_dict_list:
        nodelist = hostlist.expand_hostlist(release_res_dict['Nodes'])

        if hil_free_nodes(nodelist, hil_client):
            resname = release_res_dict['ReservationName']
            status = delete_slurm_reservation(resname, debug=False)
            if status:
               log_info('Deleted reservation `%s`' % resname)
            else:
                log_error('Failed to delete reservation `%s`' % resname)
         

if __name__ == '__main__':
    main(sys.argv[1:])
    exit(0)

# EOF

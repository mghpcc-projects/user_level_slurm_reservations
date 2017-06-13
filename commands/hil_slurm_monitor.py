"""
MassOpenCloud / Hardware Isolation Layer (HIL)

Slurm / HIL Reservation Monitor

May 2017, Tim Donahue	tpd001@gmail.com
"""

import logging
import fileinput
import sys

from hil_slurm_settings import HIL_RESERVATION_PREFIX, HIL_MONITOR_LOGFILE
from hil_slurm_helpers import exec_scontrol_show_cmd
from hil_slurm_logging import log_init, log_info, log_debug, log_error


def _get_hil_reservation_data():
    '''
    Return a dictionary of all HIL reservations extant in the system
    '''
    all_reservation_dict, stdout_data, stderr_data = exec_scontrol_show_cmd('reservation', None)

    # $$$ Works for one reservation.  When we have enough nodes to test more than one, we'll 
    # amend this
    hil_reservation_dict = {}

    resname=all_reservation_dict['ReservationName']

    if resname.startswith(HIL_RESERVATION_PREFIX):
        hil_reservations_dict[resname] = all_reservation_dict
            
    return hil_reservations_dict


def main(argv=[]):

    log_init('hil_monitor', HIL_MONITOR_LOGFILE, logging.DEBUG)

    # Look for reservations.  If there are none, return
    reservations_dict = _get_hil_reservation_data()
    if not reservations_dict:
        return

    log_info('HIL Reservation Monitor', separator=True)
    log_debug('')


if __name__ == '__main__':
    main(sys.argv[1:])
    exit(0)

# EOF

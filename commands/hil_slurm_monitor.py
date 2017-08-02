"""
MassOpenCloud / Hardware Isolation Layer (HIL)

Slurm / HIL Reservation Monitor

May 2017, Tim Donahue	tpd001@gmail.com
"""

import fileinput
# from hil import client
import inspect
import logging
from os import listdir
from os.path import realpath, dirname, isfile, join
from time import mktime, strptime

import sys

libdir = realpath(join(dirname(inspect.getfile(inspect.currentframe())), '../common'))
sys.path.append(libdir)


from hil_slurm_settings import HIL_RESERVATION_DELETE_PREFIX, HIL_MONITOR_LOGFILE
from hil_slurm_helpers import exec_scontrol_show_cmd
from hil_slurm_logging import log_init, log_info, log_debug, log_error


RESTORATION_TMPDIR = '/var/local/hil'

def _scrub_nodes():
    '''
    '''

def _restore_nodes():
    '''
    '''

def _check_reservation_status(rdict):
    '''
    Check the status of each of the passed reservations, to determine if any need service.
    '''
    for res, resdata in rdict:
        # Check if release reservation
        if not is_hil_release_reservation(resdata['ReservationName']):
            continue

def _add_nodes_to_hil(nodelist):
    '''
    '''
    subprocess.check_call()
    pass

def _add_reservation_to_hil():
    '''
    '''

def _remove_reservation_from_hil():
    '''
    '''


def _get_hil_reservations():
    '''
    Return a dictionary of all HIL reservations extant in the system
    '''
    reservation_dict_list, stdout_data, stderr_data = exec_scontrol_show_cmd('reservation', None)

    print reservation_dict_list
    hil_release_reservations_list = []

    for resdata_dict in reservation_dict_list:
        if not resdata_dict['ReservationName'].startswith(HIL_RESERVATION_DELETE_PREFIX):
            continue

        end_time_s = resdata_dict['EndTime']
        if end_time_s is 'None':
            continue

        if (mktime(strptime(end_time_s, SHOW_OBJ_TIME_FMT)) > time()):
            continue

        hil_release_reservations_list.append(resdata_dict)
            
    return hil_release_reservations_list


def _restore_one_node(nodename):
    '''
    Node has been released from HIL and may be restored.
    Invoke the restoration script and update the node restoration state file
    '''
    
    pass

def _restore_nodes(nodelist):
    '''
    '''
    for node in nodelist:
        log_info('Restoring %s', node)


def _verify_one_node_restored(nodename, tmpdir):
    '''
    '''
    # Node has been restored, remove the restoration file
    os.unlink(os.path.join(tmpdir, filename))
    pass

def _verify_nodes_restored():
    '''
    '''
    # Check what nodes have been restored
    rfiles = [f for f in listdir(tmpdir) if isfile(join(tmpdir, f))]
    if not rfiles:
        return

    for file in rfiles:
        pass

def _return_node_to_slurm():
    '''
    
    '''
    pass


def _loan_nodes_to_hil():
    '''
    Not strictly in this order
    - Invoke something to turn off Infiniband - Chris' script
    - Disconnect all networks - know what networks to detach from
        - Use revert_port()
        - Then project_detach_node()
        - Node is now in free pool
    -
    '''
    pass


def main(argv=[]):

    print 'Hello, world'
    log_init('hil_monitor', HIL_MONITOR_LOGFILE, logging.DEBUG)
    print 'Hello, world'

    # Look for reservations.  If there are none, return
    reservations_dict = _get_hil_reservations()
    if not reservations_dict:
        return

    log_info('HIL Reservation Monitor', separator=True)
    log_debug('')

    new_reservations = check_reservation_status(reservations_dict)
    

if __name__ == '__main__':
    main(sys.argv[1:])
    exit(0)

# EOF

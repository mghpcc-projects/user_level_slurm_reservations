"""
MassOpenCloud / Hardware Isolation Layer (HIL)

Slurm Control Daemon - HIL Reservation Prolog

May 2017, Tim Donahue	tpd001@gmail.com
"""

import logging
import os
import sys
from time import localtime, strftime

from hil_slurm_helpers import exec_scontrol_show_cmd, exec_scontrol_create_cmd
from hil_slurm_logging import log_init, log_info, log_warning, log_debug, log_error
from hil_slurm_settings import (HIL_CMD_NAMES, HIL_PARTITION_PREFIX,
                                HIL_RESERVATION_PREFIX,
                                RES_TIME_FMT, RES_FLAGS,
                                RES_CHECK_DEFAULT_PARTITION, RES_CHECK_EXCLUSIVE_PARTITION, 
                                RES_CHECK_SHARED_PARTITION, RES_CHECK_PARTITION_STATE,
                                HIL_SLURMCTLD_PROLOG_LOGFILE,
                                HIL_USER_LOGFILE)


def _get_prolog_environment():
    '''
    Returns a job's prolog environment in dictionary form
    '''
    env_map = {'jobname': 'SLURM_JOB_NAME',
               'partition': 'SLURM_JOB_PARTITION',
               'username': 'SLURM_JOB_USER',
               'job_uid': 'SLURM_JOB_UID',
               'job_account': 'SLURM_JOB_ACCOUNT',
               'nodelist': 'SLURM_JOB_NODELIST' }

    return {env_var: os.environ.get(slurm_env_var) 
           for env_var, slurm_env_var in env_map.iteritems()}


def _check_hil_command(env_dict):
    '''
    Get and validate the HIL command specified with srun / sbatch
    '''
    jobname= env_dict['jobname'] 
    if jobname not in HIL_CMD_NAMES:
        log_debug('Jobname `%s` is not a HIL reservation command, nothing to do.' % jobname)
        return None

    return jobname


def _check_hil_partition(env_dict, hil_command):
    '''
    Check if the partition exists and, if so, is properly named
    Retrieve partition data via 'scontrol show'
    '''
    pdata_dict = []

    pname = env_dict['partition']
    if not pname.startswith(HIL_PARTITION_PREFIX):
        log_info('Partition name `%s` does not match `%s*`' % (pname, HIL_PARTITION_PREFIX))
        return None

    pdata_dict, err_data = exec_scontrol_show_cmd('partition', pname)
    if err_data:
        log_error('Error: Failed to retrieve data for partition `%s`' % pname)
        log_error('  ', err_data)
        return None

    # Verify the partition state is UP

    if RES_CHECK_PARTITION_STATE:
        if (pdata_dict['State'] != 'UP'):
            log_info('Partition `%s` state (`%s`) is not UP' % (pname, pdata_dict['State']))
            return None

    # Verify the partition is not the default partition

    if RES_CHECK_DEFAULT_PARTITION:
        if (pdata_dict['Default'] == 'YES'):
            log_info('Partition `%s` is the default partition, cannot be used for HIL' % pname)
            return None

    # Verify the partition is not shared by checking 'Shared' and 'ExclusiveUser' attributes

    if RES_CHECK_SHARED_PARTITION:
        if (pdata_dict['Shared'] != 'NO'):
            log_info('Partition `%s` is shared, cannot be used for HIL' % pname)
            return None

    if RES_CHECK_EXCLUSIVE_PARTITION:
        if (pdata_dict['ExclusiveUser'] != 'YES'):
            log_info('Partition `%s` not exclusive to `%s`, cannot be used for HIL' % (pname, env_dict['username']))
            return None
        
    return pdata_dict


def _get_hil_reservation_times(resname, res_start_st, env_dict, pdata_dict):
    '''
    Calculate the start time and end time of the reservation, formatted for use by 'scontrol create'
    If the user specified a time, use that, plus a grace period
    If the partition MaxTime parameter is set, use that plus the HIL grace period.
    If the partition MaxTime is unlimited, use the HIL default
    '''
    ### NEITHER COMPLETE OR CORRECT
    start_time_s = strftime(RES_TIME_FMT, res_start_st)
    end_time_s = start_time_s

    # If the user specified a time limit, add that to the start time and use it

    # Otherwise, check if the partition max time is unlimited.  If so, allow the default.
    if (pdata_dict['MaxTime'] == 'UNLIMITED'):
        end_time_s += HIL_RESERVATION_DEFAULT_DURATION

    # Otherwise, use the the partition max time
    elif (pdata_dict['DefaultTime'] != 'NONE'):
        end_time_s += HIL_RESERVATION_GRACE_PERIOD
    else

    end_time_s = strftime(RES_TIME_FMT, res_end_st)

def _create_hil_reservation(resname, res_start_st, env_dict, pdata_dict):
    '''
    Create a HIL reservation using the passed reservation name
    '''
    log_info('Creating HIL reservation %s' % resname)
    resdata_dict, err_data = exec_scontrol_create_cmd('reservation', debug=True, 
                                                      ReservationName=resname,
                                                      starttime=res_start_st
                                                      endttime=0)


def _generate_hil_reservation_name(env_dict):
    ''' 
    Create a reservation name, combining the HIL reservation prefix,
    the username, the job ID, and the ToD (YMD_HMS)
    '''
    resname = HIL_RESERVATION_PREFIX + env_dict['username'] + '_'
    resname += env_dict['job_uid'] + '_'
    res_start_st = localtime()
    resname += strftime(RES_TIME_FMT, res_start_st)
    log_debug('Reservation name is %s' % resname)
    return resname, res_start_st


def _set_partition_state(pdata_dict):
    '''
    Update the state of the partition.
    Constrain final state and transition.
    '''
    pass


def _log_hil_reservation(resname, env_dict, message=None):
    '''
    Log the reservation to the user's reservation log file
    '''
    home = os.path.expanduser('~' + env_dict['username'])
    user_hil_logfile = os.path.join(home, HIL_USER_LOGFILE)
    f = open(user_hil_logfile, 'a')
    f.write('Created HIL reservation %s' % resname)
    f.close()


def _hil_reserve_cmd(env_dict, pdata_dict):
    '''
    Create a HIL reservation if it does not already exist.
    '''
    resname, res_start_st = _generate_hil_reservation_name(env_dict)
    resdata_dict, err_data = exec_scontrol_show_cmd('reservation', resname)

    if 'not found' not in err_data:
        log_info('Reservation `%s` already exists' % resname)
        return 

    # If the partition has an end time, use that, else use a fixed interval
    log_info('Reservation %s not found and may be created' % resname)

    _create_hil_reservation(resname, res_start_st, env_dict, pdata_dict)
    #_log_hil_reservation(resname, env_dict)
    

def _hil_release_cmd(env_dict, pdata_dict):
    # Release a HIL reservation
    resdata_dict, err_data = exec_scontrol_show_cmd('reservation', resname)

 
def main(argv=[]):

    log_init('hil_slurmctld.prolog', HIL_SLURMCTLD_PROLOG_LOGFILE, logging.DEBUG)
    log_info('HIL Slurmctld Prolog', separator=True)

    env_dict = _get_prolog_environment()
    hil_cmd = _check_hil_command(env_dict)
    if hil_cmd is None:
        exit(0)

    pdata_dict = _check_hil_partition(env_dict, hil_cmd)
    if not pdata_dict:
        exit(0)

    log_debug('Processing reservation request.')

    if (hil_cmd == 'hil_reserve'):
        _hil_reserve_cmd(env_dict, pdata_dict)
    elif (hil_cmd == 'hil_release'):
        _hil_release_cmd(env_dict, pdata_dict)


if __name__ == '__main__':
    main(sys.argv[1:])

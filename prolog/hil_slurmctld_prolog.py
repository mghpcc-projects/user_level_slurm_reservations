"""
MassOpenCloud / Hardware Isolation Layer (HIL)

Slurm Control Daemon - HIL Reservation Prolog

May 2017, Tim Donahue	tpd001@gmail.com
"""

import os
import sys
from time import gmtime, strftime

from hil_slurm_settings import (HIL_CMD_NAMES, HIL_PARTITION_PREFIX,
                                HIL_RESERVATION_PREFIX,
                                RES_TIME_FMT, RES_FLAGS, DEBUG)
from hil_slurm_helpers import exec_scontrol_cmd


def get_prolog_env():
    '''
    Returns a dict containing the job's prolog environment
    '''
    env_map = {'jobname': 'SLURM_JOB_NAME',
               'partition': 'SLURM_JOB_PARTITION',
               'username': 'SLURM_JOB_USER',
               'job_uid': 'SLURM_JOB_UID',
               'job_account': 'SLURM_JOB_ACCOUNT',
               'nodelist': 'SLURM_JOB_NODELIST' }

    return {env_var: os.environ.get(slurm_env_var) 
           for env_var, slurm_env_var in env_map.iteritems()}


def check_prolog_env(env):
    # If the partition is not an HIL partition, or if the 
    # command is not an HIL reservation command, do nothing
    pname = env['partition']
    if not pname.startswith(HIL_PARTITION_PREFIX):
        if DEBUG:
            print "Partition '%s' is not an HIL partition, continuing " % pname
        return None

    jobname= env['jobname'] 
    if jobname not in HIL_CMD_NAMES:
        if DEBUG:
            print "'%s' is not an HIL reservation command, continuing" % jobname
        return None

    return jobname


def get_partition_data(env):
    '''
    Check if the partition exists and, if so, retrieve data via 'scontrol show'
    '''
    pdata_dict = []
    pname = env['partition']
    pdata_dict, err_data = exec_scontrol_cmd('show', 'partition', pname)
    if err_data:
        print "Error: Failed to retrieve data for partition '%s'" % pname
        print "  ", err_data
        
    return pdata_dict


def get_job_data(env):
    '''
    Get job data, including the time limit
    '''
    

def _create_HIL_reservation(resname, env, pdata_dict):
    '''
    Create a HIL reservation using the passed reservation name
    '''
    resdata_dict, err_data = exec_scontrol_cmd('create', 'reservation', resname)


def _generate_HIL_reservation_name(env):
    ''' 
    Create a reservation name, combining the HIL reservation prefix,
    the username, the job ID, and the ToD (YMD_HMS)
    '''
    resname = HIL_RESERVATION_PREFIX + env['username'] + '_'
    resname += env['job_uid'] + '_'
    resname += strftime(RES_TIME_FMT)
    if DEBUG:
        print 'Reservation name is %s' % resname
    return resname


def _hil_reserve_cmd(env, pdata_dict):
    # Check if a reservation exists.  If not, create it
    resname = _generate_HIL_reservation_name(env)
    resdata_dict, err_data = exec_scontrol_cmd('show', 'reservation', resname)

    if 'not found' in err_data:
        _generate_hil_reservation(resname, env, pdata_dict)

    
def _hil_release_cmd(env, pdata_dict):
    # Release a HIL reservation
    resdata_dict, err_data = exec_scontrol_cmd('show', 'reservation', resname)

 
def main(argv=[]):

    env = get_prolog_env()
    hil_cmd = check_prolog_env(env)
    if hil_cmd is None:
        exit(0)

    pdata_dict = get_partition_data(env)
    if pdata_dict:
        print 'prolog: Entry checks done, processing...'

    if (hil_cmd == 'hil_reserve'):
        _hil_reserve_cmd(env, pdata_dict)
    elif (hil_cmd == 'hil_release'):
        _hil_release_cmd(env, pdata_dict)


if __name__ == '__main__':
    main(sys.argv[1:])

"""
MassOpenCloud / Hardware Isolation Layer (HIL)

Slurm Control Daemon - HIL Reservation Prolog

May 2017, Tim Donahue	tpd001@gmail.com
"""

import argparse
import hostlist
import inspect
import logging
import os
import sys
from datetime import datetime, timedelta
from time import strftime

libdir = os.path.realpath(os.path.join(os.path.dirname(inspect.getfile(inspect.currentframe())), '../common'))
sys.path.append(libdir)

from hil_slurm_client import hil_init, hil_reserve_nodes
from hil_slurm_helpers import (get_partition_data, get_job_data, get_object_data,
                               exec_scontrol_cmd, exec_scontrol_show_cmd,
                               get_hil_reservation_name, is_hil_reservation,
                               create_slurm_reservation, update_slurm_reservation,
                               delete_slurm_reservation)
from hil_slurm_constants import (SHOW_OBJ_TIME_FMT, RES_CREATE_TIME_FMT,
                                 SHOW_PARTITION_MAXTIME_HMS_FMT,
                                 RES_CREATE_HIL_FEATURES,
                                 HIL_RESERVE, HIL_RELEASE,
                                 HIL_RESERVATION_COMMANDS,
                                 RES_CREATE_FLAGS)
from hil_slurm_logging import log_init, log_info, log_debug, log_error
from hil_slurm_settings import (HIL_PARTITION_PREFIX,
                                RES_CHECK_DEFAULT_PARTITION,
                                RES_CHECK_EXCLUSIVE_PARTITION,
                                RES_CHECK_SHARED_PARTITION,
                                RES_CHECK_PARTITION_STATE,
                                HIL_RESERVATION_DEFAULT_DURATION,
                                HIL_RESERVATION_GRACE_PERIOD,
                                HIL_SLURMCTLD_PROLOG_LOGFILE,
                                HIL_ENDPOINT, 
                                HIL_SLURM_PROJECT)

from hil_slurm_client import hil_init


def _get_prolog_environment():
    '''
    Returns a job's prolog environment in dictionary form
    '''
    env_map = {'jobname': 'SLURM_JOB_NAME',
               'partition': 'SLURM_JOB_PARTITION',
               'username': 'SLURM_JOB_USER',
               'job_id': 'SLURM_JOB_ID',
               'job_uid': 'SLURM_JOB_UID',
               'job_account': 'SLURM_JOB_ACCOUNT',
               'nodelist': 'SLURM_JOB_NODELIST'
               }

    return {env_var: os.environ.get(slurm_env_var)
            for env_var, slurm_env_var in env_map.iteritems()}


def _check_hil_partition(env_dict, pdata_dict):
    '''
    Check if the partition exists and, if so, is properly named
    Retrieve partition data via 'scontrol show'
    '''
    status = True

    pname = pdata_dict['PartitionName']
    if not pname.startswith(HIL_PARTITION_PREFIX):
        log_info('Partition name `%s` does not match `%s*`' % (pname,
                                                               HIL_PARTITION_PREFIX))
        status = False

    # Verify the partition state is UP

    if RES_CHECK_PARTITION_STATE:
        if (pdata_dict['State'] != 'UP'):
            log_info('Partition `%s` state (`%s`) is not UP' % (pname, pdata_dict['State']))
            status = False

    # Verify the partition is not the default partition

    if RES_CHECK_DEFAULT_PARTITION:
        if (pdata_dict['Default'] == 'YES'):
            log_info('Partition `%s` is the default partition, cannot be used for HIL' % pname)
            status = False

    # Verify the partition is not shared by checking 'Shared' and 'ExclusiveUser' attributes

    if RES_CHECK_SHARED_PARTITION:
        if (pdata_dict['Shared'] != 'NO'):
            log_info('Partition `%s` is shared, cannot be used for HIL' % pname)
            status = False

    if RES_CHECK_EXCLUSIVE_PARTITION:
        if (pdata_dict['ExclusiveUser'] != 'YES'):
            log_info('Partition `%s` not exclusive to `%s`, cannot be used for HIL' % (pname, env_dict['username']))
            status = False

    return status


def _check_hil_command(env_dict):
    '''
    Get and validate the HIL command specified with srun / sbatch
    '''
    jobname = env_dict['jobname']
    if jobname in HIL_RESERVATION_COMMANDS:
        return jobname
    else:
        log_debug('Jobname `%s` is not a HIL reservation command, nothing to do.' % jobname)
        return None


def _get_hil_reservation_times(env_dict, pdata_dict, jobdata_dict):
    '''
    Calculate the start time and end time of the reservation
    Start time:
        If the user specified a start time for the job, use that
        Otherwise, use the current time
    End time:
        if the job has an end time, use that and extend it by the HIL grace period.
        If the job does not have an end time (e.g., TimeLimit UNLIMITED), set the
        reservation end time to either the partition MaxTime, if defined, or the HIL default
        maximum time.
    '''
    t_job_start_s = jobdata_dict['StartTime']
    t_job_end_s = jobdata_dict['EndTime']
#   log_debug('Job start %s  Job end %s' % (t_job_start_s, t_job_end_s))

    t_start_dt = datetime.strptime(t_job_start_s, SHOW_OBJ_TIME_FMT)

    if 'Unknown' not in t_job_end_s:
        log_debug('Using job end time for reservation')
        # Job has a defined end time.  Use it.
        t_end_dt = datetime.strptime(t_job_end_s, SHOW_OBJ_TIME_FMT)
        t_end_dt += timedelta(seconds=HIL_RESERVATION_GRACE_PERIOD)

    else:
        # Job does not have a defined end time.  See if there's a time limit.

        if 'UNLIMITED' in jobdata_dict['TimeLimit']:

            # Job does not have a time limit. See if the partition has a max time.
            # If so, use that. If not, use the HIL default duration.

            p_max_time_s = pdata_dict['MaxTime']
            log_debug('Partition MaxTime is %s' % p_max_time_s)
            if 'UNLIMITED' in p_max_time_s:

                # Partition does not have a max time, use HIL default.
                log_debug('No job or partition time limit, using HIL default reservation duration')
                t_end_dt = t_start_dt + timedelta(seconds=HIL_RESERVATION_DEFAULT_DURATION)

            else:

                # Partition has a max time, parse it. Output format is [days-]H:M:S.
                log_debug('Using partition time limit to calculate reservation end time')
                d_hms = p_max_time_s.split('-')
                if (len(d_hms) == 1):
                    p_max_hms_dt = datetime.strptime(d_hms[0], SHOW_PARTITION_MAXTIME_HMS_FMT)
                    p_max_timedelta = timedelta(hours=p_max_hms_dt.hour,
                                                minutes=p_max_hms_dt.minute,
                                                seconds=p_max_hms_dt.second)
                elif (len(d_hms) == 2):
                    # Days field is present
                    p_max_days_timedelta = datetime.timedelta(days=int(d_hms[0]))

                    p_max_hms_dt = datetime.strptime(d_hms[1], SHOW_PARTITION_MAXTIME_HMS_FMT)
                    p_max_hms_timedelta = timedelta(hours=p_max_hms_dt.hour,
                                                    minutes=p_max_hms_dt.minute,
                                                    seconds=p_max_hms_dt.second)
                    p_max_timedelta = p_max_days_timedelta + p_max_hms_timedelta
                    log_debug(p_max_timedelta)
                    t_end_dt = t_start_dt + p_max_timedelta
                else:
                    log_error('Cannot parse partition MaxTime (`%s`)' % p_max_time_s)
        else:
            # Job has a time limit. Use it.
            # $$$ FIX
            log_debug('Job has a time limit! Unsupported!')
            pass

    # We now have a defined reservation t_start and t_end in datetime format.
    # Convert to strings and return.
    t_start_s = t_start_dt.strftime(RES_CREATE_TIME_FMT)
    t_end_s = t_end_dt.strftime(RES_CREATE_TIME_FMT)

    # log_debug('Start time %s' % t_start_s)
    # log_debug('End time %s' % t_end_s)

    return t_start_s, t_end_s


def _create_hil_reservation(restype_s, t_start_s, t_end_s, env_dict, pdata_dict, jobdata_dict):
    '''
    Create a HIL reservation
    '''
    # Generate a HIL reservation name
    resname = get_hil_reservation_name(env_dict, restype_s, t_start_s)

    # Check if reservation exists.  If so, do nothing
    resdata_dict_list, stdout_data, stderr_data = exec_scontrol_show_cmd('reservation', resname)
    if (stderr_data) and ('not found' not in stderr_data):
        log_info('HIL reservation `%s` already exists' % resname)
        return resname, stderr_data

    log_info('Creating HIL reservation `%s`, ending %s' % (resname, t_end_s))

    stdout_data, stderr_data = create_slurm_reservation(resname, env_dict['username'],
                                                        t_start_s, t_end_s,
                                                        nodes=None, flags=RES_CREATE_FLAGS,
                                                        features=RES_CREATE_HIL_FEATURES,
                                                        debug=False)
    return resname, stderr_data


def _update_hil_reservation(env_dict, pdata_dict, jobdata_dict, resname, **kwargs):
    '''
    Update (modify) a HIL reservation.
    One use is to change the start time of the release reservation to
    the current time, after the reserve reservation has been deleted
    '''
    return update_slurm_reservation(resname, debug=False, **kwargs)


def _delete_hil_reservation(env_dict, pdata_dict, jobdata_dict, resname):
    '''
    Delete a HIL reservation after validating HIL name prefix and owner name
    The latter restricts 'hil_release' of a reservation to the owner
    It is always possible to delete the reservation with 'scontrol delete'.
    '''
    # Minimally validate the specified reservation

    if is_hil_reservation(resname, None):
        log_info('Deleting HIL reservation `%s`' % resname)
        return delete_slurm_reservation(resname, debug=False)
    else:
        log_info('Cannot delete HIL reservation, error in name (`%s`)' % resname)
        return None, 'hil_release: error: Invalid reservation name'


def _log_hil_reservation(resname, stderr_data, t_start_s=None, t_end_s=None):
    if len(stderr_data):
        log_error('Error creating reservation `%s`'% resname)
        log_error(stderr_data)
    else:
        log_info('Created  HIL reservation `%s`' % resname)


def _hil_reserve_cmd(env_dict, pdata_dict, jobdata_dict):
    '''
    Runs in Slurm control daemon prolog context

    Create HIL reserve and release reservations if they do not already exist.

    HIL reserve reservation must be created first to avoid a race condition 
    with the periodic reservation monitor

    Reservation start and end times may overlap so long as the MAINT flag is set
    '''
    t_start_s, t_end_s = _get_hil_reservation_times(env_dict, pdata_dict, jobdata_dict)
    
    # Loop and create both the reserve and the release reservations
    
    for restype_s in [HIL_RESERVE, HIL_RELEASE]:
        resname, stderr_data = _create_hil_reservation(restype_s, t_start_s, t_end_s,
                                                       env_dict, pdata_dict, jobdata_dict)
        _log_hil_reservation(resname, stderr_data, t_start_s, t_end_s)


    # Connect to HIL server 
    hil_client = hil_init()
    if not hil_client:
        log_error('Unable to connect to HIL server `%s` to reserve nodes', HIL_ENDPOINT)
    else:
        log_debug('Connected to HIL server `%s` to reserve nodes', HIL_ENDPOINT)


    # Move nodes from Slurm project to HIL
    nodelist = hostlist.expand_hostlist(env_dict['nodelist'])
    if not hil_reserve_nodes(nodelist, HIL_SLURM_PROJECT, hil_client):
        log_error('HIL reservation failure: Unable to reserve nodes `%s`' % nodelist)


def _hil_release_cmd(env_dict, pdata_dict, jobdata_dict):
    '''
    Runs in Slurm control daemon epilog context

    Delete the reserve reservation in which the release job was run.
    - Verify the reservation is a HIL reserve reservation
    - Verify the reservation is owned by the user
    - Get reserve reservation data via 'scontrol'
    - Delete the reserve reservation in which the hil_release command was run

    Release reservation will be deleted later by the HIL reservation monitor
    '''
    reserve_resname = jobdata_dict['Reservation']

    if reserve_resname:
        if not is_hil_reservation(reserve_resname, HIL_RESERVE):
            log_error('Reservation `%s` is not a HIL reserve reservation' % reserve_resname)

        elif env_dict['username'] not in reserve_resname:
            log_error('Reservation `%s` not owned by user `%s`' % (reserve_resname,
                                                                   env_dict['username']))
        else:
            # Basic validation done
            # Get reserve reservation data
            reserve_rdata = get_object_data('reservation', reserve_resname)[0]

            # Delete the reserve reservation
            stdout_data, stderr_data = _delete_hil_reservation(env_dict, pdata_dict,
                                                               jobdata_dict, reserve_resname)
            if (len(stderr_data) == 0):
                log_info('Deleted  HIL reserve reservation `%s`' % reserve_resname)
            else:
                log_error('Error deleting HIL reserve reservation `%s`' % reserve_resname)
                log_error(stderr_data)

    else:
        log_error('No reservation name specified to `%s` command' % jobdata_dict['JobName'])


def process_args():

    parser = argparse.ArgumentParser()

    parser.add_argument('--hil_prolog', action='store_true', default=False,
                        help='Function as the HIL prolog')
    parser.add_argument('--hil_epilog', action='store_true', default=False,
                        help='Function as the HIL epilog')

    return parser.parse_args()


def main(argv=[]):

    args = process_args()
    log_init('hil_slurmctld.prolog', HIL_SLURMCTLD_PROLOG_LOGFILE, logging.DEBUG)

    if args.hil_prolog:
        pass
    elif args.hil_epilog:
        pass
    else:
        log_debug('Must specify one of --hil_prolog or --hil_epilog', separator=True)
        return

    # Collect prolog/epilog environment, job data, and partition data into dictionaries,
    # perform basic sanity checks
    # Since data for one partition and one job is expected, select the first dict in the list

    env_dict = _get_prolog_environment()
    if not env_dict['partition']:
        log_debug('Missing Slurm control daemon prolog / epilog environment.')
        return

    pdata_dict = get_partition_data(env_dict['partition'])[0]
    jobdata_dict = get_job_data(env_dict['job_id'])[0]

    if not pdata_dict or not jobdata_dict:
        log_debug('One of pdata_dict, jobdata_dict, or env_dict is empty')
        log_debug('Job data', jobdata_dict)
        log_debug('P   data', pdata_dict)
        return

    if not _check_hil_partition(env_dict, pdata_dict):
        return

    # Verify the command is a HIL command.  If so, process it.

    hil_cmd = _check_hil_command(env_dict)
    if not hil_cmd:
        return

    if args.hil_prolog:
        if (hil_cmd == 'hil_reserve'):
            log_info('HIL Slurmctld Prolog', separator=True)
            log_debug('Processing reserve request')
            _hil_reserve_cmd(env_dict, pdata_dict, jobdata_dict)

    elif args.hil_epilog:
        if (hil_cmd == 'hil_release'):
            log_info('HIL Slurmctld Epilog', separator=True)
            log_debug('Processing release request')
            _hil_release_cmd(env_dict, pdata_dict, jobdata_dict)
    return


if __name__ == '__main__':
    main(sys.argv[1:])
    exit(0)

# EOF

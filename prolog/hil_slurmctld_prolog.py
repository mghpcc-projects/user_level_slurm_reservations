"""
MassOpenCloud / Hardware Isolation Layer (HIL)

Slurm Control Daemon - HIL Reservation Prolog

May 2017, Tim Donahue	tpd001@gmail.com
"""

import logging
import os
import sys
from datetime import datetime, timedelta

from hil_slurm_helpers import (get_partition_data, get_job_data,
                               exec_scontrol_show_cmd,
                               create_slurm_reservation)
from hil_slurm_constants import (SHOW_OBJ_TIME_FMT, RES_CREATE_TIME_FMT,
                                 SHOW_PARTITION_MAXTIME_HMS_FMT,
                                 RES_CREATE_FLAGS)
from hil_slurm_logging import log_init, log_info, log_debug, log_error
from hil_slurm_settings import (HIL_CMD_NAMES, HIL_PARTITION_PREFIX,
                                HIL_RESERVATION_PREFIX,
                                RES_CHECK_DEFAULT_PARTITION,
                                RES_CHECK_EXCLUSIVE_PARTITION,
                                RES_CHECK_SHARED_PARTITION,
                                RES_CHECK_PARTITION_STATE,
                                HIL_RESERVATION_DEFAULT_DURATION,
                                HIL_RESERVATION_GRACE_PERIOD,
                                HIL_SLURMCTLD_PROLOG_LOGFILE, HIL_USER_LOGFILE)


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
    if jobname not in HIL_CMD_NAMES:
        log_debug('Jobname `%s` is not a HIL reservation command, nothing to do.' % jobname)
        return None

    return jobname


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
    log_debug('Job start %s  Job end %s' % (t_job_start_s, t_job_end_s))

    t_start_dt = datetime.strptime(t_job_start_s, SHOW_OBJ_TIME_FMT)

    if 'Unknown' not in t_job_end_s:
        # Job has a defined end time.  Use it.

        t_end_dt = datetime.strptime(t_job_end_s, SHOW_OBJ_TIME_FMT)
        t_end_dt += timedelta(seconds=HIL_RESERVATION_GRACE_PERIOD)

    else:
        # Job does not have a defined end time.  See if there's a time limit.

        if 'UNLIMITED' in jobdata_dict['TimeLimit']:

            # Job does not have a time limit. See if the partition has a max time.
            # If so, use that. If not, use the HIL default duration.

            p_max_time_s = pdata_dict['MaxTime']
            if 'UNLIMITED' in p_max_time_s:

                # Partition does not have a max time, use HIL default.
                t_end_dt = t_start_dt + timedelta(seconds=HIL_RESERVATION_DEFAULT_DURATION)

            else:

                # Partition has a max time, parse it. Output format is [days-]H:M:S.
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
            pass

        # We now have a defined reservation t_start and t_end in datetime format.
        # Convert to strings and return.
        t_start_s = t_start_dt.strftime(RES_CREATE_TIME_FMT)
        t_end_s = t_end_dt.strftime(RES_CREATE_TIME_FMT)

        return t_start_s, t_end_s


def _create_hil_reservation(env_dict, pdata_dict, jobdata_dict):
    '''
    Create a HIL reservation
    '''
    # Generate HIL reservation start and end times
    t_start_s, t_end_s = _get_hil_reservation_times(env_dict, pdata_dict, jobdata_dict)

    # Generate a HIL reservation name
    resname = _get_hil_reservation_name(env_dict, t_start_s)

    # Check if reservation exists.  If so, do nothing
    resdata_dict, stdout_data, stderr_data = exec_scontrol_show_cmd('reservation', resname)
    if (stderr_data) and ('not found' not in stderr_data):
        log_info('HIL reservation `%s` already exists' % resname)
        return resname, stderr_data

    log_info('Creating HIL reservation `%s`, ending %s' % (resname, t_end_s))

    stdout_data, stderr_data = create_slurm_reservation(resname, env_dict['username'],
                                                        t_start_s, t_end_s,
                                                        nodes=None, flags=RES_CREATE_FLAGS,
                                                        debug=False)
    return resname, stderr_data


def _get_hil_reservation_name(env_dict, t_start_s):
    '''
    Create a reservation name, combining the HIL reservation prefix,
    the username, the job ID, and the ToD (YMD_HMS)
    '''
    resname = HIL_RESERVATION_PREFIX + env_dict['username'] + '_'
    resname += env_dict['job_uid'] + '_' + t_start_s
    log_debug('Reservation name is %s' % resname)
    return resname


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


def _hil_reserve_cmd(env_dict, pdata_dict, jobdata_dict):
    '''
    Create a HIL reservation if it does not already exist.
    '''
    resname, stderr_data = _create_hil_reservation(env_dict, pdata_dict, jobdata_dict)
    # _log_hil_reservation(resname, env_dict)


def _hil_release_cmd(env_dict, pdata_dict, jobdata_dict):
    # Release a HIL reservation
    resdata_dict, stdout_data, stderr_data = exec_scontrol_show_cmd('reservation', resname)


def main(argv=[]):

    log_init('hil_slurmctld.prolog', HIL_SLURMCTLD_PROLOG_LOGFILE, logging.DEBUG)
    log_info('HIL Slurmctld Prolog', separator=True)

    # Collect prolog environment, job data, and partition data into dictionaries,
    # perform basic sanity checks

    env_dict = _get_prolog_environment()
    pdata_dict = get_partition_data(env_dict['partition'])
    jobdata_dict = get_job_data(env_dict['job_id'])

    if not pdata_dict or not jobdata_dict or not env_dict:
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

    log_debug('Processing reservation request.')

    if (hil_cmd == 'hil_reserve'):
        _hil_reserve_cmd(env_dict, pdata_dict, jobdata_dict)
    elif (hil_cmd == 'hil_release'):
        _hil_release_cmd(env_dict, pdata_dict, jobdata_dict)


if __name__ == '__main__':
    main(sys.argv[1:])
    exit(0)

# EOF

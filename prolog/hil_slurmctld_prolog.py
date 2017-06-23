"""
MassOpenCloud / Hardware Isolation Layer (HIL)

Slurm Control Daemon - HIL Reservation Prolog

May 2017, Tim Donahue	tpd001@gmail.com
"""

import argparse
import hostlist
import logging
import os
import sys
from datetime import datetime, timedelta

from hil_slurm_helpers import (get_partition_data, get_job_data,
                               exec_scontrol_cmd, exec_scontrol_show_cmd,
                               create_slurm_reservation,
                               delete_slurm_reservation)
from hil_slurm_constants import (SHOW_OBJ_TIME_FMT, RES_CREATE_TIME_FMT,
                                 SHOW_PARTITION_MAXTIME_HMS_FMT,
                                 RES_CREATE_FLAGS, RES_RELEASE_FLAGS)
from hil_slurm_logging import log_init, log_info, log_debug, log_error
from hil_slurm_settings import (HIL_CMD_NAMES, HIL_PARTITION_PREFIX,
                                HIL_RESERVATION_PREFIX,
                                RES_CHECK_DEFAULT_PARTITION,
                                RES_CHECK_EXCLUSIVE_PARTITION,
                                RES_CHECK_SHARED_PARTITION,
                                RES_CHECK_PARTITION_STATE,
                                HIL_RESERVATION_DEFAULT_DURATION,
                                HIL_RESERVATION_GRACE_PERIOD,
                                HIL_SLURMCTLD_PROLOG_LOGFILE, USER_HIL_LOGFILE,
                                USER_HIL_SUBDIR, USER_HIL_RES_RELEASE_FILE)


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


def _get_user_hil_subdir(env_dict):
    home = os.path.expanduser('~' + env_dict['username'])
    return os.path.join(home, USER_HIL_SUBDIR)


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

    # $$$ Verify hil_release as been run against a HIL reservation

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
#   log_debug('Job start %s  Job end %s' % (t_job_start_s, t_job_end_s))

    t_start_dt = datetime.strptime(t_job_start_s, SHOW_OBJ_TIME_FMT)

    if 'Unknown' not in t_job_end_s:
        log_debug('Using job end time')
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
                log_debug('Using partition time limit')
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


def _create_hil_reservation(env_dict, pdata_dict, jobdata_dict):
    '''
    Create a HIL reservation
    '''
    # Generate HIL reservation start and end times
    t_start_s, t_end_s = _get_hil_reservation_times(env_dict, pdata_dict, jobdata_dict)

    # Generate a HIL reservation name
    resname = _get_hil_reservation_name(env_dict, t_start_s)

    # Check if reservation exists.  If so, do nothing
    resdata_dict_list, stdout_data, stderr_data = exec_scontrol_show_cmd('reservation', resname)
    if (stderr_data) and ('not found' not in stderr_data):
        log_info('HIL reservation `%s` already exists' % resname)
        return resname, stderr_data

    log_info('Creating HIL reservation `%s`, ending %s' % (resname, t_end_s))

    stdout_data, stderr_data = create_slurm_reservation(resname, env_dict['username'],
                                                        t_start_s, t_end_s,
                                                        nodes=None, flags=RES_CREATE_FLAGS,
                                                        debug=False)
    return resname, stderr_data


def _delete_hil_reservation(env_dict, pdata_dict, jobdata_dict, resname):
    '''
    '''
    log_info('Deleting HIL reservation `%s`' % resname)

    # Minimally validate the specified reservation has the correct name and format
    if not resname.startswith(HIL_RESERVATION_PREFIX + env_dict['username']):
        log_info('Error in HIL reservation name (`%s`)' % resname)
        return None, 'hil_release: error: Invalid reservation name'

    return delete_slurm_reservation(resname, debug=False)


def _get_hil_reservation_name(env_dict, t_start_s):
    '''
    Create a reservation name, combining the HIL reservation prefix,
    the username, the job ID, and the ToD (YMD_HMS)
    '''
    resname = HIL_RESERVATION_PREFIX + env_dict['username'] + '_'
    resname += env_dict['job_uid'] + '_' + t_start_s
    log_debug('Reservation name is %s' % resname)
    return resname


def _log_hil_reservation(resname, action, env_dict, message=None):
    '''
    Log the reservation to the user's reservation log file
    '''
    user_hil_subdir = _get_user_hil_subdir(env_dict)
    user_hil_logfile = os.path.join(user_hil_subdir, USER_HIL_LOGFILE)
    f = open(user_hil_logfile, 'a')
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    f.write('%s %s HIL reservation `%s`\n' % (ts, action, resname))
    f.close()


def _hil_reserve_cmd(env_dict, pdata_dict, jobdata_dict):
    '''
    Create a HIL reservation if it does not already exist.
    '''
    resname, stderr_data = _create_hil_reservation(env_dict, pdata_dict, jobdata_dict)
    _log_hil_reservation(resname, 'Created', env_dict)


def _slurm_find_reservations(name_prefix, jobdata_dict):
    '''
    Find Slurm reservations with names matching the name prefix and,
    if necessary, nodes matching the node prefix
    '''
    # Obtain a dictionary of all reservations active in the system
    resdata_dict_list, stdout_data, stderr_data = exec_scontrol_show_cmd('reservation', None)
    if len(stderr_data):
        return []

    # Find reservations with names matching the name prefix
    # If there's more than one, try a nodelist match
    resdata_dict_list = filter(lambda x: name_prefix in x['ReservationName'], resdata_dict_list)

    # If more than one remaining reservation, find a matching nodelist
    if (len(resdata_dict_list) <= 1):
        return resdata_dict_list

    job_nodelist = jobdata_dict['NodeList']
    resdata_dict_list = filter(lambda x: job_nodelist == x['Nodes'])

    log_debug('Candidates for release:')
    for resdata_dict in resdata_dict_list:
        log_debug('  %s' % resdata_dict['ReservationName'])

    return resdata_dict_list


def _hil_prepare_release(env_dict, pdata_dict, jobdata_dict):
    '''
    Called by the prolog when the 'hil_release' command has been passed.
    Since we cannot pass the reservation name to the prolog, find the target 
    reservations using the username and job node list.
    WARNING: This assumes the nodes in the reservation are marked as not shared
    '''
    resname_prefix = HIL_RESERVATION_PREFIX + env_dict['username']
    resdata_dict_list = _slurm_find_reservations(resname_prefix, jobdata_dict)

    user_hil_subdir = _get_user_hil_subdir(env_dict)
    user_res_release_file = os.path.join(user_hil_subdir, USER_HIL_RES_RELEASE_FILE)

    res_release_list = []

    with open(user_res_release_file, 'a') as f:
        for resdata_dict in resdata_dict_list:
            # $$$ Add time and date
            f.write(resdata_dict['ReservationName'] + '\n')

            log_debug('Wrote %s to deletion file' % resdata_dict['ReservationName'] + '\n')
    # Reservation is now ready for deletion by the epilog
        

def _hil_release_cmd(env_dict, pdata_dict, jobdata_dict):
    '''
    Release a HIL reservation
    1. Check if the user has a ~/.hil/.release file
    2. If so, see if the reservation matching that name exists
    3. If so, delete that reservation
    4. Delete the ~/.hil/.release file
    '''
    user_hil_subdir = _get_user_hil_subdir(env_dict)
    user_res_release_file = os.path.join(user_hil_subdir, USER_HIL_RES_RELEASE_FILE)

    res_release_list = []

    with open(user_res_release_file, 'r') as f:
        for line in f:
            res_release_list.append(line.strip(os.linesep))

    log_debug('Deletion file list %s' % res_release_list)

    if (len(res_release_list) == 0):
        return

    for resname in res_release_list:
        log_debug('HIL epilog: Deleting reservation %s' % resname)
        stdout_data, stderr_data = _delete_hil_reservation(env_dict, pdata_dict, jobdata_dict, resname)
        if (len(stderr_data) == 0):
            _log_hil_reservation(resname, 'Released', env_dict)

    os.remove(user_res_release_file)


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
        log_info('HIL Slurmctld Prolog', separator=True)
    elif args.hil_epilog:
        log_info('HIL Slurmctld Epilog', separator=True)
    else:
        log_debug('Must specify one of --hil_prolog or --hil_epilog', separator=True)
        return

    # Collect prolog/epilog environment, job data, and partition data into dictionaries,
    # perform basic sanity checks
    # Since data for one partition and one job is expected, select the first dict in the list

    env_dict = _get_prolog_environment()
    pdata_dict = get_partition_data(env_dict['partition'])[0]
    jobdata_dict = get_job_data(env_dict['job_id'])[0]

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

    if args.hil_prolog:
        if (hil_cmd == 'hil_reserve'):
            log_debug('Processing reservation request.')
            _hil_reserve_cmd(env_dict, pdata_dict, jobdata_dict)

        elif (hil_cmd == 'hil_release'):
            log_debug('Processing release request.')
            _hil_prepare_release(env_dict, pdata_dict, jobdata_dict)

    elif args.hil_epilog:
        _hil_release_cmd(env_dict, pdata_dict, jobdata_dict)

    return


if __name__ == '__main__':
    main(sys.argv[1:])
    exit(0)

# EOF

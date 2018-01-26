"""
MassOpenCloud / Hardware Isolation Layer (MOC/HIL)

Slurm and *NX Subprocess Command Helpers

May 2017, Tim Donahue	tpd001@gmail.com
"""

import os
from pwd import getpwnam, getpwuid
from subprocess import Popen, PIPE
from time import time

from hil_slurm_constants import (HIL_RESNAME_PREFIX, HIL_RESNAME_FIELD_SEPARATOR,
                                 HIL_RESERVATION_OPERATIONS, RES_CREATE_FLAGS,
                                 HIL_RESERVE, HIL_RELEASE)
from hil_slurm_settings import SLURM_INSTALL_DIR
from hil_slurm_logging import log_debug, log_info, log_error


def _output_debug_info(fname, stdout_data, stderr_data):
    log_debug('%s: Stdout  %s' % (fname, stdout_data))
    log_debug('%s: Stderr  %s' % (fname, stderr_data))


def _exec_subprocess_cmd(cmd):
    '''
    Execute a command in a subprocess and wait for completion
    '''
    debug = False
    p = None
    try:
        p = Popen(cmd, stdout=PIPE, stderr=PIPE)
        (stdout_data, stderr_data) = p.communicate()
    except Exception as e:
        stdout_data = None
        stderr_data ='error: Exception on Popen or communicate'
        log_debug('Exception on Popen or communicate')
        log_debug('Exception: %s' % e)

    if debug:
        f = _exec_subprocess_cmd.__name__
        log_debug('%s: cmd is %s' % (f, cmd))
        log_debug('%s: stdout is %s' % (f, stdout_data))
        log_debug('%s: stderr is %s' % (f, stderr_data))

    return stdout_data, stderr_data


def _scontrol_show_stdout_to_dict_list(stdout_data, stderr_data, debug=False):
    '''
    Convert the 'scontrol show' stdout data to a list of dicts
    Nearly all params are of the form "keyword=value".
    If they all were, a neat functional one-liner would do...
    '''
    stdout_dict_list = []

    if len(stderr_data):
        return []

    # Split the output and remove the trailing None from the subprocess output
    stdout_lines = stdout_data.split(os.linesep)
    stdout_lines = filter(None, stdout_lines)

    # Convert the output to a list of dicts
    for line in stdout_lines:
        stdout_line_dict = {}

        for kv_pair in line.split(' '):
            kv = kv_pair.split('=')
            if (len(kv) == 2):
                stdout_line_dict[kv[0]] = kv[1]
            elif debug:
                log_debug('Failed to convert `$s`' % kv_pair)

        stdout_dict_list.append(stdout_line_dict)

    return stdout_dict_list


def exec_scontrol_cmd(action, entity, entity_id=None, debug=True, **kwargs):
    '''
    Build an 'scontrol <action> <entity>' command and pass to an executor
    Specify single-line output to support stdout postprocessing
    '''
    cmd = [os.path.join(SLURM_INSTALL_DIR, 'scontrol'), action]

    if entity:
        cmd.append(entity)

    if entity_id:
        cmd.append(entity_id)

    cmd.append('-o')

    if kwargs:
        for k, v in kwargs.iteritems():
            cmd.append('%s=%s' % (k,v))

    if debug:
        log_debug('exec_scontrol_cmd(): Command  %s' % cmd)

    stdout_data, stderr_data = _exec_subprocess_cmd(cmd)

    if debug:
        log_debug('exec_scontrol_cmd(): Stdout  %s' % stdout_data)
        log_debug('exec_scontrol_cmd(): Stderr  %s' % stderr_data)

    return stdout_data, stderr_data


def exec_scontrol_show_cmd(entity, entity_id, debug=False, **kwargs):
    '''
    Run the 'scontrol show' command on the entity and ID
    Convert standard output data to a list of dictionaries, one per line
    '''
    stdout_data, stderr_data = exec_scontrol_cmd('show', entity, entity_id, debug=debug, **kwargs)

    # Check for errors.
    # If anything in stderr, return it
    # Next, check if stdout includes various error strings - 'scontrol show'
    #     writes error output to stdout.
    #     Failure indications:
    #         Reservation:  stdout includes 'not found'
    #         Job: stdout includes 'Invalid job id'
    #     Copy stdout to stderr if found.
    # If stderr is empty, and stdout does not contain an error string,
    #     convert stdout to a list of dicts and return that

    stdout_dict_list = []

    entity_error_dict = {
        'reservation': 'not found',
        'job': 'Invalid job id'
        }

    cmd = 'scontrol show ' + entity
    if (len(stderr_data) != 0):
        log_debug('Command `%s` failed' % cmd)
        log_debug('  stderr: %s' % stderr_data)

    elif (entity in entity_error_dict) and (entity_error_dict[entity] in stdout_data):
        if debug:
            log_debug('Command `%s` failed' % cmd)
            log_debug('  stderr: %s' % stderr_data)
        stderr_data = stdout_data
        stdout_data = None

    else:
        stdout_dict_list = _scontrol_show_stdout_to_dict_list(stdout_data, stderr_data)

    return stdout_dict_list, stdout_data, stderr_data


def create_slurm_reservation(name, user, t_start_s, t_end_s, nodes=None,
                             flags=RES_CREATE_FLAGS, features=None, debug=False):
    '''
    Create a Slurm reservation via 'scontrol create reservation'
    '''
    if nodes is None:
        nodes = 'ALL'

    t_end_arg = {'duration': 'UNLIMITED'} if t_end_s is None else {'endtime': t_end_s}

    return exec_scontrol_cmd('create', 'reservation', entity_id=None, debug=debug,
                             ReservationName=name, starttime=t_start_s,
                             user=user, nodes=nodes, flags=flags, features=features,
                             **t_end_arg)


def delete_slurm_reservation(name, debug=False):
    '''
    Delete a Slurm reservation via 'scontrol delete reservation=<name>'
    '''
    return exec_scontrol_cmd('delete', None, debug=debug, reservation=name)


def update_slurm_reservation(name, debug=False, **kwargs):
    '''
    Update a Slurm reservation via 'scontrol update reservation=<name> <kwargs>'
    '''
    return exec_scontrol_cmd('update', None, reservation=name, debug=debug, **kwargs)


def get_hil_reservation_name(env_dict, restype_s, t_start_s):
    '''
    Create a reservation name, combining the HIL reservation prefix,
    the username, the job ID, and the ToD (YMD_HMS)

    Structure:
      NamePrefix _ [release|reserve] _ uname _ job_UID _ str(int(time()))
    '''
    resname = HIL_RESNAME_PREFIX + restype_s + HIL_RESNAME_FIELD_SEPARATOR
    resname += env_dict['username'] + HIL_RESNAME_FIELD_SEPARATOR
    resname += env_dict['job_uid'] + HIL_RESNAME_FIELD_SEPARATOR
    resname += str(int(time()))
    return resname


def parse_hil_reservation_name(resname):
    '''
    Attempt to split a reservation name into HIL reservation name components:
    HIL reservation prefix, reservation type, user name, uid, and time

    This looks like overkill, except for the presence of other reservations in the
    system, with semi-arbitrary names.
    '''
    prefix = None
    restype = None
    user = None
    uid = None
    time_s = None

    if resname.startswith(HIL_RESNAME_PREFIX):
        resname_partitions = resname.partition(HIL_RESNAME_PREFIX)
        prefix = resname_partitions[1]

        try:
            restype, user, uid, time_s = resname_partitions[2].split(HIL_RESNAME_FIELD_SEPARATOR)
        except:
            pass

    return prefix, restype, user, uid, time_s


def is_hil_reservation(resname, restype_in):
    '''
    Check if the passed reservation name:
    - Starts with the HIL reservation prefix
    - Is a HIL reserve or release reservation
    - Contains a valid user name and UID
    - Optionally, is specifically a reserve or release reservation
    - $$$ Could verify nodes have HIL property set
    '''
    prefix, restype, uname, uid, _ = parse_hil_reservation_name(resname)
    if (prefix != HIL_RESNAME_PREFIX):
#       log_error('No HIL reservation prefix')
        return False

    if restype_in:
        if (restype != restype_in):
#           log_error('Reservation type mismatch')
            return False
    elif restype not in HIL_RESERVATION_OPERATIONS:
        log_error('Unknown reservation type')
        return False

    try:
        pwdbe1 = getpwnam(uname)
        pwdbe2 = getpwuid(int(uid))
        if pwdbe1 != pwdbe2:
#           log_error('Reservation `%s`: User and UID inconsistent' % resname)
            return False

    except KeyError:
#       log_error('Key error')
        return False

    return True


def get_object_data(what_obj, obj_id, debug=False):
    '''
    Get a list of dictionaries of information on the object, via
    'scontrol show <what_object> <object_id>'
    '''
    objdata_dict_list, stdout_data, stderr_data = exec_scontrol_show_cmd(what_obj,
                                                                         obj_id, debug=False)
    if (len(stderr_data) != 0):
        if debug:
            log_debug('Failed to retrieve data for %s `%s`' % (what_obj, obj_id))
            log_debug('  %s' % stderr_data)

    return objdata_dict_list


def get_partition_data(partition_id):
    '''
    Get a list of dictionaries of information on the partition(s),
    via 'scontrol show partition'
    '''
    return get_object_data('partition', partition_id, debug=False)


def get_job_data(job_id):
    '''
    Get a list of dictionaries of information on the job(s),
    via 'scontrol show job'
    '''
    return get_object_data('job', job_id, debug=False)


def get_hil_reservations():
    '''
    Get a list of all Slurm reservations, return that subset which are HIL reservations
    '''
    resdata_dict_list = []

    resdata_dict_list, stdout_data, stderr_data = exec_scontrol_show_cmd('reservation', None)

    for resdata_dict in resdata_dict_list:
        if resdata_dict and is_hil_reservation(resdata_dict['ReservationName'], None):
            continue
        else:
            resdata_dict_list.remove(resdata_dict)

    return resdata_dict_list


def log_hil_reservation(resname, stderr_data, t_start_s=None, t_end_s=None):
    if len(stderr_data):
        log_error('Error creating reservation `%s`'% resname)
        log_error('  Error string: %s' % stderr_data.strip('\n'), separator=False)
    else:
        log_info('Created  HIL reservation `%s`' % resname)

# EOF

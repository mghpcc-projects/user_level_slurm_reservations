"""
MassOpenCloud / Hardware Isolation Layer (MOC/HIL)

Slurm and *NX Subprocess Command Helpers

May 2017, Tim Donahue	tpd001@gmail.com
"""

import os
from subprocess import Popen, PIPE

from hil_slurm_constants import RES_CREATE_FLAGS
from hil_slurm_settings import SLURM_INSTALL_DIR
from hil_slurm_logging import log_debug, log_error


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

    return exec_scontrol_cmd('create', 'reservation', entity_id=None, debug=debug, 
                             ReservationName=name, starttime=t_start_s, endtime=t_end_s,
                             user=user, nodes=nodes, flags=flags, features=features)


def delete_slurm_reservation(name, debug=False):
    '''
    Delete a Slurm reservation via 'scontrol delete reservation=<name>'
    '''
    return exec_scontrol_cmd('delete', None, debug=debug, reservation=name)


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


# EOF

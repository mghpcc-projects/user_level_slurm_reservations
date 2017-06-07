"""
MassOpenCloud / Hardware Isolation Layer (MOC/HIL)

Slurm and *NX Subprocess Command Helpers

May 2017, Tim Donahue	tpd001@gmail.com
"""

import os
import string
from subprocess import call, Popen, PIPE
from hil_slurm_settings import (HIL_CMD_NAMES, HIL_PARTITION_PREFIX,
                                SLURM_INSTALL_DIR, DEBUG)
from hil_slurm_logging import log_debug, log_error


def exec_subprocess_cmd(cmd, debug=True):
    '''
    Execute a command in a subprocess and wait for completion
    '''
    try:
        p = Popen(cmd, stdout=PIPE)
        stdout_data, stderr_data = p.communicate()
    except:
        log_error('Exception on Popen or communicate')

    log_debug('exec_subprocess_cmd():  stdout is %s' % stdout_data)
    log_debug('exec_subprocess_cmd():  stderr is %s' % stderr_data)
    return stdout_data, stderr_data


def _scontrol_stdout_to_dict(stdout_data, stderr_data):
    '''
    Convert the scontrol stdout data to a dict.
    Nearly all params are of the form "keyword=value".  
    If they all were, a neat functional one-liner would go here.
    '''
    stdout_dict = {}

    if stderr_data is None:
        for kv_pair in stdout_data.split(' '):
            kv = kv_pair.split('=')
            if (len(kv) == 2):
                stdout_dict[kv[0]] = kv[1]
            else:
                log_debug('Failed to convert `%s`' % kv_pair)

    return stdout_dict


def exec_scontrol_create_cmd(entity, debug=False, **kwargs):
    '''
    Build an scontrol create command, then pass it to an executor function
    '''
    cmd = [os.path.join(SLURM_INSTALL_DIR, 'scontrol')]
    cmd += ['create', entity]

    if kwargs is not None:
        for k, v in kwargs.iteritems():
            cmd.append('%s=%s' % (k, v))

    log_debug('exec_scontrol_create_cmd():  %s' % cmd)

    stdout_data, stderr_data = exec_subprocess_cmd(cmd, debug)
    return stdout_data, stderr_data


def exec_scontrol_show_cmd(entity, entity_id, debug=False, **kwargs):
    '''
    Build an scontrol command, then pass it to an executor function
    Specify single-line output to support stdout postprocessing
    Optionally convert output to a dictionary
    '''
    cmd = [os.path.join(SLURM_INSTALL_DIR, 'scontrol')]
    cmd += ['show', entity, entity_id, '-o']

    if kwargs is not None:
        for k, v in kwargs.iteritems():
            cmd.append('--%s=%s' % (k, v))

    log_debug('exec_scontrol_show_cmd():  %s' % cmd)

    stdout_data, stderr_data = exec_subprocess_cmd(cmd, debug)

    # If there is no error, and there is valid output in the
    # expected 'foo=bar' one-line format, convert to a dictionary
    #
    # Failure indications:
    #  Reservation:  stdout includes 'not found'
    #  Job: stdout includes 'Invalid job id'
    # In these cases set stderr to stdout and return a null dict
    #
    entity_error_dict = {
        'reservation': 'not found',
        'job': 'Invalid job id'
        }
    if (entity in entity_error_dict):
        if (entity_error_dict[entity] in stdout_data):
            stderr_data = stdout_data

    # Convert to a dict if stderr_data is None

    stdout_dict = _scontrol_stdout_to_dict(stdout_data, stderr_data)
    return stdout_dict, stderr_data


# EOF

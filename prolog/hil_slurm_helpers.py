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
from hil_slurm_logging import log_debug


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

    # Convert the stdout output from scontrol to a dict, making
    # assumptions about the format
    if stderr_data is None:
        stdout_dict = dict(x.split('=') for x in stdout_data.split(' '))
    else:
        stdout_dict = []

    return stdout_dict


def exec_scontrol_create_cmd(entity, entity_id, debug=False, **kwargs):
    '''
    Build an scontrol create command, then pass it to an executor function
    '''
    cmd = [os.path.join(SLURM_INSTALL_DIR, 'scontrol')]
    cmd += ['create', entity, entity_id]

    if kwargs is not None:
        for k, v in kwargs.iteritems():
            cmd.append('--%s=%s' % (k, v))

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
    # Note if we went looking for an HIL reservation and it does
    # not exist, stderr is None and stdout includes "not found"
    #
    if (entity == 'reservation'):
        if 'not found' in stdout_data:
            stderr_data = stdout_data

    # Convert to a dict if stderr_data is None

    stdout_dict = _scontrol_stdout_to_dict(stdout_data, stderr_data)
    return stdout_dict, stderr_data


# EOF

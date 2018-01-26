"""
MassOpenCloud (MOC) / Hardware Isolation Layer (HIL)

User Level Slurm Reservations 

Infiniband support routines

November 2017, Tim Donahue  tdonahue@mit.edu
"""
from sys import _getframe

from hil_slurm_helpers import _exec_subprocess_cmd, _output_debug_info
from hil_slurm_settings import DISABLE_IB_LINKS
from hil_slurm_logging import log_debug, log_info, log_error


def exec_subprocess_cmd(cmd):
    '''
    Placeholder
    '''
    return _exec_subprocess_cmd(cmd)


def _parse_iblinkinfo_line():
    peer_switch_id = ''
    port_number = ''

    return peer_switch_id, port_number


def _get_peer_ib_switchports():
    '''
    '''
    iblinkinfo_cmd = 'iblinkinfo -l -D 1'
    iblinkinfo_cmd = 'cat iblinkinfo.out'
    stdout_data, stderr_data = exec_subprocess_cmd(iblinkinfo_cmd)
    if debug:
        _output_debug_info(sys._getframe().f_code.co_name, stdout_data, stderr_data)

    switchport_list = []

    switch_id, port_number = _parse_iblinkinfo_line()

    return switchport_list


def _disable_one_ib_link(switch_guid, port_number):
    '''
    '''
    ibportstate_cmd = 'ibportstate -G {} {} disable'.format(switch_guid, port_number)
    ibportstate_cmd = 'ls'

    stdout_data, stderr_data = exec_subprocess_cmd(ibportstate_cmd)
    if debug:
        _output_debug_info(sys._getframe().f_code.co_name, stdout_data, stderr_data)


# ibportstate -G 0xf4521403007cbfd0 11 disable # node065


def update_infiniband(nodelist):
    '''
    '''
    if not DISABLE_IB_LINKS:
        log_info('Infiniband connections will not be modified')
        return

    log_info('Infiniband connections will be shut down')

    for node in nodelist:
        

IBINFO_FILE = '/home/tdonahue/Documents/clush.out'
IBINFO_FILE = '/home/tdonahue/Documents/ibl_all.out'

lines = [line.strip('\n') for line in open(IBINFO_FILE)]

switches = {}

# Read each line in the IB link info output file

for line in lines:
    if line[:1] is '>':
        print 'Skipping comment line'
        continue

    print line
    lhs, _, switch_id_token = line.partition('==>')
    if 'LinkUp' not in lhs:
        continue

    switch_id = switch_id_token.lstrip()[:18]

    port_number_token, _, _ = switch_id_token.rpartition('[')
    port_number = port_number_token.split()[2].strip()

#    print 'Line %s' % line
#    print '  Switch ID %s' % switch_id
#    print '  Port number %s' % port_number

    if switch_id in switches:
        switches[switch_id].append(port_number)
    else:
        switches[switch_id] = [port_number]


for switch_id, port_list in switches.iteritems():
    print 'Switch ID  %s:  %s ports' % (switch_id, len(port_list))
    for port_number in sorted(port_list, key=lambda(n): int(n)):
        print '  Port ID %s' % port_number


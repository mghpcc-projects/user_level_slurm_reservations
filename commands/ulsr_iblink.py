"""
MassOpenCloud / Hardware Isolation Layer (HIL)
User Level Slurm Reservations (ULSR)

Infiniband Link Management 

December 2017, Tim Donahue	tdonahue@mit.edu
"""

import hostlist
import logging
import sys

from ulsr_settings import ULSR_NET_AUDIT_LOGFILE
from ulsr_logging import log_init, log_info, log_debug, log_error

IBLINKINFO_CMD = iblinkinfo.sh
IBPORTSTATE_CMD = ibportstate.sh


def main(argv=[]):
    '''
    '''
    log_init('ULSR_Infiniband_mgmt', ULSR_IB_MGMT_LOGFILE, logging.DEBUG)

    log_info('ULSR Infiniband Management', separator=True)
    log_debug('')


if __name__ == '__main__':
    main(sys.argv[1:])
    exit(0)

# EOF

"""
MassOpenCloud / Hardware Isolation Layer (HIL)
User Level Slurm Reservations (ULSR)

Periodic Network Audit

November 2017, Tim Donahue	tdonahue@mit.edu
"""

import logging
import sys

import ulsr_importpath
from ulsr_settings import ULSR_AUDIT_LOGFILE
from ulsr_logging import log_init, log_info, log_debug, log_error


def main(argv=[]):
    '''
    '''
    log_init('ULSR_network_audit', ULSR_AUDIT_LOGFILE, logging.DEBUG)

    log_info('ULSR Network Audit', separator=True)
    log_debug('')



if __name__ == '__main__':
    main(sys.argv[1:])
    exit(0)


# EOF


"""
MassOpenCloud / Hardware Isolation Layer (HIL)

Slurm / HIL Control Settings

May 2017, Tim Donahue	tpd001@gmail.com
"""

DEBUG = True

SLURM_INSTALL_DIR = '/usr/bin/'

HIL_SLURMCTLD_PROLOG_LOGFILE = '/var/log/slurm-llnl/hil_prolog.log'
HIL_MONITOR_LOGFILE = '/var/log/slurm-llnl/hil_monitor.log'

HIL_RESERVATIONS_FILE = '/var/local/slurm-llnl/hil_reservations.txt'

USER_HIL_SUBDIR = '.hil'
USER_HIL_LOGFILE = 'hil_reservations.log'

HIL_CMD_NAMES = ('hil_reserve', 'hil_release')

HIL_PARTITION_PREFIX = 'HIL_partition_'
HIL_PARTITION_PREFIX = 'debug'

HIL_RESERVATION_DEFAULT_DURATION = 24 * 60 * 60		# Seconds
HIL_RESERVATION_GRACE_PERIOD = 4 * 60 * 60		# Seconds

HIL_RESERVATION_PREFIX = 'flexalloc_MOC_'

# Partition validation controls

RES_CHECK_DEFAULT_PARTITION = False
RES_CHECK_EXCLUSIVE_PARTITION = False
RES_CHECK_SHARED_PARTITION = False
RES_CHECK_PARTITION_STATE = True

# EOF

"""
MassOpenCloud / Hardware Isolation Layer (HIL)

Slurm / HIL Control Settings

May 2017, Tim Donahue	tdonahue@mit.edu
"""

DEBUG = True

SLURM_INSTALL_DIR = '/usr/bin/'

HIL_SLURMCTLD_PROLOG_LOGFILE = '/var/log/ulsr/ulsr_prolog.log'
HIL_MONITOR_LOGFILE = '/var/log/ulsr/ulsr_monitor.log'

HIL_ENDPOINT = "http://10.0.0.16:80"
HIL_USER = 'admin'
HIL_PW = 'NavedIsSleepy'
HIL_SLURM_PROJECT = 'slurm'

HIL_PARTITION_PREFIX = 'HIL_partition'

HIL_RESERVATION_DEFAULT_DURATION = 24 * 60 * 60		# Seconds
HIL_RESERVATION_GRACE_PERIOD = 4 * 60 * 60		# Seconds

# Partition validation controls

RES_CHECK_DEFAULT_PARTITION = False
RES_CHECK_EXCLUSIVE_PARTITION = False
RES_CHECK_SHARED_PARTITION = False
RES_CHECK_PARTITION_STATE = True

# Infiniband control
# Setting to False will cause Infiniband connections, if any, to be ignored and unchanged

DISABLE_IB_LINKS = True

# EOF

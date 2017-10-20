"""
MassOpenCloud / Hardware Isolation Layer (HIL)

Slurm / HIL Control Settings

May 2017, Tim Donahue	tpd001@gmail.com
"""

DEBUG = True

SLURM_INSTALL_DIR = '/usr/bin/'

HIL_SLURMCTLD_PROLOG_LOGFILE = '/var/log/moc_hil_ulsr/hil_prolog.log'
HIL_MONITOR_LOGFILE = '/var/log/moc_hil_ulsr/hil_monitor.log'

HIL_ENDPOINT = "http://128.31.28.156:80"
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

# EOF

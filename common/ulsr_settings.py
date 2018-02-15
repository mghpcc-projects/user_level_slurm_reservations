"""
MassOpenCloud / Hardware Isolation Layer (HIL)

ULSR Control Settings

May 2017, Tim Donahue	tdonahue@mit.edu
"""

DEBUG = True

SLURM_INSTALL_DIR = '/usr/bin/'

# Log files

ULSR_SLURMCTLD_PROLOG_LOGFILE = '/var/log/ulsr/ulsr_prolog.log'
ULSR_MONITOR_LOGFILE = '/var/log/ulsr/ulsr_monitor.log'
ULSR_AUDIT_LOGFILE = '/var/log/ulsr/ulsr_audit.log'
ULSR_IB_MGMT_LOGFILE = '/var/log/ulsr/ulsr_ib_mgmt.log'

# HIL Configuration

HIL_ENDPOINT = "http://10.0.0.16:80"
HIL_USER = 'admin'
HIL_PW = 'NavedIsSleepy'
HIL_SLURM_PROJECT = 'slurm'

ULSR_PARTITION_PREFIX = 'ULSR_partition'

# Slurm Reservation Times

ULSR_RESERVATION_DEFAULT_DURATION = 24 * 60 * 60	# Seconds
ULSR_RESERVATION_GRACE_PERIOD = 4 * 60 * 60		# Seconds

# Partition validation controls

RES_CHECK_DEFAULT_PARTITION = False
RES_CHECK_EXCLUSIVE_PARTITION = False
RES_CHECK_SHARED_PARTITION = False
RES_CHECK_PARTITION_STATE = True

# Infiniband Management Settings

IB_DEVICE_DIR = '/dev/infiniband'
IB_DEVICE_NAME_PREFIX = '/dev/infiniband/umad'


DISABLE_IB_LINKS = True

ULSR_IBLINK_CFGFILE = 'iblink_conf.xml'

IBLINKINFO_CMD = '/usr/sbin/iblinkinfo'
IBPORTSTATE_CMD = '/usr/sbin/ibportstate'
IBSTATUS_CMD = '/usr/sbin/ibstatus'
IBSTAT_CMD = '/usr/sbin/ibstat'
CNH_SSS_LINKINFO_CMD = '/usr/local/bin/iblinkinfo_me.sh'
CNH_SSS_PORTSTATE_CMD = '/usr/local/bin/ibendis.sh'

# EOF

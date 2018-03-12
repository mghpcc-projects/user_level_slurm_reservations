"""
MassOpenCloud / Hardware Isolation Layer (HIL)

ULSR Control Settings

May 2017, Tim Donahue	tdonahue@mit.edu
"""

SLURM_INSTALL_DIR = '/usr/local/bin/'

# Log files

ULSR_SLURMCTLD_PROLOG_LOGFILE = '/var/log/ulsr/ulsr_prolog.log'
ULSR_MONITOR_LOGFILE = '/var/log/ulsr/ulsr_monitor.log'
ULSR_AUDIT_LOGFILE = '/var/log/ulsr/ulsr_audit.log'
ULSR_IB_MGMT_LOGFILE = '/var/log/ulsr/ulsr_ib_mgmt.log'

# HIL Configuration

HIL_AVAILABLE = False
HIL_ENDPOINT = "http://10.0.0.16:80"
HIL_USER = 'admin'
HIL_PW = 'NavedIsSleepy'
HIL_SLURM_PROJECT = 'slurm'

ULSR_PARTITION_PREFIX = 'ULSR_partition'

# Slurm Reservation Times

SLURM_AVAILABLE = False
ULSR_RESERVATION_DEFAULT_DURATION = 24 * 60 * 60        # Seconds
ULSR_RESERVATION_GRACE_PERIOD = 4 * 60 * 60		# Seconds

# Partition validation controls

RES_CHECK_DEFAULT_PARTITION = False
RES_CHECK_EXCLUSIVE_PARTITION = False
RES_CHECK_SHARED_PARTITION = False
RES_CHECK_PARTITION_STATE = True

# Infiniband Management Settings

IB_AVAILABLE = True
IB_UMAD_DEVICE_DIR = '/dev/infiniband'
IB_UMAD_DEVICE_NAME_PREFIX = '/dev/infiniband/umad'

DEFAULT_IB_PERMIT_CFGFILE = 'ulsr_ibproxy.conf'

# Privileged Mode Commands

IBLINKINFO_CMD = '/usr/sbin/iblinkinfo -l -D 0 -P'
IBPORTSTATE_CMD = '/usr/sbin/ibportstate'
IBSTAT_CMD = '/usr/sbin/ibstat -p'

# Untrusted Mode Commands

SS_LINKINFO_CMD = '/usr/local/bin/iblinkinfo_me.sh'
SS_PORTSTATE_CMD = '/usr/local/bin/ibendis.sh'

# SSH Options

SSH_OPTIONS = ['-o UserKnownHostsFile=/dev/null', '-o StrictHostKeyChecking=no', '-q']
SSH_OPTIONS = ['-o UserKnownHostsFile=/dev/null', '-o StrictHostKeyChecking=no']

# Subprocess Timeout (seconds)
# Subproccesses which do not complete in this time will be killed

SUBPROCESS_TIMEOUT = 60

# Test Settings

from ulsr_constants import ULSR_RESNAME_PREFIX

TEST_USER = 'cc'
TEST_UID = '1000'

TEST_RESNAME = ULSR_RESNAME_PREFIX + 'reserve' + '_' 
TEST_RESNAME += TEST_USER + '_' + TEST_UID + '_' + '1520606201'

TEST_NODELIST = ['ib-test-2',]

TEST_RESDATA = [{'Users': TEST_USER, 'Nodes': TEST_NODELIST, 'ReservationName': TEST_RESNAME,
                 'StartTime': '2018-01-01T00:00:00', 'EndTime': '2018-12-31T23:59:59'}]

TEST_JOB_DATA = [{'JobName': 'hil_reserve', 'TimeLimit': 'UNLIMITED', 
                  'StartTime': '2018-01-01T00:00:00', 'EndTime': '2018-12-31T23:59:59',
                  'Reservation': TEST_RESNAME}]

TEST_PARTITION_DATA = [{'Shared': 'NO', 'ExclusiveUser': 'YES', 'Default': 'NO', 
                        'State': 'UP', 'PartitionName': ULSR_PARTITION_PREFIX}]

# EOF

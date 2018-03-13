"""
MassOpenCloud / Hardware Isolation Layer (HIL)

ULSR Constants

June 2017, Tim Donahue	tdonahue@mit.edu
"""

SHOW_OBJ_TIME_FMT = '%Y-%m-%dT%H:%M:%S'
RES_CREATE_TIME_FMT = SHOW_OBJ_TIME_FMT

SHOW_PARTITION_MAXTIME_HMS_FMT = '-%H:%M:%S'

RES_NAME_TIME_FMT = '%Y%m%d_%H%M%S'

RES_CREATE_HIL_FEATURES='HIL'

RES_CREATE_FLAGS = 'MAINT,IGNORE_JOBS'
# RES_RELEASE_FLAGS = '-MAINT'


ULSR_RESERVE = 'reserve'
ULSR_RELEASE = 'release'

ULSR_RESERVATION_OPERATIONS = [ULSR_RESERVE, ULSR_RELEASE]
ULSR_RESERVATION_COMMANDS = ['hil_%s' % op for op in ULSR_RESERVATION_OPERATIONS]

ULSR_RESNAME_PREFIX = 'flexalloc_MOC_'
ULSR_RESNAME_FIELD_SEPARATOR = '_'

# $$$ Temporary

IBENDIS_PERROR = {1: 'Invalid GUID format',
                  2: 'Invalid port number format',
                  3: 'Invalid port action',
                  4: 'Invalid input line',
                  5: 'Failed GUID / port combination check',
                  6: 'File checks failed'}
    
# EOF

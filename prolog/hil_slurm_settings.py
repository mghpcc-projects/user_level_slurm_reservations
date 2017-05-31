"""
MassOpenCloud / Hardware Isolation Layer (HIL)

Slurm / HIL Control Settings

May 2017, Tim Donahue	tpd001@gmail.com
"""

DEBUG = True

SLURM_INSTALL_DIR = '/usr/bin/'

HIL_CMD_NAMES = ('hil_reserve', 'hil_release')
HIL_PARTITION_PREFIX = 'HIL_partition_'
HIL_PARTITION_PREFIX = 'debug'

HIL_RESERVATION_PREFIX = 'flexalloc_MOC_'
RES_TIME_FMT = '%Y%m%d_%H%M%S'
RES_FLAGS = 'MAINT, DOWN, ignore_jobs'

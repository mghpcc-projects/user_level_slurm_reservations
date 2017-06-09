"""
MassOpenCloud / Hardware Isolation Layer (MOC/HIL)

HIL Slurm Logging support

June 2017, Tim Donahue	tpd001@gmail.com
"""

import logging
from sys import exc_info
import traceback

info_debug_sep = '=============================================================='
warn_error_sep = '--------------------------------------------------------------'


app_logger = None


def log_init(name, file, level):
    logging.basicConfig(filename=file, level=level,
                        format='%(asctime)s %(levelname)-7s %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')


def _log_common(logger_fn, message=None, separator_s=None, exception=False):
    if separator_s:
        logger_fn(separator_s)
    if message:
        logger_fn(message)
    if exception:
        exc_type, exc_value_s, exc_traceback_obj = exc_info()
        exc_traceback_s = repr(traceback.extract_tb(exc_traceback_obj))
        logger_fn(' Exception: %s' % exc_value_s)
        logger_fn(' Traceback: %s' % exc_traceback_s)


def log_error(message=None):
    _log_common(logging.error, message, separator_s=warn_error_sep, exception=True)


def log_warning(message=None):
    _log_common(logging.warning, message, separator_s=warn_error_sep, exception=True)


def log_info(message, separator=False):
    if separator:
        s = info_debug_sep
    else:
        s = None
    _log_common(logging.info, message, separator_s=s, exception=False)


def log_debug(message, separator=False):
    if separator:
        s = info_debug_sep
    else:
        s = None
    _log_common(logging.debug, message, separator_s=s, exception=False)

# EOF

"""
MassOpenCloud / Hardware Isolation Layer (HIL)
User Level Slurm Reservations (ULSR)

ulsr_importpath.py - Set up import path

Jan 2018, Tim Donahue	tdonahue@mit.edu
"""

import inspect
from os.path import realpath, dirname, join
import sys

libdir = realpath(join(dirname(inspect.getfile(inspect.currentframe())), '../common'))
sys.path.append(libdir)

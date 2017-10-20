#!/bin/bash

HOME=/home/slurm
LOGFILE=/var/log/moc_hil_ulsr/hil_monitor.log

source $HOME/scripts/ve/bin/activate
python $HOME/scripts/hil_slurm_monitor.py 2>&1 >> $LOGFILE
deactivate


#!/bin/bash

HOME=/home/centos/user_level_slurm_reservations
LOGFILE=/var/log/moc_hil_ulsr/hil_monitor.log

source $HOME/ve/bin/activate
export PYTHONPATH=$HOME/prolog:$PYTHONPATH
# python $HOME/commands/hil_slurm_monitor.py 2>&1 >> $LOGFILE
python $HOME/commands/hil_slurm_monitor.py
deactivate


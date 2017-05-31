#! /bin/bash

HOME=<set appropriately>
LOGFILE=$HOME/monitor.log

source $HOME/ve/bin/activate
python hil_slurm_monitor.py 2>&1 >> $LOGFILE
deactivate


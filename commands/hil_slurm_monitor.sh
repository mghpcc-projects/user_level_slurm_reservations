#!/usr/bin/env bash
#
# HIL Slurm ULSR Monitor shell script
#
# Runs hil_slurm_monitor.py, intended for invocation by cron(8).
#
# Environment (DO NOT REMOVE THIS LINE)


#
source $HOME/scripts/ve/bin/activate
python $HOME/scripts/hil_slurm_monitor.py 2>&1 >> $LOGFILE
deactivate

exit 0

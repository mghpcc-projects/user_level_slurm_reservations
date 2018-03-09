#!/usr/bin/env bash
#
# HIL Slurm ULSR Monitor shell script
#
# Runs ulsr_monitor.py, intended for invocation by cron(8).
#
# Environment (DO NOT REMOVE THIS LINE)


#
source $HOME/scripts/ve/bin/activate
python $HOME/scripts/ulsr_monitor.py 2>&1 >> $LOGFILE
deactivate

exit 0

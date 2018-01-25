#!/usr/bin/env bash
#
# HIL Slurm ULSR Network Audit shell script
#
# Runs ulsr_audit.py, intended for invocation by cron(8).
#
# Environment (DO NOT REMOVE THIS LINE)


#
source $HOME/scripts/ve/bin/activate
python $HOME/scripts/ulsr_audit.py 2>&1 >> $LOGFILE
deactivate

exit 0

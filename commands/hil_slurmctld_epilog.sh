#!/usr/bin/env bash
#
# HIL Slurmctrld Epilog shell script
#
# Runs hil_slurmctld_prolog.py with --hil_epilog, e.g. as the epilog
# 
# Environment (DO NOT REMOVE THIS LINE)


#
source ${HOME}/scripts/ve/bin/activate
python ${HOME}/scripts/hil_slurmctld_prolog.py --hil_epilog >> $LOGFILE 2>&1
deactivate

exit 0


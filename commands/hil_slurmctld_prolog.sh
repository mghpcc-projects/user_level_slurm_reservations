#!/usr/bin/env bash
#
# HIL Slurmctrld Prolog shell script
#
# Runs hil_slurmctld_prolog.py with --hil_prolog, e.g. as the prolog
# 
# Environment (DO NOT REMOVE THIS LINE)


#
source ${HOME}/scripts/ve/bin/activate
python ${HOME}/scripts/hil_slurmctld_prolog.py --hil_prolog >> $LOGFILE 2>&1
deactivate

exit 0


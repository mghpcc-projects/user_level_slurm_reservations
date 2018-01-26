#!/usr/bin/env bash
#
# ULSR Slurmctrld Epilog shell script
#
# Runs ulsr_slurmctld_prolog.py with --ulsr_epilog, e.g. as the epilog
# 
# Environment (DO NOT REMOVE THIS LINE)


#
source ${HOME}/scripts/ve/bin/activate
python ${HOME}/scripts/ulsr_slurmctld_prolog.py --ulsr_epilog >> $LOGFILE 2>&1
deactivate

exit 0


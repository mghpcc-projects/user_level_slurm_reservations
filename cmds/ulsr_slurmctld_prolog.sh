#!/usr/bin/env bash
#
# ULSR Slurmctrld Prolog shell script
#
# Runs ulsr_slurmctld_prolog.py with --ulsr_prolog, e.g. as the prolog
# 
# Environment (DO NOT REMOVE THIS LINE)


#
source ${HOME}/scripts/ve/bin/activate
python ${HOME}/scripts/ulsr_slurmctld_prolog.py --ulsr_prolog >> $LOGFILE 2>&1
deactivate

exit 0


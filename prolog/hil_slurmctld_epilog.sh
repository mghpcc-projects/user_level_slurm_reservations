#!/bin/bash
#
# HIL Slurmctrld Epilog shell script
#
# Runs hil_slurmctld_prolog.py with --hil_epilog, e.g. as the epilog
#
PATH=/bin:/usr/bin:/usr/local/bin
LOGFILE=/var/log/slurm-llnl/hil_prolog.log
HOME=/home/slurm/scripts

source ${HOME}/../ve/bin/activate
python ${HOME}/hil_slurmctld_prolog.py --hil_epilog >> $LOGFILE 2>&1
deactivate

exit 0


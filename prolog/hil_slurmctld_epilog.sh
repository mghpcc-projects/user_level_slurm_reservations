#!/usr/bin/env bash
#
# HIL Slurmctrld Epilog shell script
#
# Runs hil_slurmctld_prolog.py with --hil_epilog, e.g. as the epilog
#
PATH=/bin:/usr/bin:/usr/local/bin:/usr/local/sbin
LOGFILE=/var/log/moc_hil_ulsr/hil_prolog.log
HOME=/home/slurm

source ${HOME}/scripts/ve/bin/activate
python ${HOME}/scripts/hil_slurmctld_prolog.py --hil_epilog >> $LOGFILE 2>&1
deactivate

exit 0


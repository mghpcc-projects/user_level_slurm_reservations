#!/bin/bash
#
# HIL Slurmctrld Epilog shell script
#
# Runs hil_slurmctld_prolog.py with --hil_epilog, e.g. as the epilog
#
PATH=/bin:/usr/bin
LOGFILE=/var/log/slurm-llnl/hil_prolog.log
HOME=/vagrant/user_level_slurm_reservations

source ${HOME}/../ve/bin/activate
python $HOME/prolog/hil_slurmctld_prolog.py --hil_epilog >> $LOGFILE 2>&1
deactivate

exit 0


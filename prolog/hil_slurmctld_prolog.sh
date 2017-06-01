#!/bin/bash

PATH=/bin:/usr/bin
LOGFILE=/var/log/slurm-llnl/prolog.log
HOME=/vagrant/user_level_slurm_reservations
DATE=`date`

echo "" >> $LOGFILE
echo $DATE >> $LOGFILE
# echo $PATH >> $LOGFILE
# echo $HOME >> $LOGFILE

source ${HOME}/../ve/bin/activate
python $HOME/prolog/hil_slurmctld_prolog.py >> $LOGFILE 2>&1
deactivate

exit 0


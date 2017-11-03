#!/bin/bash
#
# HIL Slurmctrld Master shell script
#
# Runs the prolog, epilog, monitor, or network audit depending
# on the argument passed by the user.
#
PATH=/bin:/usr/bin:/usr/local/bin:/usr/local/sbin
PROLOG_LOGFILE=/var/log/slurm-llnl/hil_prolog.log
MONITOR_LOGFILE=/var/log/slurm-llnl/hil_monitor.log
HOME=/home/slurm

source ${HOME}/scripts/ve/bin/activate
export PYTHONPATH=$HOME/commands:$PYTHONPATH

case $1 in
    "prolog") python ${HOME}/scripts/hil_slurmctld_prolog.py --hil_prolog >> \
            $PROLOG_LOGFILE 2>&1
        ;;
    "epilog") python ${HOME}/scripts/hil_slurmctld_prolog.py --hil_epilog >> \
            $PROLOG_LOGFILE 2>&1
        ;;
    "monitor") python ${HOME}/scripts/hil_slurm_monitor.py 2>&1 >> \
            $MONITOR_LOGFILE
        ;;
    "network") # TODO
        ;;
    *) echo "`basename ${0}`: usage: [-c command: <prolog, epilog, monitor, network>]" 
        exit 1 # Command to come out of the program with status 1
        ;;
esac

deactivate
exit 0

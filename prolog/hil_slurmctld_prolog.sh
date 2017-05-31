#!/bin/bash

PATH=/bin:/usr/bin:$PATH
HOME=/vagrant
LOGFILE=$HOME/output/prolog.log

source $HOME/ve/bin/activate
python $HOME/prolog/slurmctrld_hil_prolog.py 2>&1 >> $LOGFILE
deactivate

# exit 0


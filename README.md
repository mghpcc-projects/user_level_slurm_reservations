# user_level_slurm_reservations
Slurm prolog and epilog stuff that allows certain named partitions to carry out privileged reservation requests

# Configuration Requirements

## Partition Configuration

## SlurmCtld Prolog and Epilog

The SlurmCtld prolog and epilog must be specified:

PrologSlurmctld=/<install_dir>/prolog/hil_slurmctld_prolog.sh
EpilogSlurmctld=/<install_dir>/prolog/hil_slurmctld_epilog.sh

### MaxTime and DefaultTime

The partition MaxTime and DefaultTime must be set so that to values
other than 'INFINITE' or 'UNLIMITED', so that the hil_reserve and
hil_release commands may be run in the partition when other
reservations, starting at future times, exist. 

The following times are arbitrary.

PartitionName=debug Nodes=server[1] Default=YES DefaultTime=00:05:00 MaxTime=06:00:00 State=UP Shared=No

## Logging


# Software Requirements

* python-hostlist

Install python-hostlist 

$ cd /usr/local/lib/python2.7/site-packages
$ wget https://www.nsc.liu.se/~kent/python-hostlist/python-hostlist-1.17.tar.gz
$ tar xvf python-hostlist-1.17.tar.gz
$ cd python-hostlist-1.17
$ python setup.py build
$ python setup.py install



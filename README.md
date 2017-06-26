# MOC HIL Node Reservations

(Also known as 'user_level_slurm_reservations')

V0.1 26-Jun-2017

# Introduction

HIL reservations allow a nonprivileged Slurm user to reserve Slurm
compute nodes for HIL operations.  The nodes may later be released
and returned to the pool of Slurm compute nodes for use by others.

At present, two commands are used to manage HIL reservations:

  * hil_reserve
  * hil_release

These commands are executed as Slurm jobs via srun(1) and sbatch(1).

In future, additional commands may be made available to conduct
low-level HIL node operations.  For example:

  * hil_init - Iniitialize HIL nodes and networking infrastructure to
  desired state
  * hil_restore - Restore a HIL node to the Slurm partition, behaving
  as a Slurm compute node 


## Usage

To reserve a HIL node, specify the ```hil_reserve``` command as a job
to the Slurm srun(1) or sbatch(1) command:

```
$ srun hil_reserve
```

To verify the reservation was created, run the ```scontrol show
reservation``` command:

``` 
$ scontrol show reservation
```

When finished, to release a HIL node, specify the ```hil_release```
command to srun(1) or sbatch(1):

```
$ srun hil_release
```


## Reservation Naming

HIL reservations created using ```hil_reserve``` are named as follows:
```
flexalloc_MOC_<username>_<uid>_<start_time>
```

An example:
```
flexalloc_MOC_ubuntu_1000_2017-06-26T17:20:32
```

## Reservation Verification

## Behavior of a HIL Node in a HIL Reservation

# Assumptions and Restrictions

All nodes in the HIL reservation pool are configured in a single Slurm
partition.  The Slurm controller node in the partition is not
available for HIL operations.




# Configuration Requirements


## Partition Configuration

## SlurmCtld Prolog and Epilog

The SlurmCtld prolog and epilog must be specified:

PrologSlurmctld=/<install_dir>/prolog/hil_slurmctld_prolog.sh
EpilogSlurmctld=/<install_dir>/prolog/hil_slurmctld_epilog.sh

### MaxTime and DefaultTime

The partition MaxTime and DefaultTime must be set so that to values
other than 'INFINITE' or 'UNLIMITED', so that the hil_reserve and (in
particular) hil_release commands are not queued and blocked when other
reservations, starting at future times, exist in the partition and
include the

The illustrated times are arbitrary.

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



# MOC HIL User Level Slurm Reservations (ULSR)

# Installation Guide

V1.0  30-Nov-2017


NOTE: The following assumes Slurm version 15 or greater is installed
and running in the cluster.   For background on Slurm installation
refer to the following links:

  * [How to Install Slurm on CentOS 7 Cluster](https://www.slothparadise.com/how-to-install-slurm-on-centos-7-cluster/)

  * [Slurm on CentOS 7](https://bitsanddragons.wordpress.com/2016/08/22/slurm-on-centos-7/)

The ULSR software is installed in four main steps:

  1. Clone the ULSR repository from GitHub onto the Slurm controller
  node
  2. Customize the installation Makefile, as required
  3. Run ```make install-controller``` on the Slurm controller node
  4. Run ```make install-server``` on each of the Slurm compute server nodes

## Clone the ULSR Repository

First retrieve the ULSR software to the Slurm controller node:
```
[root@slurm-controller ~]# git clone https://github.com/mghpcc-projects/user_level_slurm_reservations.git
```

## Edit Installation Makefile

The ULSR installation Makefile may be customized to align with the
target Slurm cluster configuration and administrative preferences.

The following variables (shown with default settings) may be modified
as necessary.

```
LOCAL_BIN = /usr/local/bin

SLURM_USER=slurm
SLURM_USER_DIR=/home/$SLURM_USER

INSTALL_USER=centos
INSTALL_USER_DIR=/home/$INSTALL_USER

SLURM_CONTROLLER = slurm-controller

NFS_SHARED_DIR = /shared
ULSR_SHARED_DIR = $(NFS_SHARED_DIR)/ulsr

SLURM_CONF_FILE=/etc/slurm/slurm.conf

ULSR_LOGFILE_DIR=/var/log/ulsr

PROLOG_LOGFILE_NAME = ulsr_prolog.log

MONITOR_LOGFILE_NAME = ulsr_monitor.log

AUDIT_LOGFILE_NAME = ulsr_audit.log
```

NOTE: Changes to the Makefile variables above may require changes to
the ```common/ulsr_constants.py``` file to match.  In future, the
installation process may be modified to propagate changes to the
```ulsr_constants.py``` file automatically.


## Install ULSR on the Slurm Controller Node

```
[root@slurm-controller ~]# cd user_level_slurm_reservations
[root@slurm-controller ~]# make install-controller
```

### Slurm Control Daemon Prolog and Epilog Integration

For simplicity, the ULSR installation model assumes there are no other
Slurm control daemon prolog and epilog routines installed.  It may be
necessary to modify an existing Slurm control daemon prolog and
epilog installation hierarchy to additionally invoke the ULSR prolog
and epilog scripts.


## Install ULSR on the Slurm Compute Nodes

### Installation Makefile Transfer to Compute Nodes

During installation of ULSR on the Slurm controller node, the Makefile
will be copied to a directory exported via NFS.  This directory may
then be mounted by the Slurm compute nodes to provide direct access to
the installation Makefile.

Once the shared directory has been mounted, the Makefile may be copied
to a directory local to a compute node and passed as an argument to
```make```, or it may be referenced in place.

Alternatively, the Makefile may be copied to each compute node via
```scp(1)``` or other mechanism and passed to ```make(1)``` from its
destination location.

### Make Invocation

One each compute node, running as the root user, run ```make(1)``` and
pass the ULSR compute server installation target as an argument:

```
[root@slurm-compute1 ~]# cd /shared/ulsr
[root@slurm-compute1 ulsr]# make install-server
```
This will perform the following actions on the compute server:

  * Mount the directory NFS-exported by the Slurm controller ```$(NFS_SHARED_DIR)```
  * Create the Slurm user directory (```/home/$(SLURM_USER)```) and
```scripts``` subdirectory (this may not be necessary)
  * Copy the ```hil_reserve``` and ```hil_release``` commands from the
  NFS shared directory to the ```$(LOCAL_BIN)``` directory
  * Copy the ```slurm.conf``` file from the NFS shared directory to
the $(SLURM_CONF_FILE) directory.

At this point the Slurm compute server should be ready for use with
ULSR.

## HIL ULSR Periodic Monitor and Log File

The ULSR periodic monitor is scheduled as a ```cron(8)``` job on the
Slurm controller node.  The Slurm controller provisioning script
installs the periodic monitor wrapper script
```hil_slurm_monitor.sh``` in the ```$LOCAL_BIN``` directory, which
defaults to ```/usr/local/bin```.  The periodic monitor itself,
```hil_slurm_monitor.py``` is installed in the Slurm user
```scripts``` subdirectory.

After installation the ```crontab``` must be modified to invoke the
wrapper script periodically:
```
*/5 * * * * hil_slurm_monitor.sh
```
The above will invoke the monitor every five minutes.


## SlurmCtld Prolog and Epilog Installation

[UPDATE to reflect coexistence with other Slurm prolog / epilog modules]

If no other Slurm control daemon prolog and/or epilog is in use, the
SlurmCtld prolog and epilog must be specified in the ```slurm.conf``` file:

```
PrologSlurmctld=/<install_dir>/scripts/hil_slurmctld_prolog.sh
EpilogSlurmctld=/<install_dir>/scripts/hil_slurmctld_epilog.sh
```

These lines are added to the default ```slurm.conf``` by the Slurm
controller provisioning script.  The Slurm control daemon must be
restarted after the configuration change:

```
$ systemctl restart slurmctld.service
```

## HIL / ULSR Settings File

The ```common/ulsr_settings.py``` file contains constants used by
the ULSR software.  

### HIL Partition Name Prefix - HIL_PARTITION_PREFIX

The Slurm partition from which HIL nodes are reserved must be named in
a way which begins with the value of ```HIL_PARTITION_PREFIX```.  By
default this is set to:
```
HIL_PARTITION_PREFIX = 'HIL_partition'
```

### HIL Control Endpoint IP Address, User, and Password

```
HIL_ENDPOINT = "http://128.31.28.156:80"
HIL_USER = 'admin'
HIL_PW = <elided, see file>
```

### HIL Loaner Project Name
```
HIL_SLURM_PROJECT = 'slurm'
```

### Slurm Utility Installation Directory

This variable identifies the directory into which ```scontrol``` and
other Slurm commands have been installed prior to installation of the
ULSR software.
```
SLURM_INSTALL_DIR = '/usr/bin'
```

### ULSR Log Files
```
HIL_SLURMCTLD_PROLOG_LOGFILE = '/var/log/ulsr/hil_prolog.log'
HIL_MONITOR_LOGFILE = '/var/log/ulsr/hil_monitor.log'
```

# Other Requirements

## Required Linux Packages

  * Slurm v15 or greater, pre-installed
  * HIL

## Required Python Packages

  * python-hostlist

## Compute Nodes Marked with HIL Feature

Slurm compute nodes which are intended to be placed in a HIL
reservation must be marked in the Slurm cluster configuration as
having the Slurm feature 'HIL'.

## Partition MaxTime and DefaultTime

The partition MaxTime and DefaultTime must be set so that to values
other than 'INFINITE' or 'UNLIMITED'.  Otherwise, the

```hil_reserve``` and ```hil_release``` commands may be queued and
blocked when other reservations, starting at future times, exist in
the partition and include the Slurm compute nodes intended for use by
HIL.

In the following example, the illustrated times are arbitrary.

```
PartitionName=debug Nodes=server[1] Default=YES DefaultTime=00:05:00 MaxTime=06:00:00 State=UP Shared=No
```

## Default Nodes

Might not want a HIL node to be among the partition default nodes.

## Node Sharing and Oversubscription

Must be disabled.


# MOC HIL User Level Slurm Reservations (ULSR)

# Installation Guide

V1.0  30-Nov-2017

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


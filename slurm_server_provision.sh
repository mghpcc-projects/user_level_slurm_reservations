#!/usr/bin/env bash
#
# slurm_sever_provision.sh - SLURM MOC HIL Server VM Provisioning Script
#
# Run on the compute nodes, AFTER the controller is initialized
# Installs Slurm, assumes no prior Slurm installation
#
# Notes
#   Assumes Ubuntu environment (16.04 LTS, YMMV)
#   Run as root on compute server nodes, NOT on controller
#       Controller is provisioned separately
#   NFS kernel server must be provisioned on the controller
#      /slurm is the shared directory, exported via NFS

set -x

# Update the controller and server node addresses in /etc/hosts as appropriate after 
# VM creation

echo "10.0.0.7 controller" >> /etc/hosts
echo "127.0.0.1 `hostname`" >> /etc/hosts

# echo "10.0.0.7 server1" >> /etc/hosts
# echo "10.0.0.10 server2" >> /etc/hosts
# echo "10.0.0.15 server3" >> /etc/hosts
# echo "10.0.0.16 server4" >> /etc/hosts
# echo "10.0.0.11 server5" >> /etc/hosts
# echo "10.0.0.12 server6" >> /etc/hosts

apt-get update
apt-get -y install make
apt-get -y install gcc
apt-get -y install python2.7
ln -s /usr/bin/python2.7 /usr/bin/python
apt-get -y install emacs
apt-get -y install nfs-common
apt-get -y install munge
apt-get -y install libmunge-dev

echo "export SYSTEMD_EDITOR=emacs" >> ~/.bashrc

useradd slurm 

mkdir -p /var/spool/slurmd.spool
chmod 755 /var/spool/slurmd.spool
chown slurm:slurm /var/spool/slurmd.spool

mkdir -p /var/log/slurm-llnl
chmod 755 /var/log/slurm-llnl
chown slurm:slurm /var/log/slurm-llnl

mkdir -p /var/run/slurm-llnl
chmod 755 /var/run/slurm-llnl
chown slurm:slurm /var/run/slurm-llnl

mkdir -p /var/spool/slurmd.spool
chmod 755 /var/spool/slurmd.spool
chown slurm:slurm /var/spool/slurmd.spool

mkdir -p /var/spool/slurm.state
chmod 755 /var/spool/slurm.state
chown slurm:slurm /var/spool/slurm.state

# NFS: Mount shared FS exported by controller

mkdir /shared
chmod 777 /shared
chown nobody:nogroup /shared
mount controller:/shared /shared
echo "controller:/shared /shared nfs rsize=8192,wsize=8192,timeo=14,intr" >> /etc/fstab

# Add Munge system directories and log file
# Copy the Munge key exported by the controller

chmod 700 /etc/munge
chmod 711 /var/lib/munge
chmod 700 /var/log/munge
chmod 755 /var/run/munge

touch /var/log/munge/munged.log
chown munge:munge /var/log/munge/munged.log

cp -p /shared/munge/munge.key /etc/munge
chmod 400 /etc/munge/munge.key

# Create package download directory and download required software

mkdir /opt/packages
cd /opt/packages

wget https://www.gnupg.org/ftp/gcrypt/libgpg-error/libgpg-error-1.27.tar.bz2
tar xvf libgpg-error-1.27.tar.bz2
cd libgpg-error-1.27
./configure
make install

cd /opt/packages

wget https://www.gnupg.org/ftp/gcrypt/libgcrypt/libgcrypt-1.7.8.tar.bz2
tar xvf libgcrypt-1.7.8.tar.bz2
cd libgcrypt-1.7.8
./configure
make install

cd /opt/packages

wget https://github.com/SchedMD/slurm/archive/slurm-17-02-6-1.tar.gz
tar xvf slurm-17-02-6-1.tar.gz
cd slurm-slurm-17-02-6-1
./configure
make install

# Python Hostlist

cd /usr/local/lib/python2.7/site-packages
wget https://www.nsc.liu.se/~kent/python-hostlist/python-hostlist-1.17.tar.gz
tar xvf python-hostlist-1.17.tar.gz
cd python-hostlist-1.17
python setup.py build
python setup.py install

cd /opt/packages

# Start Munge daemon

/etc/init.d/munge start

# Get Slurm config file from controller

cp -p /shared/slurm/slurm.conf /usr/local/etc/slurm.conf
chown slurm:slurm /usr/local/etc/slurm.conf

# Create Slurm directory for reference by slurmd

mkdir -p /home/slurm/bin
mkdir -p /home/slurm/scripts
chown -R slurm:slurm /home/slurm

# Start Slurmd

/usr/local/sbin/slurmd

# Cleanup

rm -f /opt/packages/*.gz
rm -f /opt/packages/*.bz2

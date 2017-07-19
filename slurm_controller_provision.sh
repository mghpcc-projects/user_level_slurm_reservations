#!/usr/bin/env bash
#
# slurm_controller_provision.sh - SLURM MOC Controller VM Provisioning Script
#
# Run on the Slurm controller node
#
# Notes
#   Assumes Ubuntu environment (16.04 LTS, YMMV)
#   Run as root on controller node, NOT on server nodes
#   NFS kernel server must be provisioned on the controller
#      /slurm is the shared directory, exported via NFS

set -x

echo "127.0.0.1 `hostname`" >> /etc/hosts

# Update the server node list and addresses as appropriate

echo "10.0.0.5 server1" >> /etc/hosts
echo "10.0.0.10 server2" >> /etc/hosts
echo "10.0.0.15 server3" >> /etc/hosts
echo "10.0.0.16 server4" >> /etc/hosts
echo "10.0.0.11 server5" >> /etc/hosts
echo "10.0.0.12 server6" >> /etc/hosts

apt-get update
apt-get -y install make
apt-get -y install gcc
apt-get -y install python2.7
ln -s /usr/bin/python2.7 /usr/bin/python
apt-get -y install emacs
apt-get -y install nfs-common
apt-get -y install nfs-kernel-server
apt-get -y install munge
apt-get -y install libmunge-dev
apt-get -y install virtualenv

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

chmod 700 /etc/munge
chmod 711 /var/lib/munge
chmod 700 /var/log/munge
chmod 755 /var/run/munge
echo "massopencloudajointprojectamonghubuniversities" > /etc/munge/munge.key
chmod 400 /etc/munge/munge.key

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
cd /opt/packages

# MOC User Level Slurm Reservations - 
#
# This needs to be accessible via a public repo
#
# wget https://github.com/mghpcc-projects/user_level_slurm_reservations/archive/v0.0.2.tar.gz
# tar xvf v0.0.2.tar.gz

cd /opt/packages

# NFS

mkdir /shared
chmod 777 /shared
chown nobody:nogroup /shared
sudo systemctl enable nfs-kernel-server

echo "/shared *(rw,sync,no_root_squash)" >> /etc/exports
exportfs -a

mkdir /shared/slurm
chmod 755 /shared/slurm
chown slurm:slurm /shared/slurm

mkdir /shared/munge
chmod 700 /shared/munge
chown munge:munge /shared/munge

cp /etc/munge/munge.key /shared/munge
chmod 400 /shared/munge/munge.key

touch /var/log/munge/munged.log
chown root:root /var/log/munge/munged.log

# Munge again

/etc/init.d/munge start

# HIL

mkdir /shared/hil
chmod 755 /shared/hil
cd /shared/hil
virtualenv -p python2.7 ve
source ve/bin/activate

git clone https://github.com/mghpcc-project/user_level_slurm_reservations.git
cp -p /shared/hil/user_level_slurm_reservations/test/slurm.conf /usr/local/etc/slurm.conf
chown slurm:slurm /usr/local/etc/slurm/slurm.conf

chown -R slurm:slurm /shared/hil

# Slurm Daemon

systemctl enable slurmctld

# Cleanup

rm -f /opt/packages/*.gz
rm -f /opt/packages/*.bz2

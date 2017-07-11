#!bash
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

echo "10.0.0.7 server1" >> /etc/hosts
echo "10.0.0.10 server2" >> /etc/hosts
echo "10.0.0.15 server3" >> /etc/hosts
echo "10.0.0.16 server4" >> /etc/hosts
echo "10.0.0.11 server5" >> /etc/hosts
echo "10.0.0.12 server6" >> /etc/hosts

apt-get -y install make
apt-get -y install gcc
apt-get -y install python2.7
ln -s /usr/bin/python2.7 /usr/bin/python
apt-get -y install emacs
apt-get -y install nfs-common
apt-get -y install nfs-kernel-server
apg-get -y install munge

chmod 700 /etc/munge
chmod 711 /var/lib/munge
chmod 700 /var/log/munge
chmod 755 /var/run/munge
echo "massopencloud" > /etc/munge/munge.key
chmod 400 /etc/munge/munge.key

cd 
mkdir packages
cd packages

wget https://www.gnupg.org/ftp/gcrypt/libgpg-error/libgpg-error-1.27.tar.bz2
tar xvf libgpg-error-1.27.tar.bz2
cd libgpg-error-1.27
./configure
make install
cd 
cd packages

wget https://www.gnupg.org/ftp/gcrypt/libgcrypt/libgcrypt-1.7.8.tar.bz2
tar xvf libgcrypt-1.7.8.tar.bz2
cd libgcrypt-1.7.8
./configure
make install
cd 
cd packages

wget https://github.com/SchedMD/slurm/archive/slurm-17-02-6-1.tar.gz
tar xvf slurm-17-02-6-1.tar.gz
cd slurm-slurm-17-02-6-1
./configure
make install

cd 
cd packages

# NFS

mkdir -p /slurm
chmod 777 /slurm
chown nobody:nogroup /slurm
sudo systemctl enable nfs-kernel-server

echo "/slurm *(rw,sync,no_root_squash)" >> /etc/exports
exportfs -a

# Munge again

/etc/init.d/munge start

# Slurm Daemon

systemctl enable slurmctld



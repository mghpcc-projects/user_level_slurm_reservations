# -*- mode: ruby -*-
# vi: set ft=ruby :

# All Vagrant configuration is done below. The "2" in Vagrant.configure
# configures the configuration version (we support older styles for
# backwards compatibility). Please don't change it unless you know what
# you're doing.

slurm_cluster = {
  :controller => {
    :hostname => "controller",
    :ipaddress => "10.10.10.3"
  },
  :server1 => {
    :hostname => "server1",
    :ipaddress => "10.10.10.4"
  }
}
  
Vagrant.configure("2") do |global_config|
    slurm_cluster.each_pair do |name, options|
      global_config.vm.define name do |config|
        config.vm.box = "ubuntu/xenial64"
        config.vm.box_url = "ubuntu/xenial64"
        config.vm.hostname = "#{name}"

        config.vm.network :private_network, ip: options[:ipaddress]

        config.vm.provider :virtualbox do |v|
          v.customize ["modifyvm", :id, "--memory", 512]
          v.customize ["modifyvm", :id, "--name", "#{name}"]
        end

        config.vm.provision :shell, :inline=> <<SHELL
#           apt-get update
	    apt-get install -y -q emacs24
	    echo "10.10.10.3    controller" >> /etc/hosts
	    echo "10.10.10.4    server1" >> /etc/hosts
	    echo "export SYSTEMD_EDITOR=emacs" > /.bashrc
#	    cp /vagrant/test/slurm.conf /tmp
#	    cp /tmp/slurm.conf /etc/slurm-llnl
	    mkdir /var/log/slurm-llnl
            mkdir /var/run/slurm-llnl
            mkdir -p /var/spool/slurmd.spool
SHELL
        end
    end
end

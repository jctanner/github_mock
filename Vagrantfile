# -*- mode: ruby -*-
# vi: set ft=ruby :

# All Vagrant configuration is done below. The "2" in Vagrant.configure
# configures the configuration version (we support older styles for
# backwards compatibility). Please don't change it unless you know what
# you're doing.
Vagrant.configure("2") do |config|

  config.vm.synced_folder ".", "/vagrant", type: "nfs", nfs_udp: false

  config.vm.define "gmock" do |dev|
    dev.vm.box = "generic/debian12"
    dev.vm.hostname = "gmock"

    dev.vm.provider :libvirt do |libvirt|
      libvirt.cpus = 2
      libvirt.memory = 1000
      libvirt.machine_virtual_size = 20
    end

  end

  config.vm.provision "shell", inline: <<-SHELL
       export DEBIAN_FRONTEND=noninteractive
       apt -y update
       #apt -y upgrade
       apt -y install git jq python3-pip docker.io libpq-dev python3-virtualenv
  SHELL

end

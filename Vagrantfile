# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure("2") do |config|
    config.vm.box = "ubuntu_14.04"
    config.vm.box_url = "http://github.com/kraksoft/vagrant-box-ubuntu/releases/download/14.04/ubuntu-14.04-amd64.box"
    config.vm.provider "virtualbox" do |custom_virtualbox_settings|
      custom_virtualbox_settings.name = "BLT_BOX"
    end

    config.vm.network "private_network", ip: "192.168.1.2"
    config.vm.network :forwarded_port, guest: 8000, host: 8000
    config.vm.synced_folder "", "/home/vagrant/BLT"   
    config.vm.provision :shell, :path => "vagrant/setup.sh"

end


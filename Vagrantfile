# -*- mode: ruby -*-
# vi: set ft=ruby :

require 'socket'
require 'yaml'
require 'etc'

#unless Vagrant.has_plugin?("vagrant-aws")
#    raise 'vagrant-aws plugin is not installed. Please install using vagrant plugin install vagrant-aws'
#end

# load the vagrant-user.yml
hostname = Socket.gethostname
username = Etc.getlogin
user_settings = YAML.load_file 'vagrant-user.yml'
user_settings = user_settings.has_key?(hostname) ? user_settings[hostname] : {}

Vagrant.configure("2") do |config|
  # https://app.vagrantup.com/boxes/search?utf8=%E2%9C%93&sort=downloads&provider=&q=bento
  config.vm.box = "bento/ubuntu-16.04"

  # public network is akin to 'bridged'
  config.vm.network "public_network",
    ip: user_settings.fetch("static-ip", nil),
    bridge: user_settings.fetch("bridge-network", nil)

    config.vm.provider "virtualbox" do |vbox, override|
      vbox.memory = "4096"
      vbox.cpus = "4"

      # ansible executes on host
      override.vm.provision "ansible" do |ansible|
        ansible.compatibility_mode = "2.0"
        ansible.playbook = "./provisioning/bootstrap.yml"
        ansible.raw_arguments = ['--timeout=30']
      end

      override.vm.provision "shell",
        run: "always",
        inline: <<-SHELL
          echo "Discussion Capture VM available at 'public' IP:"
          ifconfig eth1 | grep 'inet addr' | cut -d: -f2 | awk '{print $1}'
          echo "Don't forget to create an application user: 'source /var/lib/chemistry-dashboard/server/venv/bin/activate && python3 /var/lib/chemistry-dashboard/server/create_user.py'"
        SHELL
    end
  end

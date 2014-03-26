# -*- mode: ruby -*-
# vi: set ft=ruby :

# Vagrantfile API/syntax version. Don't touch unless you know what you're doing!
VAGRANTFILE_API_VERSION = "2"

Vagrant.configure(VAGRANTFILE_API_VERSION) do |config|

  # Every Vagrant virtual environment requires a box to build off of.
  config.vm.box = "precise32"

  # The url from where the 'config.vm.box' box will be fetched if it
  # doesn't already exist on the user's system.
  config.vm.box_url = "http://files.vagrantup.com/precise32.box"

  # Create a forwarded port mapping which allows access to a specific port
  # within the machine from a port on the host machine. 
  config.vm.network :forwarded_port, guest: 8000, host: 8000


  # Share devops folder with guest VM. VirtualBox mounts shares with
  # all files as executable by default, which causes Ansible to try
  # and execute inventory files (even when they are not scripts.) The
  # mount options below prevent this.
  config.vm.synced_folder './devops', '/vagrant/devops', 
      :mount_options => ['fmode=666']

  # Bootstrap provisioning with the shell. (Installs Ansible, then
  # invokes our configuration playbook). Vagrant has a built-in
  # Ansible provisioner, but it won't work with Windows hosts.
  config.vm.provision :shell, :path => "devops/vagrant_bootstrap.sh"

  # TODO: create an Ansible provisioner that targets Linux hosts. 


end

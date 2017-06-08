#!/usr/bin/env bash

echo "---------------------------------------------"
echo "Configuring BLT Development Environment"
echo "---------------------------------------------"

if [ "$(whoami)" != "root" ]; then
    exit 1
fi

apt-get update
apt-get install -y libpq-dev python-dev

apt-get install -y git-core
apt-get install -y python-pip

sudo apt-get install $(grep -vE "^\s*#" /home/vagrant/BLT/vagrant/requirements.txt | tr "\n" " ")
sudo pip install -r "/home/vagrant/BLT/requirements.txt"

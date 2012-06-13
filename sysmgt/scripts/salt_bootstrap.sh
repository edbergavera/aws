#!/bin/bash

# Install saltstack
add-apt-repository ppa:saltstack/salt -y
apt-get update -y
apt-get install salt-minion -y
apt-get upgrade -y

# Set salt master location and start minion
cp /etc/salt/minion.template /etc/salt/minion
sed -i -e 's/#master: salt/master: web.linuxd.org/' /etc/salt/minion
salt-minion -d

# Install Amazon SES scripts for email purposes
#wget -q

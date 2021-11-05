#!/bin/bash
iptables -A INPUT -p tcp --destination-port 8080 -j DROP
mkdir /var/www-folder/
cd /var/www-folder/
git clone https://github.com/mianabdullah340/image-text-placer.git
cd image-text-placer
sudo apt-get update
apt install python3-pip
pip3 install -r requirements.txt
apt-get install nginx
sudo apt install redis-server
cp default /etc/nginx/sites-enabled/
apt-get install supervisor
cp celery.conf /etc/supervisor/conf.d/
service nginx reload
sudo reboot
#!/bin/bash

sudo systemctl stop dom_$1
sudo systemctl stop server_$1
sudo systemctl disable dom_$1
sudo systemctl disable server_$1
sudo rm /etc/systemd/system/dom_${1}.service
sudo rm /etc/systemd/system/server_${1}.service
sudo rm /etc/nginx/sites-available/$1.conf
sudo rm /etc/nginx/sites-enabled/$1.conf
sudo rm -rf ~/servers/$1
sudo nginx -s reload

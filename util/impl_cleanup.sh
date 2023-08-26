#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

sudo systemctl stop dom_$1
sudo systemctl stop server_$1
sudo systemctl disable dom_$1
sudo systemctl disable server_$1
sudo rm /etc/systemd/system/dom_${1}.service
sudo rm /etc/systemd/system/server_${1}.service
sudo rm -rf ~/servers/$1
sudo nginx -s reload
sps-client application delete --name $1
sudo -E python3 freeport.py $1
sudo systemctl daemon-reload

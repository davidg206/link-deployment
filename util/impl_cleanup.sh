#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

if [ -f "/etc/systemd/system/server_$1" ]; then
  sudo systemctl stop server_$1
  sleep 2
  sudo systemctl disable server_$1
  sudo rm /etc/systemd/system/server_${1}.service
fi

if [ -d "~/servers/$1" ]; then
  sudo rm -rf ~/servers/$1
fi

if [ -f "/etc/nginx/sites-available/$1.app" ]; then
  sudo rm /etc/nginx/sites-available/$1.app /etc/nginx/sites-enabled/$1.app
  sudo nginx -s reload
fi

sps-client application delete --name $1
sudo -E python3 freeport.py $1
sudo systemctl daemon-reload

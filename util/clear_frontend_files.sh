#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

if [ -f "/etc/systemd/system/dom_${1}.service" ]; then
  sudo systemctl stop dom_$1
  sudo systemctl disable dom_$1
  sudo rm /etc/systemd/system/dom_${1}.service
fi
sudo systemctl daemon-reload
#if [ -f "/etc/nginx/sites-available/$1.conf" ]; then
  #sudo rm "/etc/nginx/sites-available/$1.conf"
  #sudo rm "/etc/nginx/sites-enabled/$1.conf"
#fi

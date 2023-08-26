#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

sudo systemctl stop dom_$1
sudo systemctl disable dom_$1
sudo rm /etc/systemd/system/dom_${1}.service
sudo systemctl daemon-reload
if [ -f "/etc/nginx/sites-available/$1.conf" ]; then
  rm "/etc/nginx/sites-available/$1.conf"
  rm "/etc/nginx/sites-enabled/$1.conf"

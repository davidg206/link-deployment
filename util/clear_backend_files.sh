#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

if [ -f "/etc/systemd/system/server_${1}.service" ]; then
  sudo systemctl stop server_$1
  sudo systemctl disable server_$1
  sudo rm /etc/systemd/system/server_${1}.service
fi
sudo systemctl daemon-reload

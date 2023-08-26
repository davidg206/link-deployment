import subprocess
import datetime
import socket
import sys
import os
import re
from portlookup.portlookup import find_available_port, find_available_port_range, find_dedicated_server_port
from dotenv import load_dotenv, dotenv_values

def has_location_block(file_path, search_string):
  return os.path.exists(file_path)

def find_port_for_location(file_path, search_string):
  try:
    with open(file_path, 'r') as file:
      content = file.read()

    port_pattern = r'proxy_pass http://localhost:(\d+);'

    matches = re.search(port_pattern, content)

    if matches:
      return int(matches.group(1))

    return None
  except Exception as e:
    print(f"An error occurred: {e}")
    return None

def get_app_info(branch):
  config_file_path = f'/etc/nginx/sites-available/{branch}.app'
  values = dotenv_values('/home/david/Palatial-Web-Loading/.env')

  webport = find_port_for_location(config_file_path, branch)
  dserverport = values.get(f'REACT_APP_DEDICATED_SERVER_PORT_{branch.upper()}')

  return f"""
{{
  branch: {branch},
  url: https://{branch}.palatialxr.com/,
  webServerPort: {webport},
  dedicatedServerPort: {dserverport},
  unrealWebsocketEndpoint: wss://sps.tenant-palatial-platform.lga1.ingress.coreweave.cloud/{branch}/ws,
}}
"""

def setup_application_site(branch, log=False):
  file_path = f'/etc/nginx/sites-available/{branch}.app'
  dedicated_server_port = None

  if has_location_block(file_path, branch):
    return get_app_info(branch)

  new_location_block = f"""
  location = / {{
    proxy_pass http://localhost:3000;
  }}
"""

  new_server_block = f"""
server {{
  listen 443 ssl;
  server_name {branch}.palatialxr.com;

  ssl_certificate /etc/letsencrypt/live/{branch}.palatialxr.com/fullchain.pem;
  ssl_certificate_key /etc/letsencrypt/live/{branch}.palatialxr.com/privkey.pem;

  root /home/david/Palatial-Web-Loading/;
  index index.html;

  location ~ ^/static/ {{
    proxy_pass http://localhost:3000;
  }}

  {new_location_block}
}}
"""

  if not os.path.exists(file_path):
    if not os.path.exists(f'/etc/letsencrypt/renewal/{branch}.palatialxr.com.app'):
      make_certificate = ['sudo', 'certbot', 'certonly', '-d', f'{branch}.palatialxr.com', '--nginx']
      subprocess.run(make_certificate, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, text=True)

    with open(file_path, 'w') as file:
      file.write(new_server_block)

    subprocess.check_output(['sudo', 'ln', '-s', f'/etc/nginx/sites-available/{branch}.app', '/etc/nginx/sites-enabled/'])

  reload = ['sudo', 'nginx', '-s', 'reload']
  subprocess.run(reload)

  # Set up web service file
  file_path = f'/etc/systemd/system/dom_{branch}.service'

  # Make dedicated server first to get the port number
  setup_dedicated_server(branch)

  return get_app_info(branch)

def setup_dedicated_server(branch):
  file_path = f'/etc/systemd/system/server_{branch}.service'
  env_vars = dotenv_values('/home/david/Palatial-Web-Loading/.env')

  if not os.path.exists(file_path):
    dedicated_server_port = find_dedicated_server_port(branch, env_vars)
    subprocess.run(['sudo', 'ufw', 'allow', f'{dedicated_server_port}/udp'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, text=True)

    service_file = f"""
[Unit]
Description=Dedicated server for {branch}
After=network.target

[Service]
User=david
WorkingDirectory=/home/david/servers/{branch}/LinuxServer/
ExecStart=/bin/bash -c 'chmod +x ThirdTurn_TemplateServer.sh && ./ThirdTurn_TemplateServer.sh -port={dedicated_server_port}'
Restart=always

[Install]
WantedBy=multi-user.target
"""

    with open(file_path, 'w') as file:
      file.write(service_file)

    subprocess.run(['sudo', 'systemctl', 'daemon-reload'])
    subprocess.run(['sudo', 'systemctl', 'enable', f'server_{branch}'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, text=True)
    subprocess.run(['sudo', 'systemctl', 'start', f'server_{branch}'])

  return env_vars['REACT_APP_DEDICATED_SERVER_PORT_' + branch.upper()]

if __name__ == "__main__":
  if len(sys.argv) < 2:
    print('python run_pipeline.py <branch>')
    sys.exit(1)

  branch = sys.argv[1]

  print(setup_application_site(branch))
  sys.exit(0)

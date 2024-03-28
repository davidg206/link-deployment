import subprocess
import datetime
import socket
import sys
import os
import re
import json
from portlookup import portlookup
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
  values = dotenv_values('/home/david/palatial-web-loading/.env')

  webport = find_port_for_location(config_file_path, branch)
  dserverport = values.get(f'REACT_APP_DEDICATED_SERVER_PORT_{branch.upper()}')

  return {
   "branch": branch,
   "url": f"https://{branch}.palatialxr.com/",
   "webServerPort": webport,
   "dedicatedServerPort": dserverport,
   "unrealWebsocketEndpoint": f"wss://sps.tenant-palatial-platform.lga1.ingress.coreweave.cloud/{branch}/ws",
  }

def setup_application_site(branch, log=False):
  file_path = f'/etc/nginx/sites-available/{branch}.app'

  setup_dedicated_server(branch)

  if not has_location_block(file_path, branch):
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

  root /home/david/palatial-web-loading/;
  index index.html;

  location ~ ^/static/ {{
    proxy_pass http://localhost:3000;
  }}

  {new_location_block}
}}
"""

    if not os.path.exists(file_path):
      if not os.path.exists(f'/etc/letsencrypt/renewal/{branch}.palatialxr.com.conf'):
        make_certificate = ['sudo', 'certbot', 'certonly', '-d', f'{branch}.palatialxr.com', '--nginx']
        subprocess.run(make_certificate, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

      with open(file_path, 'w') as file:
        file.write(new_server_block)

      subprocess.run(['sudo', 'ln', '-s', f'/etc/nginx/sites-available/{branch}.app', '/etc/nginx/sites-enabled/'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    reload = ['sudo', 'nginx', '-s', 'reload']
    subprocess.run(reload, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

  return json.dumps(get_app_info(branch), indent=2)

def setup_dedicated_server(branch):
  file_path = f'/etc/systemd/system/server_{branch}.service'

  if os.path.exists(file_path):
    return

  env_path = '/home/david/palatial-web-loading/.env'
  values = dotenv_values(env_path)
  key = 'REACT_APP_DEDICATED_SERVER_PORT_' + branch.upper()

  dedicated_server_port = portlookup.find_dedicated_server_port(values)

  values[key] = str(dedicated_server_port)
  portlookup.reload_env_file(env_path, values)

  subprocess.run(['sudo', 'ufw', 'allow', f'{dedicated_server_port}/udp'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

  service_file = f"""
[Unit]
Description=Dedicated server for {branch}
After=network.target

[Service]
User=david
WorkingDirectory=/home/david/servers/{branch}/LinuxServer/
ExecStart=/bin/bash -c 'chmod +x ThirdTurn_TemplateServer.sh && ./ThirdTurn_TemplateServer.sh -port={dedicated_server_port}'
Restart=on-success

[Install]
WantedBy=multi-user.target
"""

  with open(file_path, 'w') as file:
    file.write(service_file)

  subprocess.run(['sudo', 'systemctl', 'daemon-reload'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
  subprocess.run(['sudo', 'systemctl', 'enable', f'server_{branch}'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
  subprocess.run(['sudo', 'systemctl', 'start', f'server_{branch}'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

  # When a new environment variable has been made the project needs to be rebuilt to load them in
  path = os.path.expanduser("~/palatial-web-loading/")
  os.chdir(path)
  subprocess.run(['npm', 'run', 'build'], stdout=subprocess.PIPE)

if __name__ == "__main__":
  if len(sys.argv) < 2:
    print('python run_pipeline.py <branch>')
    sys.exit(1)

  branch = sys.argv[1]

  print(setup_application_site(branch))
  sys.exit(0)

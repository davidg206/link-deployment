import subprocess
import datetime
import socket
import sys
import os
import re
from portlookup.portlookup import find_available_port, find_available_port_range, find_dedicated_server_port
from dotenv import load_dotenv, dotenv_values

def has_location_block(file_path, search_string):
  if not os.path.exists(file_path):
    return False
  with open(file_path, 'r') as file:
    for line in file:
      if f"location /{search_string}" in line:
        return True
  return False

def find_port_for_location(file_path, search_string):
  try:
    with open(file_path, 'r') as file:
      content = file.read()

    pattern = r"location\s+=\s+(/[^{\s]+)\s*{[^}]+proxy_pass\s+http://localhost:(\d+);"

    matches = re.findall(pattern, content)
    for location, port in matches:
      if location[1:] == search_string:
        return port
    return None
  except Exception as e:
    print(f"An error occurred: {e}")
    return None

def get_app_info(branch, application):
  config_file_path = f'/etc/nginx/sites-available/{branch}.branch'
  values = dotenv_values('/home/david/Palatial-Web-Loading/.env')

  webport = find_port_for_location(config_file_path, application)
  dserverport = values.get(f'REACT_APP_DEDICATED_SERVER_PORT_{application.upper()}')

  return f"""
{{
  branch: {branch},
  application: {application},
  url: https://{branch}.palatialxr.com/{application},
  webServerPort: {webport},
  dedicatedServerPort: {dserverport},
  unrealWebsocketEndpoint: wss://sps.tenant-palatial-platform.lga1.ingress.coreweave.cloud/{application}/ws,
}}
"""

def setup_application_site(branch, application, log=False):
  file_path = f'/etc/nginx/sites-available/{branch}.branch'
  dedicated_server_port = None

  if has_location_block(file_path, application):
    return get_app_info(branch, application)

  new_location_block = f"""
  location = /{application} {{
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

  location = / {{
    return 404;
  }}

  location ~ ^/static/ {{
    proxy_pass http://localhost:3000;
  }}

  {new_location_block}
}}
"""

  if os.path.exists(file_path):
    with open(file_path, 'r') as file:
      content = file.read()

    # Find the position of the last '}' character in the content
    last_brace_position = content.rfind('}')

    if last_brace_position != -1:
      # Insert the text before the last '}' character
      updated_content = content[:last_brace_position] + new_location_block + content[last_brace_position:]

      with open(file_path, 'w') as file:
        file.write(updated_content)
  else:
    if not os.path.exists(f'/etc/letsencrypt/renewal/{branch}.palatialxr.com.branch'):
      make_certificate = ['sudo', 'certbot', 'certonly', '-d', f'{branch}.palatialxr.com', '--nginx']
      subprocess.run(make_certificate, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    with open(file_path, 'w') as file:
      file.write(new_server_block)

    subprocess.check_output(['sudo', 'ln', '-s', f'/etc/nginx/sites-available/{branch}.branch', '/etc/nginx/sites-enabled/'])

  reload = ['sudo', 'nginx', '-s', 'reload']
  subprocess.run(reload)

  return get_app_info(branch, application)

def setup_dedicated_server(application):
  file_path = f'/etc/systemd/system/server_{application}.service'
  values = dotenv_values('/home/david/Palatial-Web-Loading/.env')

  if not os.path.exists(file_path):
    dedicated_server_port = find_dedicated_server_port(application, values)
    subprocess.run(['sudo', 'ufw', 'allow', f'{dedicated_server_port}/udp'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    service_file = f"""
[Unit]
Description=Dedicated server for {application}
After=network.target

[Service]
User=david
WorkingDirectory=/home/david/servers/{application}/LinuxServer/
ExecStart=/bin/bash -c 'chmod +x ThirdTurn_TemplateServer.sh && ./ThirdTurn_TemplateServer.sh -port={dedicated_server_port}'
Restart=always

[Install]
WantedBy=multi-user.target
"""

    with open(file_path, 'w') as file:
      file.write(service_file)

    subprocess.run(['sudo', 'systemctl', 'daemon-reload'])
    subprocess.run(['sudo', 'systemctl', 'enable', f'server_{application}'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    subprocess.run(['sudo', 'systemctl', 'start', f'server_{application}'])

  return values['REACT_APP_DEDICATED_SERVER_PORT_' + application.upper()]

if __name__ == "__main__":
  if len(sys.argv) < 3:
    print('python run_pipeline.py <branch> <application>')
    sys.exit(1)

  branch = sys.argv[1]
  application = sys.argv[2]

  output = setup_application_site(branch, application)

  path = os.path.expanduser("~/Palatial-Web-Loading/")
  os.chdir(path)
  subprocess.run(['npm', 'run', 'build'], stdout=subprocess.PIPE)

  print(output)
  sys.exit(0)

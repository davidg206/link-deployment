import subprocess
import datetime
import socket
import sys
import os
import re
import json
from portlookup import portlookup
from dotenv import dotenv_values

def has_location_block(file_path, search_string, is_domain):
  if not os.path.exists(file_path):
    return False
  if not is_domain:
    return True

  with open(file_path, 'r') as file:
    for line in file:
      if f"location = /{search_string}" in line:
        return True
  return False

def get_app_info(branch, app, is_domain):
  ext = 'branch' if is_domain else 'app'

  config_file_path = f'/etc/nginx/sites-available/{app}.{ext}'
  values = dotenv_values('/home/david/Palatial-Web-Loading/.env')

  dserverport = values.get(f'REACT_APP_DEDICATED_SERVER_PORT_{app.upper()}')

  return {
    "branch": "n/a" if not is_domain else branch,
    "application": app,
    "url": f"https://{branch}.palatialxr.com/{'' if not is_domain else app}",
    "webServerPort": 3000,
    "dedicatedServerPort": dserverport,
    "unrealWebsocketEndpoint": f"wss://sps.tenant-palatial-platform.lga1.ingress.coreweave.cloud/{app}/ws",
  }

def setup_application_site(config, is_domain=False):
  branch = config.get("branch")
  application = config.get("application")

  if is_domain:
    (ext, app) = ('branch', application)
  else:
    (ext, app) = ('app', branch)

  setup_dedicated_server(app)

  file_path = f'/etc/nginx/sites-available/{branch}.{ext}'

  if not has_location_block(file_path, app, is_domain):
    new_location_block = f"""
    location = /{application} {{
      proxy_pass http://localhost:3000;
    }}
""" if is_domain else """
  location = / {
    proxy_pass http://localhost:3000;
  }
"""

    new_server_block = f"""
server {{
  listen 443 ssl;
  server_name {branch}.palatialxr.com;

  ssl_certificate /etc/letsencrypt/live/{branch}.palatialxr.com/fullchain.pem;
  ssl_certificate_key /etc/letsencrypt/live/{branch}.palatialxr.com/privkey.pem;

  root /home/david/Palatial-Web-Loading/;
  index index.html;
""" + ("""
  location = / {
    return 404;
  }
""" if is_domain else "") + f"""
  location ~ ^/static/ {{
    proxy_pass http://localhost:3000;
  }}

  {new_location_block}
}}
"""

    if os.path.exists(file_path):
      if is_domain:
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
      if not os.path.exists(f'/etc/letsencrypt/renewal/{branch}.palatialxr.com.conf'):
        make_certificate = ['sudo', 'certbot', 'certonly', '-d', f'{branch}.palatialxr.com', '--nginx']
        subprocess.run(make_certificate, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

      with open(file_path, 'w') as file:
        file.write(new_server_block)

      subprocess.run(['sudo', 'ln', '-s', f'/etc/nginx/sites-available/{branch}.{ext}', '/etc/nginx/sites-enabled/'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    reload = ['sudo', 'nginx', '-s', 'reload']
    subprocess.run(reload, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

  return json.dumps(get_app_info(branch, app, is_domain), indent=2)

def setup_dedicated_server(application):
  file_path = f'/etc/systemd/system/server_{application}.service'

  if os.path.exists(file_path):
    return

  env_path = '/home/david/Palatial-Web-Loading/.env'
  values = dotenv_values(env_path)
  key = 'REACT_APP_DEDICATED_SERVER_PORT_' + application.upper()

  dedicated_server_port = portlookup.find_dedicated_server_port(values)

  values[key] = str(dedicated_server_port)
  portlookup.reload_env_file(env_path, values)

  subprocess.run(['sudo', 'ufw', 'allow', f'{dedicated_server_port}/udp'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

  service_file = f"""[Unit]
Description=Dedicated server for {application}
After=network.target

[Service]
User=david
WorkingDirectory=/home/david/servers/{application}/LinuxServer/
ExecStart=/bin/bash -c 'chmod +x ThirdTurn_TemplateServer.sh && ./ThirdTurn_TemplateServer.sh -port={dedicated_server_port}'
Restart=on-success

[Install]
WantedBy=multi-user.target
"""

  with open(file_path, 'w') as file:
    file.write(service_file)

  subprocess.run(['sudo', 'systemctl', 'daemon-reload'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
  subprocess.run(['sudo', 'systemctl', 'enable', f'server_{application}'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
  if os.path.exists(f'/home/david/servers/{application}/LinuxServer'):
    subprocess.run(['sudo', 'systemctl', 'start', f'server_{application}'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

  # When a new environment variable has been made the project needs to be rebuilt to load them in
  path = os.path.expanduser("~/Palatial-Web-Loading/")
  os.chdir(path)
  subprocess.run(['npm', 'run', 'build'], stdout=subprocess.PIPE)

if __name__ == "__main__":
  if len(sys.argv) < 2:
    print('python run_pipeline.py <branch [application] or application>')
    sys.exit(1)

  config = {}

  config["branch"] = sys.argv[1]
  if len(sys.argv) == 3:
    config["application"] = sys.argv[2]

  output = setup_application_site(config, is_domain=config.get('application') != None)

  print(output)
  sys.exit(0)


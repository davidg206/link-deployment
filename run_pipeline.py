import subprocess
import datetime
import socket
import sys
import os
import re
import json
import string
from portlookup import portlookup
from dotenv import dotenv_values
from urllib.parse import urlparse

def clean_string(input_string):
    cleaned_string = input_string.replace("'", "")
    cleaned_string = input_string.replace("_", "-")
    cleaned_string = "-".join(cleaned_string.split())
    return cleaned_string

def has_location_block(file_path, search_string, is_path_app):
  if not os.path.exists(file_path):
    return False
  if not is_path_app:
    return True

  with open(file_path, 'r') as file:
    for line in file:
      if f"location = /{search_string}" in line:
        return True
  return False

def insert_location_block(file_path, new_location_block):
 with open(file_path, 'r') as file:
   content = file.read()

 # Find the position of the last '}' character in the content
 last_brace_position = content.rfind('}')

 if last_brace_position != -1:
   # Insert the text before the last '}' character
   updated_content = content[:last_brace_position] + new_location_block + content[last_brace_position:]

   with open(file_path, 'w') as file:
     file.write(updated_content)

def get_app_info(subdomain, path, is_path_app):
  ext = 'branch' if is_path_app else 'app'

  config_file_path = f'/etc/nginx/sites-available/{subdomain}.{ext}'
  values = dotenv_values('/home/david/Palatial-Web-Loading/.env')
  app = path.split('/')[-1]

  dserverport = values.get(f'REACT_APP_DEDICATED_SERVER_PORT_{app.upper()}')

  hasWebServer = has_location_block(config_file_path, path, is_path_app)

  return {
    "branch": "" if not is_path_app else subdomain,
    "application": path,
    "url": f"https://{subdomain}.palatialxr.com/{'' if not is_path_app else path}" if hasWebServer else "",
    "webServerPort": 3000 if hasWebServer else "",
    "dedicatedServerPort": dserverport if dserverport else "",
  }

def setup_application_site(config, is_path_app):
  subdomain = config.get("subdomain")
  branch = config.get('branch')
  app = config.get("application")

  if is_path_app:
    ext = 'branch'
  else:
    ext = 'app'

  if not config.get("client-only"):
    setup_dedicated_server(app)

  file_path = f'/etc/nginx/sites-available/{subdomain}.{ext}'

  if not has_location_block(file_path, config['path'], is_path_app):
    new_location_block = ""

    if is_path_app:
      new_location_block = f"""
  location = /{config['path']} {{
    proxy_pass http://localhost:3000;
  }}
"""

    new_server_block = f"""
server {{
  listen 443 ssl;
  server_name {subdomain}.palatialxr.com;

  ssl_certificate /etc/letsencrypt/live/{subdomain}.palatialxr.com/fullchain.pem;
  ssl_certificate_key /etc/letsencrypt/live/{subdomain}.palatialxr.com/privkey.pem;

  root /home/david/Palatial-Web-Loading/;
  index index.html;

  location = / {{
    { "return 404;" if is_path_app else "proxy_pass http://localhost:3000;" }
  }}

  location ~ ^/static/ {{
    proxy_pass http://localhost:3000;
  }}

  {new_location_block}
}}
"""

    if os.path.exists(file_path):
      if is_path_app:
        insert_location_block(file_path, new_location_block)
    else:
      if not os.path.exists(f'/etc/letsencrypt/renewal/{subdomain}.palatialxr.com.conf'):
        make_certificate = ['sudo', 'certbot', 'certonly', '-d', f'{subdomain}.palatialxr.com', '--nginx']
        subprocess.run(make_certificate, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

      with open(file_path, 'w') as file:
        file.write(new_server_block)

      subprocess.run(['sudo', 'ln', '-s', f'/etc/nginx/sites-available/{subdomain}.{ext}', '/etc/nginx/sites-enabled/'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    reload = ['sudo', 'nginx', '-s', 'reload']
    subprocess.run(reload, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

  return json.dumps(get_app_info(subdomain, config['path'], is_path_app), indent=2)

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
  subprocess.run(['sudo', 'chown', '-R', 'david:david', '.'])

def generate_random_string(length):
    import random
    import string

    characters = string.ascii_letters + string.digits  # Letters and digits
    random_string = ''.join(random.choice(characters) for _ in range(length))
    return random_string

if __name__ == "__main__":
  if len(sys.argv) < 2:
    print('python run_pipeline.py <url> [option]\n\n\
-A, -C            Create a webserver\n\
-S                Create a dedicated server')
    sys.exit(1)

  config = {}

  url = sys.argv[1]
  opt = sys.argv[2] if len(sys.argv) == 3 else ""
  is_path_app = False

  if opt in ['-A', '-C']:
    config['client-only'] = True
  elif opt == '-S':
    config['server-only'] = True

  parsed_url = urlparse(url)

  hostname = clean_string(parsed_url.hostname.split(".")[0])
  path = parsed_url.path.strip("/")

  config['subdomain'] = hostname
  config['path'] = path

  if path:
    is_path_app = True
    config['branch'] = hostname
    config['application'] = path.split('/')[-1]
  else:
    config['path'] = config['application'] = hostname

  if opt == "--generate-edit-url":
    config['application'] = generate_random_string(14)
    config['path'] = 'edit/' + config['application']
    config['client-only'] = True
    is_path_app = True

  if opt == "--generate-view-url":
    config['application'] = generate_random_string(14)
    config['path'] = 'view/' + config['application']
    config['client-only'] = True
    is_path_app = True

  if config.get("server-only"):
    setup_dedicated_server(config["application"])
    print(json.dumps(get_app_info(config["subdomain"], config["path"], is_path_app), indent=2))
    sys.exit(0)

  output = setup_application_site(config, is_path_app)

  print(output)
  sys.exit(0)


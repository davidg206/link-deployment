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

def find_port_for_location(file_path, search_string):
  try:
    with open(file_path, 'r') as file:
      content = file.read()

    pattern = r"location\s*=\s*(/[^{\s]+)\s*{[^}]+proxy_pass\s+http://localhost:(\d+);"

    matches = re.findall(pattern, content)
    for location, port in matches:
      if location[1:] == search_string:
        return port
    return None
  except Exception as e:
    print(f"An error occurred: {e}")
    return None

def get_app_info(subdomain, app, is_domain):
  ext = 'branch' if is_domain else 'app'

  config_file_path = f'/etc/nginx/sites-available/{subdomain}.{ext}'
  values = dotenv_values('/home/david/Palatial-Web-Loading/.env')

  dserverport = values.get(f'REACT_APP_DEDICATED_SERVER_PORT_{app.upper()}')

  hasWebServer = has_location_block(config_file_path, app, is_domain)

  return {
    "branch": "" if not is_domain else subdomain,
    "application": app,
    "url": f"https://{subdomain}.palatialxr.com/{'' if not is_domain else app}" if hasWebServer else "",
    "webServerPort": 3000 if hasWebServer else "",
    "dedicatedServerPort": dserverport if dserverport else "",
  }

def setup_application_site(config, is_domain):
  subdomain = config.get("subdomain")
  branch = config.get('branch')
  app = config.get("application")

  if is_domain:
    ext = 'branch'
  else:
    ext = 'app'

  if not config.get("client-only"):
    setup_dedicated_server(app)

  file_path = f'/etc/nginx/sites-available/{subdomain}.{ext}'

  if not has_location_block(file_path, app, is_domain):
    new_location_block = ""
    new_edit_location_block = f"""
  location = /edit/{app if is_domain else ""} {{
    proxy_pass http://localhost:3000;
  }}
"""
    if is_domain:
      new_location_block = f"""
  location = /{app} {{
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
    { "return 404;" if is_domain else "proxy_pass http://localhost:3000;" }
  }}

  location ~ ^/static/ {{
    proxy_pass http://localhost:3000;
  }}

  {new_edit_location_block if not is_domain else ""}

  {new_location_block}
}}
"""

    if os.path.exists(file_path):
      if is_domain:
        insert_location_block(file_path, new_location_block)
    else:
      if not os.path.exists(f'/etc/letsencrypt/renewal/{subdomain}.palatialxr.com.conf'):
        make_certificate = ['sudo', 'certbot', 'certonly', '-d', f'{subdomain}.palatialxr.com', '--nginx']
        subprocess.run(make_certificate, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

      with open(file_path, 'w') as file:
        file.write(new_server_block)

      subprocess.run(['sudo', 'ln', '-s', f'/etc/nginx/sites-available/{subdomain}.{ext}', '/etc/nginx/sites-enabled/'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    if is_domain and not has_location_block(file_path, f'edit/{app}', True):
      insert_location_block(file_path, new_edit_location_block)

    reload = ['sudo', 'nginx', '-s', 'reload']
    subprocess.run(reload, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

  return json.dumps(get_app_info(subdomain, app, is_domain), indent=2)

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

if __name__ == "__main__":
  if len(sys.argv) < 2:
    print('python run_pipeline.py [options]...\n\n\
-A, -C            Create a webserver\n\
--subdomain       If the application is a path link, the subdomain it exists under\n\
--application     The name of the application')
    sys.exit(1)

  config = {}

  for i in range(1, len(sys.argv)):
    if sys.argv[i] == "-A" or sys.argv[i] == "-C":
      config["client-only"] = True
    if sys.argv[i] == "-S":
      config["server-only"] = True
    if sys.argv[i] == "--branch":
      if i + 1 >= len(sys.argv):
        print("--branch requires an argument")
        sys.exit(1)
      config["branch"] = sys.argv[i + 1]
    if sys.argv[i] == "--application":
      if i + 1 >= len(sys.argv):
        print("--application requires an argument")
        sys.exit(1)
      config["application"] = sys.argv[i + 1]

  if not config.get('application'):
    print('error: --application is required')
    sys.exit(1)

  is_domain = config.get('branch') != None
  if is_domain:
    config['subdomain'] = config.get('branch')
  else:
    config['subdomain'] = config.get('application')

  if config.get("server-only"):
    setup_dedicated_server(config["application"])
    print(json.dumps(get_app_info(config["subdomain"], config["application"], is_domain), indent=2))
    sys.exit(0)

  output = setup_application_site(config, is_domain)

  print(output)
  sys.exit(0)


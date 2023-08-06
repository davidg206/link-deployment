import subprocess
import datetime
import socket
import sys
import os
import re
import portlookup
from portlookup.portlookup import find_dedicated_server_port, find_available_port
from dotenv import load_dotenv

def setup_application_site(branch, log=False):
  file_path = f'/etc/nginx/sites-available/{branch}.conf'
  web_server_port = None
  dedicated_server_port = None

  web_server_port = find_available_port(3000, 6000)
  subprocess.run(['sudo', 'ufw', 'allow', f'{web_server_port}/tcp'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

  new_location_block = f"""
  location / {{
    proxy_pass http://localhost:{web_server_port};
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

  {new_location_block}
}}
"""

  if not os.path.exists(file_path):
    if not os.path.exists(f'/etc/letsencrypt/renewal/{branch}.palatialxr.com.conf'):
      make_certificate = ['sudo', 'certbot', 'certonly', '-d', f'{branch}.palatialxr.com', '--nginx']
      subprocess.run(make_certificate, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    with open(file_path, 'w') as file:
      file.write(new_server_block)

    subprocess.check_output(['sudo', 'ln', '-s', f'/etc/nginx/sites-available/{branch}.conf', '/etc/nginx/sites-enabled/'])

  reload = ['sudo', 'nginx', '-s', 'reload']
  subprocess.run(reload)

  # Set up web service file
  file_path = f'/etc/systemd/system/dom_{branch}.service'

  # Make dedicated server first to get the port number
  dedicated_server_port = setup_dedicated_server(branch)

  # Now set up service file for the web server
  service_file = f"""
[Unit]
Description=Web server for {branch}
After=network.target

[Service]
User=david
WorkingDirectory=/home/david/Palatial-Web-Loading
ExecStart=/bin/bash -c 'PORT={web_server_port} PUBLIC_URL=https://{branch}.palatialxr.com/ npm run start'
Restart=always

[Install]
WantedBy=multi-user.target
"""

  with open(file_path, 'w') as file:
    file.write(service_file)

  subprocess.run(['sudo', 'systemctl', 'daemon-reload'])
  subprocess.run(['sudo', 'systemctl', 'enable', f'dom_{branch}'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
  subprocess.run(['sudo', 'systemctl', 'start', f'dom_{branch}'])

  current_datetime = datetime.datetime.now()
  formatted_datetime = current_datetime.strftime("%d/%m/%Y %H:%M:%S")
  return f"""
{{
  branch: {branch},
  url: https://{branch}.palatialxr.com/,
  palatial_webserver_port: 0000:{web_server_port},
  palatial_dedicated_server_port: 0000:{dedicated_server_port},
  unreal_websocket_endpoint: wss://sps.tenant-palatial-platform.lga1.ingress.coreweave.cloud/{branch}/ws,
  created: {formatted_datetime}
}}
"""

def setup_dedicated_server(branch):
  file_path = f'/etc/systemd/system/server_{branch}.service'

  if not os.path.exists(file_path):
    dedicated_server_port = find_dedicated_server_port(branch, 7777, 10777)
    subprocess.run(['sudo', 'ufw', 'allow', f'{dedicated_server_port}/udp'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    service_file = f"""
[Unit]
Description=Dedicated server for {branch}
After=network.target

[Service]
User=david
WorkingDirectory=/home/david/servers/{branch}/LinuxServer/
ExecStart=/bin/bash -c 'chmod +x ThirdTurn_TemplateServer.sh && ./ThirdTurn_TemplateServer.sh'
Restart=always

[Install]
WantedBy=multi-user.target
"""

    with open(file_path, 'w') as file:
      file.write(service_file)

    subprocess.run(['sudo', 'systemctl', 'daemon-reload'])
    subprocess.run(['sudo', 'systemctl', 'enable', f'server_{branch}'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    subprocess.run(['sudo', 'systemctl', 'start', f'server_{branch}'])

  return os.environ['REACT_APP_DEDICATED_SERVER_PORT_' + branch.upper()]

if __name__ == "__main__":
  if len(sys.argv) < 2:
    print('python run_pipeline.py <branch>')
    sys.exit(1)

  branch = sys.argv[1]

  load_dotenv(dotenv_path='/home/david/Palatial-Web-Loading/.env')

  print(setup_application_site(branch))
  sys.exit(0)

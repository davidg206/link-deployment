import subprocess
import datetime
import socket
import sys
import os
import re

def find_port_number_in_file(file_path, pattern):
    with open(file_path, 'r') as file:
        for line in file:
            match = re.search(pattern, line)
            if match:
                port_number = int(match.group(1))
                return port_number
    return None

def find_available_port(start_port, end_port):
    for port in range(start_port, end_port + 1):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('localhost', port))
                return port
        except OSError:
            continue
    raise ValueError(f"No available port found in the range {start_port} - {end_port}")

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
ExecStart=/bin/bash -c 'PORT={web_server_port} PUBLIC_URL=https://{branch}.palatialxr.com/ REACT_APP_DEDICATED_SERVER_PORT={dedicated_server_port} npm run start'
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
    dedicated_server_port = find_available_port(7777, 10777)
    subprocess.run(['sudo', 'ufw', 'allow', f'{dedicated_server_port}/udp'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

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
    subprocess.run(['sudo', 'systemctl', 'enable', f'server_{branch}'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    subprocess.run(['sudo', 'systemctl', 'start', f'server_{branch}'])

    return dedicated_server_port
  return find_port_number_in_file(file_path, r'-port=(\d+)')

if __name__ == "__main__":
  if len(sys.argv) < 2:
    print('python run_pipeline.py <branch>')
    sys.exit(1)

  branch = sys.argv[1]

  print(setup_application_site(branch))
  sys.exit(0)
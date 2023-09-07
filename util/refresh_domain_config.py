import subprocess
import json
import sys
import os
import re
import datetime

def try_get_application(name):
  command = f"sps-client application read --name {name}"
  try:
    output = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    json_data = output.stdout

    if output.stderr:
      prefix = "Error: "
      json_data = output.stderr[len(prefix):]

    json_data = json_data.decode('utf-8')
    data = json.loads(json_data)

    return data["statusCode"] == 200, data
  except subprocess.CalledProcessError as e:
    return False, None

def refresh(domain):
  config_file = f'/etc/nginx/sites-available/{domain}.branch'
  symbol_file = f'/etc/nginx/sites-enabled/{domain}.branch'

  if not os.path.exists(config_file):
    print(f"error: {config_file} does not exist")
    sys.exit(1)

  with open(config_file, 'r') as f:
    file_content = f.read()

  pattern = r"location\s+=\s+/([\w\d_-]+)\s+{\s+proxy_pass\s+http://localhost:(\d+);"

  matches = re.findall(pattern, file_content)

  unique_elements = set()
  result = []
  to_remove = []

  for match in matches:
    path = match[0]
    port = int(match[1])

    element = (path, port)

    if element not in unique_elements:
      unique_elements.add(element)
      if try_get_application(path)[0]:
        result.append([path, port])
      else:
        to_remove.append([path, port])

  current_datetime = datetime.datetime.now()
  home_directory = os.path.expanduser("~")
  logfile = os.path.join(home_directory, "cronlog")

  print("Discarding unused files...")
  for item in to_remove:
    app = item[0]
    port = item[1]
    with open(logfile, "a") as f:
      f.write(f"{current_datetime.strftime('%A, %B %d, %Y %H:%M:%S')} Full clean {app}\n")
    os.system(f'bash ~/link-deployment/util/cleanup.sh {app}')
    subprocess.run(['sudo', 'ufw', 'deny', f'{port}/tcp'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
  print("Done")

  config_contents = f"""server {{
  listen 443 ssl;
  server_name {domain}.palatialxr.com;

  ssl_certificate /etc/letsencrypt/live/{domain}.palatialxr.com/fullchain.pem;
  ssl_certificate_key /etc/letsencrypt/live/{domain}.palatialxr.com/privkey.pem;

  root /home/david/Palatial-Web-Loading/build/;
  index index.html;

  location = / {{
    return 404;
  }}
"""

  for info in result:
    config_contents += f"""
  location = /{info[0]} {{
     proxy_pass http://localhost:{info[1]};
  }}
"""
  config_contents += "}"

  with open(config_file, 'w') as f:
    f.write(config_contents)

  delete_file = len(result) == len(to_remove)

  if delete_file:
    os.remove(config_file)
    os.remove(symbol_file)

  subprocess.run(['sudo', 'nginx', '-s', 'reload'])

  print(config_contents if not delete_file else "all paths have been removed and the file has been deleted")

if __name__ == "__main__":
  if len(sys.argv) < 2:
    print("error: refresh_domain_config.py <domain>")
    sys.exit(1)

  domain = sys.argv[1]

  refresh(domain)

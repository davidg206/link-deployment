import subprocess
import sys
import json
import sys
import os
import re
import datetime

sys.path.append('/home/david/.local/lib/python3.8/site-packages')

import pymongo

client = pymongo.MongoClient("mongodb://localhost:27017/palatial?directConnection=true&authSource=staging_db")
db = client["palatial"]

def lookup_edit_hash(hash):
  return db.changelogs.find_one({ "payload.application": hash })

def is_edit_url(hash):
  urlStub = lookup_edit_hash(hash)
  return urlStub != None

def edit_hash_to_application(hash):
  if not is_edit_url(hash):
    return None

  urlStub = lookup_edit_hash(hash)
  if not urlStub:
    return None

  buildStub = db.changelogs.find_one({ "event": "import complete", "subjectId": urlStub["subjectId"] })
  if not buildStub:
    return None

  return buildStub["application"]

def try_get_application(name):
  if "edit/" in name or "view/" in name:
    name = edit_hash_to_application(name)
    if not name:
      return False, None

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

def get_application_from_hash(hash):
  if is_edit_url(hash):
    return edit_hash_to_application(hash)
  return hash

def log(message):
  home_directory = os.path.expanduser("~")
  logfile = os.path.join(home_directory, "cronlog")
  current_datetime = datetime.datetime.now()
  print(message)
  with open(logfile, "a") as f:
    f.write(f"{current_datetime.strftime('%A, %B %d, %Y %H:%M:%S')} {message}\n")

def refresh(domain):
  config_file = f'/etc/nginx/sites-available/{domain}.branch'
  symbol_file = f'/etc/nginx/sites-enabled/{domain}.branch'

  if not os.path.exists(config_file):
    print(f"error: {config_file} does not exist")
    sys.exit(1)

  with open(config_file, 'r') as f:
    file_content = f.read()

  pattern = r'location\s+=\s+/([\w]+)/?([\w]+)?\s+{\s+proxy_pass\s+http://localhost:\d+;\s+}'

  matches = re.findall(pattern, file_content)

  unique_elements = set()
  result = []
  to_remove = []

  for element in matches:
    if element[0] == "edit" or element[0] == "view":
      application = f'{element[0]}/{element[1]}'
    else:
      application = element[0]

    if application not in unique_elements:
      unique_elements.add(application)

      if try_get_application(application)[0]:
        result.append(application)
      else:
        to_remove.append(application)

  print("Discarding unused files...")
  for item in to_remove:
    app = item
    log(f"Full clean {domain}/{app}\n")
    if get_application_from_hash(app):
      os.system(f'bash /home/david/link-deployment/util/cleanup.sh {get_application_from_hash(app)}')
  print("Done")

  config_contents = f"""server {{
  listen 443 ssl;
  server_name {domain}.palatialxr.com;

  ssl_certificate /etc/letsencrypt/live/{domain}.palatialxr.com/fullchain.pem;
  ssl_certificate_key /etc/letsencrypt/live/{domain}.palatialxr.com/privkey.pem;

  location ~ ^/(|edit)$ {{
    return 404;
  }}

  location ~ ^/static/ {{
    proxy_pass http://localhost:3000;
  }}
"""

  for info in result:
    config_contents += f"""
  location = /{info} {{
     proxy_pass http://localhost:3000;
  }}
"""
  config_contents += "}"

  with open(config_file, 'w') as f:
    f.write(config_contents)

  delete_file = len(matches) == len(to_remove)

  if delete_file:
    if os.path.exists(symbol_file):
      log(f"Deleting the symbol file for {domain}")
      os.remove(symbol_file)
    else:
      log(f"Could not find symbol file at {symbol_file}")

    log(f"Deleting the config file for {domain}")
    os.remove(config_file)
    subprocess.run(['certbot', 'delete', '--cert-name', f'{domain}.palatialxr.com'], stderr=subprocess.PIPE)

  subprocess.run(['sudo', 'nginx', '-s', 'reload'])

  print(config_contents if not delete_file else f"All paths have been removed from {domain}.branch and the file has been deleted")

if __name__ == "__main__":
  if len(sys.argv) < 2:
    print("error: refresh_domain_config.py <domain>")
    sys.exit(1)

  domain = sys.argv[1]

  refresh(domain)

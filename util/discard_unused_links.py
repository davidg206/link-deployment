import subprocess
import refresh_domain_config
import json
import sys
import os
import re

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

if __name__ == "__main__":
  directory = '/etc/nginx/sites-available/'

  for filename in os.listdir(directory):
    path = os.path.join(directory, filename)
    if os.path.isfile(path):
      name, extension = os.path.splitext(filename)
      if extension == ".app" and not try_get_application(name)[0]:
        os.remove(path)
        subprocess.run(['./cleanup.sh', name], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
      elif extension == ".branch":
        refresh_domain_config.refresh(name)

import subprocess
import refresh_domain_config
import json
import sys
import os
import re
import shutil
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

if __name__ == "__main__":
  directory = '/etc/nginx/sites-available/'

  current_datetime = datetime.datetime.now()
  home_directory = os.path.expanduser("~")
  logfile = os.path.join(home_directory, "cronlog")

  for filename in os.listdir(directory):
    path = os.path.join(directory, filename)
    if os.path.isfile(path):
      name, extension = os.path.splitext(filename)
      if extension == ".app" and not try_get_application(name)[0]:
        with open(logfile, "a") as f:
          f.write(f"{current_datetime.strftime('%A, %B %d, %Y %H:%M:%S')} Full clean {name}\n")
        os.remove(path)
        os.remove(f'/etc/nginx/sites-enabled/{filename}')
        os.system(f'bash ~/link-deployment/util/cleanup.sh {name}')
      elif extension == ".branch":
        refresh_domain_config.refresh(name)

  directory = '/home/david/servers/'
  for folder in os.listdir(directory):
    if not try_get_application(folder)[0]:
      with open(logfile, "a") as f:
        f.write(f"{current_datetime.strftime('%A, %B %d, %Y %H:%M:%S')} Deleting server {folder}\n")
      shutil.rmtree(os.path.join(directory, folder))
      os.system(f'bash ~/link-deployment/util/clear_backend_files.sh {folder}')

  os.chdir('/home/david/palatial-web-loading/')
  subprocess.run(['npm', 'run', 'build'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
  subprocess.run(['sudo', 'chown', '-R', 'david:david', '.'])

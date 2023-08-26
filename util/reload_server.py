import subprocess
from portlookup.portlookup import free_port, find_dedicated_server_port
from dotenv import dotenv_values
import sys
import os

if __name__ == "__main__":
  if len(sys.argv) < 2:
    print("error: must provide a server")

  server = sys.argv[1]

  existing_env_vars = dotenv_values('/home/david/Palatial-Web-Loading/.env')

  stop = ['sudo', 'systemctl', 'stop', f'server_{server}']
  subprocess.run(stop)

  free_port(server, os.path.expanduser("~/Palatial-Web-Loading/.env"))

  port = find_dedicated_server_port(server, existing_env_vars)
  print(f"New port: {port}")

  start = ['sudo', 'systemctl', 'start', f'server_{server}']
  subprocess.run(start)

  restart_dom = ['sudo', 'systemctl', 'restart', f'dom_{server}']
  subprocess.run(restart_dom)

  path = os.path.expanduser("~/Palatial-Web-Loading/")
  os.chdir(path)
  subprocess.run(['npm', 'run', 'build'], stdout=subprocess.PIPE)

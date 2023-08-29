import subprocess
from portlookup import portlookup
from dotenv import dotenv_values
import sys
import os

if __name__ == "__main__":
  if len(sys.argv) < 2:
    print("error: must provide a server")

  server = sys.argv[1]

  existing_env_vars = dotenv_values('/home/david/Palatial-Web-Loading/.env')

  # Stop the server
  stop = ['sudo', 'systemctl', 'stop', f'server_{server}']
  subprocess.run(stop)

  path = os.path.expanduser("~/Palatial-Web-Loading/.env")
  portlookup.free_port(server, path)

  # Find unused port
  port = portlookup.find_dedicated_server_port(existing_env_vars)
  print(f"New port: {port}")

  # Add new port as key in .env file
  key = f'REACT_APP_DEDICATED_SERVER_PORT_{server.upper()}'
  existing_env_vars[key] = str(port)
  portlookup.reload_env_file(path, existing_env_vars)

  # Start the server
  start = ['sudo', 'systemctl', 'start', f'server_{server}']
  subprocess.run(start)

  # Web server has to be restarted to load in the new values
  restart_dom = ['sudo', 'systemctl', 'restart', 'react-dom']
  subprocess.run(restart_dom)

  # Rebuild as well just in case the above doesn't do it
  path = os.path.expanduser("~/Palatial-Web-Loading/")
  os.chdir(path)
  subprocess.run(['npm', 'run', 'build'], stdout=subprocess.PIPE)

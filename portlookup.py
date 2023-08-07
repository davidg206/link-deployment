import subprocess
import os
import sys

def is_port_in_use(port):
  try:
      # Execute the 'sudo lsof -i:port' command and capture the output
      result = subprocess.check_output(["sudo", "lsof", "-i:{}".format(port)], stderr=subprocess.STDOUT)
      # If there is output, the port is in use
      return True
  except subprocess.CalledProcessError as e:
      # If the command returns a non-zero exit code, there is no output, and the port is not in use
      return False

def find_available_port(start_port, end_port):
    for port in range(start_port, end_port + 1):
      if not is_port_in_use(port):
        return port
    raise ValueError(f"No available port found in the range {start_port} - {end_port}")

def change_env_variable(env_path, key, new_value, env_vars):
    # Update the value in memory
    env_vars[key] = new_value

    # Write the changes back to the .env file
    with open(env_path, 'w') as f:
        for k, v in env_vars.items():
            f.write(f"{k}={v}\n")

def find_dedicated_server_port(application, min, max, env_vars):
  env_vars = load_dotenv(dotenv_path='/home/david/Palatial-Web-Loading/.env')
  key = f'REACT_APP_DEDICATED_SERVER_PORT_{application.upper()}'
  port = find_available_port(min, max)
  print('found available port: ' + str(port))
  change_env_variable('/home/david/Palatial-Web-Loading/.env', key, str(port), env_vars)
  command = ['sudo', 'ufw', 'allow', f'{port}/udp']
  subprocess.run(command)
  return port

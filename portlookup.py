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

def find_available_port_range(start_port, end_port):
    for port in range(start_port, end_port + 1):
      if not is_port_in_use(port):
        return port
    raise ValueError(f"No available port found in the range {start_port} - {end_port}")

def find_available_port(data):
  # Extract keys and values for fields starting with REACT_APP_DEDICATED_SERVER_PORT_
  port_values = [value for key, value in data.items() if key.startswith("REACT_APP_DEDICATED_SERVER_PORT_")]

  # Filter out non-integer values
  int_values = [int(value) for value in port_values]

  # Sort the integer values
  sorted_values = sorted(int_values)

  # Find the lowest value that is not within the range of the sorted values
  def find_lowest_missing_value(values):
      for i in range(len(values) - 1):
          if values[i + 1] - values[i] > 1:
              return values[i] + 1
      return values[-1] + 1 if values else 0

  return find_lowest_missing_value(sorted_values)

def change_env_variable(env_path, key, new_value, env_vars):
    # Update the value in memory
    env_vars[key] = new_value

    # Write the changes back to the .env file
    with open(env_path, 'w') as f:
        for k, v in env_vars.items():
            f.write(f"{k}={v}\n")

def find_dedicated_server_port(application, env_vars):
  key = f'REACT_APP_DEDICATED_SERVER_PORT_{application.upper()}'
  port = find_available_port(env_vars)
  change_env_variable('/home/david/Palatial-Web-Loading/.env', key, str(port), env_vars)
  command = ['sudo', 'ufw', 'allow', f'{port}/udp']
  subprocess.run(command)
  return port

def free_port(application, env_path):
  values = dotenv_values(env_path)
  del values['REACT_APP_DEDICATED_SERVER_PORT_' + application.upper()]
  with open(env_path, 'w') as f:
    for k, v in values.items():
      f.write(f"{k}={v}\n")

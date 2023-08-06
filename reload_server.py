from portlookup.portlookup import find_dedicated_server_port
import subprocess

if __name__ == "__main__":
  if len(sys.argv) < 2:
    print("error: must provide a server")

  server = sys.argv[1]
  find_dedicated_server_port(server, 7777, 107777)
  command = ['sudo', 'systemctl', 'restart', f'server_{server}')
  subprocess.run(command)

from portlookup import portlookup
import sys
import os
from dotenv import dotenv_values

if __name__ == "__main__":
  if len(sys.argv) < 2:
    print("error: python freeport.py <application>")

  app = sys.argv[1]
  portlookup.free_port(app, os.path.expanduser("~/Palatial-Web-Loading/.env"))

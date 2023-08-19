import re
import portlookup
from dotenv import dotenv_values

values = dotenv_values('/home/david/Palatial-Web-Loading/.env')
portlookup.find_dedicated_server_port("test2", values)

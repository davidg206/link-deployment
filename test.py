import re

config_file = """
server {
  listen 443 ssl;
  server_name butter.palatialxr.com;

  ssl_certificate /etc/letsencrypt/live/butter.palatialxr.com/fullchain.pem;
  ssl_certificate_key /etc/letsencrypt/live/butter.palatialxr.com/privkey.pem;

  root /home/david/Palatial-Web-Loading/;
  index index.html;


  location / {
    proxy_pass http://localhost:3017;
  }

}
"""

search_string = "/your_search_string"

# Use regular expressions to find the location block with the search string
pattern = r'location\s*\/your_search_string\s*{[^}]*proxy_pass\s*(http:\/\/localhost:\d+);'
match = re.search(pattern.replace('your_search_string', re.escape(search_string)), config_file)

if match:
    port = match.group(1)
    print(f"Port for '{search_string}': {port}")
else:
    print(f"No location block found for '{search_string}'")

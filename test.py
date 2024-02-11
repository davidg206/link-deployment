import json
import re
import portlookup
from dotenv import dotenv_values
from pymongo import MongoClient
import requests

webhook_url = "https://hooks.slack.com/services/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"

message = {
  "text": f"testing",
  "username": "Python Bot",
  "icon_emoji": ":snake:",
}
response = requests.post(
  webhook_url, data=json.dumps(message),
  headers={'Content-Type': 'application/json'}
)

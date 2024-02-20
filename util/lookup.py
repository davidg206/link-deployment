import sys
sys.path.append('/home/david/.local/lib/python3.8/site-packages')

import pymongo

client = pymongo.MongoClient("mongodb://localhost:27017/palatial?directConnection=true&authSource=staging_db")
db = client["palatial"]

def lookup_edit_hash(hash):
  return db.changelogs.find_one({ "payload.application": hash })

def is_edit_url(hash):
  urlStub = lookup_edit_hash(hash)
  print(urlStub)
  return urlStub != None

def edit_hash_to_application(hash):
  if not is_edit_url(hash):
    return None

  urlStub = lookup_edit_hash(hash)
  if not urlStub:
    return None

  buildStub = db.changelogs.find_one({ "event": "import complete", "subjectId": urlStub["subjectId"] })
  if not buildStub:
    return None

  return buildStub["application"]

print(edit_hash_to_application("edit/qOZZwNRPPmE3Y8"))

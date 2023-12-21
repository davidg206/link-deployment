import re
import portlookup
from dotenv import dotenv_values
from pymongo import MongoClient

nt = MongoClient('mongodb://palatial:0UDUiKxwj7fI0@mongodb.mithyalabs.com:27017/palatial?directConnection=true&authSource=staging_db')
db = nt["palatial"]
collection = db["changelog"]

filter_criteria = {"hash": "edit/GVELNobk79OqAk"}
update_operation = {"$set": {"projectId": "651db46818d4d8017e1e77ee"}}

result = collection.update_one(filter_criteria, update_operation)

print(f"Matched {result.matched_count} document and modified {result.modified_count} document")

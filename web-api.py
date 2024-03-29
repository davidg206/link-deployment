from flask import Flask, request, jsonify
from flask_cors import CORS  # Import the CORS extension
from kubernetes import client, config
from bson import ObjectId
import subprocess
import os
import pymongo
import json
import re
import jwt
import base64
import bcrypt
import sys

app = Flask(__name__)

mongo_client = pymongo.MongoClient('mongodb://localhost:27017/palatial?directConnection=true&authSource=staging_db')
db = mongo_client["palatial"]
collection = db["changelogs"]

config.load_kube_config(config_file='/home/david/.kube/config')

v1 = client.CoreV1Api()
api_instance = client.AppsV1Api()

@app.before_request
def log_request_info():
    ip_address = request.remote_addr
    request_url = request.url
    request_method = request.method
    print(f"Request from {ip_address} to {request_url} using {request_method} method")

def get_youngest_pod_name(info):
    lines = info.strip().split('\n')
    lines = [line.strip() for line in lines if line.strip()]

    youngest_age = float('inf')
    youngest_name = None

    for line in lines[1:]:  # Skip the header line
        parts = line.split()
        name = parts[0]  # Assuming name is the first element
        age = parts[-1]  # Assuming age is the last element
        age_value = int(age[:-1]) if age.endswith('d') else 0  # Extract days from age
        if age_value < youngest_age:
            youngest_age = age_value
            youngest_name = name

    return youngest_name if youngest_name is not None else "No pods found"

def parse_jwt(token):
    token_parts = token.split('.')

    base64_payload = token_parts[1]
    base64_payload += '=' * (4 - len(base64_payload) % 4)
    decoded_payload = base64.urlsafe_b64decode(base64_payload).decode('utf-8')

    payload = json.loads(decoded_payload)

    return payload

def get_pod_name_starts_with(api_instance, namespace, prefix):
    pod_list = api_instance.list_namespaced_pod(namespace)

    print('prefix = ')
    print(prefix)
    matching_pods = [pod for pod in pod_list.items if pod.metadata.name.startswith(prefix)]

    return matching_pods[0]

def pod_exists(pod_name):
  output = subprocess.run(['kubectl', 'get', 'pod', pod_name], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
  if output.stderr:
    print('cant find pod ' + pod_name)
    return False
  return True

def deployment_exists(deployment_name):
  output = subprocess.run(['kubectl', 'get', 'deployment', pod_name], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
  if output.stderr:
    print('cant find deployment ' + deployment_name)
    return False
  return True

def parse_pod_output(output):
  youngestPod = get_youngest_pod_name(output)
  result = []
  output = subprocess.run(['kubectl', 'get', 'pods', youngestPod, "-o=jsonpath='{.status.phase}'"], stdout=subprocess.PIPE)
  if output.stdout != "Terminating":
    result.append(youngestPod)
  return result

@app.after_request
def after_request(response):
  response.headers.add('Access-Control-Allow-Origin', '*')
  response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
  response.headers.add('Access-Control-Allow-Methods', 'GET,POST,PUT,DELETE,OPTIONS')
  return response

@app.route('/generate-url', methods=['POST'])
def generate_url():
  args = request.get_json()
  projectId = args["projectId"]

  output = subprocess.run(['sudo', '-E', 'python3', 'run_pipeline.py', '-C'], stdout=subprocess.PIPE, text=True)
  output = json.loads(output)

  data = {
    "hash": output["application"],
    "projectId": projectId
  }

  collection.insert_one(data)

  return output.stdout

@app.route('/v2/generateViewUrl', methods=['POST'])
def generateViewUrl():
  args = request.get_json()

  # url is expected to be https://{workspace}.palatialxr.com
  if 'url' in args:
    args['url'] = args['url'].lower().replace(' ', '-').replace('_', '-')
    output = subprocess.run(['sudo', '-E', 'python3', 'run_pipeline.py', args['url'], '--generate-view-url'], stdout=subprocess.PIPE, text=True)
    return output.stdout

  return 'Missing URL', 400

@app.route('/generate-edit-url', methods=['POST'])
def run_script():
  args = request.get_json()

  if 'url' in args:
    args['url'] = args['url'].lower().replace(' ', '-').replace('_', '-')
    output = subprocess.run(['sudo', '-E', 'python3', 'run_pipeline.py', args['url'], '--generate-edit-url'], stdout=subprocess.PIPE, text=True)
    return output.stdout

  return 'Missing URL', 400

@app.route('/v2/deleteApp', methods=['POST'])
def delete_app():
  args = request.get_json()

  projectId = args["subjectId"]
  print("deleting ... ")
  buildStub = collection.find_one({ "event": "import complete", "subjectId": ObjectId(projectId) })
  if not buildStub:
    return 'Project not found', 400

  app_name = buildStub.get('application')

  if buildStub.get("workspace"):
    workspace = buildStub["workspace"]
    subprocess.run(['sudo', '-E', 'python3', f'/home/david/link-deployment/util/refresh_domain_config.py {workspace}'])
  else:
    os.system(f"bash /home/david/link-deployment/util/cleanup.sh {app_name}")
  return 'Success', 200

@app.route('/app-info', methods=['POST'])
def app_info():
  args = request.get_json()

  if 'name' in args:
    output = subprocess.run(['sps-client', 'application', 'read', '-n', args['name']], stdout=subprocess.PIPE)
    return output.stdout
  return 'Missing argument', 400

@app.route('/v1/lookup', methods=['POST'])
def lookup():
  args = request.get_json()
  if args.get("subjectId"):
    args["subjectId"] = ObjectId(args["subjectId"])
  print('Query = ', args)
  result = collection.find_one(request.get_json())
  json_data = json.dumps(result, default=str)
  print('Result = ', json_data)
  return json_data

@app.route('/v1/insert', methods=['PUT'])
def insert():
  args = request.get_json()
  print('inserting ', args)
  collection.insert_one(args)
  return 'Succesful', 200

@app.route('/v1/send-message', methods=['POST'])
def send_message():
  message = request.get_json()
  pod = get_pod_name_starts_with(v1, 'tenant-palatial-platform', message['payload']['podName'])
  pod_name = pod.metadata.name
  message['payload']['podName'] = pod_name

  result = collection.insert_one(message)

  response_data = {
    'message': 'Message sent successfully',
    'podName': pod_name,
    'insertedId': str(result.inserted_id)
  }

  return jsonify(response_data), 201

@app.route('/v1/k8s-components', methods=['POST'])
def k8s_components():
  args = request.get_json()
  if not 'name' in args:
    return 'Name argument required', 400

  name = args['name']
  auth_pod = subprocess.run(['kubectl', 'get', 'pods', '-l', f'app.kubernetes.io/name=sps-auth-{name}'], stdout=subprocess.PIPE).stdout
  signalling_pod = subprocess.run(['kubectl', 'get', 'pods', '-l', f'app.kubernetes.io/name=sps-signalling-server-{name}'], stdout=subprocess.PIPE).stdout
  instance_manager_pod = subprocess.run(['kubectl', 'get', 'pods', '-l', f'app.kubernetes.io/name=sps-instance-manager-{name}'], stdout=subprocess.PIPE).stdout

  output = parse_pod_output(auth_pod.decode('utf-8')) + parse_pod_output(signalling_pod.decode('utf-8')) + parse_pod_output(instance_manager_pod.decode('utf-8'))

  return jsonify({ "data": output }), 201

@app.route('/v1/mythia-jwt', methods=['POST'])
def mythia_jwt():
  args = request.get_json()
  secret_key = args['secret']
  token = args['token']
  print(secret_key, token)
  try:
    print("Decoding....")
    decoded_payload = parse_jwt(token)
    print("Decoded Payload:", decoded_payload)
    return decoded_payload, 201
  except jwt.ExpiredSignatureError:
    print("Expired")
    return jsonify({ "error": "true", "message": "Token has expired" }), 201
  except jwt.InvalidTokenError:
    print("Invalid")
    return jsonify({ "error": "true", "message": "Invalid token" }), 201

@app.route('/v1/update-k8s-components', methods=['PUT'])
def update_k8s_components():
  args = request.get_json()
  name = args['name']

  data = k8s_components()['data']
  collection.insert_one({
    "event": "updateK8sComponents",
    "name": name,
    "data": data
  })

@app.route('/v1/remove-instance', methods=['PUT'])
def remove_instance():
  args = request.get_json()
  id = args['podName']

  print('Deleting ' + id)

  subprocess.run(['kubectl', 'delete', 'deployment', id, '--force', '--grace-period=0'])
  return 'Success', 200

@app.route('/v1/updateReactWebRepo', methods=['POST'])
def updateReactWebRepo():
  os.chdir('/home/david/palatial-web')
  subprocess.run(['git', 'pull', 'origin', 'develop'])

@app.route('/v1/updateNodeAPIRepo', methods=['POST'])
def updateReactApiRepo():
  os.chdir('/home/david/palatial-api')
  subprocess.run(['sudo', 'npm', 'run', 'build'])

@app.route('/v1/updateThumbnail', methods=['POST'])
def updateThumbnail():
  pass

@app.route('/v2/checkPassword', methods=['POST'])
def checkPassword():
  args = request.get_json()
  user = db.users.find_one({ '_id': ObjectId(args['id']) })
  encrypted_pw = user["password"]
  pass_to_check = args['password']
  if bcrypt.checkpw(pass_to_check.encode('utf-8'), encrypted_pw.encode('utf-8')):
    return jsonify({ 'valid': True }), 200
  return jsonify({ 'valid': False }), 200

@app.route('/v2/streamTick', methods=['POST'])
def streamTick():
  args = request.get_json()
  userId = args["userId"]
  podName = args["podName"]
  user = db.users.find_one({ '_id': ObjectId(userId) })

  if not 'streamingTime' in user:
    return jsonify({ 'expired': False }), 200

  print('checking...')
  if not pod_exists(podName):
    return jsonify({ "expired": True }), 200

  update_query = { "$inc": { "streamingTime": 1 } }
  db.users.update_one({ '_id': ObjectId(userId) }, update_query)

  if user['allotedStreamingTime'] != -1 and user['streamingTime'] >= user['allotedStreamingTime']:
    return jsonify({ "expired": True }), 200
  return jsonify({ "expired": False }), 200

if __name__ == '__main__':
    app.run(port=3001, debug=True)

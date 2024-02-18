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

app = Flask(__name__)

mongo_client = pymongo.MongoClient('mongodb://localhost:27017/palatial?directConnection=true&authSource=staging_db')
db = mongo_client["palatial"]
collection = db["changelogs"]

config.load_kube_config(config_file='/home/david/.kube/config')

v1 = client.CoreV1Api()
api_instance = client.AppsV1Api()

def parse_jwt(token):
    token_parts = token.split('.')

    base64_payload = token_parts[1]
    base64_payload += '=' * (4 - len(base64_payload) % 4)
    decoded_payload = base64.urlsafe_b64decode(base64_payload).decode('utf-8')

    payload = json.loads(decoded_payload)

    return payload

def get_pod_name_starts_with(api_instance, namespace, prefix):
    pod_list = api_instance.list_namespaced_pod(namespace)

    matching_pods = [pod for pod in pod_list.items if pod.metadata.name.startswith(prefix)]

    return matching_pods[0]

def parse_pod_output(output):
  pattern = re.compile(r'^\S+', re.MULTILINE)

  matches = pattern.findall(output)
  if not matches or matches[0] != "NAME":
    return []
  pods = matches[1:]

  result = []

  for p in pods:
    output = subprocess.run(['kubectl', 'get', 'pods', p, "-o=jsonpath='{.status.phase}'"], stdout=subprocess.PIPE)
    if output.stdout != "Terminating":
      result.append(p)
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

@app.route('/generate-edit-url', methods=['POST'])
def run_script():
  args = request.get_json()

  if 'url' in args:
    args['url'] = args['url'].lower().replace(' ', '-').replace('_', '-')
    output = subprocess.run(['sudo', '-E', 'python3', 'run_pipeline.py', args['url'], '--generate-edit-url'], stdout=subprocess.PIPE, text=True)
    return output.stdout

  return 'Missing URL', 400

@app.route('/delete-app', methods=['POST'])
def delete_app():
  args = request.get_json()

  if 'name' in args:
    os.system(f"bash ~/link-deployment/util/cleanup.sh {args['name']}")
    subprocess.run(['sudo', '-E', 'python3', 'discard_unused_links.py'])
  else:
    return 'Missing name', 400
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
  namespace = 'tenant-palatial-platform'
  deployment_name_prefix = get_pod_name_starts_with(v1, namespace, id)
  deployments = api_instance.list_namespaced_deployment(namespace)

  matching_deployment = None
  for deployment in deployments.items:
    if deployment_name_prefix.metadata.name.startswith(deployment.metadata.name):
      matching_deployment = deployment
      break

  subprocess.run(['kubectl', 'delete', 'deployment', matching_deployment.metadata.name, '--force', '--grace-period=0'])
  return 'Sucess', 200

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

if __name__ == '__main__':
    app.run(port=3001)

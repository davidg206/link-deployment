from flask import Flask, request, jsonify
from flask_cors import CORS  # Import the CORS extension
import subprocess
import os

app = Flask(__name__)

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,POST,PUT,DELETE,OPTIONS')
    return response

@app.route('/generate-edit-url', methods=['POST'])
def run_script():
    args = request.get_json()

    if 'url' in args:
        output = subprocess.run(['sudo', '-E', 'python3', 'run_pipeline.py', args['url'], '--generate-edit-url'], stdout=subprocess.PIPE, text=True)
        return output.stdout

    return 'Missing arguments', 400

@app.route('/delete-app', methods=['POST'])
def delete_app():
  args = request.get_json()

  if 'name' in args:
    os.system(f"bash ~/link-deployment/util/cleanup.sh {args['name']}")
    subprocess.run(['sudo', '-E', 'python3', 'discard_unused_links.py'])
  else:
    return 'Missing argument', 400
  return 'Success', 200

@app.route('/app-info', methods=['POST'])
def app_info():
  args = request.get_json()

  if 'name' in args:
    output = subprocess.run(['sps-client', 'application', 'read', '-n', args['name']], stdout=subprocess.PIPE)
    return output.stdout
  return 'Missing argument', 400

if __name__ == '__main__':
    app.run(port=3001)

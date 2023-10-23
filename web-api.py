from flask import Flask, request, jsonify
import subprocess

app = Flask(__name__)

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,POST,PUT,DELETE,OPTIONS')
    return response

@app.route('/generate-url', methods=['POST'])
def run_script():
    # Get arguments from the request
    args = request.get_json()  # Assuming you're sending JSON data

    if 'url' in args:
        url = args['url']

        output = subprocess.run(['sudo', '-E', 'python3', 'run_pipeline.py', url, '-C'], stdout=subprocess.PIPE, text=True)

        return output.stdout
    else:
        return 'Missing argument', 400  # Bad Request

if __name__ == '__main__':
    app.run()

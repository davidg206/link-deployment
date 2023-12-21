from kubernetes import client, config
import requests
import json

# Load kubeconfig file or use in-cluster config
config.load_kube_config()

# Create a Kubernetes API client
api_instance = client.CoreV1Api()

# Specify namespace (optional)
namespace = 'tenant-palatial-platform'

# List all pods in the namespace
pods = api_instance.list_namespaced_pod(namespace)

webhook_url = "https://hooks.slack.com/services/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"

# Iterate through pods and check for errors
for pod in pods.items:
  for container_status in pod.status.container_statuses:
    if container_status.state and container_status.state.waiting and container_status.state.waiting.reason:
      if container_status.state.waiting.reason == "ContainerCreating":
        pass
      message = {
        "text": f"Pod {pod.metadata.name} has an error: {container_status.state.waiting.reason}",
        "username": "Python Bot",
        "icon_emoji": ":snake:",
      }
      response = requests.post(
        webhook_url, data=json.dumps(message),
        headers={'Content-Type': 'application/json'}
      )

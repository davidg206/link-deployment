import json
import re
import portlookup
from dotenv import dotenv_values
from pymongo import MongoClient
import requests

def get_youngest_pod_name(info):
    # Split the info into lines and remove empty lines
    lines = info.strip().split('\n')
    lines = [line.strip() for line in lines if line.strip()]

    # Initialize variables to store the youngest pod's age and its index
    youngest_age = float('inf')
    youngest_name = None

    # Iterate over each line to find the youngest pod
    for line in lines[1:]:  # Skip the header line
        parts = line.split()
        name = parts[0]  # Assuming name is the first element
        age = parts[-1]  # Assuming age is the last element
        age_value = int(age[:-1]) if age.endswith('d') else 0  # Extract days from age
        if age_value < youngest_age:
            youngest_age = age_value
            youngest_name = name

    # Return the name of the youngest pod
    return youngest_name if youngest_name is not None else "No pods found"

# Example usage:
info = """
NAME                                  READY   STATUS    RESTARTS   AGE
sps-auth-officedemo-786696ffd-kz8np   1/1     Running   0          9d
sps-auth-officedemo-2485324-adfd 1/1 Running 0 5m
"""

youngest_pod = get_youngest_pod_name(info)
print(youngest_pod)

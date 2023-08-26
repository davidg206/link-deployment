#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

for arg in "$@"; do
    cleaned_arg=$(echo "$arg" | sed 's/^server_//; s/^dom_//')
    # Call the other script and pass the current argument
    ./impl_cleanup.sh "$cleaned_arg"
done

#!/bin/bash

for arg in "$@"; do
    cleaned_arg=$(echo "$arg" | sed 's/^server_//; s/^dom_//')
    # Call the other script and pass the current argument
    ./cleanup_impl.sh "$cleaned_arg"
done

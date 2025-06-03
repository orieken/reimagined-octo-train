#!/bin/bash
echo "Received command: $@"

export DISPLAY=:99

# Match only npm run cu:* commands
if [[ "$1" == "npm" && "$2" == "run" && "$3" == cu:* ]]; then
    echo "Running with xvfb-run..."
    exec xvfb-run -a "$@"
else
    echo "Running without xvfb-run..."
    exec "$@"
fi

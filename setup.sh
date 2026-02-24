#!/bin/bash

# Create temp dir on the larger partition to avoid /tmp space issues
mkdir -p /home/duffer/tmp

# Create venv if it doesn't exist
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

# Activate venv
source venv/bin/activate

# Install dependencies
TMPDIR=/home/duffer/tmp pip install --no-cache-dir -r requirements.txt

echo "Setup complete. Run 'source venv/bin/activate' to activate the environment."

#!/bin/bash
# OntoJSON launcher for macOS
# This script helps display the proper app name in the dock

# Get the directory where this script is located
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Change to the project directory
cd "$DIR"

# Set the app name for the dock
export __CFBundleName="OntoJSON"
export __CFBundleDisplayName="OntoJSON"

# Launch the application
exec python3 launch_ontojson.py "$@"
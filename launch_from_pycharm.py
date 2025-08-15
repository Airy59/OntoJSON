#!/usr/bin/env python
"""
Special launcher for running OntoJSON from PyCharm with proper app naming.
This script should be used as the entry point in PyCharm run configurations.
"""

import sys
import os
import subprocess
import platform

def launch_with_proper_name():
    """Launch the app using the command line to ensure proper naming."""
    if platform.system() == 'Darwin':
        # Get the directory of this script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Use the OntoJSON.command script which properly sets the name
        command_script = os.path.join(script_dir, 'OntoJSON.command')
        
        if os.path.exists(command_script):
            # Launch using the command script
            subprocess.run(['bash', command_script])
        else:
            # Fallback to launch_ontojson.py
            launcher_script = os.path.join(script_dir, 'launch_ontojson.py')
            subprocess.run([sys.executable, launcher_script])
    else:
        # On non-macOS systems, just import and run directly
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
        from owl2jsonschema_gui.app import main
        main()

if __name__ == "__main__":
    # For PyCharm, we need to launch the app in a subprocess
    # to avoid PyCharm's Python process showing in the dock
    launch_with_proper_name()
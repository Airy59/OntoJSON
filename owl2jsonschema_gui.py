#!/usr/bin/env python3
"""
Launcher script for the OWL to JSON Schema GUI application.

This script can be run directly to start the GUI application.
"""

import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from owl2jsonschema_gui.app import main
    main()
except ImportError as e:
    print(f"Error: Failed to import the GUI application: {e}")
    print("\nPlease make sure you have installed the required dependencies:")
    print("  pip install -e '.[gui]'")
    print("\nThis will install PyQt6 and other required packages.")
    sys.exit(1)
except Exception as e:
    print(f"Error starting the application: {e}")
    sys.exit(1)
#!/usr/bin/env python3
"""
PyCharm-compatible launcher for OntoJSON GUI with proper macOS app naming.

To use in PyCharm:
1. Set this file as your script path in Run Configuration
2. The app will launch with "OntoJSON" in the dock instead of "Python"
"""

import sys
import os
import platform

def setup_macos_app_name():
    """Set up proper app naming for macOS before any imports."""
    if platform.system() == 'Darwin':
        # Set environment variables BEFORE importing any GUI libraries
        os.environ['__CFBundleName'] = 'OntoJSON'
        os.environ['__CFBundleDisplayName'] = 'OntoJSON'
        os.environ['__CFBundleIdentifier'] = 'com.owl2jsonschema.ontojson'
        
        # Try to set process title
        try:
            import setproctitle
            setproctitle.setproctitle('OntoJSON')
        except ImportError:
            pass

def main():
    """Main entry point that ensures proper app naming."""
    # Set up macOS app name first
    setup_macos_app_name()
    
    # Add src to path
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
    
    # Now import and run the app
    from owl2jsonschema_gui.app import main as app_main
    app_main()

if __name__ == "__main__":
    main()
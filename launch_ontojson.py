#!/usr/bin/env python3
"""
OntoJSON launcher script with proper macOS app naming support.
"""

import sys
import os

# Set the app name before importing PyQt
if sys.platform == 'darwin':
    # This helps macOS recognize the app name
    os.environ['__CFBundleName'] = 'OntoJSON'
    os.environ['__CFBundleDisplayName'] = 'OntoJSON'
    os.environ['__CFBundleIdentifier'] = 'com.owl2jsonschema.ontojson'
    
    # Try to set the process name using setproctitle if available
    try:
        import setproctitle
        setproctitle.setproctitle('OntoJSON')
    except ImportError:
        pass
    
    # Try to use AppKit to set the app name
    try:
        from AppKit import NSProcessInfo
        NSProcessInfo.processInfo().setProcessName_('OntoJSON')
    except ImportError:
        pass

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Import and run the application
from owl2jsonschema_gui.app import main

if __name__ == "__main__":
    main()
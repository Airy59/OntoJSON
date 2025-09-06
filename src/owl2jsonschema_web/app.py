"""
Flask application entry point for OntoJSON Web.
"""

import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from owl2jsonschema_web import create_app

# Get configuration from environment
config_name = os.environ.get('FLASK_CONFIG', 'development')

# Create application
app = create_app()

if __name__ == '__main__':
    # Run the application
    port = int(os.environ.get('PORT', 5000))
    
    if config_name == 'development':
        app.run(
            host='0.0.0.0',
            port=port,
            debug=True,
            use_reloader=True
        )
    else:
        app.run(
            host='0.0.0.0',
            port=port,
            debug=False
        )
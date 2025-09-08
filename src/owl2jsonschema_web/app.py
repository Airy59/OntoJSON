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
    # Port configuration - change DEFAULT_PORT to use a different port
    # NOTE: Port 5000 is used by macOS AirPlay, so we avoid it
    DEFAULT_PORT = 9090  # Change this to your desired port (avoid 5000 on macOS)
    
    # Priority order for port selection:
    # 1. Command line argument (python app.py --port 8080)
    # 2. PORT environment variable
    # 3. DEFAULT_PORT constant defined above
    
    import argparse
    parser = argparse.ArgumentParser(description='OntoJSON Web Application')
    parser.add_argument('--port', type=int, help='Port to run the application on')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to (default: 0.0.0.0)')
    args = parser.parse_args()
    
    # Determine the port to use
    if args.port:
        port = args.port
        print(f"Using port from command line: {port}")
    elif os.environ.get('PORT'):
        port = int(os.environ.get('PORT'))
        print(f"Using port from environment variable: {port}")
    else:
        port = DEFAULT_PORT
        print(f"Using default port: {port}")
    
    host = args.host
    
    print(f"Starting OntoJSON Web App on http://{host}:{port}")
    print(f"Configuration: {config_name}")
    
    if config_name == 'development':
        app.run(
            host=host,
            port=port,
            debug=True,
            use_reloader=True
        )
    else:
        app.run(
            host=host,
            port=port,
            debug=False
        )
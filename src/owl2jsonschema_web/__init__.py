"""
Web application package for OWL to JSON Schema converter.

This package provides a Flask-based web interface and REST API
for the OntoJSON transformation engine.
"""

from flask import Flask
from flask_cors import CORS
from pathlib import Path
import os


def create_app(config=None):
    """
    Application factory for creating Flask app instances.
    
    Args:
        config: Configuration dictionary or object
        
    Returns:
        Configured Flask application
    """
    app = Flask(__name__,
                static_folder='static',
                template_folder='templates')
    
    # Load configuration
    if config:
        if isinstance(config, dict):
            app.config.update(config)
        else:
            app.config.from_object(config)
    else:
        # Load default configuration
        app.config.from_object('owl2jsonschema_web.config.DevelopmentConfig')
    
    # Enable CORS for API endpoints
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    
    # Set up upload folder
    upload_folder = Path(app.config.get('UPLOAD_FOLDER', '/tmp/ontojson_uploads'))
    upload_folder.mkdir(parents=True, exist_ok=True)
    app.config['UPLOAD_FOLDER'] = str(upload_folder)
    
    # Initialize extensions
    init_extensions(app)
    
    # Register blueprints
    register_blueprints(app)
    
    # Register error handlers
    register_error_handlers(app)
    
    return app


def init_extensions(app):
    """Initialize Flask extensions."""
    # Initialize session management
    from flask_session import Session
    app.config['SESSION_TYPE'] = 'filesystem'
    Session(app)
    
    # Initialize SocketIO for real-time updates (optional)
    if app.config.get('ENABLE_SOCKETIO', False):
        try:
            from flask_socketio import SocketIO
            socketio = SocketIO(app, cors_allowed_origins="*")
            app.socketio = socketio
        except ImportError:
            # SocketIO not installed, skip
            pass


def register_blueprints(app):
    """Register application blueprints."""
    from .api import api_bp
    from .views import main_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix='/api')


def register_error_handlers(app):
    """Register error handlers."""
    
    @app.errorhandler(404)
    def not_found(error):
        """Handle 404 errors."""
        from flask import jsonify, request
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Not found'}), 404
        return "Page not found", 404
    
    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 errors."""
        from flask import jsonify, request
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Internal server error'}), 500
        return "Internal server error", 500
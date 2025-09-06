"""
Configuration for Flask web application.
"""

import os
from pathlib import Path


class Config:
    """Base configuration."""
    
    # Flask settings
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Upload settings
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER') or '/tmp/ontojson_uploads'
    MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100MB max file size
    ALLOWED_EXTENSIONS = {
        'ttl', 'rdf', 'owl', 'xml', 'n3', 'nt', 'jsonld', 'json'
    }
    
    # Session settings
    SESSION_TYPE = 'filesystem'
    SESSION_FILE_DIR = '/tmp/ontojson_sessions'
    PERMANENT_SESSION_LIFETIME = 3600  # 1 hour
    
    # Task queue settings
    CELERY_BROKER_URL = os.environ.get('REDIS_URL') or 'redis://localhost:6379/0'
    CELERY_RESULT_BACKEND = os.environ.get('REDIS_URL') or 'redis://localhost:6379/0'
    
    # API settings
    API_RATE_LIMIT = '100/hour'
    API_VERSION = 'v1'
    
    # SocketIO settings (for real-time updates)
    ENABLE_SOCKETIO = False
    
    # Application settings
    APP_NAME = 'OntoJSON Web'
    APP_VERSION = '0.1.0'
    
    # Transformation defaults
    DEFAULT_LANGUAGE = 'en'
    DEFAULT_OUTPUT_FORMAT = 'json'
    DEFAULT_INSTANCE_COUNT = 10
    
    # Logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL') or 'INFO'
    LOG_FILE = os.environ.get('LOG_FILE') or '/tmp/ontojson_web.log'
    
    @staticmethod
    def init_app(app):
        """Initialize application with this config."""
        pass


class DevelopmentConfig(Config):
    """Development configuration."""
    
    DEBUG = True
    TESTING = False
    
    # Enable hot reloading
    TEMPLATES_AUTO_RELOAD = True
    
    # Enable SocketIO for development
    ENABLE_SOCKETIO = True
    
    # More verbose logging
    LOG_LEVEL = 'DEBUG'
    
    @classmethod
    def init_app(cls, app):
        """Initialize development environment."""
        Config.init_app(app)
        
        # Create necessary directories
        Path(cls.UPLOAD_FOLDER).mkdir(parents=True, exist_ok=True)
        Path(cls.SESSION_FILE_DIR).mkdir(parents=True, exist_ok=True)


class ProductionConfig(Config):
    """Production configuration."""
    
    DEBUG = False
    TESTING = False
    
    # Production settings
    SECRET_KEY = os.environ.get('SECRET_KEY')
    if not SECRET_KEY:
        raise ValueError("SECRET_KEY environment variable must be set in production")
    
    # Use environment variables for sensitive settings
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER') or '/var/ontojson/uploads'
    SESSION_FILE_DIR = os.environ.get('SESSION_FILE_DIR') or '/var/ontojson/sessions'
    
    # Production logging
    LOG_LEVEL = 'WARNING'
    LOG_FILE = '/var/log/ontojson_web.log'
    
    # Security headers
    SECURITY_HEADERS = {
        'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'SAMEORIGIN',
        'X-XSS-Protection': '1; mode=block',
        'Content-Security-Policy': "default-src 'self'"
    }
    
    @classmethod
    def init_app(cls, app):
        """Initialize production environment."""
        Config.init_app(app)
        
        # Set up production logging
        import logging
        from logging.handlers import RotatingFileHandler
        
        if not app.debug:
            file_handler = RotatingFileHandler(
                cls.LOG_FILE,
                maxBytes=10485760,  # 10MB
                backupCount=10
            )
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s %(levelname)s: %(message)s '
                '[in %(pathname)s:%(lineno)d]'
            ))
            file_handler.setLevel(getattr(logging, cls.LOG_LEVEL))
            app.logger.addHandler(file_handler)
            
            app.logger.setLevel(getattr(logging, cls.LOG_LEVEL))
            app.logger.info('OntoJSON Web startup')


class TestingConfig(Config):
    """Testing configuration."""
    
    TESTING = True
    DEBUG = True
    
    # Use in-memory database for testing
    UPLOAD_FOLDER = '/tmp/test_uploads'
    SESSION_FILE_DIR = '/tmp/test_sessions'
    
    # Disable CSRF for testing
    WTF_CSRF_ENABLED = False
    
    # Fast testing
    BCRYPT_LOG_ROUNDS = 4
    
    @classmethod
    def init_app(cls, app):
        """Initialize testing environment."""
        Config.init_app(app)


# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
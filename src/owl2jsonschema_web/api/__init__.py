"""
REST API for OWL to JSON Schema transformation.
"""

from flask import Blueprint

# Create API blueprint
api_bp = Blueprint('api', __name__)

# Import routes to register them
from . import routes
from . import transformation
from . import reverse_transformation
from . import configuration
from . import tasks

__all__ = ['api_bp']
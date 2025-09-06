"""
General API routes.
"""

from flask import jsonify, current_app
from . import api_bp


@api_bp.route('/', methods=['GET'])
def api_info():
    """Get API information."""
    return jsonify({
        'name': 'OntoJSON API',
        'version': current_app.config.get('API_VERSION', 'v1'),
        'endpoints': {
            'transform': '/api/transform',
            'transform_multiple': '/api/transform/multiple',
            'generate_abox': '/api/generate/abox',
            'convert_to_json': '/api/convert/json',
            'validate': '/api/validate',
            'rules': '/api/rules',
            'configurations': '/api/configurations',
            'tasks': '/api/tasks'
        }
    })


@api_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'timestamp': _get_timestamp()
    })


@api_bp.route('/rules', methods=['GET'])
def get_available_rules():
    """Get list of available transformation rules."""
    from owl2jsonschema.services import TransformationService
    
    service = TransformationService()
    rules = service.get_available_rules()
    
    return jsonify({
        'rules': rules,
        'count': len(rules)
    })


def _get_timestamp():
    """Get current timestamp."""
    from datetime import datetime
    return datetime.utcnow().isoformat()
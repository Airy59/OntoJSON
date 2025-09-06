"""
Configuration API endpoints.
"""

from flask import request, jsonify, current_app, session
from . import api_bp
from owl2jsonschema.services import ConfigurationService


@api_bp.route('/configurations', methods=['GET'])
def list_configurations():
    """List available configuration profiles."""
    try:
        config_service = ConfigurationService()
        profiles = config_service.list_profiles()
        
        return jsonify({
            'profiles': [profile.to_dict() for profile in profiles],
            'count': len(profiles)
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/configurations/<profile_name>', methods=['GET'])
def get_configuration(profile_name):
    """Get a specific configuration profile."""
    try:
        config_service = ConfigurationService()
        profile = config_service.load_profile(profile_name)
        
        if profile:
            return jsonify(profile.to_dict())
        else:
            return jsonify({'error': f'Profile {profile_name} not found'}), 404
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/configurations', methods=['POST'])
def create_configuration():
    """
    Create a new configuration profile.
    
    Expects JSON body with:
    - name: Profile name
    - description: Profile description
    - config: Configuration dictionary
    """
    try:
        if not request.json:
            return jsonify({'error': 'No data provided'}), 400
        
        required_fields = ['name', 'description', 'config']
        for field in required_fields:
            if field not in request.json:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        config_service = ConfigurationService()
        
        # Validate configuration
        is_valid, errors = config_service.validate_config(request.json['config'])
        if not is_valid:
            return jsonify({
                'error': 'Invalid configuration',
                'validation_errors': errors
            }), 400
        
        # Create profile
        from owl2jsonschema.services.configuration_service import ConfigurationProfile
        profile = ConfigurationProfile(
            name=request.json['name'],
            description=request.json['description'],
            config=request.json['config'],
            created_by=session.get('user_id', 'anonymous'),
            created_at=_get_timestamp()
        )
        
        # Save profile
        success = config_service.save_profile(profile)
        
        if success:
            return jsonify({
                'success': True,
                'profile': profile.to_dict()
            }), 201
        else:
            return jsonify({'error': 'Failed to save profile'}), 500
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/configurations/<profile_name>', methods=['PUT'])
def update_configuration(profile_name):
    """Update an existing configuration profile."""
    try:
        if not request.json:
            return jsonify({'error': 'No data provided'}), 400
        
        config_service = ConfigurationService()
        
        # Check if profile exists
        existing_profile = config_service.load_profile(profile_name)
        if not existing_profile:
            return jsonify({'error': f'Profile {profile_name} not found'}), 404
        
        # Update profile fields
        if 'description' in request.json:
            existing_profile.description = request.json['description']
        
        if 'config' in request.json:
            # Validate new configuration
            is_valid, errors = config_service.validate_config(request.json['config'])
            if not is_valid:
                return jsonify({
                    'error': 'Invalid configuration',
                    'validation_errors': errors
                }), 400
            existing_profile.config = request.json['config']
        
        # Save updated profile
        success = config_service.save_profile(existing_profile)
        
        if success:
            return jsonify({
                'success': True,
                'profile': existing_profile.to_dict()
            })
        else:
            return jsonify({'error': 'Failed to update profile'}), 500
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/configurations/<profile_name>', methods=['DELETE'])
def delete_configuration(profile_name):
    """Delete a configuration profile."""
    try:
        config_service = ConfigurationService()
        success = config_service.delete_profile(profile_name)
        
        if success:
            return jsonify({'success': True, 'message': f'Profile {profile_name} deleted'})
        else:
            return jsonify({'error': f'Profile {profile_name} not found'}), 404
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/configurations/validate', methods=['POST'])
def validate_configuration():
    """
    Validate a configuration without saving it.
    
    Expects JSON body with configuration dictionary.
    """
    try:
        if not request.json:
            return jsonify({'error': 'No configuration provided'}), 400
        
        config_service = ConfigurationService()
        is_valid, errors = config_service.validate_config(request.json)
        
        return jsonify({
            'valid': is_valid,
            'errors': errors
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/configurations/defaults/<rule_id>', methods=['GET'])
def get_rule_defaults(rule_id):
    """Get default configuration for a specific rule."""
    try:
        config_service = ConfigurationService()
        defaults = config_service.get_rule_defaults(rule_id)
        
        return jsonify({
            'rule_id': rule_id,
            'defaults': defaults
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/configurations/merge', methods=['POST'])
def merge_configurations():
    """
    Merge two configurations.
    
    Expects JSON body with:
    - base: Base configuration
    - override: Override configuration
    """
    try:
        if not request.json or 'base' not in request.json or 'override' not in request.json:
            return jsonify({'error': 'Base and override configurations required'}), 400
        
        config_service = ConfigurationService()
        merged = config_service.merge_configs(
            request.json['base'],
            request.json['override']
        )
        
        return jsonify({
            'merged': merged
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def _get_timestamp():
    """Get current timestamp."""
    from datetime import datetime
    return datetime.utcnow().isoformat()
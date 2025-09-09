"""
Transformation API endpoints.
"""

import os
import json
from flask import request, jsonify, current_app, session
from werkzeug.utils import secure_filename
from . import api_bp
from owl2jsonschema.services import TransformationService, FileService, ConfigurationService
from owl2jsonschema.services.file_service import WebUploadAdapter


def allowed_file(filename):
    """Check if file extension is allowed."""
    if '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    return ext in current_app.config['ALLOWED_EXTENSIONS']


@api_bp.route('/transform', methods=['POST'])
def transform_single():
    """
    Transform a single ontology to JSON Schema.
    
    Expects either:
    - A file upload with key 'file'
    - A multipart form with 'ontology' field (text content)
    - A JSON body with 'source' (URL or path)
    """
    try:
        # Initialize services
        file_service = FileService(WebUploadAdapter(current_app.config['UPLOAD_FOLDER']))
        transformation_service = TransformationService()
        config_service = ConfigurationService()
        
        # Get source
        source = None
        
        if 'file' in request.files:
            # Handle file upload
            file = request.files['file']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                # Save uploaded file
                upload_adapter = file_service.adapter
                if isinstance(upload_adapter, WebUploadAdapter):
                    source = upload_adapter.save_upload(file, filename)
                else:
                    # Fallback for non-web adapter
                    temp_path = file_service.get_temp_path(suffix=os.path.splitext(filename)[1])
                    file.save(temp_path)
                    source = temp_path
            else:
                return jsonify({'error': 'Invalid file or file type'}), 400
        
        elif 'ontology' in request.form:
            # Handle ontology content directly from form data
            import tempfile
            ontology_content = request.form['ontology']
            # Save to a temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.ttl', delete=False) as tmp_file:
                tmp_file.write(ontology_content)
                source = tmp_file.name
        
        elif request.json and 'source' in request.json:
            # Handle URL or path
            source = request.json['source']
            
            # Check if it's a local file that exists
            if os.path.exists(source):
                # Use the file directly
                source = os.path.abspath(source)
            else:
                # Try to resolve as URL or uploaded file
                source, is_remote = file_service.resolve_source(source)
        
        else:
            return jsonify({'error': 'No ontology source provided'}), 400
        
        # Get configuration from request or session
        if request.is_json:
            config_dict = request.json.get('config')
            language = request.json.get('language', 'en')
            rdf_format = request.json.get('format', 'auto')
        else:
            # For multipart/form-data, get from form or session
            config_dict = None
            language = request.form.get('language', 'en')
            rdf_format = request.form.get('format', 'auto')
        
        if not config_dict:
            # Try to get from session
            config_dict = session.get('config')
        
        config = config_service.create_config_from_dict(config_dict)
        
        # Perform transformation
        result = transformation_service.transform_single(
            source=source,
            config=config,
            language=language,
            rdf_format=rdf_format
        )
        
        if result.success:
            return jsonify({
                'success': True,
                'schema': result.schema,
                'metadata': result.metadata,
                'warnings': result.warnings
            })
        else:
            return jsonify({
                'success': False,
                'error': result.error
            }), 400
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/transform/multiple', methods=['POST'])
def transform_multiple():
    """
    Transform multiple ontologies to JSON Schema.
    
    Expects JSON body with:
    - sources: List of ontology sources (URLs or uploaded file IDs)
    - composite_metadata: Optional metadata for composite ontology
    - config: Optional transformation configuration
    """
    try:
        if not request.json or 'sources' not in request.json:
            return jsonify({'error': 'No sources provided'}), 400
        
        # Initialize services
        file_service = FileService(WebUploadAdapter(current_app.config['UPLOAD_FOLDER']))
        transformation_service = TransformationService()
        config_service = ConfigurationService()
        
        # Process sources
        sources = request.json['sources']
        resolved_sources = []
        
        for source in sources:
            resolved_source, _ = file_service.resolve_source(source)
            resolved_sources.append(resolved_source)
        
        # Get configuration
        config_dict = request.json.get('config')
        config = config_service.create_config_from_dict(config_dict)
        
        # Get optional parameters
        composite_metadata = request.json.get('composite_metadata')
        language = request.json.get('language', 'en')
        save_composite = request.json.get('save_composite', False)
        
        # Perform transformation
        result = transformation_service.transform_multiple(
            sources=resolved_sources,
            composite_metadata=composite_metadata,
            config=config,
            language=language,
            save_composite=save_composite
        )
        
        if result.success:
            return jsonify({
                'success': True,
                'schema': result.schema,
                'metadata': result.metadata,
                'warnings': result.warnings
            })
        else:
            return jsonify({
                'success': False,
                'error': result.error
            }), 400
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/generate/abox', methods=['POST'])
def generate_abox():
    """
    Generate ABox (individuals) from JSON Schema.
    
    Expects JSON body with:
    - schema: JSON Schema
    - instance_count: Number of instances to generate (default: 10)
    - seed: Optional random seed for reproducibility
    """
    try:
        if not request.json or 'schema' not in request.json:
            return jsonify({'error': 'No schema provided'}), 400
        
        transformation_service = TransformationService()
        
        schema = request.json['schema']
        instance_count = request.json.get('instance_count', 10)
        seed = request.json.get('seed')
        
        result = transformation_service.generate_abox(
            schema=schema,
            instance_count=instance_count,
            seed=seed
        )
        
        if result.success:
            return jsonify({
                'success': True,
                'abox': result.schema,
                'metadata': result.metadata
            })
        else:
            return jsonify({
                'success': False,
                'error': result.error
            }), 400
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/convert/json', methods=['POST'])
def convert_to_json():
    """
    Convert ABox data to JSON or JSON-LD.
    
    Expects JSON body with:
    - abox: ABox data (Turtle string or parsed data)
    - format: Output format ('json' or 'jsonld', default: 'json')
    """
    try:
        if not request.json or 'abox' not in request.json:
            return jsonify({'error': 'No ABox data provided'}), 400
        
        transformation_service = TransformationService()
        
        abox_data = request.json['abox']
        output_format = request.json.get('format', 'json')
        
        result = transformation_service.convert_abox_to_json(
            abox_data=abox_data,
            format=output_format
        )
        
        if result.success:
            return jsonify({
                'success': True,
                'json_data': result.schema,
                'metadata': result.metadata
            })
        else:
            return jsonify({
                'success': False,
                'error': result.error
            }), 400
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/pipeline', methods=['POST'])
def full_pipeline():
    """
    Execute full transformation pipeline: T-box → A-box → JSON instances.
    
    Expects JSON body with:
    - sources: List of ontology sources
    - config: Optional transformation configuration
    - generate_instances: Whether to generate instances (default: true)
    - instance_count: Number of instances to generate (default: 10)
    - output_format: Output format for instances ('json' or 'jsonld')
    """
    try:
        if not request.json or 'sources' not in request.json:
            return jsonify({'error': 'No sources provided'}), 400
        
        # Initialize services
        file_service = FileService(WebUploadAdapter(current_app.config['UPLOAD_FOLDER']))
        transformation_service = TransformationService()
        config_service = ConfigurationService()
        
        # Process sources
        sources = request.json['sources']
        resolved_sources = []
        
        for source in sources:
            resolved_source, _ = file_service.resolve_source(source)
            resolved_sources.append(resolved_source)
        
        # Get configuration
        config_dict = request.json.get('config')
        config = config_service.create_config_from_dict(config_dict)
        
        # Get optional parameters
        generate_instances = request.json.get('generate_instances', True)
        instance_count = request.json.get('instance_count', 10)
        output_format = request.json.get('output_format', 'json')
        
        # Execute pipeline
        tbox_result, abox_result, json_result = transformation_service.full_pipeline(
            sources=resolved_sources,
            config=config,
            generate_instances=generate_instances,
            instance_count=instance_count,
            output_format=output_format
        )
        
        response = {
            'success': tbox_result.success,
            'tbox': {
                'success': tbox_result.success,
                'schema': tbox_result.schema if tbox_result.success else None,
                'error': tbox_result.error,
                'metadata': tbox_result.metadata
            }
        }
        
        if abox_result:
            response['abox'] = {
                'success': abox_result.success,
                'data': abox_result.schema if abox_result.success else None,
                'error': abox_result.error,
                'metadata': abox_result.metadata
            }
        
        if json_result:
            response['json'] = {
                'success': json_result.success,
                'data': json_result.schema if json_result.success else None,
                'error': json_result.error,
                'metadata': json_result.metadata
            }
        
        status_code = 200 if tbox_result.success else 400
        return jsonify(response), status_code
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/validate', methods=['POST'])
def validate_ontology():
    """
    Validate an ontology source.
    
    Expects JSON body with:
    - source: Ontology source (URL or uploaded file ID)
    """
    try:
        if not request.json or 'source' not in request.json:
            return jsonify({'error': 'No source provided'}), 400
        
        # Initialize services
        file_service = FileService(WebUploadAdapter(current_app.config['UPLOAD_FOLDER']))
        transformation_service = TransformationService()
        
        # Resolve source
        source = request.json['source']
        resolved_source, _ = file_service.resolve_source(source)
        
        # Validate
        is_valid, error = transformation_service.validate_ontology_source(resolved_source)
        
        return jsonify({
            'valid': is_valid,
            'error': error,
            'source': source
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500
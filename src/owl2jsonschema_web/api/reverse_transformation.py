"""
Reverse Transformation API endpoints.

Endpoints for JSON Schema to OWL transformation.
"""

import os
import json
import tempfile
from flask import request, jsonify, current_app
from werkzeug.utils import secure_filename
from . import api_bp
from jsonschema2owl.services import (
    ReverseTransformationService,
    ValidationService,
    ReverseFileService
)
from jsonschema2owl.config import ReverseTransformationConfig


def allowed_json_file(filename):
    """Check if file is a JSON file."""
    if '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    return ext == 'json'


@api_bp.route('/reverse/transform', methods=['POST'])
def reverse_transform():
    """
    Transform JSON Schema to OWL ontology.
    
    Expects either:
    - A file upload with key 'file'
    - A JSON body with 'schema' (object or string)
    - A multipart form with 'schema' field (text content)
    
    Request body (JSON):
    {
        "schema": {...} or "path/to/schema.json",
        "base_namespace": "http://example.org/ontology#",
        "language": "en",
        "format": "turtle",
        "config": {...}
    }
    
    Response:
    {
        "success": true,
        "ontology": "...",
        "format": "turtle",
        "statistics": {...},
        "warnings": [...]
    }
    """
    try:
        # Initialize services
        transformation_service = ReverseTransformationService()
        file_service = ReverseFileService()
        
        # Get schema source
        schema_source = None
        
        if 'file' in request.files:
            # Handle file upload
            file = request.files['file']
            if file and allowed_json_file(file.filename):
                filename = secure_filename(file.filename)
                # Save to temporary file
                temp_path = file_service.get_temp_path(suffix='.json')
                file.save(temp_path)
                schema_source = temp_path
            else:
                return jsonify({'error': 'Invalid file or file type. Only JSON files are allowed.'}), 400
        
        elif 'schema' in request.form:
            # Handle schema content directly from form data
            schema_content = request.form['schema']
            try:
                # Try to parse as JSON
                schema_source = json.loads(schema_content)
            except json.JSONDecodeError:
                # If it's not valid JSON, save as file and let the service handle the error
                temp_path = file_service.get_temp_path(suffix='.json')
                with open(temp_path, 'w', encoding='utf-8') as f:
                    f.write(schema_content)
                schema_source = temp_path
        
        elif request.json and 'schema' in request.json:
            # Handle JSON body
            schema_source = request.json['schema']
        
        else:
            return jsonify({'error': 'No schema source provided'}), 400
        
        # Get configuration parameters
        if request.is_json:
            base_namespace = request.json.get('base_namespace', 'http://example.org/ontology#')
            language = request.json.get('language', 'en')
            output_format = request.json.get('format', 'turtle')
            config_dict = request.json.get('config')
        else:
            # For multipart/form-data
            base_namespace = request.form.get('base_namespace', 'http://example.org/ontology#')
            language = request.form.get('language', 'en')
            output_format = request.form.get('format', 'turtle')
            config_dict = None
        
        # Create configuration
        if config_dict:
            config = ReverseTransformationConfig()
            # Apply config settings (simplified for now)
            # In a full implementation, you'd iterate through config_dict
        else:
            config = None
        
        # Perform transformation
        result = transformation_service.transform(
            schema_source=schema_source,
            config=config,
            base_namespace=base_namespace,
            language=language,
            output_format=output_format
        )
        
        if result.success:
            return jsonify({
                'success': True,
                'ontology': result.ontology,
                'format': result.format,
                'statistics': result.statistics,
                'warnings': result.warnings
            })
        else:
            return jsonify({
                'success': False,
                'error': result.error
            }), 400
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/reverse/validate', methods=['POST'])
def reverse_validate():
    """
    Validate a JSON Schema.
    
    Request body:
    {
        "schema": {...} or "path/to/schema.json"
    }
    
    Response:
    {
        "valid": true,
        "error": null,
        "warnings": [...],
        "schema_version": "http://json-schema.org/draft-07/schema#"
    }
    """
    try:
        validation_service = ValidationService()
        file_service = ReverseFileService()
        
        # Get schema source
        schema_source = None
        
        if 'file' in request.files:
            # Handle file upload
            file = request.files['file']
            if file and allowed_json_file(file.filename):
                filename = secure_filename(file.filename)
                temp_path = file_service.get_temp_path(suffix='.json')
                file.save(temp_path)
                schema_source = temp_path
            else:
                return jsonify({'error': 'Invalid file or file type'}), 400
        
        elif request.json and 'schema' in request.json:
            schema_source = request.json['schema']
        
        else:
            return jsonify({'error': 'No schema provided'}), 400
        
        # Validate
        result = validation_service.validate(schema_source)
        
        return jsonify({
            'valid': result.valid,
            'error': result.error,
            'warnings': result.warnings,
            'schema_version': result.schema_version
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/reverse/preview', methods=['GET'])
def reverse_preview():
    """
    Get preview of transformation patterns.
    
    Returns information about how different JSON Schema constructs
    are mapped to OWL.
    
    Response:
    {
        "patterns": [
            {
                "json_schema": "definitions with properties",
                "owl": "OWL Classes with datatype/object properties",
                "example": {...}
            },
            ...
        ]
    }
    """
    patterns = [
        {
            "json_schema": "definitions",
            "owl": "OWL Classes",
            "description": "Each definition becomes an OWL class",
            "example": {
                "input": {"definitions": {"Person": {"type": "object"}}},
                "output": "Class: Person"
            }
        },
        {
            "json_schema": "properties with primitive types",
            "owl": "OWL Datatype Properties",
            "description": "String, number, boolean properties become datatype properties",
            "example": {
                "input": {"properties": {"name": {"type": "string"}}},
                "output": "DatatypeProperty: name with range xsd:string"
            }
        },
        {
            "json_schema": "properties with $ref",
            "owl": "OWL Object Properties",
            "description": "References to other definitions become object properties",
            "example": {
                "input": {"properties": {"address": {"$ref": "#/definitions/Address"}}},
                "output": "ObjectProperty: address with range Address"
            }
        },
        {
            "json_schema": "required array",
            "owl": "Cardinality Restrictions",
            "description": "Required properties get minimum cardinality 1",
            "example": {
                "input": {"required": ["name"]},
                "output": "Property: name with minCardinality 1"
            }
        },
        {
            "json_schema": "enum",
            "owl": "Named Individuals",
            "description": "Enum values become OWL named individuals",
            "example": {
                "input": {"enum": ["red", "green", "blue"]},
                "output": "NamedIndividuals: red, green, blue"
            }
        },
        {
            "json_schema": "allOf",
            "owl": "Class Hierarchy or Intersection",
            "description": "allOf can represent subclass relationships or intersections",
            "example": {
                "input": {"allOf": [{"$ref": "#/definitions/Person"}]},
                "output": "SubClassOf: Person"
            }
        },
        {
            "json_schema": "oneOf",
            "owl": "Class Union",
            "description": "oneOf becomes a union of classes",
            "example": {
                "input": {"oneOf": [{"$ref": "#/definitions/A"}, {"$ref": "#/definitions/B"}]},
                "output": "UnionOf: A, B"
            }
        }
    ]
    
    return jsonify({
        'patterns': patterns,
        'supported_formats': ['turtle', 'xml', 'json-ld']
    })


@api_bp.route('/reverse/formats', methods=['GET'])
def reverse_formats():
    """
    Get available output formats.
    
    Response:
    {
        "formats": [
            {"name": "turtle", "extension": ".ttl", "mime_type": "text/turtle"},
            ...
        ]
    }
    """
    formats = [
        {
            "name": "turtle",
            "extension": ".ttl",
            "mime_type": "text/turtle",
            "description": "Turtle (Terse RDF Triple Language)"
        },
        {
            "name": "xml",
            "extension": ".owl",
            "mime_type": "application/rdf+xml",
            "description": "RDF/XML"
        },
        {
            "name": "json-ld",
            "extension": ".jsonld",
            "mime_type": "application/ld+json",
            "description": "JSON-LD"
        }
    ]
    
    return jsonify({'formats': formats})
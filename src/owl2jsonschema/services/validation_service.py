"""
JSON Schema Validation Service

This module provides JSON Schema validation functionality for the web application.
"""

import json
from typing import Dict, Any, List, Optional
import jsonschema
from jsonschema import validate, ValidationError, Draft7Validator, Draft4Validator, Draft6Validator
from jsonschema.validators import Draft201909Validator, Draft202012Validator


class JSONSchemaValidator:
    """Validates JSON data against a JSON Schema."""
    
    def __init__(self, schema: Dict[str, Any], schema_version: Optional[str] = None):
        """
        Initialize the validator with a JSON Schema.
        
        Args:
            schema: The JSON Schema to validate against
            schema_version: The JSON Schema version to use (e.g., 'draft-04', 'draft-06', 'draft-07', '2019-09', '2020-12')
                          If None, will try to detect from schema's $schema property or default to draft-07
        """
        self.schema = schema
        
        # Determine which validator to use
        if schema_version:
            validator_class = self._get_validator_class(schema_version)
        else:
            # Try to detect from schema
            schema_uri = schema.get('$schema', '')
            if 'draft-04' in schema_uri or 'draft/4' in schema_uri:
                validator_class = Draft4Validator
            elif 'draft-06' in schema_uri or 'draft/6' in schema_uri:
                validator_class = Draft6Validator
            elif 'draft-07' in schema_uri or 'draft/7' in schema_uri:
                validator_class = Draft7Validator
            elif '2019-09' in schema_uri:
                validator_class = Draft201909Validator
            elif '2020-12' in schema_uri:
                validator_class = Draft202012Validator
            else:
                # Default to Draft 7
                validator_class = Draft7Validator
        
        # Pre-compile the validator for better performance
        self.validator = validator_class(schema)
    
    @staticmethod
    def _get_validator_class(schema_version: str):
        """Get the appropriate validator class for the schema version."""
        version_map = {
            'draft-04': Draft4Validator,
            'draft-4': Draft4Validator,
            'json-schema-draft-04': Draft4Validator,
            'draft-06': Draft6Validator,
            'draft-6': Draft6Validator,
            'json-schema-draft-06': Draft6Validator,
            'draft-07': Draft7Validator,
            'draft-7': Draft7Validator,
            'json-schema-draft-07': Draft7Validator,
            '2019-09': Draft201909Validator,
            'draft-2019-09': Draft201909Validator,
            '2020-12': Draft202012Validator,
            'draft-2020-12': Draft202012Validator,
        }
        
        validator_class = version_map.get(schema_version.lower())
        if not validator_class:
            # Default to Draft 7 if unknown version
            validator_class = Draft7Validator
        
        return validator_class
    
    def validate_instance(self, instance: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate a single JSON instance against the schema.
        
        Args:
            instance: The JSON instance to validate
            
        Returns:
            Dictionary with validation results
        """
        result = {
            'valid': True,
            'errors': []
        }
        
        try:
            self.validator.validate(instance)
        except ValidationError as e:
            result['valid'] = False
            result['errors'].append({
                'message': str(e.message),
                'path': list(e.absolute_path) if e.absolute_path else [],
                'schema_path': list(e.absolute_schema_path) if e.absolute_schema_path else [],
                'instance': e.instance if hasattr(e, 'instance') else None
            })
        except Exception as e:
            result['valid'] = False
            result['errors'].append({
                'message': f"Unexpected error: {str(e)}",
                'path': [],
                'schema_path': []
            })
        
        return result
    
    def validate_batch(self, instances: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validate multiple JSON instances against the schema.
        
        Args:
            instances: List of JSON instances to validate
            
        Returns:
            Dictionary with batch validation results
        """
        results = {
            'valid': True,
            'total': len(instances),
            'valid_count': 0,
            'invalid_count': 0,
            'errors': []
        }
        
        for i, instance in enumerate(instances):
            validation_result = self.validate_instance(instance)
            
            if validation_result['valid']:
                results['valid_count'] += 1
            else:
                results['invalid_count'] += 1
                results['valid'] = False
                
                # Add instance index to errors
                for error in validation_result['errors']:
                    error['instance_index'] = i
                    results['errors'].append(error)
        
        return results
    
    def validate_by_type(self, instances_by_type: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        """
        Validate JSON instances organized by type against their respective schema definitions.
        
        Args:
            instances_by_type: Dictionary mapping type names to lists of instances
            
        Returns:
            Dictionary with validation results per type
        """
        results = {
            'valid': True,
            'total_instances': 0,
            'valid_instances': 0,
            'invalid_instances': 0,
            'types': {}
        }
        
        definitions = self.schema.get('definitions', {})
        
        for type_name, instances in instances_by_type.items():
            if type_name not in definitions:
                results['types'][type_name] = {
                    'valid': False,
                    'error': f"No schema definition found for type '{type_name}'"
                }
                results['valid'] = False
                continue
            
            # Create a schema for this specific type
            type_schema = {
                "$schema": "http://json-schema.org/draft-07/schema#",
                "type": "object",
                "definitions": definitions,
                "$ref": f"#/definitions/{type_name}"
            }
            
            # Create a validator for this type (inherit the same schema version)
            schema_version = self.schema.get('$schema', '')
            type_validator = JSONSchemaValidator(type_schema, schema_version=None)
            
            # Validate instances of this type
            type_results = type_validator.validate_batch(instances)
            
            results['types'][type_name] = type_results
            results['total_instances'] += type_results['total']
            results['valid_instances'] += type_results['valid_count']
            results['invalid_instances'] += type_results['invalid_count']
            
            if not type_results['valid']:
                results['valid'] = False
        
        return results
    
    @staticmethod
    def check_schema_validity(schema: Dict[str, Any], schema_version: Optional[str] = None) -> Dict[str, Any]:
        """
        Check if a JSON Schema itself is valid.
        
        Args:
            schema: The JSON Schema to check
            schema_version: The JSON Schema version to validate against (optional)
            
        Returns:
            Dictionary with schema validity results
        """
        result = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        try:
            # Determine which validator to use
            if schema_version:
                validator_class = JSONSchemaValidator._get_validator_class(schema_version)
            else:
                # Try to detect from schema
                schema_uri = schema.get('$schema', '')
                if 'draft-04' in schema_uri or 'draft/4' in schema_uri:
                    validator_class = Draft4Validator
                elif 'draft-06' in schema_uri or 'draft/6' in schema_uri:
                    validator_class = Draft6Validator
                elif 'draft-07' in schema_uri or 'draft/7' in schema_uri:
                    validator_class = Draft7Validator
                elif '2019-09' in schema_uri:
                    validator_class = Draft201909Validator
                elif '2020-12' in schema_uri:
                    validator_class = Draft202012Validator
                else:
                    # Default to Draft 7
                    validator_class = Draft7Validator
            
            # Check if the schema is valid
            validator_class.check_schema(schema)
            
            # Check for non-standard keywords that might cause warnings
            non_standard_keywords = []
            for key in schema.keys():
                if key.startswith('$') and key not in ['$schema', '$id', '$ref', '$comment', '$defs']:
                    non_standard_keywords.append(key)
            
            if non_standard_keywords:
                result['warnings'].append(
                    f"Non-standard keywords found: {', '.join(non_standard_keywords)}. "
                    f"These may cause validation warnings."
                )
            
            # Check for x- prefixed extensions (allowed but may be ignored)
            x_keywords = [k for k in schema.keys() if k.startswith('x-')]
            if x_keywords:
                result['warnings'].append(
                    f"Extension keywords found: {', '.join(x_keywords)}. "
                    f"These are allowed but may be ignored by validators."
                )
            
        except jsonschema.SchemaError as e:
            result['valid'] = False
            result['errors'].append({
                'message': str(e.message),
                'path': list(e.absolute_path) if e.absolute_path else []
            })
        except Exception as e:
            result['valid'] = False
            result['errors'].append({
                'message': f"Unexpected error: {str(e)}"
            })
        
        return result
    
    @staticmethod
    def format_validation_report(validation_results: Dict[str, Any]) -> str:
        """
        Format validation results into a human-readable report.
        
        Args:
            validation_results: The validation results to format
            
        Returns:
            Formatted string report
        """
        report = []
        report.append("=" * 60)
        report.append("JSON SCHEMA VALIDATION REPORT")
        report.append("=" * 60)
        report.append("")
        
        if 'types' in validation_results:
            # Report for type-based validation
            report.append(f"Total Instances: {validation_results['total_instances']}")
            report.append(f"Valid Instances: {validation_results['valid_instances']}")
            report.append(f"Invalid Instances: {validation_results['invalid_instances']}")
            report.append("")
            
            if validation_results['valid']:
                report.append("✅ ALL INSTANCES VALID")
            else:
                report.append("❌ VALIDATION ERRORS FOUND")
                report.append("")
                
                for type_name, type_results in validation_results['types'].items():
                    if not type_results.get('valid', True):
                        report.append(f"\n{type_name}:")
                        report.append("-" * 40)
                        
                        if 'error' in type_results:
                            report.append(f"  Error: {type_results['error']}")
                        elif 'errors' in type_results:
                            for error in type_results['errors']:
                                instance_idx = error.get('instance_index', '?')
                                path = '.'.join(str(p) for p in error.get('path', []))
                                report.append(f"  Instance {instance_idx}:")
                                if path:
                                    report.append(f"    Path: {path}")
                                report.append(f"    Error: {error['message']}")
        else:
            # Report for simple validation
            if validation_results['valid']:
                report.append("✅ VALIDATION SUCCESSFUL")
                if 'valid_count' in validation_results:
                    report.append(f"Valid instances: {validation_results['valid_count']}")
            else:
                report.append("❌ VALIDATION FAILED")
                if 'invalid_count' in validation_results:
                    report.append(f"Invalid instances: {validation_results['invalid_count']}")
                
                if 'errors' in validation_results:
                    report.append("\nErrors:")
                    report.append("-" * 40)
                    for error in validation_results['errors']:
                        if 'instance_index' in error:
                            report.append(f"\nInstance {error['instance_index']}:")
                        path = '.'.join(str(p) for p in error.get('path', []))
                        if path:
                            report.append(f"  Path: {path}")
                        report.append(f"  Error: {error['message']}")
        
        return "\n".join(report)


class SchemaValidationService:
    """Service for handling schema validation in the web application."""
    
    @staticmethod
    def validate_json_against_schema(
        json_data: Any,
        schema: Dict[str, Any],
        schema_version: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Validate JSON data against a schema.
        
        Args:
            json_data: The JSON data to validate (can be a single instance, list, or dict of types)
            schema: The JSON Schema to validate against
            schema_version: The JSON Schema version to use (optional, will auto-detect if not provided)
            
        Returns:
            Validation results
        """
        validator = JSONSchemaValidator(schema, schema_version)
        
        # Check what type of data we have
        if isinstance(json_data, dict):
            # Check if it's instances organized by type
            if all(isinstance(v, list) for v in json_data.values()):
                # Looks like instances organized by type
                return validator.validate_by_type(json_data)
            else:
                # Single instance
                return validator.validate_instance(json_data)
        elif isinstance(json_data, list):
            # List of instances
            return validator.validate_batch(json_data)
        else:
            return {
                'valid': False,
                'errors': [{'message': 'Invalid JSON data format'}]
            }
    
    @staticmethod
    def validate_schema(schema: Dict[str, Any], schema_version: Optional[str] = None) -> Dict[str, Any]:
        """
        Validate that a JSON Schema itself is valid.
        
        Args:
            schema: The JSON Schema to validate
            schema_version: The JSON Schema version to validate against (optional)
            
        Returns:
            Schema validation results
        """
        return JSONSchemaValidator.check_schema_validity(schema, schema_version)
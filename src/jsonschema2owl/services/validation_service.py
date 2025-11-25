"""
Validation Service

Service for validating JSON Schemas before transformation.
"""

import json
import logging
from typing import Dict, Any, Optional, Union
from pathlib import Path
from dataclasses import dataclass


# Set up logging
logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of a JSON Schema validation."""
    valid: bool
    error: Optional[str] = None
    warnings: list = None
    schema_version: Optional[str] = None
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


class ValidationService:
    """
    Service for validating JSON Schemas.
    
    Validates that input is valid JSON Schema and provides
    warnings about potential transformation issues.
    """
    
    def __init__(self):
        """Initialize the validation service."""
        pass
    
    def validate(
        self,
        schema_source: Union[str, Dict[str, Any], Path]
    ) -> ValidationResult:
        """
        Validate a JSON Schema.
        
        Args:
            schema_source: JSON Schema as string, dict, or file path
            
        Returns:
            ValidationResult with validation status and any warnings
        """
        try:
            # Parse the schema
            schema_dict = self._parse_schema_source(schema_source)
            
            # Basic validation
            if not isinstance(schema_dict, dict):
                return ValidationResult(
                    valid=False,
                    error="Schema must be a JSON object"
                )
            
            # Collect warnings
            warnings = []
            
            # Check for $schema field
            schema_version = schema_dict.get('$schema')
            if not schema_version:
                warnings.append("Missing '$schema' field - schema version is recommended")
            
            # Check for definitions
            has_definitions = bool(
                schema_dict.get('definitions') or 
                schema_dict.get('$defs')
            )
            if not has_definitions:
                warnings.append("No 'definitions' or '$defs' found - schema may not generate classes")
            
            # Check for unsupported features that might cause issues
            self._check_unsupported_features(schema_dict, warnings)
            
            return ValidationResult(
                valid=True,
                schema_version=schema_version,
                warnings=warnings
            )
            
        except json.JSONDecodeError as e:
            return ValidationResult(
                valid=False,
                error=f"Invalid JSON: {e}"
            )
        except Exception as e:
            logger.error(f"Validation error: {e}", exc_info=True)
            return ValidationResult(
                valid=False,
                error=str(e)
            )
    
    def validate_file(self, file_path: Union[str, Path]) -> ValidationResult:
        """
        Validate a JSON Schema file.
        
        Args:
            file_path: Path to JSON Schema file
            
        Returns:
            ValidationResult with validation status and any warnings
        """
        return self.validate(file_path)
    
    def validate_dict(self, schema_dict: Dict[str, Any]) -> ValidationResult:
        """
        Validate a JSON Schema dictionary.
        
        Args:
            schema_dict: JSON Schema as dictionary
            
        Returns:
            ValidationResult with validation status and any warnings
        """
        return self.validate(schema_dict)
    
    def _parse_schema_source(
        self,
        schema_source: Union[str, Dict[str, Any], Path]
    ) -> Dict[str, Any]:
        """Parse schema source into dictionary."""
        if isinstance(schema_source, dict):
            return schema_source
        elif isinstance(schema_source, (str, Path)):
            source_str = str(schema_source)
            if source_str.startswith('{'):
                # It's JSON string
                return json.loads(source_str)
            else:
                # It's file path
                with open(source_str, 'r', encoding='utf-8') as f:
                    return json.load(f)
        else:
            raise ValueError(f"Invalid schema source type: {type(schema_source)}")
    
    def _check_unsupported_features(self, schema: Dict[str, Any], warnings: list):
        """Check for features that might not be fully supported in transformation."""
        
        # Check for complex conditionals
        if any(key in schema for key in ['if', 'then', 'else']):
            warnings.append(
                "Conditional schemas (if/then/else) may have limited OWL representation"
            )
        
        # Check for patternProperties
        if 'patternProperties' in schema:
            warnings.append(
                "patternProperties cannot be directly mapped to OWL"
            )
        
        # Check for additionalProperties with schema
        if isinstance(schema.get('additionalProperties'), dict):
            warnings.append(
                "Complex additionalProperties may have limited OWL representation"
            )
        
        # Recursively check definitions
        definitions = schema.get('definitions') or schema.get('$defs') or {}
        for def_name, definition in definitions.items():
            if isinstance(definition, dict):
                self._check_unsupported_features(definition, warnings)


# Export main class
__all__ = ['ValidationService', 'ValidationResult']
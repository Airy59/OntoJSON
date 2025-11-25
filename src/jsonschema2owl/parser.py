"""
JSON Schema Parser for OWL Transformation

This module parses and validates JSON Schema documents into internal model representation.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from .model import SchemaModel, DefinitionModel, PropertyModel


class SchemaParser:
    """Parse JSON Schema documents into internal model."""
    
    def __init__(self):
        """Initialize the schema parser."""
        self.supported_versions = [
            "http://json-schema.org/draft-04/schema#",
            "http://json-schema.org/draft-07/schema#",
            "https://json-schema.org/draft/2019-09/schema",
            "https://json-schema.org/draft/2020-12/schema"
        ]
    
    def parse(self, schema_str: str, validate: bool = True, filename: Optional[str] = None) -> SchemaModel:
        """
        Parse a JSON Schema from string.
        
        Args:
            schema_str: JSON Schema as string
            validate: Whether to validate the schema
            filename: Optional source filename for URI generation
        
        Returns:
            SchemaModel instance
        
        Raises:
            ValueError: If schema is invalid
            json.JSONDecodeError: If JSON is malformed
        """
        schema_dict = json.loads(schema_str)
        return self.parse_dict(schema_dict, validate, filename)
    
    def parse_file(self, file_path: str, validate: bool = True) -> SchemaModel:
        """
        Parse a JSON Schema from file.
        
        Args:
            file_path: Path to JSON Schema file
            validate: Whether to validate the schema
        
        Returns:
            SchemaModel instance
        
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If schema is invalid
        """
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"Schema file not found: {file_path}")
        
        with open(path, 'r') as f:
            schema_dict = json.load(f)
        
        # Pass filename for URI generation
        return self.parse_dict(schema_dict, validate, filename=str(path))
    
    def parse_dict(self, schema_dict: Dict[str, Any], validate: bool = True, filename: Optional[str] = None) -> SchemaModel:
        """
        Parse a JSON Schema from dictionary.
        
        Args:
            schema_dict: JSON Schema as dictionary
            validate: Whether to validate the schema
            filename: Optional source filename for URI generation
        
        Returns:
            SchemaModel instance
        
        Raises:
            ValueError: If schema is invalid
        """
        if validate:
            self._validate_schema(schema_dict)
        
        # Extract top-level information
        schema_id = schema_dict.get("$id") or schema_dict.get("id")
        schema_version = schema_dict.get("$schema", "http://json-schema.org/draft-07/schema#")
        title = schema_dict.get("title")
        description = schema_dict.get("description")
        
        # Parse definitions
        definitions = self._parse_definitions(schema_dict.get("definitions", {}))
        
        # Parse root-level properties (if any)
        root_properties = self._parse_properties(schema_dict.get("properties", {}))
        
        # Extract required fields
        required = schema_dict.get("required", [])
        
        # Extract metadata
        metadata = self._extract_metadata(schema_dict)
        
        return SchemaModel(
            schema_id=schema_id,
            schema_version=schema_version,
            title=title,
            description=description,
            definitions=definitions,
            properties=root_properties,
            required=required,
            metadata=metadata,
            source_filename=filename
        )
    
    def _validate_schema(self, schema: Dict[str, Any]) -> bool:
        """
        Validate basic schema structure.
        
        Args:
            schema: Schema dictionary
        
        Returns:
            True if valid
        
        Raises:
            ValueError: If schema is invalid
        """
        # Check if it's a dictionary
        if not isinstance(schema, dict):
            raise ValueError("Schema must be a dictionary")
        
        # Check schema version if present
        schema_version = schema.get("$schema")
        if schema_version and schema_version not in self.supported_versions:
            # Warning but don't fail - be permissive
            pass
        
        return True
    
    def _parse_definitions(self, definitions_dict: Dict[str, Any]) -> Dict[str, DefinitionModel]:
        """
        Parse definitions section.
        
        Args:
            definitions_dict: Definitions dictionary
        
        Returns:
            Dictionary mapping definition names to DefinitionModel objects
        """
        definitions = {}
        
        for name, def_schema in definitions_dict.items():
            if not isinstance(def_schema, dict):
                continue
            
            definition = self._parse_definition(name, def_schema)
            definitions[name] = definition
        
        return definitions
    
    def _parse_definition(self, name: str, def_schema: Dict[str, Any]) -> DefinitionModel:
        """
        Parse a single definition.
        
        Args:
            name: Definition name
            def_schema: Definition schema dictionary
        
        Returns:
            DefinitionModel instance
        """
        # Extract basic fields
        type_ = def_schema.get("type", "object")
        title = def_schema.get("title")
        description = def_schema.get("description")
        
        # Parse properties
        properties = self._parse_properties(def_schema.get("properties", {}))
        
        # Required fields
        required = def_schema.get("required", [])
        
        # Composition
        all_of = def_schema.get("allOf", [])
        one_of = def_schema.get("oneOf", [])
        any_of = def_schema.get("anyOf", [])
        not_ = def_schema.get("not")
        
        # Enumeration
        enum = def_schema.get("enum")
        const = def_schema.get("const")
        
        # Metadata
        metadata = self._extract_metadata(def_schema)
        
        return DefinitionModel(
            name=name,
            type=type_,
            title=title,
            description=description,
            properties=properties,
            required=required,
            all_of=all_of,
            one_of=one_of,
            any_of=any_of,
            not_=not_,
            enum=enum,
            const=const,
            metadata=metadata
        )
    
    def _parse_properties(self, properties_dict: Dict[str, Any]) -> Dict[str, PropertyModel]:
        """
        Parse properties section.
        
        Args:
            properties_dict: Properties dictionary
        
        Returns:
            Dictionary mapping property names to PropertyModel objects
        """
        properties = {}
        
        for name, prop_schema in properties_dict.items():
            if not isinstance(prop_schema, dict):
                continue
            
            prop_model = self._parse_property(name, prop_schema)
            properties[name] = prop_model
        
        return properties
    
    def _parse_property(self, name: str, prop_schema: Dict[str, Any]) -> PropertyModel:
        """
        Parse a single property.
        
        Args:
            name: Property name
            prop_schema: Property schema dictionary
        
        Returns:
            PropertyModel instance
        """
        # Extract basic fields
        type_ = prop_schema.get("type")
        title = prop_schema.get("title")
        description = prop_schema.get("description")
        ref = prop_schema.get("$ref")
        format_ = prop_schema.get("format")
        pattern = prop_schema.get("pattern")
        
        # Array-specific fields
        items = prop_schema.get("items")
        min_items = prop_schema.get("minItems")
        max_items = prop_schema.get("maxItems")
        
        # Composition
        one_of = prop_schema.get("oneOf")
        any_of = prop_schema.get("anyOf")
        all_of = prop_schema.get("allOf")
        
        # Constraints
        enum = prop_schema.get("enum")
        const = prop_schema.get("const")
        minimum = prop_schema.get("minimum")
        maximum = prop_schema.get("maximum")
        
        # Metadata
        metadata = self._extract_metadata(prop_schema)
        
        return PropertyModel(
            name=name,
            type=type_,
            title=title,
            description=description,
            ref=ref,
            items=items,
            min_items=min_items,
            max_items=max_items,
            one_of=one_of,
            any_of=any_of,
            all_of=all_of,
            enum=enum,
            const=const,
            format=format_,
            pattern=pattern,
            minimum=minimum,
            maximum=maximum,
            required=False,  # Will be set by parent definition
            metadata=metadata
        )
    
    def _extract_metadata(self, schema_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract custom metadata fields from schema.
        
        Extracts fields starting with "x-" or other custom fields.
        
        Args:
            schema_dict: Schema dictionary
        
        Returns:
            Metadata dictionary
        """
        metadata = {}
        
        # Standard metadata fields to skip
        standard_fields = {
            "$schema", "$id", "id", "title", "description", "type",
            "properties", "required", "definitions",
            "allOf", "oneOf", "anyOf", "not",
            "items", "minItems", "maxItems",
            "enum", "const", "format", "pattern",
            "minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum",
            "minLength", "maxLength", "multipleOf",
            "$ref", "$comment", "examples", "default"
        }
        
        for key, value in schema_dict.items():
            # Include custom fields (x- prefix or not in standard fields)
            if key.startswith("x-") or (key.startswith("$") and key not in standard_fields):
                metadata[key] = value
        
        return metadata
    
    def resolve_references(self, schema: SchemaModel) -> SchemaModel:
        """
        Resolve $ref references within the schema.
        
        Note: Currently returns schema as-is. 
        Full reference resolution can be implemented if needed.
        
        Args:
            schema: Schema model
        
        Returns:
            Schema with resolved references
        """
        # TODO: Implement reference resolution if needed
        # For now, we handle references during transformation
        return schema
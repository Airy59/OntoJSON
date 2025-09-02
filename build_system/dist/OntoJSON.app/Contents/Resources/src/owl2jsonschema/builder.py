"""
Schema Builder

This module implements the schema builder that constructs the final JSON Schema document.
"""

from typing import Dict, Any, Optional, List
import json
from copy import deepcopy


class SchemaBuilder:
    """Builds the final JSON Schema document from transformation results."""
    
    def __init__(self):
        """Initialize the schema builder."""
        self.schema = {
            "$schema": "http://json-schema.org/draft-07/schema#"
        }
        self.definitions = {}
        self.properties = {}
        self.required = []
        self.examples = []
    
    def add_to_root(self, key: str, value: Any):
        """
        Add a key-value pair to the root schema.
        
        Args:
            key: The key to add
            value: The value to add
        """
        self.schema[key] = value
    
    def add_to_schema(self, path: str, value: Any):
        """
        Add a value to the schema at a specific path.
        
        Args:
            path: Dot-separated path in the schema (e.g., "properties.name")
            value: The value to add
        """
        parts = path.split('.')
        current = self.schema
        
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        
        current[parts[-1]] = value
    
    def add_definition(self, name: str, schema: Dict[str, Any]):
        """
        Add a definition to the schema.
        
        Args:
            name: The name of the definition
            schema: The schema for the definition
        """
        # Clean the name to be a valid JSON Schema definition name
        clean_name = self._clean_definition_name(name)
        self.definitions[clean_name] = schema
    
    def add_property(self, name: str, schema: Dict[str, Any], required: bool = False):
        """
        Add a property to the root schema.
        
        Args:
            name: The property name
            schema: The property schema
            required: Whether the property is required
        """
        self.properties[name] = schema
        if required and name not in self.required:
            self.required.append(name)
    
    def add_property_to_class(self, class_name: str, property_name: str, property_schema: Dict[str, Any]):
        """
        Add a property to a specific class definition.
        
        Args:
            class_name: The name of the class
            property_name: The name of the property
            property_schema: The schema for the property
        """
        clean_class_name = self._clean_definition_name(class_name)
        
        if clean_class_name in self.definitions:
            if "properties" not in self.definitions[clean_class_name]:
                self.definitions[clean_class_name]["properties"] = {}
            
            self.definitions[clean_class_name]["properties"][property_name] = property_schema
    
    def add_required_to_class(self, class_name: str, property_name: str):
        """
        Mark a property as required for a specific class.
        
        Args:
            class_name: The name of the class
            property_name: The name of the property
        """
        clean_class_name = self._clean_definition_name(class_name)
        
        if clean_class_name in self.definitions:
            if "required" not in self.definitions[clean_class_name]:
                self.definitions[clean_class_name]["required"] = []
            
            if property_name not in self.definitions[clean_class_name]["required"]:
                self.definitions[clean_class_name]["required"].append(property_name)
    
    def add_example(self, example: Dict[str, Any]):
        """
        Add an example to the schema.
        
        Args:
            example: The example to add
        """
        self.examples.append(example)
    
    def merge_schema(self, schema: Dict[str, Any]):
        """
        Merge another schema into this one.
        
        Args:
            schema: The schema to merge
        """
        if "definitions" in schema:
            self.definitions.update(schema["definitions"])
        
        if "properties" in schema:
            self.properties.update(schema["properties"])
        
        if "required" in schema:
            for req in schema["required"]:
                if req not in self.required:
                    self.required.append(req)
        
        if "examples" in schema:
            self.examples.extend(schema["examples"])
        
        # Merge other top-level properties
        for key, value in schema.items():
            if key not in ["definitions", "properties", "required", "examples", "$schema"]:
                self.schema[key] = value
    
    def build(self) -> Dict[str, Any]:
        """
        Build and return the final JSON Schema.
        
        Returns:
            The complete JSON Schema
        """
        # Add definitions if any
        if self.definitions:
            self.schema["definitions"] = self.definitions
        
        # Add properties if any
        if self.properties:
            self.schema["type"] = "object"
            self.schema["properties"] = self.properties
            
            # Add required if any
            if self.required:
                self.schema["required"] = self.required
        elif self.definitions:
            # If we only have definitions and no root properties,
            # create a schema that references one of the definitions
            # or allows any of them
            if not self.schema.get("type"):
                # Make it a definitions-only schema with a default type
                self.schema["type"] = "object"
                self.schema["additionalProperties"] = False
                # Optionally, we could add a oneOf to allow any of the defined types
                # self.schema["oneOf"] = [
                #     {"$ref": f"#/definitions/{name}"}
                #     for name in self.definitions.keys()
                # ]
        
        # Add examples if any
        if self.examples:
            self.schema["examples"] = self.examples
        
        # Ensure we have at least a basic structure
        if "type" not in self.schema and "definitions" not in self.schema:
            self.schema["type"] = "object"
        
        return deepcopy(self.schema)
    
    def to_json(self, indent: int = 2) -> str:
        """
        Convert the schema to JSON string.
        
        Args:
            indent: Number of spaces for indentation
        
        Returns:
            JSON string representation of the schema
        """
        return json.dumps(self.build(), indent=indent)
    
    def _clean_definition_name(self, name: str) -> str:
        """
        Clean a name to be a valid JSON Schema definition name.
        
        Args:
            name: The name to clean
        
        Returns:
            The cleaned name
        """
        # Remove namespace prefixes if present
        if ':' in name:
            name = name.split(':')[-1]
        
        # Remove URI parts if present
        if '/' in name:
            name = name.split('/')[-1]
        
        if '#' in name:
            name = name.split('#')[-1]
        
        # Replace invalid characters
        name = name.replace(' ', '_')
        name = name.replace('-', '_')
        
        return name
    
    def reset(self):
        """Reset the builder to start fresh."""
        self.schema = {
            "$schema": "http://json-schema.org/draft-07/schema#"
        }
        self.definitions = {}
        self.properties = {}
        self.required = []
        self.examples = []
    
    def __repr__(self) -> str:
        """String representation of the builder."""
        return f"SchemaBuilder(definitions={len(self.definitions)}, properties={len(self.properties)})"


class ReferenceResolver:
    """Resolves references between schemas."""
    
    def __init__(self, base_uri: str = ""):
        """
        Initialize the reference resolver.
        
        Args:
            base_uri: The base URI for references
        """
        self.base_uri = base_uri
        self.references = {}
    
    def add_reference(self, name: str, uri: str):
        """
        Add a reference mapping.
        
        Args:
            name: The name to reference
            uri: The URI it maps to
        """
        self.references[name] = uri
    
    def resolve(self, reference: str) -> str:
        """
        Resolve a reference to its URI.
        
        Args:
            reference: The reference to resolve
        
        Returns:
            The resolved URI
        """
        if reference in self.references:
            return self.references[reference]
        
        # If not found, create a definition reference
        return f"#/definitions/{reference}"
    
    def create_ref(self, target: str) -> Dict[str, str]:
        """
        Create a JSON Schema $ref object.
        
        Args:
            target: The target to reference
        
        Returns:
            A dictionary with $ref key
        """
        return {"$ref": self.resolve(target)}
"""
URI Generator for JSON Schema to OWL Transformation

This module handles the generation of consistent OWL URIs from JSON Schema names.
"""

import re
import os
from typing import Dict, Optional
from urllib.parse import quote


class URIGenerator:
    """Generate consistent OWL URIs from schema names."""
    
    def __init__(
        self,
        base_namespace: str = "https://cdm.ovh/examples/",
        class_pattern: str = "{base}{name}",
        property_pattern: str = "{base}{name}",
        individual_pattern: str = "{base}individual/{name}",
        schema_name: Optional[str] = None
    ):
        """
        Initialize the URI generator.
        
        Args:
            base_namespace: Base namespace URI
            class_pattern: Pattern for class URIs
            property_pattern: Pattern for property URIs
            individual_pattern: Pattern for individual URIs
            schema_name: Optional schema name extracted from filename
        """
        self.base_namespace = base_namespace
        self.class_pattern = class_pattern
        self.property_pattern = property_pattern
        self.individual_pattern = individual_pattern
        self.schema_name = schema_name
        self.namespace_map: Dict[str, str] = {}
        self.uri_cache: Dict[str, str] = {}
    
    def set_base_namespace(self, namespace: str):
        """Set the base namespace URI."""
        # Don't automatically add # - it will be added when needed
        self.base_namespace = namespace
        self.uri_cache.clear()
    
    def set_schema_name(self, schema_name: str):
        """Set the schema name for URI generation."""
        self.schema_name = schema_name
        self.uri_cache.clear()
    
    @staticmethod
    def extract_schema_name(filename: str) -> str:
        """
        Extract schema name from filename, removing extension.
        
        Args:
            filename: Path to schema file (can be full or relative path)
        
        Returns:
            Schema name without extension
        
        Examples:
            "offlineOSDM.json" → "offlineOSDM"
            "/path/to/company_hierarchy.json" → "company_hierarchy"
            "schema.yaml" → "schema"
        """
        if not filename:
            return "ontology"
        
        basename = os.path.basename(filename)
        name_without_ext = os.path.splitext(basename)[0]
        
        # Return name or default if empty
        return name_without_ext if name_without_ext else "ontology"
    
    def set_namespace(self, prefix: str, uri: str):
        """
        Register a namespace prefix.
        
        Args:
            prefix: Namespace prefix
            uri: Namespace URI
        """
        self.namespace_map[prefix] = uri
    
    def get_namespace(self, prefix: str) -> Optional[str]:
        """Get namespace URI for a prefix."""
        return self.namespace_map.get(prefix)
    
    def normalize_name(self, name: str) -> str:
        """
        Normalize a name for use in URIs.
        
        - Converts to PascalCase for classes
        - Handles special characters
        - Ensures valid URI component
        
        Args:
            name: The name to normalize
        
        Returns:
            Normalized name suitable for URIs
        """
        if not name:
            return "Unnamed"
        
        # Remove leading/trailing whitespace
        name = name.strip()
        
        # Replace common separators with underscores
        name = re.sub(r'[\s\-\.]+', '_', name)
        
        # Remove characters that are not alphanumeric or underscore
        name = re.sub(r'[^\w]', '', name)
        
        # Ensure it starts with a letter (prepend 'C' if it starts with a digit)
        if name and name[0].isdigit():
            name = 'C' + name
        
        return name if name else "Unnamed"
    
    def generate_class_uri(self, name: str, namespace: Optional[str] = None) -> str:
        """
        Generate a URI for an OWL class.
        
        The URI format is: base_namespace + schema_name + "#" + class_name
        For example: "https://cdm.ovh/examples/offlineOSDM#Person"
        
        Args:
            name: Class name from schema
            namespace: Optional namespace override
        
        Returns:
            Generated class URI
        """
        cache_key = f"class:{namespace or 'default'}:{self.schema_name or 'default'}:{name}"
        if cache_key in self.uri_cache:
            return self.uri_cache[cache_key]
        
        normalized_name = self.normalize_name(name)
        
        if namespace:
            base = namespace
        else:
            # Use namespace with schema name
            base = self.get_namespace_with_schema()
        
        uri = self.class_pattern.format(base=base, name=normalized_name)
        self.uri_cache[cache_key] = uri
        return uri
    
    def generate_property_uri(
        self,
        name: str,
        namespace: Optional[str] = None,
        owner_class: Optional[str] = None,
        naming_strategy: str = "scoped"
    ) -> str:
        """
        Generate a URI for an OWL property.
        
        The URI format is: base_namespace + schema_name + "#" + property_name
        For example: "https://cdm.ovh/examples/offlineOSDM#Person_name"
        
        Args:
            name: Property name from schema
            namespace: Optional namespace override
            owner_class: Optional owning class name for scoped properties
            naming_strategy: Naming strategy - "scoped" (ClassName_propertyName),
                           "reverse_scoped" (propertyName_ClassName), or
                           "global" (just propertyName)
        
        Returns:
            Generated property URI
        """
        # Build cache key including owner class and strategy
        cache_key = f"property:{namespace or 'default'}:{self.schema_name or 'default'}:{owner_class or 'global'}:{name}:{naming_strategy}"
        if cache_key in self.uri_cache:
            return self.uri_cache[cache_key]
        
        normalized_name = self.normalize_name(name)
        
        if namespace:
            base = namespace
        else:
            # Use namespace with schema name
            base = self.get_namespace_with_schema()
        
        # Apply naming strategy
        if owner_class and naming_strategy == "scoped":
            # ClassName_propertyName
            normalized_owner = self.normalize_name(owner_class)
            property_name = f"{normalized_owner}_{normalized_name}"
        elif owner_class and naming_strategy == "reverse_scoped":
            # propertyName_ClassName
            normalized_owner = self.normalize_name(owner_class)
            property_name = f"{normalized_name}_{normalized_owner}"
        else:
            # global - just propertyName
            property_name = normalized_name
        
        uri = self.property_pattern.format(base=base, name=property_name)
        self.uri_cache[cache_key] = uri
        return uri
    
    def generate_individual_uri(self, name: str, namespace: Optional[str] = None) -> str:
        """
        Generate a URI for an OWL named individual.
        
        The URI format is: base_namespace + schema_name + "#individual/" + name
        For example: "https://cdm.ovh/examples/offlineOSDM#individual/TicketType1"
        
        Args:
            name: Individual name (e.g., enum value)
            namespace: Optional namespace override
        
        Returns:
            Generated individual URI
        """
        cache_key = f"individual:{namespace or 'default'}:{self.schema_name or 'default'}:{name}"
        if cache_key in self.uri_cache:
            return self.uri_cache[cache_key]
        
        normalized_name = self.normalize_name(name)
        
        if namespace:
            base = namespace
        else:
            # Use namespace with schema name
            base = self.get_namespace_with_schema()
        
        uri = self.individual_pattern.format(base=base, name=normalized_name)
        self.uri_cache[cache_key] = uri
        return uri
    
    def generate_ontology_uri(self, schema_id: Optional[str] = None) -> str:
        """
        Generate a URI for the ontology itself.
        
        The ontology URI is constructed as: base_namespace + schema_name
        For example: "https://cdm.ovh/examples/offlineOSDM"
        
        Args:
            schema_id: Optional schema $id (will NOT be used as ontology URI,
                      but stored as rdfs:seeAlso)
        
        Returns:
            Ontology URI
        """
        # Build ontology URI from base namespace + schema name
        base = self.base_namespace
        
        # Remove trailing # or / if present
        if base.endswith('#'):
            base = base[:-1]
        elif base.endswith('/'):
            base = base[:-1]
        
        # Add schema name if available
        if self.schema_name:
            return f"{base}/{self.schema_name}"
        
        # Default fallback
        return base
    
    def get_namespace_with_schema(self) -> str:
        """
        Get the full namespace including schema name and fragment separator.
        
        For classes and properties, the namespace is: base + schema_name + "#"
        For example: "https://cdm.ovh/examples/offlineOSDM#"
        
        Returns:
            Full namespace with # separator
        """
        ontology_uri = self.generate_ontology_uri()
        return f"{ontology_uri}#"
    
    def resolve_reference(self, ref: str) -> Optional[str]:
        """
        Resolve a $ref reference to extract the definition name.
        
        Args:
            ref: JSON Schema $ref string (e.g., "#/definitions/Person")
        
        Returns:
            Definition name or None
        """
        if not ref:
            return None
        
        # Handle local references (#/definitions/Name)
        if ref.startswith('#/definitions/'):
            return ref.split('/')[-1]
        
        # Handle relative references
        if '/' in ref:
            return ref.split('/')[-1]
        
        return ref
    
    def extract_definition_name(self, ref: str) -> str:
        """
        Extract definition name from a reference.
        
        Args:
            ref: JSON Schema reference
        
        Returns:
            Definition name
        """
        name = self.resolve_reference(ref)
        return name if name else "Unknown"
    
    def validate_uri(self, uri: str) -> bool:
        """
        Validate that a URI is well-formed.
        
        Args:
            uri: URI to validate
        
        Returns:
            True if valid, False otherwise
        """
        if not uri:
            return False
        
        # Basic validation - should contain :// or be a fragment
        return '://' in uri or uri.startswith('#')
    
    def clear_cache(self):
        """Clear the URI cache."""
        self.uri_cache.clear()
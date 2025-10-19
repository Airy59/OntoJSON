"""
Cross-Reference Resolver

This module handles cross-references between JSON schemas generated from different ontologies.
It tracks class-to-ontology mappings and rewrites internal references to external references
when generating component schemas.
"""

from typing import Dict, Any, List, Set, Optional
from pathlib import Path
import re


class CrossReferenceResolver:
    """
    Resolves cross-references between component schemas.
    
    When multiple ontologies are transformed into separate component schemas,
    this resolver ensures that references to classes from other ontologies
    are converted to external JSON Schema $ref URIs.
    """
    
    def __init__(self):
        """Initialize the cross-reference resolver."""
        # Map class URI -> ontology source name
        self.class_to_source: Dict[str, str] = {}
        
        # Map class name -> ontology source name
        self.class_name_to_source: Dict[str, str] = {}
        
        # Map source name -> set of class URIs
        self.source_to_classes: Dict[str, Set[str]] = {}
        
        # Map source name -> set of class names (cleaned)
        self.source_to_class_names: Dict[str, Set[str]] = {}
    
    def register_class(self, class_uri: str, class_name: str, source_name: str):
        """
        Register a class from a specific ontology source.
        
        Args:
            class_uri: The full URI of the class
            class_name: The cleaned name used in the schema (without namespace)
            source_name: The name of the source ontology (e.g., filename without extension)
        """
        self.class_to_source[class_uri] = source_name
        self.class_name_to_source[class_name] = source_name
        
        if source_name not in self.source_to_classes:
            self.source_to_classes[source_name] = set()
        self.source_to_classes[source_name].add(class_uri)
        
        if source_name not in self.source_to_class_names:
            self.source_to_class_names[source_name] = set()
        self.source_to_class_names[source_name].add(class_name)
    
    def get_source_for_class(self, class_name: str) -> Optional[str]:
        """
        Get the source ontology name for a given class.
        
        Args:
            class_name: The cleaned class name
            
        Returns:
            The source ontology name, or None if not found
        """
        return self.class_name_to_source.get(class_name)
    
    def is_external_reference(self, class_name: str, current_source: str) -> bool:
        """
        Check if a class reference is external to the current source.
        
        Args:
            class_name: The class name being referenced
            current_source: The current ontology source name
            
        Returns:
            True if the class is from a different source, False otherwise
        """
        source = self.get_source_for_class(class_name)
        return source is not None and source != current_source
    
    def resolve_reference(self, class_name: str, current_source: str, 
                         component_suffix: str = "_schema.json") -> str:
        """
        Resolve a class reference to either internal or external $ref.
        
        Args:
            class_name: The class name being referenced
            current_source: The current ontology source name
            component_suffix: Suffix for component schema files
            
        Returns:
            The appropriate $ref string (internal or external)
        """
        source = self.get_source_for_class(class_name)
        
        if source is None or source == current_source:
            # Internal reference
            return f"#/definitions/{class_name}"
        else:
            # External reference to another component
            return f"{source}{component_suffix}#/definitions/{class_name}"
    
    def rewrite_schema_references(self, schema: Dict[str, Any], current_source: str,
                                  component_suffix: str = "_schema.json") -> Dict[str, Any]:
        """
        Rewrite all $ref in a schema to use external references where appropriate.
        
        Args:
            schema: The JSON schema to process
            current_source: The source name of this schema
            component_suffix: Suffix for component schema files
            
        Returns:
            The schema with rewritten references
        """
        return self._rewrite_refs_recursive(schema, current_source, component_suffix)
    
    def _rewrite_refs_recursive(self, obj: Any, current_source: str,
                                component_suffix: str) -> Any:
        """
        Recursively rewrite $ref values in a schema object.
        
        Args:
            obj: The object to process (dict, list, or primitive)
            current_source: The source name of this schema
            component_suffix: Suffix for component schema files
            
        Returns:
            The processed object with rewritten references
        """
        if isinstance(obj, dict):
            result = {}
            for key, value in obj.items():
                if key == "$ref" and isinstance(value, str):
                    # This is a reference - check if it needs rewriting
                    result[key] = self._rewrite_single_ref(value, current_source, component_suffix)
                else:
                    # Recursively process
                    result[key] = self._rewrite_refs_recursive(value, current_source, component_suffix)
            return result
        elif isinstance(obj, list):
            return [self._rewrite_refs_recursive(item, current_source, component_suffix) 
                   for item in obj]
        else:
            return obj
    
    def _rewrite_single_ref(self, ref: str, current_source: str, 
                           component_suffix: str) -> str:
        """
        Rewrite a single $ref value if it's a cross-reference.
        
        Args:
            ref: The reference string (e.g., "#/definitions/Person")
            current_source: The source name of this schema
            component_suffix: Suffix for component schema files
            
        Returns:
            The rewritten reference string
        """
        # Match internal references like #/definitions/ClassName
        internal_ref_pattern = r'^#/definitions/(.+)$'
        match = re.match(internal_ref_pattern, ref)
        
        if match:
            class_name = match.group(1)
            # Check if this is an external reference
            if self.is_external_reference(class_name, current_source):
                return self.resolve_reference(class_name, current_source, component_suffix)
        
        # Return unchanged if not an internal reference or if it's truly internal
        return ref
    
    def get_external_dependencies(self, source_name: str) -> Set[str]:
        """
        Get the set of external sources that a given source depends on.
        
        Args:
            source_name: The source ontology name
            
        Returns:
            Set of external source names that this source references
        """
        dependencies = set()
        
        # Check all classes to see which sources they reference
        # This would require tracking which classes reference which other classes
        # For now, this is a placeholder - could be enhanced by tracking
        # property ranges and restrictions
        
        return dependencies
    
    def generate_dependency_graph(self) -> Dict[str, List[str]]:
        """
        Generate a dependency graph showing which sources depend on which.
        
        Returns:
            Dictionary mapping source name to list of sources it depends on
        """
        graph = {}
        for source in self.source_to_class_names.keys():
            graph[source] = list(self.get_external_dependencies(source))
        return graph
    
    def __repr__(self) -> str:
        """String representation of the resolver."""
        return (f"CrossReferenceResolver(sources={len(self.source_to_classes)}, "
                f"classes={len(self.class_to_source)})")
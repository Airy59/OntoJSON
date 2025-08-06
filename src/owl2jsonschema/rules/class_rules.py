"""
Class Transformation Rules

This module contains transformation rules for OWL classes.
"""

from typing import Any, Dict, List, Optional
from ..visitor import TransformationRule
from ..model import OntologyModel, OntologyClass, OntologyRestriction
from ..builder import ReferenceResolver


class ClassToObjectRule(TransformationRule):
    """Transform OWL classes to JSON Schema objects."""
    
    def visit_ontology(self, ontology: OntologyModel) -> Dict[str, Any]:
        """Visit the ontology and transform all classes."""
        if not self.is_enabled():
            return None
        
        definitions = {}
        
        for owl_class in ontology.classes:
            schema = self._transform_class(owl_class)
            if schema:
                # Extract class name from URI
                class_name = self._get_class_name(owl_class.uri)
                definitions[class_name] = schema
        
        return {"definitions": definitions} if definitions else None
    
    def visit_class(self, owl_class: OntologyClass) -> Dict[str, Any]:
        """Transform a single OWL class to JSON Schema."""
        if not self.is_enabled():
            return None
        
        return self._transform_class(owl_class)
    
    def _transform_class(self, owl_class: OntologyClass) -> Dict[str, Any]:
        """Transform an OWL class to a JSON Schema object."""
        schema = {
            "type": "object",
            "properties": {}
        }
        
        # Add title from label if available
        label = owl_class.get_label(self.get_option("language", "en"))
        if label:
            schema["title"] = label
        
        # Add description from comment if available
        comment = owl_class.get_comment(self.get_option("language", "en"))
        if comment:
            schema["description"] = comment
        
        # Add URI as metadata if configured
        if self.get_option("include_uri", False):
            schema["$comment"] = f"OWL Class: {owl_class.uri}"
        
        return schema
    
    def _get_class_name(self, uri: str) -> str:
        """Extract class name from URI."""
        if '#' in uri:
            return uri.split('#')[-1]
        elif '/' in uri:
            return uri.split('/')[-1]
        return uri


class ClassHierarchyRule(TransformationRule):
    """Transform OWL class hierarchy to JSON Schema inheritance using allOf."""
    
    def visit_ontology(self, ontology: OntologyModel) -> Dict[str, Any]:
        """Process class hierarchy for all classes."""
        if not self.is_enabled():
            return None
        
        updates = {}
        resolver = ReferenceResolver()
        
        for owl_class in ontology.classes:
            if owl_class.super_classes:
                class_name = self._get_class_name(owl_class.uri)
                all_of = []
                
                for super_uri in owl_class.super_classes:
                    super_name = self._get_class_name(super_uri)
                    all_of.append(resolver.create_ref(super_name))
                
                # The class should extend its parents
                if all_of:
                    updates[class_name] = {
                        "allOf": all_of + [
                            {
                                "type": "object",
                                "properties": {}
                            }
                        ]
                    }
        
        return {"hierarchy_updates": updates} if updates else None
    
    def visit_class(self, owl_class: OntologyClass) -> Dict[str, Any]:
        """Process hierarchy for a single class."""
        if not self.is_enabled():
            return None
        
        if not owl_class.super_classes:
            return None
        
        resolver = ReferenceResolver()
        all_of = []
        
        for super_uri in owl_class.super_classes:
            super_name = self._get_class_name(super_uri)
            all_of.append(resolver.create_ref(super_name))
        
        if all_of:
            return {
                "allOf": all_of + [
                    {
                        "type": "object",
                        "properties": {}
                    }
                ]
            }
        
        return None
    
    def _get_class_name(self, uri: str) -> str:
        """Extract class name from URI."""
        if '#' in uri:
            return uri.split('#')[-1]
        elif '/' in uri:
            return uri.split('/')[-1]
        return uri


class ClassRestrictionsRule(TransformationRule):
    """Transform OWL class restrictions to JSON Schema constraints."""
    
    def visit_class(self, owl_class: OntologyClass) -> Dict[str, Any]:
        """Process restrictions for a class."""
        if not self.is_enabled():
            return None
        
        if not owl_class.restrictions:
            return None
        
        constraints = {}
        required = []
        
        for restriction in owl_class.restrictions:
            constraint = self._process_restriction(restriction)
            if constraint:
                if "property" in constraint:
                    prop_name = constraint["property"]
                    if "schema" in constraint:
                        if "properties" not in constraints:
                            constraints["properties"] = {}
                        constraints["properties"][prop_name] = constraint["schema"]
                    
                    if constraint.get("required", False):
                        required.append(prop_name)
        
        if required:
            constraints["required"] = required
        
        return constraints if constraints else None
    
    def _process_restriction(self, restriction: OntologyRestriction) -> Optional[Dict[str, Any]]:
        """Process a single restriction."""
        from ..model import CardinalityRestriction, ValueRestriction
        
        prop_name = self._get_property_name(restriction.property_uri)
        result = {"property": prop_name}
        
        if isinstance(restriction, CardinalityRestriction):
            schema = {}
            
            if restriction.min_cardinality is not None:
                if restriction.min_cardinality == 1:
                    result["required"] = True
                elif restriction.min_cardinality > 1:
                    schema["type"] = "array"
                    schema["minItems"] = restriction.min_cardinality
            
            if restriction.max_cardinality is not None:
                if restriction.max_cardinality == 1:
                    # Single value, not an array
                    pass
                else:
                    if "type" not in schema:
                        schema["type"] = "array"
                    schema["maxItems"] = restriction.max_cardinality
            
            if restriction.exact_cardinality is not None:
                if restriction.exact_cardinality == 1:
                    result["required"] = True
                else:
                    schema["type"] = "array"
                    schema["minItems"] = restriction.exact_cardinality
                    schema["maxItems"] = restriction.exact_cardinality
            
            if schema:
                result["schema"] = schema
        
        elif isinstance(restriction, ValueRestriction):
            schema = {}
            
            if restriction.restriction_type == "allValuesFrom":
                # All values must be from the specified class/type
                filler_ref = self._create_type_reference(restriction.filler)
                if self.get_option("use_arrays_for_restrictions", False):
                    schema["type"] = "array"
                    schema["items"] = filler_ref
                else:
                    schema = filler_ref
            
            elif restriction.restriction_type == "someValuesFrom":
                # At least one value must be from the specified class/type
                filler_ref = self._create_type_reference(restriction.filler)
                schema["type"] = "array"
                schema["minItems"] = 1
                schema["items"] = filler_ref
            
            elif restriction.restriction_type == "hasValue":
                # Must have this specific value
                schema["const"] = restriction.value
            
            if schema:
                result["schema"] = schema
        
        return result
    
    def _get_property_name(self, uri: str) -> str:
        """Extract property name from URI."""
        if '#' in uri:
            return uri.split('#')[-1]
        elif '/' in uri:
            return uri.split('/')[-1]
        return uri
    
    def _create_type_reference(self, type_uri: str) -> Dict[str, Any]:
        """Create a type reference for a class or datatype."""
        # Check if it's an XSD datatype
        xsd_types = {
            "http://www.w3.org/2001/XMLSchema#string": {"type": "string"},
            "http://www.w3.org/2001/XMLSchema#integer": {"type": "integer"},
            "http://www.w3.org/2001/XMLSchema#decimal": {"type": "number"},
            "http://www.w3.org/2001/XMLSchema#boolean": {"type": "boolean"},
            "http://www.w3.org/2001/XMLSchema#date": {"type": "string", "format": "date"},
            "http://www.w3.org/2001/XMLSchema#dateTime": {"type": "string", "format": "date-time"},
        }
        
        if type_uri in xsd_types:
            return xsd_types[type_uri]
        
        # Otherwise, it's a reference to another class
        class_name = self._get_property_name(type_uri)
        return {"$ref": f"#/definitions/{class_name}"}
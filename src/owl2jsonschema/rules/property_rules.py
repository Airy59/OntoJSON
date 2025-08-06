"""
Property Transformation Rules

This module contains transformation rules for OWL properties.
"""

from typing import Any, Dict, List, Optional
from ..visitor import TransformationRule
from ..model import (
    OntologyModel,
    ObjectProperty,
    DatatypeProperty,
    OntologyClass,
    CardinalityRestriction
)


class ObjectPropertyRule(TransformationRule):
    """Transform OWL object properties to JSON Schema properties."""
    
    def visit_ontology(self, ontology: OntologyModel) -> List[Dict[str, Any]]:
        """Process all object properties in the ontology."""
        if not self.is_enabled():
            return None
        
        results = []
        
        for property in ontology.object_properties:
            prop_result = self._transform_object_property(property, ontology)
            if prop_result:
                results.extend(prop_result)
        
        return results if results else None
    
    def visit_object_property(self, property: ObjectProperty) -> Dict[str, Any]:
        """Transform a single object property."""
        if not self.is_enabled():
            return None
        
        prop_name = self._get_property_name(property.uri)
        schema = {}
        
        # Object properties reference other objects
        if property.range:
            # If there's a specific range, reference it
            range_class = self._get_property_name(property.range[0])
            schema = {"$ref": f"#/definitions/{range_class}"}
        else:
            # Generic object reference
            schema = {"type": "object"}
        
        # Add title and description if available
        if property.label:
            schema["title"] = property.get_label(self.get_option("language", "en"))
        
        if property.comment:
            schema["description"] = property.get_comment(self.get_option("language", "en"))
        
        return {
            "property": prop_name,
            "schema": schema,
            "domains": property.domain
        }
    
    def _transform_object_property(self, property: ObjectProperty, ontology: OntologyModel) -> List[Dict[str, Any]]:
        """Transform an object property and assign it to its domain classes."""
        prop_name = self._get_property_name(property.uri)
        results = []
        
        # Create the property schema
        if property.range:
            # If there's a specific range, reference it
            range_class = self._get_property_name(property.range[0])
            schema = {"$ref": f"#/definitions/{range_class}"}
        else:
            # Generic object reference
            schema = {"type": "object"}
        
        # Add title and description if available
        if property.label:
            schema["title"] = property.get_label(self.get_option("language", "en"))
        
        if property.comment:
            schema["description"] = property.get_comment(self.get_option("language", "en"))
        
        # Handle functional properties (max cardinality 1)
        if property.functional:
            # Functional properties have at most one value
            pass  # Single value is the default
        else:
            # Non-functional properties can have multiple values
            if self.get_option("arrays_for_non_functional", True):
                schema = {
                    "type": "array",
                    "items": schema
                }
        
        # Assign to domain classes
        if property.domain:
            for domain_uri in property.domain:
                domain_name = self._get_property_name(domain_uri)
                results.append({
                    "class": domain_name,
                    "property": {
                        "name": prop_name,
                        "schema": schema
                    }
                })
        else:
            # If no domain specified, could be a global property
            if self.get_option("include_global_properties", False):
                results.append({
                    "class": "_global",
                    "property": {
                        "name": prop_name,
                        "schema": schema
                    }
                })
        
        return results
    
    def _get_property_name(self, uri: str) -> str:
        """Extract property name from URI."""
        if '#' in uri:
            return uri.split('#')[-1]
        elif '/' in uri:
            return uri.split('/')[-1]
        return uri


class DatatypePropertyRule(TransformationRule):
    """Transform OWL datatype properties to JSON Schema properties."""
    
    def visit_ontology(self, ontology: OntologyModel) -> List[Dict[str, Any]]:
        """Process all datatype properties in the ontology."""
        if not self.is_enabled():
            return None
        
        results = []
        
        for property in ontology.datatype_properties:
            prop_result = self._transform_datatype_property(property, ontology)
            if prop_result:
                results.extend(prop_result)
        
        return results if results else None
    
    def visit_datatype_property(self, property: DatatypeProperty) -> Dict[str, Any]:
        """Transform a single datatype property."""
        if not self.is_enabled():
            return None
        
        prop_name = self._get_property_name(property.uri)
        schema = self._get_datatype_schema(property.range[0] if property.range else None)
        
        # Add title and description if available
        if property.label:
            schema["title"] = property.get_label(self.get_option("language", "en"))
        
        if property.comment:
            schema["description"] = property.get_comment(self.get_option("language", "en"))
        
        return {
            "property": prop_name,
            "schema": schema,
            "domains": property.domain
        }
    
    def _transform_datatype_property(self, property: DatatypeProperty, ontology: OntologyModel) -> List[Dict[str, Any]]:
        """Transform a datatype property and assign it to its domain classes."""
        prop_name = self._get_property_name(property.uri)
        results = []
        
        # Create the property schema based on its range
        schema = self._get_datatype_schema(property.range[0] if property.range else None)
        
        # Add title and description if available
        if property.label:
            schema["title"] = property.get_label(self.get_option("language", "en"))
        
        if property.comment:
            schema["description"] = property.get_comment(self.get_option("language", "en"))
        
        # Handle functional properties
        if property.functional:
            # Functional properties have at most one value
            pass  # Single value is the default
        else:
            # Non-functional properties can have multiple values
            if self.get_option("arrays_for_non_functional", False):
                schema = {
                    "type": "array",
                    "items": schema
                }
        
        # Assign to domain classes
        if property.domain:
            for domain_uri in property.domain:
                domain_name = self._get_property_name(domain_uri)
                results.append({
                    "class": domain_name,
                    "property": {
                        "name": prop_name,
                        "schema": schema
                    }
                })
        else:
            # If no domain specified, could be a global property
            if self.get_option("include_global_properties", False):
                results.append({
                    "class": "_global",
                    "property": {
                        "name": prop_name,
                        "schema": schema
                    }
                })
        
        return results
    
    def _get_datatype_schema(self, datatype_uri: Optional[str]) -> Dict[str, Any]:
        """Get JSON Schema for an XSD datatype."""
        if not datatype_uri:
            return {"type": "string"}  # Default to string
        
        # Map XSD datatypes to JSON Schema types
        xsd_mapping = {
            "http://www.w3.org/2001/XMLSchema#string": {"type": "string"},
            "http://www.w3.org/2001/XMLSchema#boolean": {"type": "boolean"},
            "http://www.w3.org/2001/XMLSchema#decimal": {"type": "number"},
            "http://www.w3.org/2001/XMLSchema#float": {"type": "number"},
            "http://www.w3.org/2001/XMLSchema#double": {"type": "number"},
            "http://www.w3.org/2001/XMLSchema#integer": {"type": "integer"},
            "http://www.w3.org/2001/XMLSchema#nonNegativeInteger": {"type": "integer", "minimum": 0},
            "http://www.w3.org/2001/XMLSchema#positiveInteger": {"type": "integer", "minimum": 1},
            "http://www.w3.org/2001/XMLSchema#nonPositiveInteger": {"type": "integer", "maximum": 0},
            "http://www.w3.org/2001/XMLSchema#negativeInteger": {"type": "integer", "maximum": -1},
            "http://www.w3.org/2001/XMLSchema#long": {"type": "integer"},
            "http://www.w3.org/2001/XMLSchema#int": {"type": "integer"},
            "http://www.w3.org/2001/XMLSchema#short": {"type": "integer"},
            "http://www.w3.org/2001/XMLSchema#byte": {"type": "integer", "minimum": -128, "maximum": 127},
            "http://www.w3.org/2001/XMLSchema#unsignedLong": {"type": "integer", "minimum": 0},
            "http://www.w3.org/2001/XMLSchema#unsignedInt": {"type": "integer", "minimum": 0},
            "http://www.w3.org/2001/XMLSchema#unsignedShort": {"type": "integer", "minimum": 0, "maximum": 65535},
            "http://www.w3.org/2001/XMLSchema#unsignedByte": {"type": "integer", "minimum": 0, "maximum": 255},
            "http://www.w3.org/2001/XMLSchema#date": {"type": "string", "format": "date"},
            "http://www.w3.org/2001/XMLSchema#time": {"type": "string", "format": "time"},
            "http://www.w3.org/2001/XMLSchema#dateTime": {"type": "string", "format": "date-time"},
            "http://www.w3.org/2001/XMLSchema#duration": {"type": "string"},
            "http://www.w3.org/2001/XMLSchema#anyURI": {"type": "string", "format": "uri"},
        }
        
        # Also check without namespace
        datatype_name = datatype_uri.split('#')[-1] if '#' in datatype_uri else datatype_uri
        xsd_base = "http://www.w3.org/2001/XMLSchema#"
        
        if datatype_uri in xsd_mapping:
            return xsd_mapping[datatype_uri].copy()
        elif xsd_base + datatype_name in xsd_mapping:
            return xsd_mapping[xsd_base + datatype_name].copy()
        else:
            # Default to string for unknown types
            return {"type": "string"}
    
    def _get_property_name(self, uri: str) -> str:
        """Extract property name from URI."""
        if '#' in uri:
            return uri.split('#')[-1]
        elif '/' in uri:
            return uri.split('/')[-1]
        return uri


class PropertyCardinalityRule(TransformationRule):
    """Transform property cardinality restrictions to JSON Schema constraints."""
    
    def visit_class(self, owl_class: OntologyClass) -> Dict[str, Any]:
        """Process cardinality restrictions for a class."""
        if not self.is_enabled():
            return None
        
        constraints = {}
        required = []
        
        for restriction in owl_class.restrictions:
            if isinstance(restriction, CardinalityRestriction):
                prop_name = self._get_property_name(restriction.property_uri)
                schema = self._process_cardinality(restriction)
                
                if schema:
                    if "properties" not in constraints:
                        constraints["properties"] = {}
                    
                    # Merge with existing property schema if present
                    if prop_name in constraints["properties"]:
                        constraints["properties"][prop_name].update(schema)
                    else:
                        constraints["properties"][prop_name] = schema
                
                # Check if property is required
                if restriction.min_cardinality and restriction.min_cardinality >= 1:
                    if prop_name not in required:
                        required.append(prop_name)
        
        if required:
            constraints["required"] = required
        
        return constraints if constraints else None
    
    def _process_cardinality(self, restriction: CardinalityRestriction) -> Dict[str, Any]:
        """Process a cardinality restriction."""
        schema = {}
        use_arrays = self.get_option("use_arrays", True)
        
        if restriction.exact_cardinality is not None:
            if restriction.exact_cardinality == 1:
                # Exactly one value - no array needed
                pass
            elif use_arrays:
                schema["type"] = "array"
                schema["minItems"] = restriction.exact_cardinality
                schema["maxItems"] = restriction.exact_cardinality
        else:
            # Check min and max separately
            if restriction.min_cardinality is not None and restriction.max_cardinality is not None:
                if restriction.min_cardinality == 0 and restriction.max_cardinality == 1:
                    # Optional single value
                    pass
                elif use_arrays:
                    schema["type"] = "array"
                    if restriction.min_cardinality > 0:
                        schema["minItems"] = restriction.min_cardinality
                    schema["maxItems"] = restriction.max_cardinality
            elif restriction.min_cardinality is not None:
                if restriction.min_cardinality > 1 and use_arrays:
                    schema["type"] = "array"
                    schema["minItems"] = restriction.min_cardinality
            elif restriction.max_cardinality is not None:
                if restriction.max_cardinality == 1:
                    # At most one value
                    pass
                elif use_arrays:
                    schema["type"] = "array"
                    schema["maxItems"] = restriction.max_cardinality
        
        return schema
    
    def _get_property_name(self, uri: str) -> str:
        """Extract property name from URI."""
        if '#' in uri:
            return uri.split('#')[-1]
        elif '/' in uri:
            return uri.split('/')[-1]
        return uri


class PropertyRestrictionsRule(TransformationRule):
    """Transform property value restrictions to JSON Schema validation."""
    
    def visit_class(self, owl_class: OntologyClass) -> Dict[str, Any]:
        """Process property restrictions for a class."""
        if not self.is_enabled():
            return None
        
        from ..model import ValueRestriction
        
        constraints = {}
        
        for restriction in owl_class.restrictions:
            if isinstance(restriction, ValueRestriction):
                prop_name = self._get_property_name(restriction.property_uri)
                schema = self._process_value_restriction(restriction)
                
                if schema:
                    if "properties" not in constraints:
                        constraints["properties"] = {}
                    
                    # Merge with existing property schema if present
                    if prop_name in constraints["properties"]:
                        # Combine constraints
                        existing = constraints["properties"][prop_name]
                        if "allOf" in existing:
                            existing["allOf"].append(schema)
                        else:
                            constraints["properties"][prop_name] = {
                                "allOf": [existing, schema]
                            }
                    else:
                        constraints["properties"][prop_name] = schema
        
        return constraints if constraints else None
    
    def _process_value_restriction(self, restriction) -> Dict[str, Any]:
        """Process a value restriction."""
        schema = {}
        
        if restriction.restriction_type == "allValuesFrom":
            # All values must be from the specified type
            type_ref = self._create_type_reference(restriction.filler)
            if self.get_option("arrays_for_restrictions", False):
                schema = {
                    "type": "array",
                    "items": type_ref
                }
            else:
                schema = type_ref
        
        elif restriction.restriction_type == "someValuesFrom":
            # At least one value must be from the specified type
            type_ref = self._create_type_reference(restriction.filler)
            schema = {
                "type": "array",
                "minItems": 1,
                "contains": type_ref
            }
        
        elif restriction.restriction_type == "hasValue":
            # Must have this specific value
            schema = {"const": restriction.value}
        
        return schema
    
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
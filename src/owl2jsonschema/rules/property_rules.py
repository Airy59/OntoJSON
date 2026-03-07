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
from ..utils import clean_string


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
        range_class = None
        
        # Object properties reference other objects
        if property.range:
            # If there's a specific range, reference it
            range_class = self._get_property_name(property.range[0])
        
        # Create oneOf pattern: either a full object reference or an @id reference
        if range_class:
            schema = {
                "oneOf": [
                    {"$ref": f"#/definitions/{range_class}"},
                    {
                        "type": "object",
                        "properties": {
                            "@id": {
                                "type": "string",
                                "format": "uri"
                            }
                        },
                        "required": ["@id"],
                        "additionalProperties": False
                    }
                ]
            }
            # Add description that clarifies the target type
            base_description = f"Reference to {range_class} or @id"
            if property.comment:
                comment = property.get_comment(self.get_option("language", "en"))
                # Clean the comment to remove tab sequences
                schema["description"] = clean_string(f"{comment} ({base_description})")
            else:
                schema["description"] = clean_string(base_description)
        else:
            # No range specified - in OWL this means owl:Thing (any object)
            # In JSON Schema, use empty schema {} which accepts any value
            # For object properties, we still provide the oneOf pattern for flexibility
            schema = {
                "oneOf": [
                    {},  # Empty schema accepts any value (equivalent to owl:Thing)
                    {
                        "type": "object",
                        "properties": {
                            "@id": {
                                "type": "string",
                                "format": "uri"
                            }
                        },
                        "required": ["@id"],
                        "additionalProperties": False
                    }
                ]
            }
            if property.comment:
                # Clean the comment to remove tab sequences
                schema["description"] = clean_string(property.get_comment(self.get_option("language", "en")))
        
        # Add title if available
        if property.label:
            schema["title"] = property.get_label(self.get_option("language", "en"))
        
        return {
            "property": prop_name,
            "schema": schema,
            "domains": property.domain
        }
    
    def _transform_object_property(self, property: ObjectProperty, ontology: OntologyModel) -> List[Dict[str, Any]]:
        """Transform an object property and assign it to its domain classes."""
        prop_name = self._get_property_name(property.uri)
        results = []
        
        # Determine domain - either explicit or inferred from inverse or super properties
        domains = list(property.domain) if property.domain else []
        
        # If no explicit domain and has an inverse, infer domain from inverse's range
        if not domains and property.inverse_of:
            inverse_prop = self._find_property_by_uri(property.inverse_of, ontology)
            if inverse_prop and inverse_prop.range:
                # The domain of a property is the range of its inverse
                domains = inverse_prop.range
        
        # If still no domain, inherit from super properties (OWL subproperty semantics)
        if not domains and property.super_properties:
            for super_prop_uri in property.super_properties:
                super_prop = self._find_property_by_uri(super_prop_uri, ontology)
                if super_prop and super_prop.domain:
                    domains = list(super_prop.domain)
                    break  # Use first super property with a domain
        
        # Determine if property is functional
        is_functional = property.functional
        
        # If not explicitly functional but has an inverse that is inverse-functional,
        # then this property is functional
        if not is_functional and property.inverse_of:
            inverse_prop = self._find_property_by_uri(property.inverse_of, ontology)
            if inverse_prop and inverse_prop.inverse_functional:
                is_functional = True
        
        # Similarly, if this property is inverse-functional and has an inverse,
        # then the inverse is functional
        if property.inverse_functional and property.inverse_of:
            # This will be handled when processing the inverse property
            pass
        
        # Create the property schema with oneOf pattern for object references
        range_class = None
        range_uri = None
        range_schema = None
        
        if property.range:
            # If there's a specific range, it could be a simple URI or a complex expression
            range_uri = property.range[0]
            
            # Check if range is a complex class expression (dict)
            if isinstance(range_uri, dict):
                # Handle unionOf, intersectionOf, etc.
                range_schema = self._create_range_schema(range_uri)
            else:
                # Simple URI range
                range_class = self._get_property_name(range_uri)
                
                # Special handling for owl:Thing - map to _Thing
                if range_uri == "http://www.w3.org/2002/07/owl#Thing" or range_class == "Thing":
                    range_class = "_Thing"
        else:
            # If no explicit range and has an inverse, try to infer range
            if property.inverse_of:
                inverse_prop = self._find_property_by_uri(property.inverse_of, ontology)
                if inverse_prop:
                    if inverse_prop.domain:
                        # The range of a property is the domain of its inverse
                        range_uri = inverse_prop.domain[0]
                        
                        if isinstance(range_uri, dict):
                            range_schema = self._create_range_schema(range_uri)
                        else:
                            range_class = self._get_property_name(range_uri)
                            
                            # Special handling for owl:Thing - map to _Thing
                            if range_uri == "http://www.w3.org/2002/07/owl#Thing" or range_class == "Thing":
                                range_class = "_Thing"
                    else:
                        # Try to infer from usage - check which classes use the inverse property
                        inferred_domain = self._infer_property_domain_from_usage(inverse_prop, ontology)
                        if inferred_domain:
                            range_uri = inferred_domain[0]
                            
                            if isinstance(range_uri, dict):
                                range_schema = self._create_range_schema(range_uri)
                            else:
                                range_class = self._get_property_name(range_uri)
                                
                                # Special handling for owl:Thing - map to _Thing
                                if range_uri == "http://www.w3.org/2002/07/owl#Thing" or range_class == "Thing":
                                    range_class = "_Thing"
            
            # If still no range, inherit from super properties (OWL subproperty semantics)
            if not range_uri and not range_schema and property.super_properties:
                for super_prop_uri in property.super_properties:
                    super_prop = self._find_property_by_uri(super_prop_uri, ontology)
                    if super_prop and super_prop.range:
                        range_uri = super_prop.range[0]
                        
                        if isinstance(range_uri, dict):
                            range_schema = self._create_range_schema(range_uri)
                        else:
                            range_class = self._get_property_name(range_uri)
                            
                            # Special handling for owl:Thing - map to _Thing
                            if range_uri == "http://www.w3.org/2002/07/owl#Thing" or range_class == "Thing":
                                range_class = "_Thing"
                        break  # Use first super property with a range
        
        # Create oneOf pattern: either a full object reference or an @id reference
        if range_schema:
            # Use the complex range schema (e.g., unionOf)
            schema = range_schema
        elif range_class:
            schema = {
                "oneOf": [
                    {"$ref": f"#/definitions/{range_class}"},
                    {
                        "type": "object",
                        "properties": {
                            "@id": {
                                "type": "string",
                                "format": "uri"
                            }
                        },
                        "required": ["@id"],
                        "additionalProperties": False
                    }
                ]
            }
        else:
            # No range specified - in OWL this means owl:Thing (any object)
            # In JSON Schema, use empty schema {} which accepts any value
            # For object properties, we still provide the oneOf pattern for flexibility
            schema = {
                "oneOf": [
                    {},  # Empty schema accepts any value (equivalent to owl:Thing)
                    {
                        "type": "object",
                        "properties": {
                            "@id": {
                                "type": "string",
                                "format": "uri"
                            }
                        },
                        "required": ["@id"],
                        "additionalProperties": False
                    }
                ]
            }
        
        # Add title and description if available
        if property.label:
            schema["title"] = property.get_label(self.get_option("language", "en"))
        
        # Build description with comment and subproperty info
        description_parts = []
        if property.comment:
            # Clean the comment to remove tab sequences
            description_parts.append(clean_string(property.get_comment(self.get_option("language", "en"))))
        
        # Add subproperty information
        if property.super_properties:
            super_prop_names = [self._get_property_name(uri) for uri in property.super_properties]
            if len(super_prop_names) == 1:
                description_parts.append(f"Subproperty of {super_prop_names[0]}")
            else:
                description_parts.append(f"Subproperty of {', '.join(super_prop_names)}")
        
        if description_parts:
            schema["description"] = ". ".join(description_parts)
        
        # Handle functional properties (max cardinality 1)
        if is_functional:
            # Functional properties have at most one value - keep as single object
            pass
        else:
            # Non-functional properties have indeterminate multiplicity (0..*) by default in OWL
            # So we should use arrays unless explicitly disabled
            schema = {
                "type": "array",
                "items": schema
            }
        
        # Assign to domain classes
        if domains:
            for domain_uri in domains:
                domain_name = self._get_property_name(domain_uri)
                # Check if domain is owl:Thing (universal domain)
                if domain_uri == "http://www.w3.org/2002/07/owl#Thing" or domain_name == "Thing":
                    # Property with explicit domain owl:Thing applies to all classes
                    # Add to all classes in the ontology
                    for owl_class in ontology.classes:
                        class_name = self._get_property_name(owl_class.uri)
                        results.append({
                            "class": class_name,
                            "property": {
                                "name": prop_name,
                                "schema": schema,
                                "uri": property.uri
                            }
                        })
                else:
                    results.append({
                        "class": domain_name,
                        "property": {
                            "name": prop_name,
                            "schema": schema,
                            "uri": property.uri  # Include OWL property URI
                        }
                    })
        # If no domain specified, don't add the property
        # This handles cases where:
        # - Property is imported from another ontology and domain wasn't parsed
        # - Property domain is declared elsewhere and not available in current context
        # Only properties with explicit domains (including owl:Thing) are added
        
        return results
    
    def _find_property_by_uri(self, uri: str, ontology: OntologyModel) -> Optional[ObjectProperty]:
        """Find an object property by its URI."""
        for prop in ontology.object_properties:
            if prop.uri == uri:
                return prop
        return None
    
    def _infer_property_domain_from_usage(self, property: ObjectProperty, ontology: OntologyModel) -> List[str]:
        """Infer the domain of a property from its usage in class restrictions."""
        domains = []
        prop_uri = property.uri
        
        # Check all classes for restrictions using this property
        for owl_class in ontology.classes:
            for restriction in owl_class.restrictions:
                if restriction.property_uri == prop_uri:
                    # This class uses the property, so it's part of the domain
                    if owl_class.uri not in domains:
                        domains.append(owl_class.uri)
        
        return domains
    
    def _get_property_name(self, uri: str) -> str:
        """Extract property name from URI."""
        # Handle complex class expressions (dict)
        if isinstance(uri, dict):
            # For complex expressions, we can't extract a simple name
            # Return a placeholder or handle specially
            return str(uri)  # This shouldn't happen for property/class names
        
        if '#' in uri:
            return uri.split('#')[-1]
        elif '/' in uri:
            return uri.split('/')[-1]
        return uri
    
    def _create_range_schema(self, range_expr: Any) -> Dict[str, Any]:
        """
        Create JSON Schema for a complex range expression (unionOf, intersectionOf).
        
        Args:
            range_expr: Either a dict with 'unionOf' or 'intersectionOf', or a simple URI string
            
        Returns:
            JSON Schema representation
        """
        # Check if it's a complex class expression (dict)
        if isinstance(range_expr, dict):
            if "unionOf" in range_expr:
                # Create oneOf with references to each class in the union
                union_schemas = []
                for class_uri in range_expr["unionOf"]:
                    # Recursively handle nested expressions
                    if isinstance(class_uri, dict):
                        union_schemas.append(self._create_range_schema(class_uri))
                    else:
                        class_name = self._get_property_name(class_uri)
                        # Special handling for owl:Thing
                        if class_uri == "http://www.w3.org/2002/07/owl#Thing" or class_name == "Thing":
                            class_name = "_Thing"
                        
                        # Add both full object and @id reference for each class
                        union_schemas.append({
                            "oneOf": [
                                {"$ref": f"#/definitions/{class_name}"},
                                {
                                    "type": "object",
                                    "properties": {
                                        "@id": {
                                            "type": "string",
                                            "format": "uri"
                                        }
                                    },
                                    "required": ["@id"],
                                    "additionalProperties": False
                                }
                            ]
                        })
                
                return {"oneOf": union_schemas}
            
            elif "intersectionOf" in range_expr:
                # Create allOf with references to each class in the intersection
                intersection_schemas = []
                for class_uri in range_expr["intersectionOf"]:
                    # Recursively handle nested expressions
                    if isinstance(class_uri, dict):
                        intersection_schemas.append(self._create_range_schema(class_uri))
                    else:
                        class_name = self._get_property_name(class_uri)
                        # Special handling for owl:Thing
                        if class_uri == "http://www.w3.org/2002/07/owl#Thing" or class_name == "Thing":
                            class_name = "_Thing"
                        
                        intersection_schemas.append({"$ref": f"#/definitions/{class_name}"})
                
                return {"allOf": intersection_schemas}
        
        # If it's a simple URI string, create basic reference
        class_name = self._get_property_name(str(range_expr))
        if str(range_expr) == "http://www.w3.org/2002/07/owl#Thing" or class_name == "Thing":
            class_name = "_Thing"
        
        return {
            "oneOf": [
                {"$ref": f"#/definitions/{class_name}"},
                {
                    "type": "object",
                    "properties": {
                        "@id": {
                            "type": "string",
                            "format": "uri"
                        }
                    },
                    "required": ["@id"],
                    "additionalProperties": False
                }
            ]
        }


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
            # Clean the comment to remove tab sequences
            schema["description"] = clean_string(property.get_comment(self.get_option("language", "en")))
        
        return {
            "property": prop_name,
            "schema": schema,
            "domains": property.domain
        }
    
    def _transform_datatype_property(self, property: DatatypeProperty, ontology: OntologyModel) -> List[Dict[str, Any]]:
        """Transform a datatype property and assign it to its domain classes."""
        prop_name = self._get_property_name(property.uri)
        results = []
        
        # Determine domain - explicit or inherited from super properties
        domains = list(property.domain) if property.domain else []
        
        # If no explicit domain, inherit from super properties (OWL subproperty semantics)
        if not domains and property.super_properties:
            for super_prop_uri in property.super_properties:
                super_prop = self._find_datatype_property_by_uri(super_prop_uri, ontology)
                if super_prop and super_prop.domain:
                    domains = list(super_prop.domain)
                    break  # Use first super property with a domain
        
        # Create the property schema based on its range
        # First try explicit range, then inherit from super property
        range_uri = property.range[0] if property.range else None
        if not range_uri and property.super_properties:
            for super_prop_uri in property.super_properties:
                super_prop = self._find_datatype_property_by_uri(super_prop_uri, ontology)
                if super_prop and super_prop.range:
                    range_uri = super_prop.range[0]
                    break  # Use first super property with a range
        
        schema = self._get_datatype_schema(range_uri)
        
        # Add title and description if available
        if property.label:
            schema["title"] = property.get_label(self.get_option("language", "en"))
        
        # Build description with comment and subproperty info
        description_parts = []
        if property.comment:
            # Clean the comment to remove tab sequences
            description_parts.append(clean_string(property.get_comment(self.get_option("language", "en"))))
        
        # Add subproperty information
        if property.super_properties:
            super_prop_names = [self._get_property_name(uri) for uri in property.super_properties]
            if len(super_prop_names) == 1:
                description_parts.append(f"Subproperty of {super_prop_names[0]}")
            else:
                description_parts.append(f"Subproperty of {', '.join(super_prop_names)}")
        
        if description_parts:
            schema["description"] = ". ".join(description_parts)
        
        # Handle functional properties
        if property.functional:
            # Functional properties have at most one value - keep as single value
            pass
        else:
            # Non-functional datatype properties have indeterminate multiplicity (0..*) by default
            # Use arrays for non-functional properties
            schema = {
                "type": "array",
                "items": schema
            }
        
        # Assign to domain classes
        if domains:
            for domain_uri in domains:
                domain_name = self._get_property_name(domain_uri)
                # Check if domain is owl:Thing (universal domain)
                if domain_uri == "http://www.w3.org/2002/07/owl#Thing" or domain_name == "Thing":
                    # Property with explicit domain owl:Thing applies to all classes
                    # Add to all classes in the ontology
                    for owl_class in ontology.classes:
                        class_name = self._get_property_name(owl_class.uri)
                        results.append({
                            "class": class_name,
                            "property": {
                                "name": prop_name,
                                "schema": schema,
                                "uri": property.uri
                            }
                        })
                else:
                    results.append({
                        "class": domain_name,
                        "property": {
                            "name": prop_name,
                            "schema": schema,
                            "uri": property.uri  # Include OWL property URI
                        }
                    })
        # If no domain specified, don't add the property
        # This handles cases where:
        # - Property is imported from another ontology and domain wasn't parsed
        # - Property domain is declared elsewhere and not available in current context
        # Only properties with explicit domains (including owl:Thing) are added
        
        return results
    
    def _get_datatype_schema(self, datatype_uri: Optional[str]) -> Dict[str, Any]:
        """Get JSON Schema for an XSD datatype."""
        if not datatype_uri:
            # No range specified - in OWL this means owl:Thing (for object properties)
            # or any datatype (for datatype properties)
            # In JSON Schema, use empty schema {} which accepts any value (equivalent to type: any)
            return {}
        
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
            "http://www.w3.org/2001/XMLSchema#dateTimeStamp": {"type": "string", "format": "date-time"},
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
    
    def _find_datatype_property_by_uri(self, uri: str, ontology: OntologyModel) -> Optional[DatatypeProperty]:
        """Find a datatype property by its URI."""
        for prop in ontology.datatype_properties:
            if prop.uri == uri:
                return prop
        return None
    
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
    
    def _create_type_reference(self, type_uri: Any) -> Dict[str, Any]:
        """
        Create a type reference for a class or datatype.
        
        Handles simple types (strings) as well as complex class expressions
        (dicts with 'unionOf' or 'intersectionOf' keys).
        """
        # Check if it's a complex class expression (dict)
        if isinstance(type_uri, dict):
            if "unionOf" in type_uri:
                # Expand union inline as oneOf
                union_refs = []
                for class_uri in type_uri["unionOf"]:
                    # Recursively handle nested expressions
                    union_refs.append(self._create_type_reference(class_uri))
                return {"oneOf": union_refs}
            elif "intersectionOf" in type_uri:
                # Expand intersection inline as allOf
                intersection_refs = []
                for class_uri in type_uri["intersectionOf"]:
                    # Recursively handle nested expressions
                    intersection_refs.append(self._create_type_reference(class_uri))
                return {"allOf": intersection_refs}
        
        # Handle simple type URI (string)
        type_str = str(type_uri)
        
        # Check if it's an XSD datatype
        xsd_types = {
            "http://www.w3.org/2001/XMLSchema#string": {"type": "string"},
            "http://www.w3.org/2001/XMLSchema#integer": {"type": "integer"},
            "http://www.w3.org/2001/XMLSchema#decimal": {"type": "number"},
            "http://www.w3.org/2001/XMLSchema#boolean": {"type": "boolean"},
            "http://www.w3.org/2001/XMLSchema#date": {"type": "string", "format": "date"},
            "http://www.w3.org/2001/XMLSchema#time": {"type": "string", "format": "time"},
            "http://www.w3.org/2001/XMLSchema#dateTime": {"type": "string", "format": "date-time"},
            "http://www.w3.org/2001/XMLSchema#dateTimeStamp": {"type": "string", "format": "date-time"},
        }
        
        if type_str in xsd_types:
            return xsd_types[type_str]
        
        # Otherwise, it's a reference to another class
        # Use oneOf pattern for object references
        class_name = self._get_property_name(type_str)
        
        # Special handling for owl:Thing - map to _Thing
        if type_str == "http://www.w3.org/2002/07/owl#Thing" or class_name == "Thing":
            class_name = "_Thing"
        
        return {
            "oneOf": [
                {"$ref": f"#/definitions/{class_name}"},
                {
                    "type": "object",
                    "properties": {
                        "@id": {
                            "type": "string",
                            "format": "uri"
                        }
                    },
                    "required": ["@id"],
                    "additionalProperties": False
                }
            ]
        }
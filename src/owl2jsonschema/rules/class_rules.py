"""
Class Transformation Rules

This module contains transformation rules for OWL classes.
"""

from typing import Any, Dict, List, Optional
from ..visitor import TransformationRule
from ..model import OntologyModel, OntologyClass, OntologyRestriction
from ..builder import ReferenceResolver
from ..utils import clean_string


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
            # Clean the comment to remove tab sequences
            schema["description"] = clean_string(comment)
        
        # Store the OWL class URI for later processing
        # The engine will convert this to appropriate metadata
        schema["uri"] = owl_class.uri
        
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
    
    def visit_ontology(self, ontology: OntologyModel) -> List[Dict[str, Any]]:
        """Process restrictions for all classes in the ontology."""
        if not self.is_enabled():
            return None
        
        results = []
        
        for owl_class in ontology.classes:
            class_result = self._process_class_restrictions(owl_class)
            if class_result:
                results.append(class_result)
        
        return results if results else None
    
    def visit_class(self, owl_class: OntologyClass) -> Dict[str, Any]:
        """Process restrictions for a single class."""
        if not self.is_enabled():
            return None
        
        return self._process_class_restrictions(owl_class)
    
    def _process_class_restrictions(self, owl_class: OntologyClass) -> Optional[Dict[str, Any]]:
        """Process restrictions for a class and return with class context."""
        if not owl_class.restrictions:
            return None
        
        class_name = self._get_class_name(owl_class.uri)
        constraints = {
            "class": class_name,
            "properties": {},
            "required": []
        }
        
        # First pass: collect all restrictions by property
        property_restrictions = {}
        for restriction in owl_class.restrictions:
            prop_name = self._get_property_name(restriction.property_uri)
            if prop_name not in property_restrictions:
                property_restrictions[prop_name] = []
            property_restrictions[prop_name].append(restriction)
        
        # Second pass: merge restrictions for each property
        for prop_name, restrictions in property_restrictions.items():
            merged_schema = {}
            is_required = False
            
            # Process all restrictions for this property
            for restriction in restrictions:
                constraint = self._process_restriction(restriction)
                if constraint:
                    # Merge schema
                    if "schema" in constraint:
                        merged_schema.update(constraint["schema"])
                    
                    # If ANY restriction marks it as required, keep it required
                    if constraint.get("required", False):
                        is_required = True
            
            # Add the merged result
            # Always add the property if it has any restrictions, even if schema is empty
            if restrictions:  # If there were any restrictions for this property
                # Use merged schema if available, otherwise empty object
                constraints["properties"][prop_name] = merged_schema if merged_schema else {}
                
                if is_required:
                    if prop_name not in constraints["required"]:
                        constraints["required"].append(prop_name)
        
        # Only return if we have properties
        if constraints["properties"]:
            # Remove empty required array
            if not constraints["required"]:
                del constraints["required"]
            return constraints
        
        return None
    
    def _process_restriction(self, restriction: OntologyRestriction) -> Optional[Dict[str, Any]]:
        """Process a single restriction."""
        from ..model import CardinalityRestriction, ValueRestriction
        
        prop_name = self._get_property_name(restriction.property_uri)
        result = {"property": prop_name}
        
        if isinstance(restriction, CardinalityRestriction):
            schema = {}
            
            if restriction.min_cardinality is not None:
                if restriction.min_cardinality >= 1:
                    # Property is required only if min cardinality is 1 or more
                    result["required"] = True
                    if restriction.min_cardinality == 1:
                        # Single value required
                        pass
                    else:
                        # Multiple values required
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
                
                # In OWL, without explicit cardinality, properties have indeterminate multiplicity (0..*)
                # So we should default to arrays unless explicitly set to single value
                schema["type"] = "array"
                schema["items"] = filler_ref
                # Clean any potential tabs in the generated description
                schema["description"] = clean_string(f"Array of {self._get_property_name(restriction.filler)} or @id references")
            
            elif restriction.restriction_type == "someValuesFrom":
                # At least one value must be from the specified class/type
                # This makes the property required
                result["required"] = True
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
    
    def _get_class_name(self, uri: str) -> str:
        """Extract class name from URI."""
        if '#' in uri:
            return uri.split('#')[-1]
        elif '/' in uri:
            return uri.split('/')[-1]
        return uri
    
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
        # Use oneOf pattern: either a full object reference or an @id reference
        class_name = self._get_property_name(type_uri)
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


class IndividualsToEnumRule(TransformationRule):
    """
    Transform OWL individuals to JSON Schema constraints.
    
    For classes defined as equivalent to (or subclass of) a disjoint union of individuals,
    creates a closed enum constraint. For other classes with individuals, adds them as
    examples/documentation only (open set).
    """
    
    def visit_ontology(self, ontology: OntologyModel) -> Dict[str, Any]:
        """Process all individuals and add appropriate constraints to their classes."""
        if not self.is_enabled():
            return None
        
        # Group individuals by their class types
        individuals_by_class = {}
        
        for individual in ontology.individuals:
            for type_uri in individual.types:
                class_name = self._get_class_name(type_uri)
                if class_name not in individuals_by_class:
                    individuals_by_class[class_name] = []
                
                # Store individual URI and label
                individual_info = {
                    "uri": individual.uri,
                    "label": individual.label if individual.label else self._get_class_name(individual.uri)
                }
                individuals_by_class[class_name].append(individual_info)
        
        if not individuals_by_class:
            return None
        
        # Check which classes have closed vs open sets
        individuals_constraints = {}
        for class_name, individuals in individuals_by_class.items():
            # Find the corresponding class in the ontology
            owl_class = self._find_class_by_name(ontology, class_name)
            
            if owl_class and self._is_closed_enumeration(owl_class):
                # Closed set: Use enum constraint
                individuals_constraints[class_name] = self._create_closed_constraint(class_name, individuals)
            else:
                # Open set: Add as examples/documentation
                individuals_constraints[class_name] = self._create_open_constraint(class_name, individuals)
        
        return {"individuals_constraints": individuals_constraints} if individuals_constraints else None
    
    def _find_class_by_name(self, ontology: OntologyModel, class_name: str) -> Optional[OntologyClass]:
        """Find a class in the ontology by its local name."""
        for owl_class in ontology.classes:
            if self._get_class_name(owl_class.uri) == class_name:
                return owl_class
        return None
    
    def _is_closed_enumeration(self, owl_class: OntologyClass) -> bool:
        """
        Check if a class represents a closed enumeration.
        
        A class is closed if it has an 'enumeration' annotation (from oneOf parsing)
        or if it's equivalent to a oneOf construct.
        """
        # Check if the class has an enumeration annotation (from oneOf)
        if "enumeration" in owl_class.annotations:
            return True
        
        # For now, default to open (conservative approach)
        # In the future, could add more sophisticated checks for equivalentClass with oneOf
        return False
    
    def _create_closed_constraint(self, class_name: str, individuals: List[Dict[str, str]]) -> Dict[str, Any]:
        """Create a closed enum constraint (only listed values allowed)."""
        enum_values = [ind["uri"] for ind in individuals]
        enum_titles = {ind["uri"]: ind["label"] for ind in individuals}
        
        uri_constraint = {
            "enum": enum_values,
            "description": f"Must be one of the defined {class_name} individuals (closed set)"
        }
        
        if enum_titles:
            uri_constraint["x-enum-labels"] = enum_titles
        
        return {"uri": uri_constraint}
    
    def _create_open_constraint(self, class_name: str, individuals: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Create documentation for an open set (other values are also allowed).
        
        Uses x-enum-individuals to list known individuals without restricting to only those.
        """
        enum_values = [ind["uri"] for ind in individuals]
        enum_titles = {ind["uri"]: ind["label"] for ind in individuals}
        
        uri_metadata = {
            "description": f"URI of a {class_name} instance. Known individuals include: {', '.join(enum_titles.values())}",
            "x-known-individuals": enum_values
        }
        
        if enum_titles:
            uri_metadata["x-known-individual-labels"] = enum_titles
        
        return {"uri": uri_metadata}
    
    def _get_class_name(self, uri: str) -> str:
        """Extract class name from URI."""
        if '#' in uri:
            return uri.split('#')[-1]
        elif '/' in uri:
            return uri.split('/')[-1]
        return uri
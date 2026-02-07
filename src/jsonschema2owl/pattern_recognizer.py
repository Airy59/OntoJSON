"""
Pattern Recognizer for JSON Schema to OWL Transformation

This module identifies OWL patterns in JSON Schema constructs.
"""

from typing import Dict, Any, Optional, List, Tuple
from .model import PropertyModel, DefinitionModel, CardinalityConstraint, PatternInfo


class PatternRecognizer:
    """Recognize OWL patterns in JSON Schema constructs."""
    
    def __init__(self):
        """Initialize the pattern recognizer."""
        self.xsd_type_mapping = {
            "string": "http://www.w3.org/2001/XMLSchema#string",
            "integer": "http://www.w3.org/2001/XMLSchema#integer",
            "number": "http://www.w3.org/2001/XMLSchema#decimal",
            "boolean": "http://www.w3.org/2001/XMLSchema#boolean",
            "null": None  # No direct XSD mapping
        }
    
    def is_object_property(self, property_schema: Dict[str, Any]) -> bool:
        """
        Detect if a property represents an OWL object property.
        
        Object property patterns:
        1. Property with $ref to another definition
        2. Property with oneOf containing $ref and @id pattern
        3. Array with items containing $ref
        
        Args:
            property_schema: Property schema dictionary
        
        Returns:
            True if this appears to be an object property
        """
        # Direct $ref reference
        if "$ref" in property_schema:
            return True
        
        # oneOf with object reference pattern
        if "oneOf" in property_schema:
            for option in property_schema["oneOf"]:
                if isinstance(option, dict):
                    # Check for $ref
                    if "$ref" in option:
                        return True
                    # Check for @id pattern (indicates URI reference)
                    if "properties" in option and "@id" in option.get("properties", {}):
                        return True
        
        # anyOf with object references
        if "anyOf" in property_schema:
            for option in property_schema["anyOf"]:
                if isinstance(option, dict) and "$ref" in option:
                    return True
        
        # Array with object items (including nested arrays)
        if property_schema.get("type") == "array" and "items" in property_schema:
            items = property_schema["items"]
            if isinstance(items, dict):
                # Direct $ref in items
                if "$ref" in items:
                    return True
                # Inline object type in items (array of objects)
                if items.get("type") == "object":
                    return True
                # oneOf with $ref in items
                if "oneOf" in items:
                    for option in items["oneOf"]:
                        if isinstance(option, dict) and "$ref" in option:
                            return True
                # Nested array: array of arrays with $ref or object
                if items.get("type") == "array" and "items" in items:
                    nested_items = items["items"]
                    if isinstance(nested_items, dict):
                        if "$ref" in nested_items:
                            return True
                        # Nested array of objects
                        if nested_items.get("type") == "object":
                            return True
                        if "oneOf" in nested_items:
                            for option in nested_items["oneOf"]:
                                if isinstance(option, dict) and "$ref" in option:
                                    return True
        
        return False
    
    def is_datatype_property(self, property_schema: Dict[str, Any]) -> bool:
        """
        Detect if a property represents an OWL datatype property.
        
        Datatype property patterns:
        1. Property with primitive type (string, number, boolean, integer)
        2. Array with primitive items
        
        Args:
            property_schema: Property schema dictionary
        
        Returns:
            True if this appears to be a datatype property
        """
        prop_type = property_schema.get("type")
        
        # Direct primitive types
        if isinstance(prop_type, str) and prop_type in ["string", "number", "integer", "boolean"]:
            return True
        
        # Array of primitive types
        if isinstance(prop_type, list):
            for t in prop_type:
                if t in ["string", "number", "integer", "boolean"]:
                    return True
        
        # Array with primitive items
        if prop_type == "array" and "items" in property_schema:
            items = property_schema["items"]
            if isinstance(items, dict):
                items_type = items.get("type")
                if isinstance(items_type, str) and items_type in ["string", "number", "integer", "boolean"]:
                    return True
        
        return False
    
    def extract_datatype(self, property_schema: Dict[str, Any]) -> Optional[str]:
        """
        Extract the XSD datatype from a property schema.
        
        Args:
            property_schema: Property schema dictionary
        
        Returns:
            XSD datatype URI or None
        """
        prop_type = property_schema.get("type")
        
        # Handle array types - get the item type
        if prop_type == "array" and "items" in property_schema:
            items = property_schema["items"]
            if isinstance(items, dict):
                prop_type = items.get("type")
        
        # Map JSON Schema type to XSD type
        if isinstance(prop_type, str):
            return self.xsd_type_mapping.get(prop_type)
        
        # If multiple types, prefer the first non-null type
        if isinstance(prop_type, list):
            for t in prop_type:
                if t != "null" and t in self.xsd_type_mapping:
                    return self.xsd_type_mapping[t]
        
        return None
    
    def extract_range_from_ref(self, property_schema: Dict[str, Any], property_name: Optional[str] = None) -> Optional[str]:
        """
        Extract the range class from a $ref reference or inline object.
        
        Args:
            property_schema: Property schema dictionary
            property_name: Optional property name for generating anonymous class names
        
        Returns:
            Referenced class name or generated class name for inline objects
        """
        # Direct $ref
        if "$ref" in property_schema:
            return self._extract_definition_name(property_schema["$ref"])
        
        # oneOf with $ref
        if "oneOf" in property_schema:
            for option in property_schema["oneOf"]:
                if isinstance(option, dict) and "$ref" in option:
                    return self._extract_definition_name(option["$ref"])
        
        # Array items with $ref or inline object (including nested arrays)
        if property_schema.get("type") == "array" and "items" in property_schema:
            items = property_schema["items"]
            if isinstance(items, dict):
                # Direct $ref in items
                if "$ref" in items:
                    return self._extract_definition_name(items["$ref"])
                # Inline object type in items - generate class name
                if items.get("type") == "object":
                    if property_name:
                        # Generate class name from property name (e.g., "requiredData" -> "RequiredDataItem")
                        return self._generate_inline_class_name(property_name)
                    return None
                # oneOf with $ref in items
                if "oneOf" in items:
                    for option in items["oneOf"]:
                        if isinstance(option, dict) and "$ref" in option:
                            return self._extract_definition_name(option["$ref"])
                # Nested array: array of arrays with $ref or object
                if items.get("type") == "array" and "items" in items:
                    nested_items = items["items"]
                    if isinstance(nested_items, dict):
                        if "$ref" in nested_items:
                            return self._extract_definition_name(nested_items["$ref"])
                        # Nested array of objects
                        if nested_items.get("type") == "object":
                            if property_name:
                                return self._generate_inline_class_name(property_name)
                            return None
                        if "oneOf" in nested_items:
                            for option in nested_items["oneOf"]:
                                if isinstance(option, dict) and "$ref" in option:
                                    return self._extract_definition_name(option["$ref"])
        
        return None
    
    def _generate_inline_class_name(self, property_name: str) -> str:
        """
        Generate a class name for an inline object definition.
        
        Args:
            property_name: Property name
        
        Returns:
            Generated class name (e.g., "requiredData" -> "RequiredDataItem")
        """
        # Convert camelCase or snake_case to PascalCase
        import re
        # Split on camelCase boundaries or underscores
        parts = re.split(r'([A-Z][a-z]+|[a-z]+)', property_name)
        parts = [p for p in parts if p]
        # Capitalize first letter of each part
        pascal_parts = [p.capitalize() for p in parts if p]
        # Join and add "Item" suffix
        return ''.join(pascal_parts) + "Item"
    
    def _extract_definition_name(self, ref: str) -> Optional[str]:
        """Extract definition name from $ref string."""
        if ref.startswith("#/definitions/"):
            return ref.split("/")[-1]
        return None
    
    def is_enumeration(self, definition: DefinitionModel) -> bool:
        """
        Check if a definition represents an enumeration.
        
        Args:
            definition: Definition model
        
        Returns:
            True if this is an enumeration
        """
        return definition.enum is not None and len(definition.enum) > 0
    
    def extract_enum_values(self, definition: DefinitionModel) -> List[Any]:
        """
        Extract enumeration values from a definition.
        
        Args:
            definition: Definition model
        
        Returns:
            List of enum values
        """
        if definition.enum:
            return definition.enum
        return []
    
    def recognize_cardinality(self, property_schema: Dict[str, Any], is_required: bool = False) -> CardinalityConstraint:
        """
        Recognize cardinality constraints from a property schema.
        
        Args:
            property_schema: Property schema dictionary
            is_required: Whether this property is in the required list
        
        Returns:
            CardinalityConstraint object
        """
        constraint = CardinalityConstraint()
        
        # Check if it's an array
        if property_schema.get("type") == "array":
            # Min cardinality from minItems
            if "minItems" in property_schema:
                constraint.min_cardinality = property_schema["minItems"]
            elif is_required:
                constraint.min_cardinality = 1
            else:
                constraint.min_cardinality = 0
            
            # Max cardinality from maxItems
            if "maxItems" in property_schema:
                constraint.max_cardinality = property_schema["maxItems"]
            # Otherwise no max (unbounded)
        else:
            # Non-array property
            if is_required:
                constraint.min_cardinality = 1
                constraint.max_cardinality = 1
                constraint.exact_cardinality = 1
            else:
                constraint.min_cardinality = 0
                constraint.max_cardinality = 1
        
        return constraint
    
    def recognize_inheritance_pattern(self, all_of: List[Any]) -> Tuple[Optional[str], List[Dict]]:
        """
        Recognize inheritance patterns in allOf.
        
        Heuristic:
        - If first item is a $ref, it's likely the parent class
        - Remaining items are additional constraints or mixins
        
        Args:
            all_of: List of allOf items
        
        Returns:
            Tuple of (parent_class_name, additional_constraints)
        """
        if not all_of or len(all_of) == 0:
            return None, []
        
        parent_class = None
        additional_constraints = []
        
        # Check if first item is a $ref
        first_item = all_of[0]
        if isinstance(first_item, dict) and "$ref" in first_item:
            parent_class = self._extract_definition_name(first_item["$ref"])
            additional_constraints = all_of[1:]
        else:
            # No clear parent, treat all as constraints
            additional_constraints = all_of
        
        return parent_class, additional_constraints
    
    def recognize_intersection_pattern(self, all_of: List[Any]) -> List[str]:
        """
        Recognize intersection patterns in allOf.
        
        Returns list of class names that form the intersection.
        
        Args:
            all_of: List of allOf items
        
        Returns:
            List of class names in the intersection
        """
        class_names = []
        
        for item in all_of:
            if isinstance(item, dict) and "$ref" in item:
                name = self._extract_definition_name(item["$ref"])
                if name:
                    class_names.append(name)
        
        return class_names
    
    def recognize_union_pattern(self, one_of: List[Any]) -> List[str]:
        """
        Recognize union patterns in oneOf.
        
        Args:
            one_of: List of oneOf items
        
        Returns:
            List of class names in the union
        """
        class_names = []
        
        for item in one_of:
            if isinstance(item, dict) and "$ref" in item:
                name = self._extract_definition_name(item["$ref"])
                if name:
                    class_names.append(name)
        
        return class_names
    
    def analyze_property(self, property_model: PropertyModel, is_required: bool = False) -> PatternInfo:
        """
        Analyze a property and return pattern information.
        
        Args:
            property_model: Property model to analyze
            is_required: Whether property is required
        
        Returns:
            PatternInfo with analysis results
        """
        # Convert property model to dict for analysis
        prop_dict = {
            "type": property_model.type,
            "items": property_model.items,
            "oneOf": property_model.one_of,
            "anyOf": property_model.any_of,
            "minItems": property_model.min_items,
            "maxItems": property_model.max_items,
        }
        
        if property_model.ref:
            prop_dict["$ref"] = property_model.ref
        
        # Determine property type
        if self.is_object_property(prop_dict):
            cardinality = self.recognize_cardinality(prop_dict, is_required)
            range_class = self.extract_range_from_ref(prop_dict)
            
            return PatternInfo(
                pattern_type="object_property",
                property_type="object",
                range_class=range_class,
                is_functional=cardinality.is_functional(),
                cardinality=cardinality,
                confidence=0.9
            )
        
        elif self.is_datatype_property(prop_dict):
            cardinality = self.recognize_cardinality(prop_dict, is_required)
            datatype = self.extract_datatype(prop_dict)
            
            return PatternInfo(
                pattern_type="datatype_property",
                property_type="datatype",
                datatype=datatype,
                is_functional=cardinality.is_functional(),
                cardinality=cardinality,
                confidence=0.9
            )
        
        else:
            # Unknown pattern
            return PatternInfo(
                pattern_type="unknown",
                confidence=0.0,
                metadata={"property_name": property_model.name}
            )
"""
Property Transformation Rules

Rules for transforming JSON Schema properties to OWL properties.
"""

from typing import Any, Tuple
from . import PropertyRule
from ..model import PropertyModel, DefinitionModel, TransformationContext
from ..builder import OWLBuilder
from ..config import ReverseTransformationConfig
from ..pattern_recognizer import PatternRecognizer


class TypeToPropertyRule(PropertyRule):
    """Transform primitive type properties to OWL datatype properties."""
    
    def __init__(self, config: ReverseTransformationConfig = None):
        super().__init__("type_to_property", config)
        self.recognizer = PatternRecognizer()
    
    def applies_to(self, element: Any, context: TransformationContext) -> bool:
        """Applies to properties with primitive types."""
        if not isinstance(element, tuple) or len(element) != 2:
            return False
        
        definition, prop = element
        if not isinstance(definition, DefinitionModel) or not isinstance(prop, PropertyModel):
            return False
        
        # Check if it's a datatype property
        prop_dict = self._property_to_dict(prop)
        return self.recognizer.is_datatype_property(prop_dict)
    
    def apply(self, element: Tuple[DefinitionModel, PropertyModel], builder: OWLBuilder, context: TransformationContext) -> None:
        """Create an OWL datatype property."""
        definition, prop = element
        
        # Always use reverse_scoped naming: propertyName_ClassName
        # This groups properties by original name while keeping them distinct per domain
        prop_uri = builder.uri_generator.generate_property_uri(
            prop.name,
            owner_class=definition.name,
            naming_strategy="reverse_scoped"  # propertyName_ClassName format
        )
        
        # Get domain class URI
        domain_uri = builder.uri_generator.generate_class_uri(definition.name)
        
        # Get datatype
        prop_dict = self._property_to_dict(prop)
        datatype = self.recognizer.extract_datatype(prop_dict)
        
        # Determine if functional (not an array)
        is_functional = not prop.is_array()
        
        # Create datatype property with explicit domain
        # Label is original property name (for grouping), URI is scoped
        builder.add_datatype_property(
            property_uri=prop_uri,
            domain=domain_uri,
            range_=datatype,
            label=prop.title or prop.name,  # Original property name as label
            comment=prop.description,
            functional=is_functional
        )
    
    def _property_to_dict(self, prop: PropertyModel) -> dict:
        """Convert PropertyModel to dict for pattern recognizer."""
        result = {"type": prop.type}
        if prop.items:
            # Handle nested PropertyModel items (though parser stores as dict)
            if isinstance(prop.items, PropertyModel):
                result["items"] = {
                    "type": prop.items.type,
                    "items": prop.items.items if prop.items.items else None,
                    "$ref": prop.items.ref if prop.items.ref else None
                }
            else:
                result["items"] = prop.items
        if prop.one_of:
            result["oneOf"] = prop.one_of
        if prop.ref:
            result["$ref"] = prop.ref
        return result


class ObjectRefToPropertyRule(PropertyRule):
    """Transform $ref properties to OWL object properties."""
    
    def __init__(self, config: ReverseTransformationConfig = None):
        super().__init__("object_ref_to_property", config)
        self.recognizer = PatternRecognizer()
    
    def applies_to(self, element: Any, context: TransformationContext) -> bool:
        """Applies to properties with object references."""
        if not isinstance(element, tuple) or len(element) != 2:
            return False
        
        definition, prop = element
        if not isinstance(definition, DefinitionModel) or not isinstance(prop, PropertyModel):
            return False
        
        # Check if it's an object property
        prop_dict = self._property_to_dict(prop)
        return self.recognizer.is_object_property(prop_dict)
    
    def apply(self, element: Tuple[DefinitionModel, PropertyModel], builder: OWLBuilder, context: TransformationContext) -> None:
        """Create an OWL object property."""
        definition, prop = element
        
        # Always use reverse_scoped naming: propertyName_ClassName
        # This groups properties by original name while keeping them distinct per domain
        prop_uri = builder.uri_generator.generate_property_uri(
            prop.name,
            owner_class=definition.name,
            naming_strategy="reverse_scoped"  # propertyName_ClassName format
        )
        
        # Get domain class URI
        domain_uri = builder.uri_generator.generate_class_uri(definition.name)
        
        # Get range class
        prop_dict = self._property_to_dict(prop)
        range_class_name = self.recognizer.extract_range_from_ref(prop_dict, property_name=prop.name)
        
        if not range_class_name:
            # No clear range, skip or warn
            context.add_warning(
                f"Could not determine range for object property '{prop.name}'",
                f"Definition: {definition.name}"
            )
            return
        
        # If this is an inline object (generated class name), create the class
        # Check if it's a generated name (ends with "Item")
        if range_class_name.endswith("Item") and range_class_name not in context.uri_mapping:
            # This is an inline object - create a class for it
            range_uri = builder.uri_generator.generate_class_uri(range_class_name)
            builder.add_class(
                class_uri=range_uri,
                label=range_class_name,
                comment=f"Inline class for array items in property '{prop.name}'"
            )
            context.uri_mapping[range_class_name] = range_uri
        else:
            range_uri = builder.uri_generator.generate_class_uri(range_class_name)
        
        # Determine if functional (not an array)
        is_functional = not prop.is_array()
        
        # Create object property with explicit domain
        # Label is original property name (for grouping), URI is scoped
        builder.add_object_property(
            property_uri=prop_uri,
            domain=domain_uri,
            range_=range_uri,
            label=prop.title or prop.name,  # Original property name as label
            comment=prop.description,
            functional=is_functional
        )
    
    def _property_to_dict(self, prop: PropertyModel) -> dict:
        """Convert PropertyModel to dict for pattern recognizer."""
        result = {"type": prop.type}
        if prop.items:
            # Handle nested PropertyModel items (though parser stores as dict)
            if isinstance(prop.items, PropertyModel):
                result["items"] = {
                    "type": prop.items.type,
                    "items": prop.items.items if prop.items.items else None,
                    "$ref": prop.items.ref if prop.items.ref else None
                }
            else:
                result["items"] = prop.items
        if prop.one_of:
            result["oneOf"] = prop.one_of
        if prop.ref:
            result["$ref"] = prop.ref
        return result


class RequiredToCardinalityRule(PropertyRule):
    """Add cardinality restrictions for required properties."""
    
    def __init__(self, config: ReverseTransformationConfig = None):
        super().__init__("required_to_cardinality", config)
    
    def applies_to(self, element: Any, context: TransformationContext) -> bool:
        """Applies to required properties."""
        if not isinstance(element, tuple) or len(element) != 2:
            return False
        
        definition, prop = element
        if not isinstance(definition, DefinitionModel) or not isinstance(prop, PropertyModel):
            return False
        
        # Check if property is required
        return prop.name in definition.required
    
    def apply(self, element: Tuple[DefinitionModel, PropertyModel], builder: OWLBuilder, context: TransformationContext) -> None:
        """Add minimum cardinality of 1 for required properties."""
        definition, prop = element
        
        # Always use reverse_scoped naming: propertyName_ClassName (matches property creation)
        class_uri = builder.uri_generator.generate_class_uri(definition.name)
        prop_uri = builder.uri_generator.generate_property_uri(
            prop.name,
            owner_class=definition.name,
            naming_strategy="reverse_scoped"  # propertyName_ClassName format
        )
        
        # For non-array required properties, min=1, max=1 (functional)
        # For array required properties, min=1 (already set by ArrayToCardinalityRule if enabled)
        if not prop.is_array():
            # Single-valued required property: exactly 1
            builder.add_cardinality_restriction(
                class_uri=class_uri,
                property_uri=prop_uri,
                exact_cardinality=1
            )
        else:
            # Array required property: at least 1
            builder.add_cardinality_restriction(
                class_uri=class_uri,
                property_uri=prop_uri,
                min_cardinality=1
            )


# Export all rule classes
__all__ = [
    "TypeToPropertyRule",
    "ObjectRefToPropertyRule",
    "RequiredToCardinalityRule"
]
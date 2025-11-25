"""
Constraint Transformation Rules

Rules for transforming JSON Schema constraints to OWL restrictions.
"""

from typing import Any, Tuple
from . import PropertyRule, DefinitionRule
from ..model import PropertyModel, DefinitionModel, TransformationContext
from ..builder import OWLBuilder
from ..config import ReverseTransformationConfig


class ArrayToCardinalityRule(PropertyRule):
    """Transform array min/maxItems to cardinality restrictions."""
    
    def __init__(self, config: ReverseTransformationConfig = None):
        super().__init__("array_to_cardinality", config)
    
    def applies_to(self, element: Any, context: TransformationContext) -> bool:
        """Applies to array properties with minItems or maxItems."""
        if not isinstance(element, tuple) or len(element) != 2:
            return False
        
        definition, prop = element
        if not isinstance(definition, DefinitionModel) or not isinstance(prop, PropertyModel):
            return False
        
        # Check if it's an array with cardinality constraints
        return prop.is_array() and (prop.min_items is not None or prop.max_items is not None)
    
    def apply(self, element: Tuple[DefinitionModel, PropertyModel], builder: OWLBuilder, context: TransformationContext) -> None:
        """Add cardinality restrictions based on minItems/maxItems."""
        definition, prop = element
        
        # Get URIs
        class_uri = builder.uri_generator.generate_class_uri(definition.name)
        prop_uri = builder.uri_generator.generate_property_uri(prop.name)
        
        # Add cardinality restriction
        builder.add_cardinality_restriction(
            class_uri=class_uri,
            property_uri=prop_uri,
            min_cardinality=prop.min_items,
            max_cardinality=prop.max_items
        )


class ItemsToRangeRule(PropertyRule):
    """Transform array items with $ref to range restrictions."""
    
    def __init__(self, config: ReverseTransformationConfig = None):
        super().__init__("items_to_range", config)
    
    def applies_to(self, element: Any, context: TransformationContext) -> bool:
        """Applies to array properties with items containing $ref."""
        if not isinstance(element, tuple) or len(element) != 2:
            return False
        
        definition, prop = element
        if not isinstance(definition, DefinitionModel) or not isinstance(prop, PropertyModel):
            return False
        
        # Check if it's an array with items containing $ref
        if not prop.is_array() or not prop.items:
            return False
        
        if isinstance(prop.items, dict):
            return "$ref" in prop.items
        
        return False
    
    def apply(self, element: Tuple[DefinitionModel, PropertyModel], builder: OWLBuilder, context: TransformationContext) -> None:
        """Add allValuesFrom restriction for array items."""
        definition, prop = element
        
        # Get URIs
        class_uri = builder.uri_generator.generate_class_uri(definition.name)
        prop_uri = builder.uri_generator.generate_property_uri(prop.name)
        
        # Extract referenced class from items
        if isinstance(prop.items, dict) and "$ref" in prop.items:
            ref = prop.items["$ref"]
            # Extract class name from #/definitions/ClassName
            if ref.startswith("#/definitions/"):
                range_class_name = ref.split("/")[-1]
                range_uri = builder.uri_generator.generate_class_uri(range_class_name)
                
                # Add allValuesFrom restriction
                builder.add_value_restriction(
                    class_uri=class_uri,
                    property_uri=prop_uri,
                    restriction_type="allValuesFrom",
                    value=range_uri
                )


class EnumToIndividualsRule(DefinitionRule):
    """Transform enum definitions to named individuals with oneOf."""
    
    def __init__(self, config: ReverseTransformationConfig = None):
        super().__init__("enum_to_individuals", config)
    
    def applies_to(self, element: Any, context: TransformationContext) -> bool:
        """Applies to definitions with enum."""
        if not isinstance(element, DefinitionModel):
            return False
        
        return element.is_enumeration()
    
    def apply(self, element: DefinitionModel, builder: OWLBuilder, context: TransformationContext) -> None:
        """Create enumeration class with individuals."""
        # Get class URI
        class_uri = builder.uri_generator.generate_class_uri(element.name)
        
        # Create individuals for each enum value
        individual_uris = []
        for value in element.enum:
            # Generate individual URI
            ind_uri = builder.uri_generator.generate_individual_uri(str(value))
            individual_uris.append(ind_uri)
            
            # Create individual
            builder.add_individual(
                individual_uri=ind_uri,
                class_uri=class_uri,
                label=str(value)
            )
        
        # Create enumeration class with oneOf
        builder.add_enumeration_class(
            class_uri=class_uri,
            individuals=individual_uris,
            label=element.title or element.name,
            comment=element.description
        )
        
        # Mark as processed
        context.uri_mapping[element.name] = class_uri
        context.mark_processed(element.name)


class ConstToHasValueRule(PropertyRule):
    """Transform const properties to hasValue restrictions."""
    
    def __init__(self, config: ReverseTransformationConfig = None):
        super().__init__("const_to_hasvalue", config)
    
    def applies_to(self, element: Any, context: TransformationContext) -> bool:
        """Applies to properties with const."""
        if not isinstance(element, tuple) or len(element) != 2:
            return False
        
        definition, prop = element
        if not isinstance(definition, DefinitionModel) or not isinstance(prop, PropertyModel):
            return False
        
        return prop.const is not None
    
    def apply(self, element: Tuple[DefinitionModel, PropertyModel], builder: OWLBuilder, context: TransformationContext) -> None:
        """Add hasValue restriction for const."""
        definition, prop = element
        
        # Get URIs
        class_uri = builder.uri_generator.generate_class_uri(definition.name)
        prop_uri = builder.uri_generator.generate_property_uri(prop.name)
        
        # Add hasValue restriction
        from rdflib import Literal
        builder.add_value_restriction(
            class_uri=class_uri,
            property_uri=prop_uri,
            restriction_type="hasValue",
            value=Literal(prop.const)
        )


# Export all rule classes
__all__ = [
    "ArrayToCardinalityRule",
    "ItemsToRangeRule",
    "EnumToIndividualsRule",
    "ConstToHasValueRule"
]
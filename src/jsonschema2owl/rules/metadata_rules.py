"""
Metadata Transformation Rules

Rules for transforming custom metadata and annotations.
"""

from typing import Any
from . import DefinitionRule
from ..model import DefinitionModel, TransformationContext
from ..builder import OWLBuilder
from ..config import ReverseTransformationConfig


class CustomFieldsRule(DefinitionRule):
    """Transform custom fields (x-* prefix) to OWL annotations."""
    
    def __init__(self, config: ReverseTransformationConfig = None):
        super().__init__("custom_fields", config)
    
    def applies_to(self, element: Any, context: TransformationContext) -> bool:
        """Applies to definitions with custom metadata."""
        if not isinstance(element, DefinitionModel):
            return False
        
        # Check if there are custom fields
        return len(element.metadata) > 0
    
    def apply(self, element: DefinitionModel, builder: OWLBuilder, context: TransformationContext) -> None:
        """Add custom fields as annotations."""
        # Get class URI
        class_uri = builder.uri_generator.generate_class_uri(element.name)
        
        # Add each custom field as annotation
        from rdflib import URIRef, Literal
        class_ref = URIRef(class_uri)
        
        for key, value in element.metadata.items():
            # Create predicate URI
            if key.startswith("x-"):
                # Use the key as-is in the namespace
                predicate = builder.base_namespace[key.replace("x-", "")]
            else:
                predicate = builder.base_namespace[key]
            
            # Add annotation
            builder.graph.add((class_ref, predicate, Literal(str(value))))


# Export all rule classes
__all__ = [
    "CustomFieldsRule"
]
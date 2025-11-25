"""
Composition Transformation Rules

Rules for transforming JSON Schema composition (allOf, oneOf, anyOf, not) to OWL constructs.
"""

from typing import Any
from . import DefinitionRule
from ..model import DefinitionModel, TransformationContext
from ..builder import OWLBuilder
from ..config import ReverseTransformationConfig
from ..pattern_recognizer import PatternRecognizer


class AllOfToHierarchyRule(DefinitionRule):
    """Transform allOf to class hierarchy (inheritance)."""
    
    def __init__(self, config: ReverseTransformationConfig = None):
        super().__init__("allof_to_hierarchy", config)
        self.recognizer = PatternRecognizer()
    
    def applies_to(self, element: Any, context: TransformationContext) -> bool:
        """Applies when allOf interpretation is 'inheritance' and allOf has $ref."""
        if not isinstance(element, DefinitionModel):
            return False
        
        if not element.all_of:
            return False
        
        # Only apply if using inheritance strategy
        return self.config.get_allof_interpretation_strategy() == "inheritance"
    
    def apply(self, element: DefinitionModel, builder: OWLBuilder, context: TransformationContext) -> None:
        """Already handled in DefinitionToClassRule - this is a no-op."""
        # Inheritance is already processed in DefinitionToClassRule
        pass


class AllOfToIntersectionRule(DefinitionRule):
    """Transform allOf with multiple $refs to owl:intersectionOf."""
    
    def __init__(self, config: ReverseTransformationConfig = None):
        super().__init__("allof_to_intersection", config)
        self.recognizer = PatternRecognizer()
    
    def applies_to(self, element: Any, context: TransformationContext) -> bool:
        """Applies when allOf interpretation is 'intersection'."""
        if not isinstance(element, DefinitionModel):
            return False
        
        if not element.all_of:
            return False
        
        # Only apply if using intersection strategy
        return self.config.get_allof_interpretation_strategy() == "intersection"
    
    def apply(self, element: DefinitionModel, builder: OWLBuilder, context: TransformationContext) -> None:
        """Create intersection class."""
        # Get class names from allOf
        class_names = self.recognizer.recognize_intersection_pattern(element.all_of)
        
        if len(class_names) < 2:
            # Not enough classes for intersection, skip
            return
        
        # Generate URIs
        class_uri = builder.uri_generator.generate_class_uri(element.name)
        intersection_uris = [builder.uri_generator.generate_class_uri(name) for name in class_names]
        
        # Create intersection class
        builder.add_intersection_class(
            class_uri=class_uri,
            intersection_classes=intersection_uris,
            label=element.title or element.name
        )


class OneOfToUnionRule(DefinitionRule):
    """Transform oneOf to owl:unionOf."""
    
    def __init__(self, config: ReverseTransformationConfig = None):
        super().__init__("oneof_to_union", config)
        self.recognizer = PatternRecognizer()
    
    def applies_to(self, element: Any, context: TransformationContext) -> bool:
        """Applies to definitions with oneOf containing $refs."""
        if not isinstance(element, DefinitionModel):
            return False
        
        if not element.one_of:
            return False
        
        # Check if oneOf contains class references
        class_names = self.recognizer.recognize_union_pattern(element.one_of)
        return len(class_names) > 0
    
    def apply(self, element: DefinitionModel, builder: OWLBuilder, context: TransformationContext) -> None:
        """Create union class."""
        # Get class names from oneOf
        class_names = self.recognizer.recognize_union_pattern(element.one_of)
        
        if len(class_names) < 2:
            # Not enough classes for union, skip
            return
        
        # Generate URIs
        class_uri = builder.uri_generator.generate_class_uri(element.name)
        union_uris = [builder.uri_generator.generate_class_uri(name) for name in class_names]
        
        # Create union class
        builder.add_union_class(
            class_uri=class_uri,
            union_classes=union_uris,
            label=element.title or element.name
        )


class NotToComplementRule(DefinitionRule):
    """Transform not to owl:complementOf."""
    
    def __init__(self, config: ReverseTransformationConfig = None):
        super().__init__("not_to_complement", config)
    
    def applies_to(self, element: Any, context: TransformationContext) -> bool:
        """Applies to definitions with not containing $ref."""
        if not isinstance(element, DefinitionModel):
            return False
        
        if not element.not_:
            return False
        
        # Check if not contains a $ref
        return isinstance(element.not_, dict) and "$ref" in element.not_
    
    def apply(self, element: DefinitionModel, builder: OWLBuilder, context: TransformationContext) -> None:
        """Create complement class."""
        # Extract class name from not
        ref = element.not_["$ref"]
        if ref.startswith("#/definitions/"):
            complement_class_name = ref.split("/")[-1]
            
            # Generate URIs
            class_uri = builder.uri_generator.generate_class_uri(element.name)
            complement_uri = builder.uri_generator.generate_class_uri(complement_class_name)
            
            # Add complement using RDF
            from rdflib import URIRef, OWL
            class_ref = URIRef(class_uri)
            complement_ref = URIRef(complement_uri)
            
            builder.graph.add((class_ref, OWL.complementOf, complement_ref))


# Export all rule classes
__all__ = [
    "AllOfToHierarchyRule",
    "AllOfToIntersectionRule",
    "OneOfToUnionRule",
    "NotToComplementRule"
]
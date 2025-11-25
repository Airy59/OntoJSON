"""
Schema-Level Transformation Rules

Rules for transforming JSON Schema definitions to OWL classes.
"""

from typing import Any
from . import DefinitionRule, SchemaRule
from ..model import DefinitionModel, SchemaModel, TransformationContext
from ..builder import OWLBuilder
from ..config import ReverseTransformationConfig


class DefinitionToClassRule(DefinitionRule):
    """Transform JSON Schema definitions to OWL classes."""
    
    def __init__(self, config: ReverseTransformationConfig = None):
        super().__init__("definition_to_class", config)
    
    def applies_to(self, element: Any, context: TransformationContext) -> bool:
        """Applies to all definitions that are not enumerations."""
        if not isinstance(element, DefinitionModel):
            return False
        
        # Skip enumerations (handled by EnumToIndividualsRule)
        if element.is_enumeration():
            return False
        
        return True
    
    def apply(self, element: DefinitionModel, builder: OWLBuilder, context: TransformationContext) -> None:
        """Create an OWL class for the definition."""
        # Generate class URI
        class_uri = builder.uri_generator.generate_class_uri(element.name)
        
        # Extract parent classes from allOf if using inheritance strategy
        parent_classes = None
        if element.all_of and self.config.get_allof_interpretation_strategy() == "inheritance":
            # Get the first $ref as parent class
            from ..pattern_recognizer import PatternRecognizer
            recognizer = PatternRecognizer()
            parent_name, _ = recognizer.recognize_inheritance_pattern(element.all_of)
            
            if parent_name:
                parent_uri = builder.uri_generator.generate_class_uri(parent_name)
                parent_classes = [parent_uri]
        
        # Create the class
        builder.add_class(
            class_uri=class_uri,
            label=element.title or element.name,
            comment=element.description,
            parent_classes=parent_classes
        )
        
        # Store mapping for later use
        context.uri_mapping[element.name] = class_uri
        context.mark_processed(element.name)


class LabelsRule(DefinitionRule):
    """Add rdfs:label from title field."""
    
    def __init__(self, config: ReverseTransformationConfig = None):
        super().__init__("labels_rule", config)
    
    def applies_to(self, element: Any, context: TransformationContext) -> bool:
        """Applies to definitions with title."""
        return isinstance(element, DefinitionModel) and element.title is not None
    
    def apply(self, element: DefinitionModel, builder: OWLBuilder, context: TransformationContext) -> None:
        """Labels are added by DefinitionToClassRule, so this is a no-op."""
        # Label is already added in DefinitionToClassRule
        pass


class CommentsRule(DefinitionRule):
    """Add rdfs:comment from description field."""
    
    def __init__(self, config: ReverseTransformationConfig = None):
        super().__init__("comments_rule", config)
    
    def applies_to(self, element: Any, context: TransformationContext) -> bool:
        """Applies to definitions with description."""
        return isinstance(element, DefinitionModel) and element.description is not None
    
    def apply(self, element: DefinitionModel, builder: OWLBuilder, context: TransformationContext) -> None:
        """Comments are added by DefinitionToClassRule, so this is a no-op."""
        # Comment is already added in DefinitionToClassRule
        pass


class SchemaMetadataRule(SchemaRule):
    """Transform schema-level metadata to ontology annotations."""
    
    def __init__(self, config: ReverseTransformationConfig = None):
        super().__init__("schema_metadata", config)
    
    def applies_to(self, element: Any, context: TransformationContext) -> bool:
        """Applies to SchemaModel."""
        return isinstance(element, SchemaModel)
    
    def apply(self, element: SchemaModel, builder: OWLBuilder, context: TransformationContext) -> None:
        """Add ontology-level annotations."""
        from rdflib import RDFS, URIRef
        
        # Add title as label
        if element.title:
            builder.add_ontology_annotation(RDFS.label, element.title)
        
        # Add description as comment
        if element.description:
            builder.add_ontology_annotation(RDFS.comment, element.description)
        
        # Add original schema $id as rdfs:seeAlso if present
        if element.schema_id:
            builder.add_ontology_annotation(RDFS.seeAlso, URIRef(element.schema_id))
        
        # Add schema version as annotation
        if element.schema_version:
            builder.add_ontology_annotation(
                builder.base_namespace["schemaVersion"],
                element.schema_version
            )


# Export all rule classes
__all__ = [
    "DefinitionToClassRule",
    "LabelsRule",
    "CommentsRule",
    "SchemaMetadataRule"
]
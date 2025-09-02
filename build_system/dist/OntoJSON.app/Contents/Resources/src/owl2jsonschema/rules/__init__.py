"""
Transformation Rules

This module contains implementations of specific transformation rules.
"""

from .class_rules import (
    ClassToObjectRule,
    ClassHierarchyRule,
    ClassRestrictionsRule
)

from .property_rules import (
    ObjectPropertyRule,
    DatatypePropertyRule,
    PropertyCardinalityRule,
    PropertyRestrictionsRule
)

from .annotation_rules import (
    LabelsToTitlesRule,
    CommentsToDescriptionsRule,
    AnnotationsToMetadataRule
)

from .advanced_rules import (
    EnumerationToEnumRule,
    UnionToAnyOfRule,
    IntersectionToAllOfRule,
    ComplementToNotRule,
    EquivalentClassesRule,
    DisjointClassesRule
)

from .structural_rules import (
    OntologyToDocumentRule,
    IndividualsToExamplesRule,
    OntologyMetadataRule,
    ThingWithUriRule
)

__all__ = [
    # Class rules
    "ClassToObjectRule",
    "ClassHierarchyRule",
    "ClassRestrictionsRule",
    
    # Property rules
    "ObjectPropertyRule",
    "DatatypePropertyRule",
    "PropertyCardinalityRule",
    "PropertyRestrictionsRule",
    
    # Annotation rules
    "LabelsToTitlesRule",
    "CommentsToDescriptionsRule",
    "AnnotationsToMetadataRule",
    
    # Advanced rules
    "EnumerationToEnumRule",
    "UnionToAnyOfRule",
    "IntersectionToAllOfRule",
    "ComplementToNotRule",
    "EquivalentClassesRule",
    "DisjointClassesRule",
    
    # Structural rules
    "OntologyToDocumentRule",
    "IndividualsToExamplesRule",
    "OntologyMetadataRule",
    "ThingWithUriRule"
]
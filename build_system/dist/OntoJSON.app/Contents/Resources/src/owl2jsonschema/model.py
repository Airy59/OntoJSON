"""
Ontology Model Classes

This module defines the object model for representing OWL ontologies in memory.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, Set
from dataclasses import dataclass, field


class OntologyElement(ABC):
    """Base class for all ontology elements."""
    
    @abstractmethod
    def accept(self, visitor):
        """Accept a visitor for the visitor pattern."""
        pass


@dataclass
class OntologyModel:
    """Represents an entire OWL ontology."""
    
    uri: str
    classes: List["OntologyClass"] = field(default_factory=list)
    object_properties: List["ObjectProperty"] = field(default_factory=list)
    datatype_properties: List["DatatypeProperty"] = field(default_factory=list)
    individuals: List["OntologyIndividual"] = field(default_factory=list)
    annotations: Dict[str, Any] = field(default_factory=dict)
    imports: List[str] = field(default_factory=list)
    
    def accept(self, visitor):
        """Accept a visitor for the visitor pattern."""
        return visitor.visit_ontology(self)
    
    def get_class_by_uri(self, uri: str) -> Optional["OntologyClass"]:
        """Get a class by its URI."""
        for cls in self.classes:
            if cls.uri == uri:
                return cls
        return None


@dataclass
class OntologyClass(OntologyElement):
    """Represents an OWL class."""
    
    uri: str
    label: Optional[str] = None
    comment: Optional[str] = None
    super_classes: List[str] = field(default_factory=list)
    equivalent_classes: List[str] = field(default_factory=list)
    disjoint_with: List[str] = field(default_factory=list)
    restrictions: List["OntologyRestriction"] = field(default_factory=list)
    annotations: Dict[str, Any] = field(default_factory=dict)
    
    def accept(self, visitor):
        """Accept a visitor for the visitor pattern."""
        return visitor.visit_class(self)
    
    def get_label(self, lang: Optional[str] = None) -> Optional[str]:
        """Get the label of the class."""
        if isinstance(self.label, dict):
            return self.label.get(lang or "en", self.label.get("en"))
        return self.label
    
    def get_comment(self, lang: Optional[str] = None) -> Optional[str]:
        """Get the comment of the class."""
        if isinstance(self.comment, dict):
            return self.comment.get(lang or "en", self.comment.get("en"))
        return self.comment


@dataclass
class OntologyProperty(OntologyElement):
    """Base class for properties."""
    
    uri: str
    label: Optional[str] = None
    comment: Optional[str] = None
    domain: List[str] = field(default_factory=list)
    range: List[str] = field(default_factory=list)
    super_properties: List[str] = field(default_factory=list)
    annotations: Dict[str, Any] = field(default_factory=dict)
    
    def get_label(self, lang: Optional[str] = None) -> Optional[str]:
        """Get the label of the property."""
        if isinstance(self.label, dict):
            return self.label.get(lang or "en", self.label.get("en"))
        return self.label
    
    def get_comment(self, lang: Optional[str] = None) -> Optional[str]:
        """Get the comment of the property."""
        if isinstance(self.comment, dict):
            return self.comment.get(lang or "en", self.comment.get("en"))
        return self.comment


@dataclass
class ObjectProperty(OntologyProperty):
    """Represents an OWL object property."""
    
    inverse_of: Optional[str] = None
    functional: bool = False
    inverse_functional: bool = False
    transitive: bool = False
    symmetric: bool = False
    asymmetric: bool = False
    irreflexive: bool = False
    reflexive: bool = False
    
    def accept(self, visitor):
        """Accept a visitor for the visitor pattern."""
        return visitor.visit_object_property(self)


@dataclass
class DatatypeProperty(OntologyProperty):
    """Represents an OWL datatype property."""
    
    functional: bool = False
    
    def accept(self, visitor):
        """Accept a visitor for the visitor pattern."""
        return visitor.visit_datatype_property(self)


@dataclass
class OntologyIndividual(OntologyElement):
    """Represents a named individual in the ontology."""
    
    uri: str
    label: Optional[str] = None
    types: List[str] = field(default_factory=list)
    properties: Dict[str, Any] = field(default_factory=dict)
    annotations: Dict[str, Any] = field(default_factory=dict)
    
    def accept(self, visitor):
        """Accept a visitor for the visitor pattern."""
        return visitor.visit_individual(self)


@dataclass
class OntologyRestriction(OntologyElement):
    """Represents a restriction on a class or property."""
    
    property_uri: str
    restriction_type: str  # e.g., "allValuesFrom", "someValuesFrom", "cardinality"
    value: Any  # The value depends on restriction type
    
    def accept(self, visitor):
        """Accept a visitor for the visitor pattern."""
        return visitor.visit_restriction(self)


@dataclass
class CardinalityRestriction(OntologyRestriction):
    """Represents a cardinality restriction."""
    
    min_cardinality: Optional[int] = None
    max_cardinality: Optional[int] = None
    exact_cardinality: Optional[int] = None
    
    def __post_init__(self):
        self.restriction_type = "cardinality"


@dataclass
class ValueRestriction(OntologyRestriction):
    """Represents a value restriction (allValuesFrom, someValuesFrom)."""
    
    filler: str  # The class or datatype that fills the restriction
    
    def __post_init__(self):
        if self.restriction_type not in ["allValuesFrom", "someValuesFrom", "hasValue"]:
            self.restriction_type = "allValuesFrom"
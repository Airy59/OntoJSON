"""
Visitor Pattern Implementation

This module defines the visitor interface and base classes for transformation rules.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional, Dict
from .model import (
    OntologyModel,
    OntologyClass,
    ObjectProperty,
    DatatypeProperty,
    OntologyIndividual,
    OntologyRestriction
)


class OntologyVisitor(ABC):
    """Base visitor interface for traversing ontology elements."""
    
    @abstractmethod
    def visit_ontology(self, ontology: OntologyModel) -> Any:
        """Visit an ontology model."""
        pass
    
    @abstractmethod
    def visit_class(self, owl_class: OntologyClass) -> Any:
        """Visit an ontology class."""
        pass
    
    @abstractmethod
    def visit_object_property(self, property: ObjectProperty) -> Any:
        """Visit an object property."""
        pass
    
    @abstractmethod
    def visit_datatype_property(self, property: DatatypeProperty) -> Any:
        """Visit a datatype property."""
        pass
    
    @abstractmethod
    def visit_individual(self, individual: OntologyIndividual) -> Any:
        """Visit an individual."""
        pass
    
    @abstractmethod
    def visit_restriction(self, restriction: OntologyRestriction) -> Any:
        """Visit a restriction."""
        pass


class TransformationRule(OntologyVisitor):
    """Base class for all transformation rules."""
    
    def __init__(self, rule_id: str, config: Optional[Dict[str, Any]] = None):
        """
        Initialize a transformation rule.
        
        Args:
            rule_id: Unique identifier for the rule
            config: Configuration dictionary for the rule
        """
        self.rule_id = rule_id
        self.config = config or {}
        self.enabled = self.config.get("enabled", True)
        self.options = self.config.get("options", {})
        self.result = None
    
    def is_enabled(self) -> bool:
        """Check if the rule is enabled."""
        return self.enabled
    
    def enable(self):
        """Enable the rule."""
        self.enabled = True
    
    def disable(self):
        """Disable the rule."""
        self.enabled = False
    
    def get_option(self, key: str, default: Any = None) -> Any:
        """Get an option value from the configuration."""
        return self.options.get(key, default)
    
    def reset(self):
        """Reset the rule state."""
        self.result = None
    
    # Default implementations that can be overridden by specific rules
    
    def visit_ontology(self, ontology: OntologyModel) -> Any:
        """Default implementation for visiting an ontology."""
        if not self.is_enabled():
            return None
        
        # Visit all elements in the ontology
        results = []
        
        for owl_class in ontology.classes:
            result = owl_class.accept(self)
            if result is not None:
                results.append(result)
        
        for property in ontology.object_properties:
            result = property.accept(self)
            if result is not None:
                results.append(result)
        
        for property in ontology.datatype_properties:
            result = property.accept(self)
            if result is not None:
                results.append(result)
        
        for individual in ontology.individuals:
            result = individual.accept(self)
            if result is not None:
                results.append(result)
        
        return results if results else None
    
    def visit_class(self, owl_class: OntologyClass) -> Any:
        """Default implementation for visiting a class."""
        if not self.is_enabled():
            return None
        
        # Visit restrictions if any
        for restriction in owl_class.restrictions:
            restriction.accept(self)
        
        return None
    
    def visit_object_property(self, property: ObjectProperty) -> Any:
        """Default implementation for visiting an object property."""
        if not self.is_enabled():
            return None
        return None
    
    def visit_datatype_property(self, property: DatatypeProperty) -> Any:
        """Default implementation for visiting a datatype property."""
        if not self.is_enabled():
            return None
        return None
    
    def visit_individual(self, individual: OntologyIndividual) -> Any:
        """Default implementation for visiting an individual."""
        if not self.is_enabled():
            return None
        return None
    
    def visit_restriction(self, restriction: OntologyRestriction) -> Any:
        """Default implementation for visiting a restriction."""
        if not self.is_enabled():
            return None
        return None


class CompositeVisitor(OntologyVisitor):
    """Composite visitor that applies multiple visitors in sequence."""
    
    def __init__(self, visitors: Optional[list] = None):
        """
        Initialize a composite visitor.
        
        Args:
            visitors: List of visitors to apply
        """
        self.visitors = visitors or []
    
    def add_visitor(self, visitor: OntologyVisitor):
        """Add a visitor to the composite."""
        self.visitors.append(visitor)
    
    def remove_visitor(self, visitor: OntologyVisitor):
        """Remove a visitor from the composite."""
        if visitor in self.visitors:
            self.visitors.remove(visitor)
    
    def visit_ontology(self, ontology: OntologyModel) -> Dict[str, Any]:
        """Apply all visitors to the ontology."""
        results = {}
        for visitor in self.visitors:
            if isinstance(visitor, TransformationRule):
                if visitor.is_enabled():
                    result = ontology.accept(visitor)
                    if result is not None:
                        results[visitor.rule_id] = result
            else:
                result = ontology.accept(visitor)
                if result is not None:
                    results[visitor.__class__.__name__] = result
        return results
    
    def visit_class(self, owl_class: OntologyClass) -> Dict[str, Any]:
        """Apply all visitors to the class."""
        results = {}
        for visitor in self.visitors:
            if isinstance(visitor, TransformationRule):
                if visitor.is_enabled():
                    result = owl_class.accept(visitor)
                    if result is not None:
                        results[visitor.rule_id] = result
            else:
                result = owl_class.accept(visitor)
                if result is not None:
                    results[visitor.__class__.__name__] = result
        return results
    
    def visit_object_property(self, property: ObjectProperty) -> Dict[str, Any]:
        """Apply all visitors to the object property."""
        results = {}
        for visitor in self.visitors:
            if isinstance(visitor, TransformationRule):
                if visitor.is_enabled():
                    result = property.accept(visitor)
                    if result is not None:
                        results[visitor.rule_id] = result
            else:
                result = property.accept(visitor)
                if result is not None:
                    results[visitor.__class__.__name__] = result
        return results
    
    def visit_datatype_property(self, property: DatatypeProperty) -> Dict[str, Any]:
        """Apply all visitors to the datatype property."""
        results = {}
        for visitor in self.visitors:
            if isinstance(visitor, TransformationRule):
                if visitor.is_enabled():
                    result = property.accept(visitor)
                    if result is not None:
                        results[visitor.rule_id] = result
            else:
                result = property.accept(visitor)
                if result is not None:
                    results[visitor.__class__.__name__] = result
        return results
    
    def visit_individual(self, individual: OntologyIndividual) -> Dict[str, Any]:
        """Apply all visitors to the individual."""
        results = {}
        for visitor in self.visitors:
            if isinstance(visitor, TransformationRule):
                if visitor.is_enabled():
                    result = individual.accept(visitor)
                    if result is not None:
                        results[visitor.rule_id] = result
            else:
                result = individual.accept(visitor)
                if result is not None:
                    results[visitor.__class__.__name__] = result
        return results
    
    def visit_restriction(self, restriction: OntologyRestriction) -> Dict[str, Any]:
        """Apply all visitors to the restriction."""
        results = {}
        for visitor in self.visitors:
            if isinstance(visitor, TransformationRule):
                if visitor.is_enabled():
                    result = restriction.accept(visitor)
                    if result is not None:
                        results[visitor.rule_id] = result
            else:
                result = restriction.accept(visitor)
                if result is not None:
                    results[visitor.__class__.__name__] = result
        return results
"""
Rule System for JSON Schema to OWL Transformation

This module provides the base classes and rule registry for reverse transformation rules.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional, Dict, List
from ..model import SchemaModel, DefinitionModel, PropertyModel, TransformationContext
from ..builder import OWLBuilder
from ..config import ReverseTransformationConfig


class ReverseRule(ABC):
    """Base class for reverse transformation rules."""
    
    def __init__(self, rule_id: str, config: Optional[ReverseTransformationConfig] = None):
        """
        Initialize the rule.
        
        Args:
            rule_id: Unique identifier for this rule
            config: Optional configuration
        """
        self.rule_id = rule_id
        self.config = config or ReverseTransformationConfig()
        self.enabled = self.config.is_rule_enabled(rule_id)
        self.priority = self._get_priority()
    
    @abstractmethod
    def applies_to(self, element: Any, context: TransformationContext) -> bool:
        """
        Check if this rule applies to the given element.
        
        Args:
            element: Element to check (SchemaModel, DefinitionModel, PropertyModel, etc.)
            context: Transformation context
        
        Returns:
            True if rule applies to this element
        """
        pass
    
    @abstractmethod
    def apply(self, element: Any, builder: OWLBuilder, context: TransformationContext) -> None:
        """
        Apply the transformation rule.
        
        Args:
            element: Element to transform
            builder: OWL builder to add triples to
            context: Transformation context
        """
        pass
    
    def _get_priority(self) -> int:
        """
        Get the priority of this rule.
        Lower numbers execute first.
        
        Returns:
            Priority value
        """
        # Try to get from config first
        rule_config = self.config.get_rule_config(self.rule_id)
        if "priority" in rule_config:
            return rule_config["priority"]
        
        # Default priority
        return 100
    
    def is_enabled(self) -> bool:
        """Check if this rule is enabled."""
        return self.enabled
    
    def __repr__(self) -> str:
        """String representation."""
        return f"{self.__class__.__name__}(rule_id='{self.rule_id}', enabled={self.enabled}, priority={self.priority})"


class SchemaRule(ReverseRule):
    """Base class for schema-level transformation rules."""
    
    def applies_to(self, element: Any, context: TransformationContext) -> bool:
        """Check if this is a SchemaModel."""
        return isinstance(element, SchemaModel)


class DefinitionRule(ReverseRule):
    """Base class for definition-level transformation rules."""
    
    def applies_to(self, element: Any, context: TransformationContext) -> bool:
        """Check if this is a DefinitionModel."""
        return isinstance(element, DefinitionModel)


class PropertyRule(ReverseRule):
    """Base class for property-level transformation rules."""
    
    def applies_to(self, element: Any, context: TransformationContext) -> bool:
        """Check if this is a PropertyModel."""
        return isinstance(element, PropertyModel)


class RuleRegistry:
    """Registry for managing transformation rules."""
    
    def __init__(self):
        """Initialize the rule registry."""
        self.rules: List[ReverseRule] = []
        self._rules_by_id: Dict[str, ReverseRule] = {}
    
    def register(self, rule: ReverseRule):
        """
        Register a rule.
        
        Args:
            rule: Rule to register
        """
        if rule.rule_id in self._rules_by_id:
            # Replace existing rule
            self.rules = [r for r in self.rules if r.rule_id != rule.rule_id]
        
        self.rules.append(rule)
        self._rules_by_id[rule.rule_id] = rule
        
        # Sort by priority
        self.rules.sort(key=lambda r: r.priority)
    
    def get_rule(self, rule_id: str) -> Optional[ReverseRule]:
        """
        Get a rule by ID.
        
        Args:
            rule_id: Rule identifier
        
        Returns:
            Rule or None if not found
        """
        return self._rules_by_id.get(rule_id)
    
    def get_all_rules(self) -> List[ReverseRule]:
        """Get all registered rules."""
        return self.rules.copy()
    
    def get_enabled_rules(self) -> List[ReverseRule]:
        """Get all enabled rules."""
        return [r for r in self.rules if r.is_enabled()]
    
    def get_applicable_rules(self, element: Any, context: TransformationContext) -> List[ReverseRule]:
        """
        Get all enabled rules that apply to an element.
        
        Args:
            element: Element to check
            context: Transformation context
        
        Returns:
            List of applicable rules, sorted by priority
        """
        applicable = []
        for rule in self.rules:
            if rule.is_enabled() and rule.applies_to(element, context):
                applicable.append(rule)
        
        return applicable
    
    def enable_rule(self, rule_id: str):
        """Enable a rule by ID."""
        rule = self.get_rule(rule_id)
        if rule:
            rule.enabled = True
    
    def disable_rule(self, rule_id: str):
        """Disable a rule by ID."""
        rule = self.get_rule(rule_id)
        if rule:
            rule.enabled = False
    
    def clear(self):
        """Clear all rules."""
        self.rules.clear()
        self._rules_by_id.clear()
    
    def __len__(self) -> int:
        """Return number of registered rules."""
        return len(self.rules)
    
    def __repr__(self) -> str:
        """String representation."""
        enabled_count = len(self.get_enabled_rules())
        return f"RuleRegistry(total={len(self.rules)}, enabled={enabled_count})"


# Export main classes
__all__ = [
    "ReverseRule",
    "SchemaRule",
    "DefinitionRule",
    "PropertyRule",
    "RuleRegistry"
]
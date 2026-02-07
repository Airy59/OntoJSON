"""
JSON Schema Model Classes

This module defines the object model for representing JSON Schema documents in memory.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, Set, Union
from dataclasses import dataclass, field


class SchemaElement(ABC):
    """Base class for all schema elements."""
    
    @abstractmethod
    def accept(self, visitor):
        """Accept a visitor for the visitor pattern."""
        pass


@dataclass
class SchemaModel:
    """Represents a complete JSON Schema document."""
    
    schema_id: Optional[str] = None
    schema_version: str = "http://json-schema.org/draft-07/schema#"
    title: Optional[str] = None
    description: Optional[str] = None
    definitions: Dict[str, "DefinitionModel"] = field(default_factory=dict)
    properties: Dict[str, "PropertyModel"] = field(default_factory=dict)
    required: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    source_filename: Optional[str] = None  # Track source filename for URI generation
    
    def accept(self, visitor):
        """Accept a visitor for the visitor pattern."""
        return visitor.visit_schema(self)
    
    def get_definition(self, name: str) -> Optional["DefinitionModel"]:
        """Get a definition by name."""
        return self.definitions.get(name)


@dataclass
class DefinitionModel(SchemaElement):
    """Represents a JSON Schema definition (typically becomes an OWL class)."""
    
    name: str
    type: Union[str, List[str]] = "object"
    title: Optional[str] = None
    description: Optional[str] = None
    properties: Dict[str, "PropertyModel"] = field(default_factory=dict)
    required: List[str] = field(default_factory=list)
    all_of: List[Union[str, Dict[str, Any]]] = field(default_factory=list)
    one_of: List[Union[str, Dict[str, Any]]] = field(default_factory=list)
    any_of: List[Union[str, Dict[str, Any]]] = field(default_factory=list)
    not_: Optional[Union[str, Dict[str, Any]]] = None
    enum: Optional[List[Any]] = None
    const: Optional[Any] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def accept(self, visitor):
        """Accept a visitor for the visitor pattern."""
        return visitor.visit_definition(self)
    
    def is_enumeration(self) -> bool:
        """Check if this definition represents an enumeration."""
        return self.enum is not None and len(self.enum) > 0
    
    def has_composition(self) -> bool:
        """Check if this definition has composition (allOf/oneOf/anyOf)."""
        return bool(self.all_of or self.one_of or self.any_of)


@dataclass
class PropertyModel(SchemaElement):
    """Represents a JSON Schema property."""
    
    name: str
    type: Union[str, List[str], None] = None
    title: Optional[str] = None
    description: Optional[str] = None
    ref: Optional[str] = None  # For $ref references
    items: Optional[Union[Dict[str, Any], "PropertyModel"]] = None  # For arrays
    min_items: Optional[int] = None
    max_items: Optional[int] = None
    one_of: Optional[List[Dict[str, Any]]] = None
    any_of: Optional[List[Dict[str, Any]]] = None
    all_of: Optional[List[Dict[str, Any]]] = None
    enum: Optional[List[Any]] = None
    const: Optional[Any] = None
    format: Optional[str] = None
    pattern: Optional[str] = None
    minimum: Optional[Union[int, float]] = None
    maximum: Optional[Union[int, float]] = None
    required: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def accept(self, visitor):
        """Accept a visitor for the visitor pattern."""
        return visitor.visit_property(self)
    
    def is_object_reference(self) -> bool:
        """Check if this property references an object (potential object property)."""
        if self.ref:
            return True
        if self.one_of:
            # Check if oneOf contains $ref or @id pattern (object property pattern)
            for option in self.one_of:
                if "$ref" in option:
                    return True
                if isinstance(option, dict) and option.get("properties", {}).get("@id"):
                    return True
        if self.items:
            if isinstance(self.items, dict) and "$ref" in self.items:
                return True
        return False
    
    def is_array(self) -> bool:
        """Check if this property is an array."""
        if isinstance(self.type, str):
            return self.type == "array"
        if isinstance(self.type, list):
            return "array" in self.type
        return False
    
    def get_referenced_class(self) -> Optional[str]:
        """Extract the referenced class name from $ref."""
        if self.ref:
            # Extract from #/definitions/ClassName
            parts = self.ref.split("/")
            if len(parts) >= 3 and parts[1] == "definitions":
                return parts[2]
        if self.items and isinstance(self.items, dict) and "$ref" in self.items:
            parts = self.items["$ref"].split("/")
            if len(parts) >= 3 and parts[1] == "definitions":
                return parts[2]
        if self.one_of:
            for option in self.one_of:
                if "$ref" in option:
                    parts = option["$ref"].split("/")
                    if len(parts) >= 3 and parts[1] == "definitions":
                        return parts[2]
        return None


@dataclass
class CardinalityConstraint:
    """Represents cardinality constraints on a property."""
    
    min_cardinality: Optional[int] = None
    max_cardinality: Optional[int] = None
    exact_cardinality: Optional[int] = None
    
    def is_functional(self) -> bool:
        """Check if this represents a functional property (max 1)."""
        return self.max_cardinality == 1 or self.exact_cardinality == 1
    
    def is_required(self) -> bool:
        """Check if this property is required (min >= 1)."""
        if self.min_cardinality is not None and self.min_cardinality >= 1:
            return True
        if self.exact_cardinality is not None and self.exact_cardinality >= 1:
            return True
        return False


@dataclass
class PatternInfo:
    """Information about recognized OWL patterns in JSON Schema."""
    
    pattern_type: str  # "object_property", "datatype_property", "enumeration", etc.
    confidence: float = 1.0  # 0.0 to 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Pattern-specific information
    property_type: Optional[str] = None  # "object" or "datatype"
    range_class: Optional[str] = None
    datatype: Optional[str] = None
    is_functional: bool = False
    cardinality: Optional[CardinalityConstraint] = None


@dataclass
class TransformationContext:
    """Context information for the transformation process."""
    
    base_namespace: str = "http://example.org/ontology#"
    namespace_prefixes: Dict[str, str] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    processed_definitions: Set[str] = field(default_factory=set)
    uri_mapping: Dict[str, str] = field(default_factory=dict)
    
    def add_warning(self, message: str, location: Optional[str] = None):
        """Add a warning message."""
        if location:
            self.warnings.append(f"{location}: {message}")
        else:
            self.warnings.append(message)
    
    def mark_processed(self, definition_name: str):
        """Mark a definition as processed."""
        self.processed_definitions.add(definition_name)
    
    def is_processed(self, definition_name: str) -> bool:
        """Check if a definition has been processed."""
        return definition_name in self.processed_definitions
    
    def add_property_domain(self, property_uri: str, domain_uri: str):
        """
        Track a property domain for unionOf post-processing.
        
        Args:
            property_uri: Property URI
            domain_uri: Domain class URI
        """
        if not hasattr(self, 'property_domains'):
            self.property_domains = {}
        if property_uri not in self.property_domains:
            self.property_domains[property_uri] = set()
        self.property_domains[property_uri].add(domain_uri)
    
    def get_property_domains(self) -> dict:
        """Get all tracked property domains."""
        return getattr(self, 'property_domains', {})
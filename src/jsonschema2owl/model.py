"""
In-memory model for JSON Schema.
Minimal representation for deterministic rule-based transformation to OWL.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class SchemaNode:
    """Represents a node in the schema (object, property value, ref target)."""

    node_type: str  # 'object', 'property', 'ref', 'enum', 'primitive', 'array'
    name: Optional[str] = None  # key/fragment name for properties/definitions
    title: Optional[str] = None
    description: Optional[str] = None
    raw: Optional[Dict[str, Any]] = None  # original JSON Schema fragment
    parent: Optional["SchemaNode"] = None
    children: List["SchemaNode"] = field(default_factory=list)

    # For object: map property name -> SchemaNode (value schema)
    properties: Dict[str, "SchemaNode"] = field(default_factory=dict)
    # For $ref
    ref_target: Optional[str] = None  # resolved URI or definition path
    # For enum
    enum_values: List[Any] = field(default_factory=list)
    # JSON Schema type
    json_type: Optional[str] = None  # 'object', 'string', 'number', 'integer', 'boolean', 'array', 'null'
    # For array
    items: Optional["SchemaNode"] = None
    # definitions/$defs for local refs
    definitions: Dict[str, "SchemaNode"] = field(default_factory=dict)


@dataclass
class SchemaModel:
    """Root model: parsed JSON Schema with optional definitions."""

    root: SchemaNode
    definitions: Dict[str, SchemaNode] = field(default_factory=dict)
    base_uri: Optional[str] = None
    raw_schema: Optional[Dict[str, Any]] = None

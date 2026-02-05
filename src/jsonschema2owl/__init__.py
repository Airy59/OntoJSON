"""
JSON Schema to OWL transformation library.
Rule-based, deterministic conversion; no dependency on owl2jsonschema.
"""

from .parser import SchemaParser
from .transformer import JsonSchema2OwlTransformer
from .config import JsonSchema2OwlConfig
from .model import SchemaModel, SchemaNode
from .rules import RuleRegistry, TransformationRule

__all__ = [
    "SchemaParser",
    "SchemaModel",
    "SchemaNode",
    "JsonSchema2OwlTransformer",
    "JsonSchema2OwlConfig",
    "RuleRegistry",
    "TransformationRule",
]

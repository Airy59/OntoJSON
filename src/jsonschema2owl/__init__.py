"""
JSON Schema to OWL2 Reverse Transformation Engine

A configurable transformation engine for converting JSON Schema documents to OWL2 ontologies.
"""

__version__ = "0.1.0"

from .engine import ReverseEngine
from .config import ReverseTransformationConfig
from .parser import SchemaParser
from .model import SchemaModel, DefinitionModel, PropertyModel

__all__ = [
    "ReverseEngine",
    "ReverseTransformationConfig",
    "SchemaParser",
    "SchemaModel",
    "DefinitionModel",
    "PropertyModel"
]
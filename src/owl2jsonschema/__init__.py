"""
OWL to JSON Schema Transformation Engine

A configurable transformation engine for converting OWL/RDF ontologies to JSON Schema.
"""

__version__ = "0.1.0"

from .engine import TransformationEngine
from .config import TransformationConfig
from .parser import OntologyParser
from .abox_generator import ABoxGenerator

__all__ = ["TransformationEngine", "TransformationConfig", "OntologyParser", "ABoxGenerator"]
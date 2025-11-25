"""
Reverse Transformation Service

Platform-agnostic service for JSON Schema to OWL transformation.
This service can be used by CLI, GUI, and Web interfaces.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass
from enum import Enum
from rdflib import Graph

from ..engine import ReverseEngine
from ..config import ReverseTransformationConfig
from ..parser import SchemaParser


# Set up logging
logger = logging.getLogger(__name__)


class ReverseTransformationStatus(Enum):
    """Status of a reverse transformation task."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ReverseTransformationResult:
    """Result of a reverse transformation operation."""
    success: bool
    ontology: Optional[str] = None  # Serialized ontology
    format: str = "turtle"
    error: Optional[str] = None
    warnings: list = None
    statistics: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []
        if self.statistics is None:
            self.statistics = {}


class ReverseTransformationService:
    """
    Service for managing JSON Schema to OWL transformations.
    
    This service provides a high-level API for reverse transformation operations
    that can be used across different presentation layers.
    """
    
    def __init__(self):
        """Initialize the reverse transformation service."""
        self.parser = SchemaParser()
        
    def transform(
        self,
        schema_source: Union[str, Dict[str, Any], Path],
        config: Optional[ReverseTransformationConfig] = None,
        base_namespace: str = "https://cdm.ovh/examples/",
        language: str = "en",
        output_format: str = "turtle",
        filename: Optional[str] = None
    ) -> ReverseTransformationResult:
        """
        Transform a JSON Schema to OWL ontology.
        
        Args:
            schema_source: JSON Schema as string, dict, or file path
            config: Transformation configuration
            base_namespace: Base namespace for the ontology
            language: Language tag for labels/comments
            output_format: Output format (turtle, xml, json-ld)
            filename: Optional filename to derive schema name from
            
        Returns:
            ReverseTransformationResult with the ontology or error information
        """
        try:
            # Use default config if not provided
            if config is None:
                config = ReverseTransformationConfig()
            
            # Set base namespace
            config.set_base_namespace(base_namespace)
            
            # Set language if metadata rules are enabled
            if config.is_rule_enabled("labels_rule"):
                config.set_rule_option("labels_rule", "language", language)
            if config.is_rule_enabled("comments_rule"):
                config.set_rule_option("comments_rule", "language", language)
            
            # Parse the schema with filename
            if isinstance(schema_source, dict):
                # If filename not provided for dict, use generic name
                schema_model = self.parser.parse(json.dumps(schema_source), filename=filename)
            elif isinstance(schema_source, (str, Path)):
                source_str = str(schema_source)
                if source_str.startswith('{'):
                    # It's JSON string
                    schema_model = self.parser.parse(source_str, filename=filename)
                else:
                    # It's file path - parse_file will handle filename automatically
                    schema_model = self.parser.parse_file(source_str)
            else:
                raise ValueError(f"Invalid schema source type: {type(schema_source)}")
            
            # Create and run the transformation engine
            engine = ReverseEngine(config)
            graph = engine.transform(schema_model)
            
            # Serialize the ontology
            ontology_str = engine.serialize(graph, format=output_format)
            
            # Calculate statistics
            statistics = self._calculate_statistics(graph)
            
            # Prepare warnings from transformation context
            warnings = []
            # Note: warnings would come from the transformation context
            # For now, we'll keep it empty
            
            return ReverseTransformationResult(
                success=True,
                ontology=ontology_str,
                format=output_format,
                statistics=statistics,
                warnings=warnings
            )
            
        except Exception as e:
            logger.error(f"Transformation failed: {e}", exc_info=True)
            return ReverseTransformationResult(
                success=False,
                error=str(e),
                format=output_format
            )
    
    def transform_file(
        self,
        file_path: Union[str, Path],
        config: Optional[ReverseTransformationConfig] = None,
        base_namespace: str = "https://cdm.ovh/examples/",
        language: str = "en",
        output_format: str = "turtle"
    ) -> ReverseTransformationResult:
        """
        Transform a JSON Schema file to OWL ontology.
        
        Args:
            file_path: Path to JSON Schema file
            config: Transformation configuration
            base_namespace: Base namespace for the ontology
            language: Language tag for labels/comments
            output_format: Output format (turtle, xml, json-ld)
            
        Returns:
            ReverseTransformationResult with the ontology or error information
        """
        return self.transform(
            schema_source=file_path,
            config=config,
            base_namespace=base_namespace,
            language=language,
            output_format=output_format,
            filename=None  # parser.parse_file will handle this
        )
    
    def transform_dict(
        self,
        schema_dict: Dict[str, Any],
        config: Optional[ReverseTransformationConfig] = None,
        base_namespace: str = "https://cdm.ovh/examples/",
        language: str = "en",
        output_format: str = "turtle",
        filename: Optional[str] = None
    ) -> ReverseTransformationResult:
        """
        Transform a JSON Schema dictionary to OWL ontology.
        
        Args:
            schema_dict: JSON Schema as dictionary
            config: Transformation configuration
            base_namespace: Base namespace for the ontology
            language: Language tag for labels/comments
            output_format: Output format (turtle, xml, json-ld)
            filename: Optional filename to derive schema name from
            
        Returns:
            ReverseTransformationResult with the ontology or error information
        """
        return self.transform(
            schema_source=schema_dict,
            config=config,
            base_namespace=base_namespace,
            language=language,
            output_format=output_format,
            filename=filename
        )
    
    def _calculate_statistics(self, graph: Graph) -> Dict[str, Any]:
        """
        Calculate statistics from the generated ontology.
        
        Args:
            graph: RDFLib graph
            
        Returns:
            Dictionary of statistics
        """
        from rdflib import OWL, RDF, RDFS
        
        stats = {
            'classes': 0,
            'object_properties': 0,
            'datatype_properties': 0,
            'individuals': 0,
            'total_triples': len(graph)
        }
        
        # Count classes
        stats['classes'] = len(list(graph.subjects(RDF.type, OWL.Class)))
        
        # Count object properties
        stats['object_properties'] = len(list(graph.subjects(RDF.type, OWL.ObjectProperty)))
        
        # Count datatype properties
        stats['datatype_properties'] = len(list(graph.subjects(RDF.type, OWL.DatatypeProperty)))
        
        # Count named individuals
        stats['individuals'] = len(list(graph.subjects(RDF.type, OWL.NamedIndividual)))
        
        return stats
    
    def get_available_formats(self) -> list:
        """
        Get list of available output formats.
        
        Returns:
            List of format names
        """
        return ["turtle", "xml", "json-ld"]
    
    def validate_namespace(self, namespace: str) -> tuple:
        """
        Validate that a namespace URI is well-formed.
        
        Args:
            namespace: Namespace URI to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            from rdflib import Namespace
            Namespace(namespace)
            
            # Check if it ends with # or /
            if not (namespace.endswith('#') or namespace.endswith('/')):
                return False, "Namespace should end with '#' or '/'"
            
            return True, None
        except Exception as e:
            return False, str(e)


# Export main class
__all__ = [
    'ReverseTransformationService',
    'ReverseTransformationResult',
    'ReverseTransformationStatus'
]
"""
Transformation Service

Platform-agnostic service for OWL to JSON Schema transformation.
This service can be used by CLI, GUI, and Web interfaces.
"""

import json
import tempfile
from pathlib import Path
from typing import Dict, Any, List, Optional, Union, Tuple
from dataclasses import dataclass
from enum import Enum

from ..engine import TransformationEngine
from ..config import TransformationConfig
from ..parser import OntologyParser
from ..composite_builder import CompositeOntologyBuilder
from ..abox_generator import ABoxGenerator
from ..abox_to_json import ABoxToJSONConverter


class TransformationStatus(Enum):
    """Status of a transformation task."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TransformationResult:
    """Result of a transformation operation."""
    success: bool
    schema: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    warnings: List[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []
        if self.metadata is None:
            self.metadata = {}


@dataclass
class TransformationTask:
    """Represents a transformation task."""
    id: str
    status: TransformationStatus
    input_sources: List[str]
    config: Optional[Dict[str, Any]]
    result: Optional[TransformationResult] = None
    progress: int = 0
    message: str = ""
    created_at: Optional[str] = None
    completed_at: Optional[str] = None


class TransformationService:
    """
    Service for managing OWL to JSON Schema transformations.
    
    This service provides a high-level API for transformation operations
    that can be used across different presentation layers.
    """
    
    def __init__(self):
        """Initialize the transformation service."""
        self.parser = OntologyParser()
        self.tasks: Dict[str, TransformationTask] = {}
        
    def transform_single(
        self,
        source: Union[str, Path],
        config: Optional[TransformationConfig] = None,
        language: str = "en",
        rdf_format: str = "auto"
    ) -> TransformationResult:
        """
        Transform a single ontology file to JSON Schema.
        
        Args:
            source: Path or URI to the ontology
            config: Transformation configuration
            language: Language for labels and comments
            rdf_format: RDF format of the input file
            
        Returns:
            TransformationResult with the schema or error information
        """
        try:
            # Use default config if not provided
            if config is None:
                config = TransformationConfig()
            
            # Set language options
            config.set_rule_option("labels_to_titles", "language", language)
            config.set_rule_option("comments_to_descriptions", "language", language)
            
            # Parse the ontology
            if rdf_format == "auto":
                ontology = self.parser.parse(source)
            else:
                ontology = self.parser.parse(source, format=rdf_format)
            
            # Create and run the transformation engine
            engine = TransformationEngine(config)
            json_schema = engine.transform(ontology)
            
            # Prepare metadata
            metadata = {
                "source": str(source),
                "classes_count": len(ontology.classes),
                "properties_count": len(ontology.object_properties) + len(ontology.datatype_properties),
                "individuals_count": len(ontology.individuals),
                "enabled_rules": engine.get_enabled_rules()
            }
            
            return TransformationResult(
                success=True,
                schema=json_schema,
                metadata=metadata
            )
            
        except Exception as e:
            return TransformationResult(
                success=False,
                error=str(e)
            )
    
    def transform_multiple(
        self,
        sources: List[Union[str, Path]],
        composite_metadata: Optional[Dict[str, Any]] = None,
        config: Optional[TransformationConfig] = None,
        language: str = "en",
        save_composite: bool = False,
        composite_output_path: Optional[Path] = None
    ) -> TransformationResult:
        """
        Transform multiple ontology sources to JSON Schema.
        
        Args:
            sources: List of paths or URIs to ontologies
            composite_metadata: Metadata for the composite ontology
            config: Transformation configuration
            language: Language for labels and comments
            save_composite: Whether to save the composite ontology
            composite_output_path: Path to save the composite ontology
            
        Returns:
            TransformationResult with the schema or error information
        """
        temp_file = None
        try:
            # Create composite ontology
            builder = CompositeOntologyBuilder()
            
            # Add metadata if provided
            if composite_metadata:
                builder.add_metadata(composite_metadata)
            
            # Add imports for all sources
            builder.add_imports(sources)
            
            # Serialize to temporary file or specified path
            if save_composite and composite_output_path:
                composite_path = composite_output_path
                builder.serialize_to_file(str(composite_path))
            else:
                temp_file = tempfile.NamedTemporaryFile(
                    mode='w',
                    suffix='.ttl',
                    delete=False
                )
                temp_file.write(builder.serialize())
                temp_file.close()
                composite_path = temp_file.name
            
            # Transform the composite ontology
            result = self.transform_single(
                composite_path,
                config=config,
                language=language,
                rdf_format="turtle"
            )
            
            # Add composite-specific metadata
            if result.success and result.metadata:
                result.metadata["is_composite"] = True
                result.metadata["source_count"] = len(sources)
                result.metadata["sources"] = [str(s) for s in sources]
                if save_composite:
                    result.metadata["composite_saved_to"] = str(composite_output_path)
            
            return result
            
        except Exception as e:
            return TransformationResult(
                success=False,
                error=str(e)
            )
        finally:
            # Clean up temporary file if created
            if temp_file and Path(temp_file.name).exists():
                Path(temp_file.name).unlink()
    
    def generate_abox(
        self,
        schema: Dict[str, Any],
        instance_count: int = 10,
        seed: Optional[int] = None
    ) -> TransformationResult:
        """
        Generate ABox (individuals) from a JSON Schema.
        
        Args:
            schema: JSON Schema to generate individuals from
            instance_count: Number of instances to generate
            seed: Random seed for reproducible generation
            
        Returns:
            TransformationResult with the generated ABox
        """
        try:
            generator = ABoxGenerator(schema, seed=seed)
            abox = generator.generate(instance_count)
            
            return TransformationResult(
                success=True,
                schema=abox,
                metadata={
                    "instance_count": instance_count,
                    "seed": seed
                }
            )
            
        except Exception as e:
            return TransformationResult(
                success=False,
                error=str(e)
            )
    
    def convert_abox_to_json(
        self,
        abox_data: Union[str, Dict[str, Any]],
        format: str = "json"
    ) -> TransformationResult:
        """
        Convert ABox data to JSON or JSON-LD format.
        
        Args:
            abox_data: ABox data (Turtle string or parsed data)
            format: Output format ("json" or "jsonld")
            
        Returns:
            TransformationResult with the converted data
        """
        try:
            # Note: This is a placeholder implementation
            # The actual conversion would require proper JSON Schema
            # and RDF graph processing
            
            # For now, just return the data as-is or convert to JSON-LD format
            if format == "jsonld":
                result = {
                    "@context": {
                        "@base": "https://example.org#",
                        "@vocab": "https://example.org#"
                    },
                    "@graph": abox_data if isinstance(abox_data, list) else [abox_data]
                }
            else:
                result = abox_data
            
            return TransformationResult(
                success=True,
                schema=result,
                metadata={
                    "format": format
                }
            )
            
        except Exception as e:
            return TransformationResult(
                success=False,
                error=str(e)
            )
    
    def full_pipeline(
        self,
        sources: List[Union[str, Path]],
        config: Optional[TransformationConfig] = None,
        generate_instances: bool = True,
        instance_count: int = 10,
        output_format: str = "json"
    ) -> Tuple[TransformationResult, Optional[TransformationResult], Optional[TransformationResult]]:
        """
        Execute the full transformation pipeline: T-box → A-box → JSON instances.
        
        Args:
            sources: Ontology sources
            config: Transformation configuration
            generate_instances: Whether to generate instances
            instance_count: Number of instances to generate
            output_format: Output format for instances
            
        Returns:
            Tuple of (T-box result, A-box result, JSON result)
        """
        # Step 1: Transform to JSON Schema (T-box)
        if len(sources) == 1:
            tbox_result = self.transform_single(sources[0], config=config)
        else:
            tbox_result = self.transform_multiple(sources, config=config)
        
        if not tbox_result.success or not generate_instances:
            return tbox_result, None, None
        
        # Step 2: Generate A-box
        abox_result = self.generate_abox(
            tbox_result.schema,
            instance_count=instance_count
        )
        
        if not abox_result.success:
            return tbox_result, abox_result, None
        
        # Step 3: Convert to JSON instances
        json_result = self.convert_abox_to_json(
            abox_result.schema,
            format=output_format
        )
        
        return tbox_result, abox_result, json_result
    
    def validate_ontology_source(
        self,
        source: Union[str, Path]
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate that an ontology source is accessible and parseable.
        
        Args:
            source: Path or URI to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Try to parse the ontology
            self.parser.parse(source)
            return True, None
        except Exception as e:
            return False, str(e)
    
    def get_available_rules(self) -> List[Dict[str, Any]]:
        """
        Get list of available transformation rules.
        
        Returns:
            List of rule information dictionaries
        """
        # This could be enhanced to dynamically discover rules
        rules = [
            {"id": "class_to_object", "name": "Classes to Objects", "description": "Transform OWL classes to JSON Schema objects"},
            {"id": "class_hierarchy", "name": "Class Hierarchy", "description": "Transform class hierarchy to JSON Schema inheritance"},
            {"id": "class_restrictions", "name": "Class Restrictions", "description": "Transform class restrictions to JSON Schema constraints"},
            {"id": "object_property", "name": "Object Properties", "description": "Transform object properties to JSON Schema properties"},
            {"id": "datatype_property", "name": "Datatype Properties", "description": "Transform datatype properties to JSON Schema properties"},
            {"id": "property_cardinality", "name": "Property Cardinality", "description": "Transform property cardinality to JSON Schema constraints"},
            {"id": "labels_to_titles", "name": "Labels to Titles", "description": "Transform RDFS labels to JSON Schema titles"},
            {"id": "comments_to_descriptions", "name": "Comments to Descriptions", "description": "Transform RDFS comments to JSON Schema descriptions"},
            {"id": "enumeration_to_enum", "name": "Enumerations", "description": "Transform OWL enumerations to JSON Schema enum"},
            {"id": "union_to_anyOf", "name": "Unions", "description": "Transform OWL unions to JSON Schema anyOf"},
            {"id": "intersection_to_allOf", "name": "Intersections", "description": "Transform OWL intersections to JSON Schema allOf"},
            {"id": "disjoint_classes", "name": "Disjoint Classes", "description": "Handle OWL disjoint classes"},
            {"id": "ontology_metadata", "name": "Ontology Metadata", "description": "Transform ontology metadata to JSON Schema metadata"},
            {"id": "thing_with_uri", "name": "Thing with URI", "description": "Add base Thing object with URI support"}
        ]
        return rules
    
    def create_task(
        self,
        sources: List[str],
        config: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a new transformation task (for async processing).
        
        Args:
            sources: List of ontology sources
            config: Transformation configuration
            
        Returns:
            Task ID
        """
        import uuid
        from datetime import datetime
        
        task_id = str(uuid.uuid4())
        task = TransformationTask(
            id=task_id,
            status=TransformationStatus.PENDING,
            input_sources=sources,
            config=config,
            created_at=datetime.utcnow().isoformat()
        )
        self.tasks[task_id] = task
        return task_id
    
    def get_task(self, task_id: str) -> Optional[TransformationTask]:
        """Get a transformation task by ID."""
        return self.tasks.get(task_id)
    
    def update_task_progress(
        self,
        task_id: str,
        progress: int,
        message: str = ""
    ):
        """Update task progress."""
        if task_id in self.tasks:
            self.tasks[task_id].progress = progress
            self.tasks[task_id].message = message
            if progress > 0:
                self.tasks[task_id].status = TransformationStatus.IN_PROGRESS
    
    def complete_task(
        self,
        task_id: str,
        result: TransformationResult
    ):
        """Mark a task as completed."""
        from datetime import datetime
        
        if task_id in self.tasks:
            self.tasks[task_id].status = (
                TransformationStatus.COMPLETED if result.success
                else TransformationStatus.FAILED
            )
            self.tasks[task_id].result = result
            self.tasks[task_id].progress = 100
            self.tasks[task_id].completed_at = datetime.utcnow().isoformat()
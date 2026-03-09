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
import re

from ..engine import TransformationEngine
from ..config import TransformationConfig
from ..parser import OntologyParser
from ..composite_builder import CompositeOntologyBuilder
from ..abox_generator import ABoxGenerator
from ..abox_to_json import ABoxToJSONConverter
from ..crossref_resolver import CrossReferenceResolver


def normalize_line_endings(file_path: Union[str, Path]) -> str:
    """
    Normalize line endings in a file to Unix-style (LF).
    
    This function handles Windows (CRLF), old Mac (CR), and mixed line endings,
    converting them all to Unix-style (LF). It also removes any duplicate line
    endings that might cause parsing issues.
    
    Args:
        file_path: Path to the file to normalize
        
    Returns:
        Path to a temporary file with normalized content
    """
    try:
        # Read the file in binary mode to preserve encoding
        with open(file_path, 'rb') as f:
            content = f.read()
        
        # Decode with error handling for different encodings
        try:
            text = content.decode('utf-8')
        except UnicodeDecodeError:
            try:
                text = content.decode('latin-1')
            except UnicodeDecodeError:
                text = content.decode('utf-8', errors='replace')
        
        # Normalize all line endings to \n
        # First, replace \r\n with \n (Windows)
        text = text.replace('\r\n', '\n')
        # Then replace remaining \r with \n (old Mac)
        text = text.replace('\r', '\n')
        # Remove any duplicate newlines that might have been created
        text = re.sub(r'\n\n+', '\n\n', text)
        
        # Create a temporary file with normalized content
        suffix = Path(file_path).suffix
        with tempfile.NamedTemporaryFile(mode='w', suffix=suffix, delete=False, encoding='utf-8') as temp_file:
            temp_file.write(text)
            return temp_file.name
            
    except Exception as e:
        print(f"Warning: Could not normalize line endings for {file_path}: {e}")
        # Return original file path if normalization fails
        return str(file_path)


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
    component_schemas: Optional[Dict[str, Dict[str, Any]]] = None  # Maps component name to schema
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []
        if self.metadata is None:
            self.metadata = {}
        if self.component_schemas is None:
            self.component_schemas = {}


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
        normalized_file = None
        try:
            # Use default config if not provided
            if config is None:
                config = TransformationConfig()
            
            # Set language options
            config.set_rule_option("labels_to_titles", "language", language)
            config.set_rule_option("comments_to_descriptions", "language", language)
            
            # Normalize line endings for local files
            source_to_parse = source
            if not str(source).startswith(('http://', 'https://', 'ftp://')):
                normalized_file = normalize_line_endings(source)
                source_to_parse = normalized_file
                print(f"Normalized line endings for: {Path(source).name}")
            
            # Parse the ontology
            if rdf_format == "auto":
                ontology = self.parser.parse(source_to_parse)
            else:
                ontology = self.parser.parse(source_to_parse, format=rdf_format)
            
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
        finally:
            # Clean up normalized temp file
            if normalized_file and Path(normalized_file).exists():
                try:
                    Path(normalized_file).unlink()
                except Exception:
                    pass
    
    def transform_multiple(
        self,
        sources: List[Union[str, Path]],
        composite_metadata: Optional[Dict[str, Any]] = None,
        config: Optional[TransformationConfig] = None,
        language: str = "en",
        save_composite: bool = False,
        composite_output_path: Optional[Path] = None,
        transform_components: bool = True
    ) -> TransformationResult:
        """
        Transform multiple ontology sources to JSON Schema.
        
        Creates schemas for:
        1. The composite ontology (imports all sources)
        2. Each individual component ontology (if transform_components=True)
        
        Args:
            sources: List of paths or URIs to ontologies
            composite_metadata: Metadata for the composite ontology
            config: Transformation configuration
            language: Language for labels and comments
            save_composite: Whether to save the composite ontology
            composite_output_path: Path to save the composite ontology
            transform_components: Whether to also transform individual components
            
        Returns:
            TransformationResult with the composite schema and component schemas
        """
        temp_file = None
        normalized_files = []
        try:
            # Normalize line endings for all local source files
            normalized_sources = []
            for source in sources:
                if not str(source).startswith(('http://', 'https://', 'ftp://')):
                    normalized = normalize_line_endings(source)
                    normalized_files.append(normalized)
                    normalized_sources.append(normalized)
                    print(f"Normalized line endings for: {Path(source).name}")
                else:
                    normalized_sources.append(source)
            # Create composite ontology using normalized sources
            builder = CompositeOntologyBuilder()
            
            # Add metadata if provided
            if composite_metadata:
                builder.add_metadata(composite_metadata)
            
            # Add imports using NORMALIZED sources (not originals) to avoid line ending issues
            print(f"DEBUG: Adding imports for normalized sources: {normalized_sources}")
            builder.add_imports(normalized_sources)
            
            # Serialize to temporary file or specified path
            if save_composite and composite_output_path:
                composite_path = composite_output_path
                builder.save_to_file(str(composite_path))
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
            # Store original sources (HTTP URIs) in config so they can be used in comments
            # Only set if not already set (e.g., by task endpoint which has the original HTTP URIs)
            existing_original_sources = config.get_rule_config("ontology_to_document").get("options", {}).get("original_sources", [])
            if not existing_original_sources:
                # Filter to only HTTP/HTTPS URIs (not file paths)
                original_http_sources = [str(s) for s in sources if str(s).startswith(('http://', 'https://'))]
                if original_http_sources and config:
                    # Store in config so it can be accessed by rules
                    config.set_rule_option("ontology_to_document", "original_sources", original_http_sources)
            
            result = self.transform_single(
                composite_path,
                config=config,
                language=language,
                rdf_format="turtle"
            )
            
            # Transform each individual component if requested
            component_schemas = {}
            crossref_resolver = CrossReferenceResolver()
            component_source_map = {}  # Map component names to original sources
            
            if transform_components and result.success:
                # First pass: Transform all components and register classes
                parsed_ontologies = []
                for i, source in enumerate(sources):
                    # Extract meaningful name from original source (handles URIs and file paths)
                    component_name = self._extract_name_from_source(source)
                    
                    # Store the mapping of component name to original source
                    component_source_map[component_name] = str(source)
                    
                    # Use normalized source for transformation
                    source_to_transform = normalized_sources[i]
                    
                    try:
                        # Parse the ontology first to register classes
                        ontology = self.parser.parse(source_to_transform)
                        parsed_ontologies.append((component_name, ontology))
                        
                        # Register all classes from this ontology
                        for owl_class in ontology.classes:
                            class_uri = owl_class.uri
                            # Extract clean class name (same logic as in builder)
                            class_name = self._clean_definition_name(class_uri)
                            crossref_resolver.register_class(class_uri, class_name, component_name)
                        
                        # Transform this component
                        component_result = self.transform_single(
                            source_to_transform,
                            config=config,
                            language=language
                        )
                        
                        if component_result.success:
                            component_schemas[component_name] = component_result.schema
                            print(f"✓ Component '{component_name}' transformed successfully")
                        else:
                            # Log warning but continue with other components
                            warning_msg = f"Failed to transform component '{component_name}': {component_result.error}"
                            result.warnings.append(warning_msg)
                            print(f"✗ Component '{component_name}' failed: {component_result.error}")
                    except Exception as e:
                        warning_msg = f"Exception transforming component '{component_name}': {str(e)}"
                        result.warnings.append(warning_msg)
                        print(f"✗ Component '{component_name}' exception: {str(e)}")
                
                # Second pass: Rewrite cross-references in all component schemas
                print("\n🔗 Resolving cross-references...")
                for component_name in component_schemas.keys():
                    original_schema = component_schemas[component_name]
                    rewritten_schema = crossref_resolver.rewrite_schema_references(
                        original_schema,
                        component_name,
                        component_suffix="_schema.json"
                    )
                    component_schemas[component_name] = rewritten_schema
                    print(f"  ✓ Resolved references for '{component_name}'")
            
            # Add component schemas to result
            result.component_schemas = component_schemas
            
            # Add composite-specific metadata
            if result.success and result.metadata:
                result.metadata["is_composite"] = True
                result.metadata["source_count"] = len(sources)
                result.metadata["sources"] = [str(s) for s in sources]
                result.metadata["component_count"] = len(component_schemas)
                result.metadata["component_names"] = list(component_schemas.keys())
                result.metadata["component_source_map"] = component_source_map  # Add source mapping
                if save_composite:
                    result.metadata["composite_saved_to"] = str(composite_output_path)
            
            return result
            
        except Exception as e:
            return TransformationResult(
                success=False,
                error=str(e)
            )
        finally:
            # Clean up temporary files
            if temp_file and Path(temp_file.name).exists():
                try:
                    Path(temp_file.name).unlink()
                except Exception:
                    pass
            for normalized_file in normalized_files:
                if Path(normalized_file).exists():
                    try:
                        Path(normalized_file).unlink()
                    except Exception:
                        pass
    
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
    
    def save_transformation_results(
        self,
        result: TransformationResult,
        output_dir: Union[str, Path],
        composite_filename: str = "composite_schema.json",
        component_prefix: str = "",
        component_suffix: str = "_schema.json"
    ) -> Dict[str, str]:
        """
        Save transformation results to separate files.
        
        Saves:
        1. The composite schema to a file
        2. Each component schema to separate files
        
        Args:
            result: TransformationResult containing schemas
            output_dir: Directory where to save the schemas
            composite_filename: Filename for the composite schema
            component_prefix: Prefix for component schema filenames
            component_suffix: Suffix for component schema filenames
            
        Returns:
            Dictionary mapping schema name to saved file path
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        saved_files = {}
        
        # Save composite schema
        if result.schema:
            composite_path = output_path / composite_filename
            with open(composite_path, 'w', encoding='utf-8') as f:
                json.dump(result.schema, f, indent=2)
            saved_files["composite"] = str(composite_path)
        
        # Save component schemas
        if result.component_schemas:
            for component_name, component_schema in result.component_schemas.items():
                filename = f"{component_prefix}{component_name}{component_suffix}"
                component_path = output_path / filename
                with open(component_path, 'w', encoding='utf-8') as f:
                    json.dump(component_schema, f, indent=2)
                saved_files[component_name] = str(component_path)
        
        return saved_files
    
    def _extract_name_from_source(self, source: Union[str, Path]) -> str:
        """
        Extract a meaningful name from a source (file path or URI).
        
        Args:
            source: The source path or URI
            
        Returns:
            A clean, meaningful name for the component
        """
        source_str = str(source)
        
        # Check if source is a URL
        if source_str.startswith(('http://', 'https://', 'ftp://')):
            # Try to get fragment (after #) first
            if '#' in source_str:
                fragment = source_str.split('#')[-1]
                if fragment and not fragment.startswith('http'):
                    # Remove file extension if present
                    fragment = re.sub(r'\.(ttl|rdf|owl|xml|n3|nt|jsonld)$', '', fragment, flags=re.IGNORECASE)
                    if fragment:
                        return fragment
            
            # Fall back to last path segment (after last /)
            path_parts = source_str.split('/')
            last_name = path_parts[-1] if path_parts else ''
            
            # Remove query parameters and fragments
            last_name = last_name.split('?')[0].split('#')[0]
            
            # Remove file extension
            last_name = re.sub(r'\.(ttl|rdf|owl|xml|n3|nt|jsonld)$', '', last_name, flags=re.IGNORECASE)
            
            if last_name:
                return last_name
            
            # Final fallback for URIs
            return 'ontology'
        else:
            # It's a file path - extract filename without extension
            name = Path(source).stem
            
            # Remove UUID prefixes that may have been added by file upload system
            # Remove full UUID (with or without dashes): xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx or xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
            # Also remove temp file prefixes like tmpXXXXXX
            name = re.sub(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}[-_]?', '', name, flags=re.IGNORECASE)
            name = re.sub(r'^[0-9a-f]{32}[-_]?', '', name, flags=re.IGNORECASE)
            name = re.sub(r'^[0-9a-f]{8}[-_]', '', name, flags=re.IGNORECASE)
            name = re.sub(r'^tmp[a-z0-9]+[-_]', '', name, flags=re.IGNORECASE)
            
            # If nothing remains after cleanup, use fallback
            if not name:
                name = 'ontology'
            
            return name
    
    def _clean_definition_name(self, name: str) -> str:
        """
        Clean a name to be a valid JSON Schema definition name.
        
        Args:
            name: The name to clean
        
        Returns:
            The cleaned name
        """
        # Remove namespace prefixes if present
        if ':' in name:
            name = name.split(':')[-1]
        
        # Remove URI parts if present
        if '/' in name:
            name = name.split('/')[-1]
        
        if '#' in name:
            name = name.split('#')[-1]
        
        # Replace invalid characters
        name = name.replace(' ', '_')
        name = name.replace('-', '_')
        
        return name
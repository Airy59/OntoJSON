"""
Structural Transformation Rules

This module contains structural transformation rules for ontology-level constructs.
"""

from typing import Any, Dict, List, Optional
from ..visitor import TransformationRule
from ..model import OntologyModel, OntologyIndividual


class OntologyToDocumentRule(TransformationRule):
    """Transform the ontology structure to a JSON Schema document."""
    
    def visit_ontology(self, ontology: OntologyModel) -> Dict[str, Any]:
        """Transform the ontology to a JSON Schema document structure."""
        if not self.is_enabled():
            return None
        
        document = {}
        
        # Add schema version from configuration
        schema_format = self.get_option("schema_format", "json-schema-draft-07")
        document["$schema"] = self._get_schema_uri(schema_format)
        
        # Add ID from ontology URI
        if ontology.uri:
            document["$id"] = ontology.uri
        
        # Add title and description from ontology metadata
        if "title" in ontology.annotations:
            document["title"] = ontology.annotations["title"]
        elif ontology.uri:
            # Use the last part of the URI as title
            document["title"] = self._get_name_from_uri(ontology.uri)
        
        if "description" in ontology.annotations:
            document["description"] = ontology.annotations["description"]
        elif "comment" in ontology.annotations:
            document["description"] = ontology.annotations["comment"]
        
        # Handle imports
        if ontology.imports and self.get_option("include_imports", True):
            document["$comment"] = f"Imports: {', '.join(ontology.imports)}"
        
        return document
    
    def _get_schema_uri(self, schema_format: str) -> str:
        """Get the JSON Schema $schema URI for the specified format."""
        schema_uri_map = {
            "json-schema-draft-04": "http://json-schema.org/draft-04/schema#",
            "json-schema-draft-06": "http://json-schema.org/draft-06/schema#",
            "json-schema-draft-07": "http://json-schema.org/draft-07/schema#",
            "json-schema-2019-09": "https://json-schema.org/draft/2019-09/schema",
            "json-schema-2020-12": "https://json-schema.org/draft/2020-12/schema",
            # Also support short format names
            "draft-04": "http://json-schema.org/draft-04/schema#",
            "draft-06": "http://json-schema.org/draft-06/schema#",
            "draft-07": "http://json-schema.org/draft-07/schema#",
            "2019-09": "https://json-schema.org/draft/2019-09/schema",
            "2020-12": "https://json-schema.org/draft/2020-12/schema"
        }
        return schema_uri_map.get(schema_format, "http://json-schema.org/draft-07/schema#")
    
    def _get_name_from_uri(self, uri: str) -> str:
        """Extract a name from URI."""
        if '#' in uri:
            return uri.split('#')[0].split('/')[-1]
        elif '/' in uri:
            return uri.split('/')[-1]
        return uri


class IndividualsToExamplesRule(TransformationRule):
    """Transform OWL named individuals to JSON Schema examples."""
    
    def visit_ontology(self, ontology: OntologyModel) -> Dict[str, Any]:
        """Process all individuals in the ontology."""
        if not self.is_enabled():
            return None
        
        if not ontology.individuals:
            return None
        
        examples = []
        include_type = self.get_option("include_type", True)
        
        for individual in ontology.individuals:
            example = self._transform_individual(individual, include_type)
            if example:
                examples.append(example)
        
        if examples:
            return {"examples": examples}
        
        return None
    
    def visit_individual(self, individual: OntologyIndividual) -> Dict[str, Any]:
        """Transform a single individual to an example."""
        if not self.is_enabled():
            return None
        
        include_type = self.get_option("include_type", True)
        return self._transform_individual(individual, include_type)
    
    def _transform_individual(self, individual: OntologyIndividual, include_type: bool) -> Dict[str, Any]:
        """Transform an individual to an example object."""
        example = {}
        
        # Add type information if requested
        if include_type and individual.types:
            if len(individual.types) == 1:
                example["@type"] = self._get_class_name(individual.types[0])
            else:
                example["@type"] = [self._get_class_name(t) for t in individual.types]
        
        # Add label if available
        if individual.label:
            example["label"] = individual.label
        
        # Add properties
        for prop_uri, value in individual.properties.items():
            prop_name = self._get_property_name(prop_uri)
            example[prop_name] = value
        
        # Add URI as @id if configured
        if self.get_option("include_id", False):
            example["@id"] = individual.uri
        
        return example if example else None
    
    def _get_class_name(self, uri: str) -> str:
        """Extract class name from URI."""
        if '#' in uri:
            return uri.split('#')[-1]
        elif '/' in uri:
            return uri.split('/')[-1]
        return uri
    
    def _get_property_name(self, uri: str) -> str:
        """Extract property name from URI."""
        if '#' in uri:
            return uri.split('#')[-1]
        elif '/' in uri:
            return uri.split('/')[-1]
        return uri


class OntologyMetadataRule(TransformationRule):
    """Transform ontology metadata to JSON Schema metadata."""
    
    def _serialize_value(self, value: Any) -> Any:
        """Convert values to JSON-serializable format."""
        from datetime import datetime, date
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        elif isinstance(value, dict):
            return {k: self._serialize_value(v) for k, v in value.items()}
        elif isinstance(value, (list, tuple)):
            return [self._serialize_value(v) for v in value]
        else:
            return str(value) if value is not None else None
    
    def visit_ontology(self, ontology: OntologyModel) -> Dict[str, Any]:
        """Extract and transform ontology metadata."""
        if not self.is_enabled():
            return None
        
        metadata = {}
        result = {}
        
        # Title information (from composite metadata)
        if "label" in ontology.annotations:
            result["title"] = ontology.annotations["label"]
        elif "dc:title" in ontology.annotations:
            result["title"] = ontology.annotations["dc:title"]
        elif "title" in ontology.annotations:
            result["title"] = ontology.annotations["title"]
        
        # Description information (from composite metadata)
        if "comment" in ontology.annotations:
            result["description"] = ontology.annotations["comment"]
        elif "dc:description" in ontology.annotations:
            result["description"] = ontology.annotations["dc:description"]
        elif "description" in ontology.annotations:
            result["description"] = ontology.annotations["description"]
        
        # Version information
        if "versionInfo" in ontology.annotations:
            metadata["version"] = ontology.annotations["versionInfo"]
        elif "version" in ontology.annotations:
            metadata["version"] = ontology.annotations["version"]
        
        # Creator/Author information (from composite metadata)
        if "creator" in ontology.annotations:
            metadata["author"] = ontology.annotations["creator"]
        elif "dc:creator" in ontology.annotations:
            metadata["author"] = ontology.annotations["dc:creator"]
        elif "author" in ontology.annotations:
            metadata["author"] = ontology.annotations["author"]
        
        # License information
        if "license" in ontology.annotations:
            metadata["license"] = ontology.annotations["license"]
        elif "dc:rights" in ontology.annotations:
            metadata["license"] = ontology.annotations["dc:rights"]
        elif "dcterms:license" in ontology.annotations:
            metadata["license"] = ontology.annotations["dcterms:license"]
        
        # Creation date (from composite metadata)
        if "created" in ontology.annotations:
            metadata["created"] = self._serialize_value(ontology.annotations["created"])
        elif "dc:date" in ontology.annotations:
            metadata["created"] = self._serialize_value(ontology.annotations["dc:date"])
        elif "dcterms:created" in ontology.annotations:
            metadata["created"] = self._serialize_value(ontology.annotations["dcterms:created"])
        
        # Modified date (from composite metadata)
        if "modified" in ontology.annotations:
            metadata["modified"] = self._serialize_value(ontology.annotations["modified"])
        elif "dc:modified" in ontology.annotations:
            metadata["modified"] = self._serialize_value(ontology.annotations["dc:modified"])
        elif "dcterms:modified" in ontology.annotations:
            metadata["modified"] = self._serialize_value(ontology.annotations["dcterms:modified"])
        
        # Contributors
        if "contributor" in ontology.annotations:
            metadata["contributors"] = ontology.annotations["contributor"]
        elif "dc:contributor" in ontology.annotations:
            metadata["contributors"] = ontology.annotations["dc:contributor"]
        
        # Source
        if "source" in ontology.annotations:
            metadata["source"] = ontology.annotations["source"]
        elif "dc:source" in ontology.annotations:
            metadata["source"] = ontology.annotations["dc:source"]
        
        # Composite-specific metadata (from CompositeOntologyBuilder)
        if "composite:note" in ontology.annotations:
            metadata["compositeNote"] = ontology.annotations["composite:note"]
        
        # Check for composite source annotation
        if "compositeSource" in ontology.annotations:
            metadata["compositeSource"] = ontology.annotations["compositeSource"]
        
        # Add namespace information if requested
        if self.get_option("include_namespaces", False):
            # This would need to be passed from the parser
            # For now, we'll just add a placeholder
            metadata["namespaces"] = {
                "$comment": "Namespace information would be included here"
            }
        
        # Add other annotations if configured
        if self.get_option("include_all_annotations", False):
            for key, value in ontology.annotations.items():
                if key not in ["versionInfo", "creator", "dc:creator", "license",
                              "dc:rights", "created", "dc:date", "modified",
                              "dc:modified", "contributor", "dc:contributor",
                              "source", "dc:source", "title", "description", "comment",
                              "label", "dc:title", "dc:description", "dcterms:created",
                              "dcterms:modified", "dcterms:license", "composite:note",
                              "compositeSource", "version", "author"]:
                    # Use a custom prefix for other annotations
                    metadata[f"owl:{key}"] = value
        
        # Add metadata to result based on placement preference
        if metadata:
            # Decide where to put the metadata
            placement = self.get_option("placement", "comment")
            
            if placement == "root":
                # Add metadata fields directly to root schema
                # But preserve them in a special $metadata field for full preservation
                if metadata:
                    result["$metadata"] = metadata
                # Also add key fields directly for JSON Schema validators
                if "version" in metadata:
                    result["$schema-version"] = metadata["version"]
                if "author" in metadata:
                    result["$schema-author"] = metadata["author"]
                if "created" in metadata:
                    result["$schema-created"] = metadata["created"]
                if "modified" in metadata:
                    result["$schema-modified"] = metadata["modified"]
                if "license" in metadata:
                    result["$schema-license"] = metadata["license"]
            elif placement == "x-metadata":
                # Use x-metadata (Draft 7 allows custom properties starting with x-)
                result["x-metadata"] = metadata
            elif placement == "info":
                # Group under an "info" field (similar to OpenAPI)
                result["info"] = metadata
            elif placement == "comment":
                # Add as a comment (fully Draft 7 compliant)
                import json
                result["$comment"] = f"Metadata: {json.dumps(metadata)}"
            elif placement == "defs":
                # Store in $defs as a special definition (Draft 7 compliant)
                result["$defs"] = {
                    "_metadata": metadata
                }
            elif placement == "none":
                # Don't include metadata at all
                pass
            else:
                # Default: use x-metadata for Draft 7 compatibility
                result["x-metadata"] = metadata
        
        return result if result else None


class ThingWithUriRule(TransformationRule):
    """Add a base '_Thing' object with URI property that all classes inherit from."""
    
    def visit_ontology(self, ontology: OntologyModel) -> Dict[str, Any]:
        """Create the base _Thing object if enabled."""
        if not self.is_enabled():
            return None
        
        # Create the base _Thing object with URI property
        thing_object = {
            "type": "object",
            "properties": {
                "uri": {
                    "type": "string",
                    "format": "uri",
                    "description": "The URI identifier for this instance"
                }
            },
            "required": self.get_option("uri_required", [])  # URI can be optional or required
        }
        
        # Add additional metadata if configured
        if self.get_option("include_description", True):
            thing_object["description"] = "Base object that all classes inherit from"
        
        if self.get_option("include_title", True):
            thing_object["title"] = "_Thing"
        
        # Return the _Thing definition to be added to the schema
        return {
            "definitions": {
                "_Thing": thing_object
            }
        }
    
    def should_apply_to_class(self, class_schema: Dict[str, Any]) -> bool:
        """Check if a class should inherit from _Thing."""
        if not self.is_enabled():
            return False
        
        # Don't apply to _Thing itself
        if class_schema.get("title") == "_Thing":
            return False
        
        # Check if we should skip certain classes
        skip_patterns = self.get_option("skip_patterns", [])
        class_title = class_schema.get("title", "")
        
        for pattern in skip_patterns:
            if pattern in class_title:
                return False
        
        return True
    
    def apply_inheritance(self, class_schema: Dict[str, Any]) -> Dict[str, Any]:
        """Apply _Thing inheritance to a class schema."""
        if not self.should_apply_to_class(class_schema):
            return class_schema
        
        # Check if the class already has an allOf (from ClassHierarchyRule)
        if "allOf" in class_schema:
            # The class already has inheritance, we need to add _Thing to the chain
            # Check if _Thing is already in the inheritance chain
            thing_ref = {"$ref": "#/definitions/_Thing"}
            if thing_ref not in class_schema["allOf"]:
                # Insert _Thing at the beginning of the inheritance chain
                class_schema["allOf"].insert(0, thing_ref)
            return class_schema
        else:
            # No existing inheritance, create a new schema with allOf inheritance
            inherited_schema = {
                "allOf": [
                    {"$ref": "#/definitions/_Thing"},
                    class_schema
                ]
            }
            
            # Preserve title and description at the top level if they exist
            if "title" in class_schema:
                inherited_schema["title"] = class_schema["title"]
                # Remove from the inner schema to avoid duplication
                class_schema = {k: v for k, v in class_schema.items() if k != "title"}
                inherited_schema["allOf"][1] = class_schema
            
            if "description" in class_schema:
                inherited_schema["description"] = class_schema["description"]
                # Remove from the inner schema to avoid duplication
                class_schema = {k: v for k, v in class_schema.items() if k != "description"}
                inherited_schema["allOf"][1] = class_schema
            
            return inherited_schema
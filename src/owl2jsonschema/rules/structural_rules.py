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
        
        # Add schema version
        document["$schema"] = "http://json-schema.org/draft-07/schema#"
        
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
    
    def visit_ontology(self, ontology: OntologyModel) -> Dict[str, Any]:
        """Extract and transform ontology metadata."""
        if not self.is_enabled():
            return None
        
        metadata = {}
        
        # Version information
        if "versionInfo" in ontology.annotations:
            metadata["version"] = ontology.annotations["versionInfo"]
        
        # Creator information
        if "creator" in ontology.annotations:
            metadata["author"] = ontology.annotations["creator"]
        elif "dc:creator" in ontology.annotations:
            metadata["author"] = ontology.annotations["dc:creator"]
        
        # License information
        if "license" in ontology.annotations:
            metadata["license"] = ontology.annotations["license"]
        elif "dc:rights" in ontology.annotations:
            metadata["license"] = ontology.annotations["dc:rights"]
        
        # Creation date
        if "created" in ontology.annotations:
            metadata["created"] = ontology.annotations["created"]
        elif "dc:date" in ontology.annotations:
            metadata["created"] = ontology.annotations["dc:date"]
        
        # Modified date
        if "modified" in ontology.annotations:
            metadata["modified"] = ontology.annotations["modified"]
        elif "dc:modified" in ontology.annotations:
            metadata["modified"] = ontology.annotations["dc:modified"]
        
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
                              "source", "dc:source", "title", "description", "comment"]:
                    # Use a custom prefix for other annotations
                    metadata[f"owl:{key}"] = value
        
        if metadata:
            # Decide where to put the metadata
            placement = self.get_option("placement", "root")
            
            if placement == "root":
                # Add directly to root schema
                return metadata
            elif placement == "info":
                # Group under an "info" field (similar to OpenAPI)
                return {"info": metadata}
            elif placement == "comment":
                # Add as a comment
                import json
                return {"$comment": f"Metadata: {json.dumps(metadata)}"}
            else:
                return metadata
        
        return None
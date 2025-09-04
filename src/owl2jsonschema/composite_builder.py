"""
Composite Ontology Builder

This module creates a composite ontology that imports multiple source ontologies,
allowing them to be processed together as a unified schema.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
from rdflib import Graph, Namespace, URIRef, Literal
from rdflib.namespace import RDF, RDFS, OWL, DC, DCTERMS, XSD
import tempfile
import uuid


class CompositeOntologyBuilder:
    """Builder for creating composite ontologies that import multiple source ontologies."""
    
    def __init__(self, base_uri: Optional[str] = None):
        """
        Initialize the composite ontology builder.
        
        Args:
            base_uri: Base URI for the composite ontology. If None, a UUID-based URI will be generated.
        """
        if base_uri is None:
            # Generate a unique base URI using UUID
            unique_id = uuid.uuid4().hex[:8]
            self.base_uri = f"https://example.org/composite-ontology-{unique_id}#"
        else:
            self.base_uri = base_uri
            if not self.base_uri.endswith('#') and not self.base_uri.endswith('/'):
                self.base_uri += '#'
        
        self.graph = Graph()
        self.ontology_uri = URIRef(self.base_uri[:-1])  # Remove trailing # or /
        
        # Bind common prefixes
        self.graph.bind("owl", OWL)
        self.graph.bind("rdf", RDF)
        self.graph.bind("rdfs", RDFS)
        self.graph.bind("dc", DC)
        self.graph.bind("dcterms", DCTERMS)
        self.graph.bind("xsd", XSD)
        
        # Declare the ontology
        self.graph.add((self.ontology_uri, RDF.type, OWL.Ontology))
    
    def add_metadata(self, metadata: Dict[str, Any]) -> None:
        """
        Add metadata to the composite ontology.
        
        Args:
            metadata: Dictionary containing metadata fields like:
                - title: Ontology title
                - description: Ontology description
                - version: Version string
                - author: Author name
                - created: Creation date (will use current date if not provided)
                - comment: Additional comments
                - license: License information
        """
        # Title
        if "title" in metadata:
            self.graph.add((self.ontology_uri, RDFS.label, Literal(metadata["title"], lang="en")))
            self.graph.add((self.ontology_uri, DC.title, Literal(metadata["title"])))
        
        # Description
        if "description" in metadata:
            self.graph.add((self.ontology_uri, RDFS.comment, Literal(metadata["description"], lang="en")))
            self.graph.add((self.ontology_uri, DC.description, Literal(metadata["description"])))
        
        # Version
        if "version" in metadata:
            self.graph.add((self.ontology_uri, OWL.versionInfo, Literal(metadata["version"])))
        
        # Author/Creator
        if "author" in metadata:
            self.graph.add((self.ontology_uri, DC.creator, Literal(metadata["author"])))
        
        # Creation date
        if "created" in metadata:
            created_date = metadata["created"]
        else:
            created_date = datetime.now().isoformat()
        self.graph.add((self.ontology_uri, DCTERMS.created, Literal(created_date, datatype=XSD.dateTime)))
        
        # Additional comment
        if "comment" in metadata:
            # Use a custom annotation for additional comments to avoid conflict with description
            COMPOSITE_NS = Namespace(self.base_uri)
            self.graph.bind("composite", COMPOSITE_NS)
            self.graph.add((self.ontology_uri, COMPOSITE_NS.note, Literal(metadata["comment"])))
        
        # License
        if "license" in metadata:
            self.graph.add((self.ontology_uri, DCTERMS.license, Literal(metadata["license"])))
        
        # Modified date (always set to now when building)
        self.graph.add((self.ontology_uri, DCTERMS.modified, 
                       Literal(datetime.now().isoformat(), datatype=XSD.dateTime)))
    
    def add_imports(self, ontology_paths: List[str]) -> None:
        """
        Add import statements for the specified ontology files.
        
        Args:
            ontology_paths: List of file paths or URLs to import
        """
        for path in ontology_paths:
            # Convert file paths to file:// URIs for proper importing
            if not path.startswith(('http://', 'https://', 'file://')):
                # This is a local file path
                abs_path = Path(path).resolve()
                import_uri = abs_path.as_uri()
            else:
                # Already a URI
                import_uri = path
            
            # Add the import statement
            self.graph.add((self.ontology_uri, OWL.imports, URIRef(import_uri)))
    
    def add_custom_annotation(self, predicate: str, value: str) -> None:
        """
        Add a custom annotation to the ontology.
        
        Args:
            predicate: The annotation property URI or local name
            value: The annotation value
        """
        # If predicate doesn't look like a URI, make it one using the base URI
        if not predicate.startswith(('http://', 'https://')):
            predicate = self.base_uri + predicate
        
        self.graph.add((self.ontology_uri, URIRef(predicate), Literal(value)))
    
    def serialize(self, format: str = "turtle") -> str:
        """
        Serialize the composite ontology to a string.
        
        Args:
            format: RDF serialization format (turtle, xml, n3, etc.)
        
        Returns:
            Serialized ontology as string
        """
        return self.graph.serialize(format=format)
    
    def save_to_file(self, file_path: str, format: Optional[str] = None) -> None:
        """
        Save the composite ontology to a file.
        
        Args:
            file_path: Path where to save the ontology
            format: RDF format. If None, will be guessed from extension.
        """
        if format is None:
            # Guess format from extension
            ext = Path(file_path).suffix.lower()
            format_map = {
                '.ttl': 'turtle',
                '.rdf': 'xml',
                '.owl': 'xml',
                '.n3': 'n3',
                '.nt': 'nt',
                '.jsonld': 'json-ld'
            }
            format = format_map.get(ext, 'turtle')
        
        serialized = self.serialize(format=format)
        
        # Write to file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(serialized)
    
    def save_to_temp_file(self, format: str = "turtle") -> str:
        """
        Save the composite ontology to a temporary file.
        
        Args:
            format: RDF serialization format
        
        Returns:
            Path to the temporary file
        """
        # Determine file extension
        ext_map = {
            'turtle': '.ttl',
            'xml': '.rdf',
            'n3': '.n3',
            'nt': '.nt',
            'json-ld': '.jsonld'
        }
        ext = ext_map.get(format, '.ttl')
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix=ext, delete=False, encoding='utf-8') as f:
            f.write(self.serialize(format=format))
            return f.name
    
    @classmethod
    def create_composite(cls, 
                        ontology_paths: List[str],
                        metadata: Optional[Dict[str, Any]] = None,
                        base_uri: Optional[str] = None) -> 'CompositeOntologyBuilder':
        """
        Convenience method to create a composite ontology in one step.
        
        Args:
            ontology_paths: List of ontology files to import
            metadata: Optional metadata for the composite ontology
            base_uri: Optional base URI for the composite ontology
        
        Returns:
            Configured CompositeOntologyBuilder instance
        """
        builder = cls(base_uri)
        
        # Add default metadata if not provided
        if metadata is None:
            metadata = {}
        
        # Set default title if not provided
        if "title" not in metadata:
            if len(ontology_paths) == 1:
                metadata["title"] = f"Composite wrapper for {Path(ontology_paths[0]).name}"
            else:
                metadata["title"] = f"Composite ontology importing {len(ontology_paths)} sources"
        
        # Set default description if not provided
        if "description" not in metadata:
            onto_names = [Path(p).name for p in ontology_paths]
            metadata["description"] = f"Composite ontology that imports: {', '.join(onto_names)}"
        
        # Add metadata
        builder.add_metadata(metadata)
        
        # Add imports
        builder.add_imports(ontology_paths)
        
        # Add a note about the composite nature
        builder.add_custom_annotation(
            "compositeSource",
            f"Generated composite of {len(ontology_paths)} ontologies"
        )
        
        return builder
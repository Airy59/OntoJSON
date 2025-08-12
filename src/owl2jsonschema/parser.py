"""
Ontology Parser

This module implements the parser for loading OWL/RDF ontologies into the object model.
"""

from typing import Optional, Dict, Any, List
from rdflib import Graph, Namespace, URIRef, Literal, BNode
from rdflib.namespace import RDF, RDFS, OWL, XSD
import ssl
import urllib.request
from .model import (
    OntologyModel,
    OntologyClass,
    ObjectProperty,
    DatatypeProperty,
    OntologyIndividual,
    OntologyRestriction,
    CardinalityRestriction,
    ValueRestriction
)


class OntologyParser:
    """Parser for OWL/RDF ontologies."""
    
    def __init__(self):
        """Initialize the parser."""
        self.graph = Graph()
        self.ontology = None
        self.namespaces = {}
        
    def parse(self, file_path: str, format: Optional[str] = None) -> OntologyModel:
        """
        Parse an ontology file.
        
        Args:
            file_path: Path to the ontology file
            format: RDF format (e.g., 'xml', 'turtle', 'n3'). If None, will be guessed.
        
        Returns:
            The parsed ontology model
        """
        # Configure SSL for rdflib (for JSON-LD context fetching)
        self._configure_ssl_for_rdflib()
        
        # Parse the file into an RDF graph
        self.graph = Graph()
        
        # If format not specified, try to detect it
        if format is None:
            format = self._detect_format(file_path)
        
        try:
            self.graph.parse(file_path, format=format)
        except Exception as e:
            # If parsing fails and format was auto-detected, try alternative formats
            if format == 'xml':
                # The file might be Turtle despite .owl extension
                try:
                    self.graph = Graph()  # Reset graph
                    self.graph.parse(file_path, format='turtle')
                except:
                    # If Turtle also fails, re-raise original error
                    raise e
            else:
                raise e
        
        # Extract namespace information
        self._extract_namespaces()
        
        # Get the ontology URI
        ontology_uri = self._get_ontology_uri()
        
        # Create the ontology model
        self.ontology = OntologyModel(uri=ontology_uri)
        
        # Parse ontology components
        self._parse_classes()
        self._parse_object_properties()
        self._parse_datatype_properties()
        self._parse_individuals()
        self._parse_ontology_metadata()
        
        return self.ontology
    
    def parse_string(self, data: str, format: str = 'xml') -> OntologyModel:
        """
        Parse an ontology from a string.
        
        Args:
            data: The ontology data as a string
            format: RDF format (e.g., 'xml', 'turtle', 'n3')
        
        Returns:
            The parsed ontology model
        """
        # Configure SSL for rdflib (for JSON-LD context fetching)
        self._configure_ssl_for_rdflib()
        
        # Parse the string into an RDF graph
        self.graph = Graph()
        self.graph.parse(data=data, format=format)
        
        # Extract namespace information
        self._extract_namespaces()
        
        # Get the ontology URI
        ontology_uri = self._get_ontology_uri()
        
        # Create the ontology model
        self.ontology = OntologyModel(uri=ontology_uri)
        
        # Parse ontology components
        self._parse_classes()
        self._parse_object_properties()
        self._parse_datatype_properties()
        self._parse_individuals()
        self._parse_ontology_metadata()
        
        return self.ontology
    
    def _extract_namespaces(self):
        """Extract namespace information from the graph."""
        self.namespaces = dict(self.graph.namespaces())
    
    def _get_ontology_uri(self) -> str:
        """Get the ontology URI."""
        # Look for owl:Ontology declarations
        for s in self.graph.subjects(RDF.type, OWL.Ontology):
            return str(s)
        
        # If no explicit ontology declaration, use the base namespace
        for prefix, namespace in self.namespaces.items():
            if prefix == '':
                return str(namespace)
        
        return ""
    
    def _parse_classes(self):
        """Parse OWL classes from the graph."""
        for class_uri in self.graph.subjects(RDF.type, OWL.Class):
            # Skip blank nodes for now
            if isinstance(class_uri, BNode):
                continue
            
            owl_class = OntologyClass(uri=str(class_uri))
            
            # Get labels
            labels = self._get_labels(class_uri)
            if labels:
                owl_class.label = labels
            
            # Get comments
            comments = self._get_comments(class_uri)
            if comments:
                owl_class.comment = comments
            
            # Get super classes and check for enumerations
            for super_class in self.graph.objects(class_uri, RDFS.subClassOf):
                if isinstance(super_class, URIRef):
                    owl_class.super_classes.append(str(super_class))
                elif isinstance(super_class, BNode):
                    # Check if this is an enumeration (oneOf)
                    enum_values = self._parse_enumeration(super_class)
                    if enum_values:
                        # Store enumeration values in annotations for the EnumerationToEnumRule
                        owl_class.annotations["enumeration"] = enum_values
            
            # Get equivalent classes
            for equiv_class in self.graph.objects(class_uri, OWL.equivalentClass):
                if isinstance(equiv_class, URIRef):
                    owl_class.equivalent_classes.append(str(equiv_class))
            
            # Get disjoint classes
            for disjoint_class in self.graph.objects(class_uri, OWL.disjointWith):
                if isinstance(disjoint_class, URIRef):
                    owl_class.disjoint_with.append(str(disjoint_class))
            
            # Parse restrictions
            self._parse_class_restrictions(class_uri, owl_class)
            
            # Get other annotations
            annotations = self._get_annotations(class_uri)
            owl_class.annotations.update(annotations)
            
            self.ontology.classes.append(owl_class)
    
    def _parse_object_properties(self):
        """Parse OWL object properties from the graph."""
        for prop_uri in self.graph.subjects(RDF.type, OWL.ObjectProperty):
            if isinstance(prop_uri, BNode):
                continue
            
            obj_prop = ObjectProperty(uri=str(prop_uri))
            
            # Get labels and comments
            labels = self._get_labels(prop_uri)
            if labels:
                obj_prop.label = labels
            
            comments = self._get_comments(prop_uri)
            if comments:
                obj_prop.comment = comments
            
            # Get domain
            for domain in self.graph.objects(prop_uri, RDFS.domain):
                if isinstance(domain, URIRef):
                    obj_prop.domain.append(str(domain))
            
            # Get range
            for range_class in self.graph.objects(prop_uri, RDFS.range):
                if isinstance(range_class, URIRef):
                    obj_prop.range.append(str(range_class))
            
            # Get super properties
            for super_prop in self.graph.objects(prop_uri, RDFS.subPropertyOf):
                if isinstance(super_prop, URIRef):
                    obj_prop.super_properties.append(str(super_prop))
            
            # Check characteristics
            if (prop_uri, RDF.type, OWL.FunctionalProperty) in self.graph:
                obj_prop.functional = True
            
            if (prop_uri, RDF.type, OWL.InverseFunctionalProperty) in self.graph:
                obj_prop.inverse_functional = True
            
            if (prop_uri, RDF.type, OWL.TransitiveProperty) in self.graph:
                obj_prop.transitive = True
            
            if (prop_uri, RDF.type, OWL.SymmetricProperty) in self.graph:
                obj_prop.symmetric = True
            
            if (prop_uri, RDF.type, OWL.AsymmetricProperty) in self.graph:
                obj_prop.asymmetric = True
            
            if (prop_uri, RDF.type, OWL.IrreflexiveProperty) in self.graph:
                obj_prop.irreflexive = True
            
            if (prop_uri, RDF.type, OWL.ReflexiveProperty) in self.graph:
                obj_prop.reflexive = True
            
            # Get inverse property
            for inverse in self.graph.objects(prop_uri, OWL.inverseOf):
                if isinstance(inverse, URIRef):
                    obj_prop.inverse_of = str(inverse)
                    break
            
            # Get annotations
            obj_prop.annotations = self._get_annotations(prop_uri)
            
            self.ontology.object_properties.append(obj_prop)
        
        # Post-process to ensure bidirectional inverse relationships
        self._ensure_bidirectional_inverses()
    
    def _ensure_bidirectional_inverses(self):
        """Ensure that inverse relationships are bidirectional."""
        # Create a map of property URIs to properties for quick lookup
        prop_map = {prop.uri: prop for prop in self.ontology.object_properties}
        
        # For each property with an inverse, ensure the inverse also points back
        for prop in self.ontology.object_properties:
            if prop.inverse_of:
                inverse_prop = prop_map.get(prop.inverse_of)
                if inverse_prop and not inverse_prop.inverse_of:
                    inverse_prop.inverse_of = prop.uri
    
    def _parse_datatype_properties(self):
        """Parse OWL datatype properties from the graph."""
        for prop_uri in self.graph.subjects(RDF.type, OWL.DatatypeProperty):
            if isinstance(prop_uri, BNode):
                continue
            
            dt_prop = DatatypeProperty(uri=str(prop_uri))
            
            # Get labels and comments
            labels = self._get_labels(prop_uri)
            if labels:
                dt_prop.label = labels
            
            comments = self._get_comments(prop_uri)
            if comments:
                dt_prop.comment = comments
            
            # Get domain
            for domain in self.graph.objects(prop_uri, RDFS.domain):
                if isinstance(domain, URIRef):
                    dt_prop.domain.append(str(domain))
            
            # Get range
            for range_type in self.graph.objects(prop_uri, RDFS.range):
                if isinstance(range_type, URIRef):
                    dt_prop.range.append(str(range_type))
            
            # Get super properties
            for super_prop in self.graph.objects(prop_uri, RDFS.subPropertyOf):
                if isinstance(super_prop, URIRef):
                    dt_prop.super_properties.append(str(super_prop))
            
            # Check if functional
            if (prop_uri, RDF.type, OWL.FunctionalProperty) in self.graph:
                dt_prop.functional = True
            
            # Get annotations
            dt_prop.annotations = self._get_annotations(prop_uri)
            
            self.ontology.datatype_properties.append(dt_prop)
    
    def _parse_individuals(self):
        """Parse named individuals from the graph."""
        for ind_uri in self.graph.subjects(RDF.type, OWL.NamedIndividual):
            if isinstance(ind_uri, BNode):
                continue
            
            individual = OntologyIndividual(uri=str(ind_uri))
            
            # Get labels
            labels = self._get_labels(ind_uri)
            if labels:
                individual.label = labels
            
            # Get types
            for type_class in self.graph.objects(ind_uri, RDF.type):
                if isinstance(type_class, URIRef) and type_class != OWL.NamedIndividual:
                    individual.types.append(str(type_class))
            
            # Get property values
            for predicate, obj in self.graph.predicate_objects(ind_uri):
                if predicate not in [RDF.type, RDFS.label, RDFS.comment]:
                    prop_name = str(predicate)
                    if isinstance(obj, Literal):
                        individual.properties[prop_name] = obj.value
                    else:
                        individual.properties[prop_name] = str(obj)
            
            # Get annotations
            individual.annotations = self._get_annotations(ind_uri)
            
            self.ontology.individuals.append(individual)
    
    def _parse_class_restrictions(self, class_uri: URIRef, owl_class: OntologyClass):
        """Parse restrictions for a class."""
        # Look for restrictions in subClassOf statements
        for super_class in self.graph.objects(class_uri, RDFS.subClassOf):
            if isinstance(super_class, BNode):
                # This might be a restriction
                if (super_class, RDF.type, OWL.Restriction) in self.graph:
                    restriction = self._parse_restriction(super_class)
                    if restriction:
                        owl_class.restrictions.append(restriction)
                # Check if this is an intersection containing restrictions
                elif (super_class, OWL.intersectionOf, None) in self.graph:
                    # Parse restrictions from the intersection
                    for intersection_list in self.graph.objects(super_class, OWL.intersectionOf):
                        self._parse_intersection_restrictions(intersection_list, owl_class)
    
    def _parse_intersection_restrictions(self, intersection_list, owl_class: OntologyClass):
        """Parse restrictions from an intersection list."""
        # Traverse the RDF list
        current = intersection_list
        while current and current != RDF.nil:
            # Get the first element
            for first in self.graph.objects(current, RDF.first):
                if isinstance(first, BNode):
                    # Check if this is a restriction
                    if (first, RDF.type, OWL.Restriction) in self.graph:
                        restriction = self._parse_restriction(first)
                        if restriction:
                            owl_class.restrictions.append(restriction)
                break
            
            # Move to the rest of the list
            next_node = None
            for rest in self.graph.objects(current, RDF.rest):
                next_node = rest
                break
            current = next_node
    
    def _parse_restriction(self, restriction_node: BNode) -> Optional[OntologyRestriction]:
        """Parse a restriction node."""
        # Get the property being restricted
        prop_uri = None
        for prop in self.graph.objects(restriction_node, OWL.onProperty):
            prop_uri = str(prop)
            break
        
        if not prop_uri:
            return None
        
        # Check for cardinality restrictions
        for pred, obj in self.graph.predicate_objects(restriction_node):
            if pred == OWL.minCardinality:
                return CardinalityRestriction(
                    property_uri=prop_uri,
                    restriction_type="cardinality",
                    value=obj.value,
                    min_cardinality=obj.value
                )
            elif pred == OWL.maxCardinality:
                return CardinalityRestriction(
                    property_uri=prop_uri,
                    restriction_type="cardinality",
                    value=obj.value,
                    max_cardinality=obj.value
                )
            elif pred == OWL.cardinality:
                return CardinalityRestriction(
                    property_uri=prop_uri,
                    restriction_type="cardinality",
                    value=obj.value,
                    exact_cardinality=obj.value
                )
            # Handle qualified cardinality restrictions
            elif pred == OWL.minQualifiedCardinality:
                return CardinalityRestriction(
                    property_uri=prop_uri,
                    restriction_type="cardinality",
                    value=obj.value,
                    min_cardinality=obj.value
                )
            elif pred == OWL.maxQualifiedCardinality:
                return CardinalityRestriction(
                    property_uri=prop_uri,
                    restriction_type="cardinality",
                    value=obj.value,
                    max_cardinality=obj.value
                )
            elif pred == OWL.qualifiedCardinality:
                return CardinalityRestriction(
                    property_uri=prop_uri,
                    restriction_type="cardinality",
                    value=obj.value,
                    exact_cardinality=obj.value
                )
            elif pred == OWL.allValuesFrom:
                return ValueRestriction(
                    property_uri=prop_uri,
                    restriction_type="allValuesFrom",
                    value=str(obj),
                    filler=str(obj)
                )
            elif pred == OWL.someValuesFrom:
                return ValueRestriction(
                    property_uri=prop_uri,
                    restriction_type="someValuesFrom",
                    value=str(obj),
                    filler=str(obj)
                )
            elif pred == OWL.hasValue:
                return ValueRestriction(
                    property_uri=prop_uri,
                    restriction_type="hasValue",
                    value=str(obj) if isinstance(obj, URIRef) else obj.value,
                    filler=str(obj) if isinstance(obj, URIRef) else str(obj.datatype) if obj.datatype else "string"
                )
        
        return None
    
    def _parse_enumeration(self, node: BNode) -> Optional[List[str]]:
        """Parse an enumeration (oneOf) from a blank node."""
        # Check if this node has an owl:oneOf property
        for one_of in self.graph.objects(node, OWL.oneOf):
            # Parse the RDF list
            enum_values = []
            current = one_of
            while current and current != RDF.nil:
                # Get the first element
                for first in self.graph.objects(current, RDF.first):
                    if isinstance(first, URIRef):
                        # Extract the local name for the enum value
                        enum_values.append(self._get_enum_value(first))
                    break
                
                # Move to the rest of the list
                next_node = None
                for rest in self.graph.objects(current, RDF.rest):
                    next_node = rest
                    break
                current = next_node
            
            if enum_values:
                return enum_values
        
        return None
    
    def _get_enum_value(self, uri: URIRef) -> str:
        """Get the enum value from a URI."""
        # First try to get label
        labels = self._get_labels(uri)
        if labels:
            if isinstance(labels, str):
                return labels
            elif isinstance(labels, dict):
                # Prefer English label
                return labels.get("en", labels.get("default", self._get_local_name(str(uri))))
        
        # Fall back to the local name (without prefix)
        return self._get_local_name(str(uri))
    
    def _get_local_name(self, uri: str) -> str:
        """Get the local name from a URI without prefix."""
        if '#' in uri:
            return uri.split('#')[-1]
        elif '/' in uri:
            return uri.split('/')[-1]
        return uri
    
    def _parse_ontology_metadata(self):
        """Parse ontology-level metadata."""
        ontology_uri = URIRef(self.ontology.uri) if self.ontology.uri else None
        
        if not ontology_uri:
            return
        
        # Get version info
        for version in self.graph.objects(ontology_uri, OWL.versionInfo):
            self.ontology.annotations["versionInfo"] = str(version)
        
        # Get imports
        for imported in self.graph.objects(ontology_uri, OWL.imports):
            self.ontology.imports.append(str(imported))
        
        # Get other annotations
        annotations = self._get_annotations(ontology_uri)
        self.ontology.annotations.update(annotations)
    
    def _get_labels(self, subject: URIRef) -> Optional[Any]:
        """Get labels for a subject."""
        labels = {}
        for label in self.graph.objects(subject, RDFS.label):
            if isinstance(label, Literal):
                if label.language:
                    labels[label.language] = str(label)
                else:
                    labels["default"] = str(label)
        
        if len(labels) == 1 and "default" in labels:
            return labels["default"]
        elif labels:
            return labels
        
        return None
    
    def _get_comments(self, subject: URIRef) -> Optional[Any]:
        """Get comments for a subject."""
        comments = {}
        for comment in self.graph.objects(subject, RDFS.comment):
            if isinstance(comment, Literal):
                if comment.language:
                    comments[comment.language] = str(comment)
                else:
                    comments["default"] = str(comment)
        
        if len(comments) == 1 and "default" in comments:
            return comments["default"]
        elif comments:
            return comments
        
        return None
    
    def _get_annotations(self, subject: URIRef) -> Dict[str, Any]:
        """Get all annotations for a subject."""
        annotations = {}
        
        # Skip standard properties we handle elsewhere
        skip_predicates = {RDF.type, RDFS.label, RDFS.comment, RDFS.subClassOf,
                          RDFS.subPropertyOf, RDFS.domain, RDFS.range,
                          OWL.equivalentClass, OWL.disjointWith, OWL.onProperty,
                          OWL.allValuesFrom, OWL.someValuesFrom, OWL.hasValue,
                          OWL.minCardinality, OWL.maxCardinality, OWL.cardinality}
        
        for pred, obj in self.graph.predicate_objects(subject):
            if pred not in skip_predicates:
                pred_str = self._shorten_uri(str(pred))
                if isinstance(obj, Literal):
                    annotations[pred_str] = obj.value
                else:
                    annotations[pred_str] = str(obj)
        
        return annotations
    
    def _shorten_uri(self, uri: str) -> str:
        """Shorten a URI using known namespaces."""
        for prefix, namespace in self.namespaces.items():
            namespace_str = str(namespace)
            if uri.startswith(namespace_str):
                local_name = uri[len(namespace_str):]
                if prefix:
                    return f"{prefix}:{local_name}"
                else:
                    return local_name
        
        # If no namespace match, return the last part of the URI
        if '#' in uri:
            return uri.split('#')[-1]
        elif '/' in uri:
            return uri.split('/')[-1]
        
        return uri
    
    def _detect_format(self, file_path: str) -> Optional[str]:
        """
        Detect the RDF format from file extension or content.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Detected format string or None
        """
        import os
        
        # First try by extension
        ext = os.path.splitext(file_path)[1].lower()
        
        # Common extensions
        extension_map = {
            '.ttl': 'turtle',
            '.turtle': 'turtle',
            '.n3': 'n3',
            '.nt': 'nt',
            '.ntriples': 'nt',
            '.jsonld': 'json-ld',
            '.json': 'json-ld',
            '.rdf': 'xml',
            '.rdfs': 'xml',
            '.owl': 'xml',  # Default to XML for .owl, but we'll try Turtle if it fails
            '.xml': 'xml'
        }
        
        if ext in extension_map:
            return extension_map[ext]
        
        # If no extension match, try to detect from content
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                # Read first few lines
                content = f.read(1000).strip()
                
                # Check for common patterns
                if content.startswith('<?xml'):
                    return 'xml'
                elif content.startswith('{') or content.startswith('['):
                    return 'json-ld'
                elif '@prefix' in content or '@base' in content:
                    return 'turtle'
                elif content.startswith('<') and '>' in content and not content.startswith('<?xml'):
                    # Could be N-Triples or Turtle with URIs
                    if '.' in content.split('\n')[0]:
                        return 'nt'
                    else:
                        return 'turtle'
        except:
            pass
        
        # Default to None (let rdflib guess)
        return None
    
    def _configure_ssl_for_rdflib(self):
        """Configure SSL context for rdflib's URL fetching (especially for JSON-LD contexts)."""
        try:
            # Create a custom SSL context
            ssl_context = ssl.create_default_context()
            
            # Try to use certifi for certificates
            try:
                import certifi
                ssl_context.load_verify_locations(certifi.where())
            except ImportError:
                pass
            
            # Install a custom opener with the SSL context
            https_handler = urllib.request.HTTPSHandler(context=ssl_context)
            opener = urllib.request.build_opener(https_handler)
            urllib.request.install_opener(opener)
            
        except Exception:
            # If SSL configuration fails, try to create a more permissive context
            # This is less secure but may work for development
            try:
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
                
                https_handler = urllib.request.HTTPSHandler(context=ssl_context)
                opener = urllib.request.build_opener(https_handler)
                urllib.request.install_opener(opener)
            except Exception:
                # If all else fails, continue without custom SSL configuration
                pass
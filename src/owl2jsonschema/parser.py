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
        self.graph.parse(file_path, format=format)
        
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
            
            # Get super classes
            for super_class in self.graph.objects(class_uri, RDFS.subClassOf):
                if isinstance(super_class, URIRef):
                    owl_class.super_classes.append(str(super_class))
            
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
            owl_class.annotations = self._get_annotations(class_uri)
            
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
            
            # Get inverse property
            for inverse in self.graph.objects(prop_uri, OWL.inverseOf):
                if isinstance(inverse, URIRef):
                    obj_prop.inverse_of = str(inverse)
                    break
            
            # Get annotations
            obj_prop.annotations = self._get_annotations(prop_uri)
            
            self.ontology.object_properties.append(obj_prop)
    
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
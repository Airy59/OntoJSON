"""
OWL Graph Builder for JSON Schema to OWL Transformation

This module builds RDF graphs representing OWL ontologies using RDFLib.
"""

from typing import Dict, Any, Optional, List, Union
from rdflib import Graph, Namespace, URIRef, Literal, BNode
from rdflib.namespace import RDF, RDFS, OWL, XSD
from .uri_generator import URIGenerator


class OWLBuilder:
    """Build RDF graph representing an OWL ontology."""
    
    def __init__(self, uri_generator: URIGenerator, ontology_uri: Optional[str] = None):
        """
        Initialize the OWL builder.
        
        Args:
            uri_generator: URI generator instance
            ontology_uri: Optional ontology URI
        """
        self.uri_generator = uri_generator
        self.graph = Graph()
        
        # Bind standard namespaces
        self.graph.bind("owl", OWL)
        self.graph.bind("rdf", RDF)
        self.graph.bind("rdfs", RDFS)
        self.graph.bind("xsd", XSD)
        
        # Create base namespace using the namespace with schema name
        # This will be something like "https://cdm.ovh/examples/offlineOSDM#"
        namespace_with_schema = uri_generator.get_namespace_with_schema()
        self.base_namespace = Namespace(namespace_with_schema)
        self.graph.bind("", self.base_namespace)
        
        # Create ontology node
        self.ontology_uri = ontology_uri or uri_generator.generate_ontology_uri()
        self.ontology = URIRef(self.ontology_uri)
        self.graph.add((self.ontology, RDF.type, OWL.Ontology))
    
    def add_namespace(self, prefix: str, uri: str):
        """
        Add a namespace binding.
        
        Args:
            prefix: Namespace prefix
            uri: Namespace URI
        """
        self.graph.bind(prefix, Namespace(uri))
    
    def add_ontology_annotation(self, predicate: Union[URIRef, str], value: Union[str, URIRef]):
        """
        Add an annotation to the ontology.
        
        Args:
            predicate: Annotation property URI or string
            value: Annotation value
        """
        if isinstance(predicate, str):
            predicate = URIRef(predicate)
        
        if isinstance(value, str):
            value = Literal(value)
        elif not isinstance(value, (URIRef, Literal)):
            value = Literal(str(value))
        
        self.graph.add((self.ontology, predicate, value))
    
    def add_class(
        self,
        class_uri: str,
        label: Optional[str] = None,
        comment: Optional[str] = None,
        parent_classes: Optional[List[str]] = None,
        **metadata
    ) -> URIRef:
        """
        Add an OWL class to the graph.
        
        Args:
            class_uri: Class URI
            label: rdfs:label
            comment: rdfs:comment
            parent_classes: List of parent class URIs
            **metadata: Additional metadata
        
        Returns:
            URIRef of the created class
        """
        class_ref = URIRef(class_uri)
        
        # Add class declaration
        self.graph.add((class_ref, RDF.type, OWL.Class))
        
        # Add label
        if label:
            self.graph.add((class_ref, RDFS.label, Literal(label)))
        
        # Add comment
        if comment:
            self.graph.add((class_ref, RDFS.comment, Literal(comment)))
        
        # Add parent classes
        if parent_classes:
            for parent_uri in parent_classes:
                self.graph.add((class_ref, RDFS.subClassOf, URIRef(parent_uri)))
        
        # Add custom metadata
        for key, value in metadata.items():
            # Convert key to predicate URI
            pred = self._metadata_key_to_predicate(key)
            self.graph.add((class_ref, pred, Literal(value)))
        
        return class_ref
    
    def add_object_property(
        self,
        property_uri: str,
        domain: Optional[Union[str, List[str]]] = None,
        range_: Optional[Union[str, List[str]]] = None,
        label: Optional[str] = None,
        comment: Optional[str] = None,
        functional: bool = False,
        inverse_functional: bool = False,
        transitive: bool = False,
        symmetric: bool = False,
        **metadata
    ) -> URIRef:
        """
        Add an OWL object property to the graph.
        
        Args:
            property_uri: Property URI
            domain: Domain class URI(s)
            range_: Range class URI(s)
            label: rdfs:label
            comment: rdfs:comment
            functional: Is functional property
            inverse_functional: Is inverse functional
            transitive: Is transitive
            symmetric: Is symmetric
            **metadata: Additional metadata
        
        Returns:
            URIRef of the created property
        """
        prop_ref = URIRef(property_uri)
        
        # Add property declaration
        self.graph.add((prop_ref, RDF.type, OWL.ObjectProperty))
        
        # Add characteristics
        if functional:
            self.graph.add((prop_ref, RDF.type, OWL.FunctionalProperty))
        if inverse_functional:
            self.graph.add((prop_ref, RDF.type, OWL.InverseFunctionalProperty))
        if transitive:
            self.graph.add((prop_ref, RDF.type, OWL.TransitiveProperty))
        if symmetric:
            self.graph.add((prop_ref, RDF.type, OWL.SymmetricProperty))
        
        # Add domain
        if domain:
            domains = [domain] if isinstance(domain, str) else domain
            for d in domains:
                self.graph.add((prop_ref, RDFS.domain, URIRef(d)))
        
        # Add range
        if range_:
            ranges = [range_] if isinstance(range_, str) else range_
            for r in ranges:
                self.graph.add((prop_ref, RDFS.range, URIRef(r)))
        
        # Add label and comment
        if label:
            self.graph.add((prop_ref, RDFS.label, Literal(label)))
        if comment:
            self.graph.add((prop_ref, RDFS.comment, Literal(comment)))
        
        # Add custom metadata
        for key, value in metadata.items():
            pred = self._metadata_key_to_predicate(key)
            self.graph.add((prop_ref, pred, Literal(value)))
        
        return prop_ref
    
    def add_datatype_property(
        self,
        property_uri: str,
        domain: Optional[Union[str, List[str]]] = None,
        range_: Optional[str] = None,
        label: Optional[str] = None,
        comment: Optional[str] = None,
        functional: bool = False,
        **metadata
    ) -> URIRef:
        """
        Add an OWL datatype property to the graph.
        
        Args:
            property_uri: Property URI
            domain: Domain class URI(s)
            range_: XSD datatype URI
            label: rdfs:label
            comment: rdfs:comment
            functional: Is functional property
            **metadata: Additional metadata
        
        Returns:
            URIRef of the created property
        """
        prop_ref = URIRef(property_uri)
        
        # Add property declaration
        self.graph.add((prop_ref, RDF.type, OWL.DatatypeProperty))
        
        # Add functional characteristic
        if functional:
            self.graph.add((prop_ref, RDF.type, OWL.FunctionalProperty))
        
        # Add domain
        if domain:
            domains = [domain] if isinstance(domain, str) else domain
            for d in domains:
                self.graph.add((prop_ref, RDFS.domain, URIRef(d)))
        
        # Add range (XSD datatype)
        if range_:
            self.graph.add((prop_ref, RDFS.range, URIRef(range_)))
        
        # Add label and comment
        if label:
            self.graph.add((prop_ref, RDFS.label, Literal(label)))
        if comment:
            self.graph.add((prop_ref, RDFS.comment, Literal(comment)))
        
        # Add custom metadata
        for key, value in metadata.items():
            pred = self._metadata_key_to_predicate(key)
            self.graph.add((prop_ref, pred, Literal(value)))
        
        return prop_ref
    
    def add_cardinality_restriction(
        self,
        class_uri: str,
        property_uri: str,
        min_cardinality: Optional[int] = None,
        max_cardinality: Optional[int] = None,
        exact_cardinality: Optional[int] = None,
        on_class: Optional[str] = None
    ):
        """
        Add a cardinality restriction to a class.
        
        Args:
            class_uri: Class to add restriction to
            property_uri: Property the restriction applies to
            min_cardinality: Minimum cardinality
            max_cardinality: Maximum cardinality
            exact_cardinality: Exact cardinality
            on_class: Optional qualified cardinality on class
        """
        class_ref = URIRef(class_uri)
        prop_ref = URIRef(property_uri)
        
        # Create blank node for restriction
        restriction = BNode()
        self.graph.add((restriction, RDF.type, OWL.Restriction))
        self.graph.add((restriction, OWL.onProperty, prop_ref))
        
        # Add cardinality constraints
        if exact_cardinality is not None:
            if on_class:
                self.graph.add((restriction, OWL.qualifiedCardinality, Literal(exact_cardinality)))
                self.graph.add((restriction, OWL.onClass, URIRef(on_class)))
            else:
                self.graph.add((restriction, OWL.cardinality, Literal(exact_cardinality)))
        else:
            if min_cardinality is not None:
                if on_class:
                    self.graph.add((restriction, OWL.minQualifiedCardinality, Literal(min_cardinality)))
                    self.graph.add((restriction, OWL.onClass, URIRef(on_class)))
                else:
                    self.graph.add((restriction, OWL.minCardinality, Literal(min_cardinality)))
            
            if max_cardinality is not None:
                if on_class:
                    self.graph.add((restriction, OWL.maxQualifiedCardinality, Literal(max_cardinality)))
                    self.graph.add((restriction, OWL.onClass, URIRef(on_class)))
                else:
                    self.graph.add((restriction, OWL.maxCardinality, Literal(max_cardinality)))
        
        # Add restriction as subclass
        self.graph.add((class_ref, RDFS.subClassOf, restriction))
    
    def add_value_restriction(
        self,
        class_uri: str,
        property_uri: str,
        restriction_type: str,
        value: Union[str, URIRef, Literal]
    ):
        """
        Add a value restriction (allValuesFrom, someValuesFrom, hasValue).
        
        Args:
            class_uri: Class to add restriction to
            property_uri: Property the restriction applies to
            restriction_type: Type of restriction (allValuesFrom, someValuesFrom, hasValue)
            value: The value/class for the restriction
        """
        class_ref = URIRef(class_uri)
        prop_ref = URIRef(property_uri)
        
        # Create blank node for restriction
        restriction = BNode()
        self.graph.add((restriction, RDF.type, OWL.Restriction))
        self.graph.add((restriction, OWL.onProperty, prop_ref))
        
        # Convert value to appropriate type
        if isinstance(value, str) and value.startswith("http"):
            value = URIRef(value)
        elif not isinstance(value, (URIRef, Literal)):
            value = Literal(value)
        
        # Add restriction type
        if restriction_type == "allValuesFrom":
            self.graph.add((restriction, OWL.allValuesFrom, value))
        elif restriction_type == "someValuesFrom":
            self.graph.add((restriction, OWL.someValuesFrom, value))
        elif restriction_type == "hasValue":
            self.graph.add((restriction, OWL.hasValue, value))
        
        # Add restriction as subclass
        self.graph.add((class_ref, RDFS.subClassOf, restriction))
    
    def add_individual(
        self,
        individual_uri: str,
        class_uri: str,
        label: Optional[str] = None,
        **metadata
    ) -> URIRef:
        """
        Add a named individual to the graph.
        
        Args:
            individual_uri: Individual URI
            class_uri: Class the individual belongs to
            label: rdfs:label
            **metadata: Additional metadata
        
        Returns:
            URIRef of the created individual
        """
        ind_ref = URIRef(individual_uri)
        class_ref = URIRef(class_uri)
        
        # Add individual declaration
        self.graph.add((ind_ref, RDF.type, OWL.NamedIndividual))
        self.graph.add((ind_ref, RDF.type, class_ref))
        
        # Add label
        if label:
            self.graph.add((ind_ref, RDFS.label, Literal(label)))
        
        # Add custom metadata
        for key, value in metadata.items():
            pred = self._metadata_key_to_predicate(key)
            self.graph.add((ind_ref, pred, Literal(value)))
        
        return ind_ref
    
    def add_enumeration_class(
        self,
        class_uri: str,
        individuals: List[str],
        label: Optional[str] = None,
        comment: Optional[str] = None
    ):
        """
        Create an enumeration class using owl:oneOf.
        
        Args:
            class_uri: Class URI
            individuals: List of individual URIs
            label: rdfs:label
            comment: rdfs:comment
        """
        class_ref = URIRef(class_uri)
        
        # Add class declaration
        self.graph.add((class_ref, RDF.type, OWL.Class))
        
        # Add label and comment
        if label:
            self.graph.add((class_ref, RDFS.label, Literal(label)))
        if comment:
            self.graph.add((class_ref, RDFS.comment, Literal(comment)))
        
        # Create oneOf list
        oneof_list = self._create_rdf_list([URIRef(ind) for ind in individuals])
        
        # Create equivalent class with oneOf
        equiv_class = BNode()
        self.graph.add((equiv_class, RDF.type, OWL.Class))
        self.graph.add((equiv_class, OWL.oneOf, oneof_list))
        self.graph.add((class_ref, OWL.equivalentClass, equiv_class))
    
    def add_union_class(
        self,
        class_uri: str,
        union_classes: List[str],
        label: Optional[str] = None
    ):
        """
        Create a union class using owl:unionOf.
        
        Args:
            class_uri: Class URI
            union_classes: List of class URIs in the union
            label: rdfs:label
        """
        class_ref = URIRef(class_uri)
        
        # Add class declaration
        self.graph.add((class_ref, RDF.type, OWL.Class))
        
        if label:
            self.graph.add((class_ref, RDFS.label, Literal(label)))
        
        # Create unionOf list
        union_list = self._create_rdf_list([URIRef(c) for c in union_classes])
        self.graph.add((class_ref, OWL.unionOf, union_list))
    
    def add_intersection_class(
        self,
        class_uri: str,
        intersection_classes: List[str],
        label: Optional[str] = None
    ):
        """
        Create an intersection class using owl:intersectionOf.
        
        Args:
            class_uri: Class URI
            intersection_classes: List of class URIs in the intersection
            label: rdfs:label
        """
        class_ref = URIRef(class_uri)
        
        # Add class declaration
        self.graph.add((class_ref, RDF.type, OWL.Class))
        
        if label:
            self.graph.add((class_ref, RDFS.label, Literal(label)))
        
        # Create intersectionOf list
        intersection_list = self._create_rdf_list([URIRef(c) for c in intersection_classes])
        self.graph.add((class_ref, OWL.intersectionOf, intersection_list))
    
    def _create_rdf_list(self, items: List[URIRef]) -> BNode:
        """
        Create an RDF list from items.
        
        Args:
            items: List of URIRefs
        
        Returns:
            BNode representing the list head
        """
        if not items:
            return RDF.nil
        
        # Create list nodes
        head = BNode()
        self.graph.add((head, RDF.first, items[0]))
        
        current = head
        for item in items[1:]:
            next_node = BNode()
            self.graph.add((current, RDF.rest, next_node))
            self.graph.add((next_node, RDF.first, item))
            current = next_node
        
        self.graph.add((current, RDF.rest, RDF.nil))
        
        return head
    
    def _metadata_key_to_predicate(self, key: str) -> URIRef:
        """
        Convert a metadata key to a predicate URI.
        
        Args:
            key: Metadata key
        
        Returns:
            URIRef for the predicate
        """
        # If it's already a URI, use it
        if key.startswith("http://") or key.startswith("https://"):
            return URIRef(key)
        
        # Otherwise, create from base namespace
        return self.base_namespace[key]
    
    def build(self) -> Graph:
        """
        Build and return the RDF graph.
        
        Returns:
            RDFLib Graph
        """
        return self.graph
    
    def serialize(self, format: str = "turtle", **kwargs) -> str:
        """
        Serialize the graph to a string.
        
        Args:
            format: Serialization format (turtle, xml, json-ld, etc.)
            **kwargs: Additional arguments for serialization
        
        Returns:
            Serialized graph as string
        """
        return self.graph.serialize(format=format, **kwargs)
    
    def save(self, file_path: str, format: str = "turtle"):
        """
        Save the graph to a file.
        
        Args:
            file_path: Path to save the file
            format: Serialization format
        """
        with open(file_path, 'w') as f:
            f.write(self.serialize(format=format))
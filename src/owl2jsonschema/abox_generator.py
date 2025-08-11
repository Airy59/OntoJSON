"""
A-box generator for creating random OWL individuals based on T-box definitions.
"""

import random
import string
from typing import Dict, List, Any, Optional, Set, Tuple
from datetime import datetime, timedelta
from rdflib import Graph, Namespace, URIRef, Literal, RDF, RDFS, OWL, XSD
from faker import Faker
from .model import OntologyModel, OntologyClass, ObjectProperty, DatatypeProperty


class ABoxGenerator:
    """Generator for creating random OWL individuals (A-box) based on T-box."""
    
    def __init__(self, ontology: OntologyModel, base_uri: str = "https://example.org#"):
        """
        Initialize the A-box generator.
        
        Args:
            ontology: The parsed OWL ontology model (T-box)
            base_uri: Base URI for generated individuals
        """
        self.ontology = ontology
        self.base_uri = base_uri.rstrip('#/') + '#'
        self.faker = Faker()
        self.graph = Graph()
        
        # Define namespaces
        self.ns = Namespace(self.base_uri)
        self.graph.bind('ex', self.ns)
        self.graph.bind('owl', OWL)
        self.graph.bind('rdfs', RDFS)
        self.graph.bind('rdf', RDF)
        
        # Track generated individuals
        self.individuals: Dict[str, List[URIRef]] = {}
        self.individual_classes: Dict[URIRef, str] = {}
        
        # Create lookup maps for classes and properties
        self.class_map: Dict[str, OntologyClass] = {}
        self.object_prop_map: Dict[str, ObjectProperty] = {}
        self.datatype_prop_map: Dict[str, DatatypeProperty] = {}
        self._build_lookup_maps()
        
    def generate(self, min_instances: int = 1, max_instances: int = 3) -> Graph:
        """
        Generate random A-box with individuals.
        
        Args:
            min_instances: Minimum number of instances per class
            max_instances: Maximum number of instances per class
            
        Returns:
            RDF graph containing the generated A-box
        """
        # Reset for new generation
        self.graph = Graph()
        self.graph.bind('ex', self.ns)
        self.graph.bind('owl', OWL)
        self.graph.bind('rdfs', RDFS)
        self.graph.bind('rdf', RDF)
        self.individuals = {}
        self.individual_classes = {}
        
        # Rebuild lookup maps in case ontology changed
        self._build_lookup_maps()
        
        # Step 1: Generate individuals for each class
        for owl_class in self.ontology.classes:
            if self._is_concrete_class(owl_class):
                num_instances = random.randint(min_instances, max_instances)
                self._generate_class_individuals(owl_class.uri, owl_class, num_instances)
        
        # Step 2: Generate property assertions
        self._generate_property_assertions()
        
        # Step 3: Add ontology declaration
        ontology_uri = URIRef(self.base_uri.rstrip('#'))
        self.graph.add((ontology_uri, RDF.type, OWL.Ontology))
        
        return self.graph
    
    def _build_lookup_maps(self):
        """Build lookup dictionaries for efficient access."""
        self.class_map = {cls.uri: cls for cls in self.ontology.classes}
        self.object_prop_map = {prop.uri: prop for prop in self.ontology.object_properties}
        self.datatype_prop_map = {prop.uri: prop for prop in self.ontology.datatype_properties}
    
    def _is_concrete_class(self, owl_class: OntologyClass) -> bool:
        """Check if a class is concrete (not abstract)."""
        # For now, consider all non-Thing classes as concrete
        # Could be enhanced to check for abstract markers
        return owl_class.uri != "http://www.w3.org/2002/07/owl#Thing"
    
    def _generate_class_individuals(self, class_uri: str, owl_class: OntologyClass, num_instances: int):
        """Generate individuals for a specific class."""
        class_name = self._get_local_name(class_uri)
        self.individuals[class_uri] = []
        
        for i in range(num_instances):
            # Generate unique individual name
            individual_name = f"{class_name}_{i+1}_{self._generate_id()}"
            individual_uri = URIRef(self.base_uri + individual_name)
            
            # Add type assertion
            self.graph.add((individual_uri, RDF.type, URIRef(class_uri)))
            self.graph.add((individual_uri, RDF.type, OWL.NamedIndividual))
            
            # Add label
            label = f"{class_name} {i+1}"
            if owl_class.label:
                if isinstance(owl_class.label, dict):
                    label = f"{owl_class.label.get('en', class_name)} {i+1}"
                else:
                    label = f"{owl_class.label} {i+1}"
            self.graph.add((individual_uri, RDFS.label, Literal(label, lang="en")))
            
            # Store individual
            self.individuals[class_uri].append(individual_uri)
            self.individual_classes[individual_uri] = class_uri
            
            # Handle superclasses
            for superclass in owl_class.super_classes:
                if superclass != "http://www.w3.org/2002/07/owl#Thing":
                    self.graph.add((individual_uri, RDF.type, URIRef(superclass)))
    
    def _generate_property_assertions(self):
        """Generate property assertions for all individuals."""
        # Process each individual
        for individual, class_uri in self.individual_classes.items():
            owl_class = self.class_map.get(class_uri)
            if not owl_class:
                continue
            
            # Generate datatype property assertions
            self._generate_datatype_properties(individual, owl_class)
            
            # Generate object property assertions
            self._generate_object_properties(individual, owl_class)
    
    def _generate_datatype_properties(self, individual: URIRef, owl_class: OntologyClass):
        """Generate datatype property assertions for an individual."""
        # Get all applicable datatype properties
        applicable_properties = self._get_applicable_datatype_properties(owl_class)
        
        for prop_uri, prop in applicable_properties:
            # Get cardinality constraints
            min_card, max_card = self._get_property_cardinality(owl_class, prop_uri)
            
            # Only generate if we have a minimum cardinality requirement or randomly decide to
            if min_card == 0 and random.random() > 0.5:  # 50% chance if not required
                continue
            
            # Determine number of values
            if max_card == 1:
                num_values = 1 if min_card > 0 or random.random() > 0.5 else 0
            else:
                max_val = min(max_card if max_card > 0 else 3, 3)
                num_values = random.randint(min_card, max_val)
            
            # Generate values
            for _ in range(num_values):
                value = self._generate_datatype_value(prop)
                if value is not None:
                    self.graph.add((individual, URIRef(prop_uri), value))
    
    def _generate_object_properties(self, individual: URIRef, owl_class: OntologyClass):
        """Generate object property assertions for an individual."""
        # Get all applicable object properties
        applicable_properties = self._get_applicable_object_properties(owl_class)
        
        for prop_uri, prop in applicable_properties:
            # Get possible target individuals first - if none exist, skip this property
            target_individuals = self._get_target_individuals(prop)
            if not target_individuals:
                continue
            
            # Get cardinality constraints
            min_card, max_card = self._get_property_cardinality(owl_class, prop_uri)
            
            # Only generate if we have a minimum cardinality requirement or randomly decide to
            if min_card == 0 and random.random() > 0.3:  # 30% chance if not required
                continue
            
            # Determine number of values
            if max_card == 1:
                num_values = 1 if min_card > 0 or random.random() > 0.5 else 0
            else:
                max_val = min(max_card if max_card > 0 else 2, 2)
                num_values = random.randint(min_card, max_val)
            
            if num_values == 0:
                continue
            
            # Generate object property assertions
            selected_targets = random.sample(
                target_individuals,
                min(num_values, len(target_individuals))
            )
            
            for target in selected_targets:
                self.graph.add((individual, URIRef(prop_uri), target))
                
                # Handle inverse properties
                if prop.inverse_of:
                    self.graph.add((target, URIRef(prop.inverse_of), individual))
    
    def _get_applicable_datatype_properties(self, owl_class: OntologyClass) -> List[Tuple[str, DatatypeProperty]]:
        """Get all datatype properties applicable to a class."""
        applicable = []
        
        for prop_uri, prop in self.datatype_prop_map.items():
            # Check if property domain includes this class or its superclasses
            if self._is_property_applicable(owl_class, prop.domain):
                applicable.append((prop_uri, prop))
        
        return applicable
    
    def _get_applicable_object_properties(self, owl_class: OntologyClass) -> List[Tuple[str, ObjectProperty]]:
        """Get all object properties applicable to a class."""
        applicable = []
        
        for prop_uri, prop in self.object_prop_map.items():
            # Check if property domain includes this class or its superclasses
            if self._is_property_applicable(owl_class, prop.domain):
                applicable.append((prop_uri, prop))
        
        return applicable
    
    def _is_property_applicable(self, owl_class: OntologyClass, domains: List[str]) -> bool:
        """Check if a property is applicable to a class based on domain."""
        if not domains:
            # No explicit domain means it could apply to any class,
            # but we should be conservative and not apply it randomly
            return False
        
        # Check if class or its superclasses are in domain
        class_hierarchy = {owl_class.uri} | set(owl_class.super_classes)
        
        # Also check if any domain is owl:Thing (universal domain)
        for domain in domains:
            if domain == "http://www.w3.org/2002/07/owl#Thing":
                return True
        
        return bool(class_hierarchy & set(domains))
    
    def _get_property_cardinality(self, owl_class: OntologyClass, prop_uri: str) -> Tuple[int, int]:
        """Get cardinality constraints for a property on a class."""
        min_card = 0
        max_card = -1  # -1 means unbounded
        
        # Check class restrictions
        for restriction in owl_class.restrictions:
            # Check if this restriction is for the property we're interested in
            if restriction.property_uri == prop_uri:
                # Handle CardinalityRestriction objects
                if hasattr(restriction, 'min_cardinality') and restriction.min_cardinality is not None:
                    min_card = max(min_card, restriction.min_cardinality)
                if hasattr(restriction, 'max_cardinality') and restriction.max_cardinality is not None:
                    if max_card == -1:
                        max_card = restriction.max_cardinality
                    else:
                        max_card = min(max_card, restriction.max_cardinality)
                if hasattr(restriction, 'exact_cardinality') and restriction.exact_cardinality is not None:
                    min_card = max_card = restriction.exact_cardinality
        
        return min_card, max_card
    
    def _get_target_individuals(self, prop: ObjectProperty) -> List[URIRef]:
        """Get possible target individuals for an object property."""
        targets = []
        
        if prop.range:
            # Get individuals of range classes
            for range_class in prop.range:
                # Direct class match
                if range_class in self.individuals:
                    targets.extend(self.individuals[range_class])
                
                # Also check for individuals whose classes are subclasses of the range
                for class_uri, individuals_list in self.individuals.items():
                    if class_uri != range_class:  # Already handled direct match
                        owl_class = self.class_map.get(class_uri)
                        if owl_class and range_class in owl_class.super_classes:
                            targets.extend(individuals_list)
        # If no range specified, we should NOT link to random individuals
        # The property simply shouldn't be used if we don't know what it can link to
        
        return targets
    
    def _generate_datatype_value(self, prop: DatatypeProperty) -> Optional[Literal]:
        """Generate a random value for a datatype property."""
        # Determine datatype from range
        datatype = self._infer_datatype(prop)
        
        if datatype == XSD.string:
            return Literal(self._generate_string_value(prop), datatype=XSD.string)
        elif datatype == XSD.integer:
            return Literal(random.randint(1, 100), datatype=XSD.integer)
        elif datatype == XSD.decimal or datatype == XSD.float or datatype == XSD.double:
            return Literal(round(random.uniform(0.0, 1000.0), 2), datatype=XSD.decimal)
        elif datatype == XSD.boolean:
            return Literal(random.choice([True, False]), datatype=XSD.boolean)
        elif datatype == XSD.date:
            date = self.faker.date_between(start_date='-5y', end_date='today')
            return Literal(date.isoformat(), datatype=XSD.date)
        elif datatype == XSD.dateTime:
            dt = self.faker.date_time_between(start_date='-5y', end_date='now')
            return Literal(dt.isoformat(), datatype=XSD.dateTime)
        else:
            # Default to string
            return Literal(self._generate_string_value(prop), datatype=XSD.string)
    
    def _infer_datatype(self, prop: DatatypeProperty) -> URIRef:
        """Infer the datatype for a property."""
        if prop.range:
            # Use first range type
            range_uri = prop.range[0]
            if '#' in range_uri:
                datatype_name = range_uri.split('#')[-1].lower()
            else:
                datatype_name = range_uri.split('/')[-1].lower()
            
            # Map to XSD datatypes
            if 'int' in datatype_name:
                return XSD.integer
            elif 'float' in datatype_name or 'double' in datatype_name or 'decimal' in datatype_name:
                return XSD.decimal
            elif 'bool' in datatype_name:
                return XSD.boolean
            elif 'date' in datatype_name and 'time' in datatype_name:
                return XSD.dateTime
            elif 'date' in datatype_name:
                return XSD.date
            elif 'time' in datatype_name:
                return XSD.time
        
        # Default to string
        return XSD.string
    
    def _generate_string_value(self, prop: DatatypeProperty) -> str:
        """Generate a string value based on property name."""
        prop_name = self._get_local_name(prop.uri).lower()
        
        # Generate contextual string based on property name
        if 'name' in prop_name:
            if 'first' in prop_name:
                return self.faker.first_name()
            elif 'last' in prop_name or 'surname' in prop_name:
                return self.faker.last_name()
            else:
                return self.faker.name()
        elif 'email' in prop_name:
            return self.faker.email()
        elif 'phone' in prop_name or 'tel' in prop_name:
            return self.faker.phone_number()
        elif 'address' in prop_name:
            return self.faker.address()
        elif 'city' in prop_name:
            return self.faker.city()
        elif 'country' in prop_name:
            return self.faker.country()
        elif 'company' in prop_name or 'organization' in prop_name:
            return self.faker.company()
        elif 'job' in prop_name or 'position' in prop_name:
            return self.faker.job()
        elif 'description' in prop_name or 'comment' in prop_name:
            return self.faker.text(max_nb_chars=200)
        elif 'url' in prop_name or 'website' in prop_name:
            return self.faker.url()
        elif 'color' in prop_name:
            return self.faker.color_name()
        elif 'id' in prop_name or 'code' in prop_name:
            return self.faker.uuid4()[:8].upper()
        else:
            # Generate generic text
            return self.faker.word().capitalize()
    
    def _get_local_name(self, uri: str) -> str:
        """Extract local name from URI."""
        if '#' in uri:
            return uri.split('#')[-1]
        else:
            return uri.split('/')[-1]
    
    def _generate_id(self) -> str:
        """Generate a unique ID."""
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    
    def serialize(self, format: str = 'turtle') -> str:
        """
        Serialize the generated A-box to string.
        
        Args:
            format: Serialization format ('turtle', 'xml', 'n3', 'nt')
            
        Returns:
            Serialized RDF string
        """
        return self.graph.serialize(format=format)
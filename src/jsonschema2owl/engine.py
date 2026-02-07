"""
Reverse Transformation Engine

Main engine for coordinating JSON Schema to OWL transformation.
"""

import logging
from typing import Optional, List
from rdflib import Graph

from .model import SchemaModel, TransformationContext
from .config import ReverseTransformationConfig
from .parser import SchemaParser
from .builder import OWLBuilder
from .uri_generator import URIGenerator
from .pattern_recognizer import PatternRecognizer
from .rules import RuleRegistry

# Import all rule classes
from .rules.schema_rules import (
    DefinitionToClassRule,
    LabelsRule,
    CommentsRule,
    SchemaMetadataRule
)
from .rules.property_rules import (
    TypeToPropertyRule,
    ObjectRefToPropertyRule,
    RequiredToCardinalityRule
)
from .rules.constraint_rules import (
    ArrayToCardinalityRule,
    ItemsToRangeRule,
    EnumToIndividualsRule,
    EnumToRestrictionRule,
    ConstToHasValueRule
)
from .rules.composition_rules import (
    AllOfToHierarchyRule,
    AllOfToIntersectionRule,
    OneOfToUnionRule,
    NotToComplementRule
)
from .rules.metadata_rules import (
    CustomFieldsRule
)


# Set up logging
logger = logging.getLogger(__name__)


class ReverseEngine:
    """Main engine for JSON Schema → OWL transformation."""
    
    def __init__(self, config: Optional[ReverseTransformationConfig] = None):
        """
        Initialize the reverse transformation engine.
        
        Args:
            config: Optional configuration
        """
        self.config = config or ReverseTransformationConfig()
        self.parser = SchemaParser()
        self.uri_generator = URIGenerator(
            base_namespace=self.config.get_base_namespace()
        )
        self.pattern_recognizer = PatternRecognizer()
        self.rule_registry = RuleRegistry()
        
        # Initialize rules
        self._initialize_rules()
    
    def _initialize_rules(self):
        """Initialize and register all transformation rules."""
        # Schema-level rules (priority 10)
        self.rule_registry.register(SchemaMetadataRule(self.config))
        self.rule_registry.register(LabelsRule(self.config))
        self.rule_registry.register(CommentsRule(self.config))
        
        # Definition-to-class rules (priority 20)
        self.rule_registry.register(DefinitionToClassRule(self.config))
        
        # Property rules (priority 30)
        self.rule_registry.register(TypeToPropertyRule(self.config))
        self.rule_registry.register(ObjectRefToPropertyRule(self.config))
        
        # Constraint rules (priority 40)
        self.rule_registry.register(RequiredToCardinalityRule(self.config))
        self.rule_registry.register(ArrayToCardinalityRule(self.config))
        self.rule_registry.register(ItemsToRangeRule(self.config))
        self.rule_registry.register(EnumToRestrictionRule(self.config))
        self.rule_registry.register(ConstToHasValueRule(self.config))
        
        # Composition rules (priority 50)
        self.rule_registry.register(AllOfToHierarchyRule(self.config))
        self.rule_registry.register(AllOfToIntersectionRule(self.config))
        self.rule_registry.register(OneOfToUnionRule(self.config))
        self.rule_registry.register(NotToComplementRule(self.config))
        
        # Enumeration rules (priority 60)
        self.rule_registry.register(EnumToIndividualsRule(self.config))
        
        # Metadata rules (priority 10)
        self.rule_registry.register(CustomFieldsRule(self.config))
        
        logger.info(f"Initialized {len(self.rule_registry)} transformation rules")
    
    def transform(self, schema: SchemaModel) -> Graph:
        """
        Transform a JSON Schema to an OWL ontology.
        
        Args:
            schema: Parsed schema model
        
        Returns:
            RDFLib Graph containing the OWL ontology
        """
        logger.info(f"Starting transformation of schema: {schema.schema_id or 'unnamed'}")
        
        # Extract and set schema name from filename if available
        if schema.source_filename:
            schema_name = URIGenerator.extract_schema_name(schema.source_filename)
            self.uri_generator.set_schema_name(schema_name)
            logger.info(f"Using schema name from filename: {schema_name}")
        
        # Create transformation context
        context = TransformationContext(
            base_namespace=self.config.get_base_namespace()
        )
        
        # Generate ontology URI (doesn't use schema $id anymore)
        ontology_uri = self.uri_generator.generate_ontology_uri()
        
        # Initialize OWL builder
        builder = OWLBuilder(
            uri_generator=self.uri_generator,
            ontology_uri=ontology_uri
        )
        
        # Apply schema-level rules first
        self._apply_schema_rules(schema, builder, context)
        
        # Apply definition-level rules
        self._apply_definition_rules(schema, builder, context)
        
        # Apply property-level rules for each definition
        self._apply_property_rules(schema, builder, context)
        
        # Post-processing: Property simplification and super-property creation
        if self.config.should_simplify_single_properties() or self.config.should_create_super_properties():
            self._post_process_properties(builder, context)
        
        # Log any warnings
        if context.warnings:
            logger.warning(f"Transformation completed with {len(context.warnings)} warnings:")
            for warning in context.warnings:
                logger.warning(f"  - {warning}")
        else:
            logger.info("Transformation completed successfully")
        
        return builder.build()
    
    def transform_from_file(self, file_path: str) -> Graph:
        """
        Transform a JSON Schema file to OWL.
        
        Args:
            file_path: Path to JSON Schema file
        
        Returns:
            RDFLib Graph containing the OWL ontology
        """
        schema = self.parser.parse_file(file_path)
        return self.transform(schema)
    
    def transform_from_string(self, schema_str: str) -> Graph:
        """
        Transform a JSON Schema string to OWL.
        
        Args:
            schema_str: JSON Schema as string
        
        Returns:
            RDFLib Graph containing the OWL ontology
        """
        schema = self.parser.parse(schema_str)
        return self.transform(schema)
    
    def _apply_schema_rules(self, schema: SchemaModel, builder: OWLBuilder, context: TransformationContext):
        """Apply schema-level rules."""
        logger.debug("Applying schema-level rules")
        
        # Get applicable rules
        rules = self.rule_registry.get_applicable_rules(schema, context)
        
        for rule in rules:
            try:
                logger.debug(f"Applying rule: {rule.rule_id}")
                rule.apply(schema, builder, context)
            except Exception as e:
                logger.error(f"Error applying rule {rule.rule_id}: {e}")
                if self.config.should_fail_on_unsupported():
                    raise
                context.add_warning(f"Failed to apply rule {rule.rule_id}: {e}")
    
    def _apply_definition_rules(self, schema: SchemaModel, builder: OWLBuilder, context: TransformationContext):
        """Apply definition-level rules."""
        logger.debug(f"Applying definition-level rules for {len(schema.definitions)} definitions")
        
        for def_name, definition in schema.definitions.items():
            # Get applicable rules for this definition
            rules = self.rule_registry.get_applicable_rules(definition, context)
            
            for rule in rules:
                try:
                    logger.debug(f"Applying rule {rule.rule_id} to definition: {def_name}")
                    rule.apply(definition, builder, context)
                except Exception as e:
                    logger.error(f"Error applying rule {rule.rule_id} to {def_name}: {e}")
                    if self.config.should_fail_on_unsupported():
                        raise
                    context.add_warning(f"Failed to apply rule {rule.rule_id} to {def_name}: {e}", def_name)
    
    def _apply_property_rules(self, schema: SchemaModel, builder: OWLBuilder, context: TransformationContext):
        """Apply property-level rules."""
        logger.debug("Applying property-level rules")
        
        for def_name, definition in schema.definitions.items():
            for prop_name, prop in definition.properties.items():
                # Mark property as required if in definition's required list
                prop.required = prop_name in definition.required
                
                # Create tuple of (definition, property) for rule application
                element = (definition, prop)
                
                # Get applicable rules for this property
                rules = self.rule_registry.get_applicable_rules(element, context)
                
                for rule in rules:
                    try:
                        logger.debug(f"Applying rule {rule.rule_id} to property: {def_name}.{prop_name}")
                        rule.apply(element, builder, context)
                    except Exception as e:
                        logger.error(f"Error applying rule {rule.rule_id} to {def_name}.{prop_name}: {e}")
                        if self.config.should_fail_on_unsupported():
                            raise
                        context.add_warning(
                            f"Failed to apply rule {rule.rule_id} to property {prop_name}: {e}",
                            f"{def_name}.{prop_name}"
                        )
    
    def add_rule(self, rule):
        """
        Add a custom transformation rule.
        
        Args:
            rule: ReverseRule instance
        """
        self.rule_registry.register(rule)
    
    def enable_rule(self, rule_id: str):
        """Enable a specific rule."""
        self.rule_registry.enable_rule(rule_id)
        self.config.enable_rule(rule_id)
    
    def disable_rule(self, rule_id: str):
        """Disable a specific rule."""
        self.rule_registry.disable_rule(rule_id)
        self.config.disable_rule(rule_id)
    
    def set_namespace(self, prefix: str, uri: str):
        """
        Set a namespace prefix.
        
        Args:
            prefix: Namespace prefix
            uri: Namespace URI
        """
        self.uri_generator.set_namespace(prefix, uri)
    
    def serialize(self, graph: Graph, format: str = "turtle") -> str:
        """
        Serialize a graph to string.
        
        Args:
            graph: RDFLib graph
            format: Output format (turtle, xml, json-ld, etc.)
        
        Returns:
            Serialized string
        """
        format_map = {
            "turtle": "turtle",
            "ttl": "turtle",
            "rdfxml": "xml",
            "xml": "xml",
            "jsonld": "json-ld",
            "json-ld": "json-ld",
            "nt": "nt",
            "n3": "n3"
        }
        
        rdf_format = format_map.get(format.lower(), format)
        return graph.serialize(format=rdf_format)
    
    def transform_and_serialize(
        self,
        schema: SchemaModel,
        format: str = "turtle"
    ) -> str:
        """
        Transform schema and return serialized output.
        
        Args:
            schema: Parsed schema model
            format: Output format
        
        Returns:
            Serialized OWL ontology
        """
        graph = self.transform(schema)
        return self.serialize(graph, format)
    
    def _post_process_properties(self, builder: OWLBuilder, context: TransformationContext):
        """
        Post-process properties: simplify single properties and create super-properties.
        
        Args:
            builder: OWL builder instance
            context: Transformation context
        """
        from rdflib import URIRef, Literal
        from rdflib.namespace import RDF, RDFS, OWL
        
        graph = builder.graph
        
        # Collect all properties and group by base name
        properties_by_base_name = {}
        property_info = {}  # Maps property URI to (base_name, domain, label, type)
        
        # Find all object and datatype properties
        for prop_uri in list(graph.subjects(RDF.type, OWL.ObjectProperty)):
            prop_uri_str = str(prop_uri)
            base_name, domain = self._extract_property_info(prop_uri_str, graph)
            if base_name:
                if base_name not in properties_by_base_name:
                    properties_by_base_name[base_name] = []
                properties_by_base_name[base_name].append(prop_uri_str)
                # Get label
                labels = list(graph.objects(prop_uri, RDFS.label))
                label = str(labels[0]) if labels else base_name
                property_info[prop_uri_str] = (base_name, domain, label, "ObjectProperty")
        
        for prop_uri in list(graph.subjects(RDF.type, OWL.DatatypeProperty)):
            prop_uri_str = str(prop_uri)
            base_name, domain = self._extract_property_info(prop_uri_str, graph)
            if base_name:
                if base_name not in properties_by_base_name:
                    properties_by_base_name[base_name] = []
                properties_by_base_name[base_name].append(prop_uri_str)
                # Get label
                labels = list(graph.objects(prop_uri, RDFS.label))
                label = str(labels[0]) if labels else base_name
                property_info[prop_uri_str] = (base_name, domain, label, "DatatypeProperty")
        
        # Option 2: Simplify single properties (must be done first)
        if self.config.should_simplify_single_properties():
            self._simplify_single_properties(graph, properties_by_base_name, property_info, builder)
            # Rebuild the grouping after simplification (simplified properties won't have underscore)
            properties_by_base_name = {}
            property_info = {}
            for prop_uri in list(graph.subjects(RDF.type, OWL.ObjectProperty)):
                prop_uri_str = str(prop_uri)
                base_name, domain = self._extract_property_info(prop_uri_str, graph)
                # If no underscore, use the full local name as base_name
                if not base_name:
                    if "#" in prop_uri_str:
                        base_name = prop_uri_str.split("#")[-1]
                    else:
                        continue
                if base_name not in properties_by_base_name:
                    properties_by_base_name[base_name] = []
                properties_by_base_name[base_name].append(prop_uri_str)
                labels = list(graph.objects(URIRef(prop_uri_str), RDFS.label))
                label = str(labels[0]) if labels else base_name
                property_info[prop_uri_str] = (base_name, domain, label, "ObjectProperty")
            for prop_uri in list(graph.subjects(RDF.type, OWL.DatatypeProperty)):
                prop_uri_str = str(prop_uri)
                base_name, domain = self._extract_property_info(prop_uri_str, graph)
                # If no underscore, use the full local name as base_name
                if not base_name:
                    if "#" in prop_uri_str:
                        base_name = prop_uri_str.split("#")[-1]
                    else:
                        continue
                if base_name not in properties_by_base_name:
                    properties_by_base_name[base_name] = []
                properties_by_base_name[base_name].append(prop_uri_str)
                labels = list(graph.objects(URIRef(prop_uri_str), RDFS.label))
                label = str(labels[0]) if labels else base_name
                property_info[prop_uri_str] = (base_name, domain, label, "DatatypeProperty")
        
        # Option 1: Create super-properties for groups (after simplification if enabled)
        if self.config.should_create_super_properties():
            self._create_super_properties(graph, properties_by_base_name, property_info, builder)
    
    def _extract_property_info(self, prop_uri_str: str, graph) -> tuple:
        """
        Extract base name and domain from a property URI.
        
        Args:
            prop_uri_str: Property URI as string
            graph: RDF graph
        
        Returns:
            Tuple of (base_name, domain_uri) or (None, None) if not reverse_scoped format
        """
        # Extract the local name (part after #)
        if "#" not in prop_uri_str:
            return None, None
        
        local_name = prop_uri_str.split("#")[-1]
        
        # Check if it's reverse_scoped format: propertyName_ClassName
        if "_" not in local_name:
            return None, None
        
        # Split on last underscore (in case property name itself contains underscores)
        parts = local_name.rsplit("_", 1)
        if len(parts) != 2:
            return None, None
        
        base_name, class_name = parts
        
        # Try to find the domain class URI
        from rdflib import URIRef
        from rdflib.namespace import RDFS
        prop_ref = URIRef(prop_uri_str)
        domains = list(graph.objects(prop_ref, RDFS.domain))
        domain_uri = str(domains[0]) if domains else None
        
        return base_name, domain_uri
    
    def _simplify_single_properties(self, graph, properties_by_base_name: dict, property_info: dict, builder: OWLBuilder):
        """
        Simplify properties that are the only one with their base name.
        
        Args:
            graph: RDF graph
            properties_by_base_name: Dictionary mapping base names to property URI lists
            property_info: Dictionary mapping property URIs to (base_name, domain, label, type)
            builder: OWL builder instance
        """
        from rdflib import URIRef
        from rdflib.namespace import RDF, RDFS, OWL
        
        # Find single properties (only one property with this base name)
        single_properties = {
            base_name: props[0] 
            for base_name, props in properties_by_base_name.items() 
            if len(props) == 1
        }
        
        if not single_properties:
            return
        
        logger.debug(f"Simplifying {len(single_properties)} single properties")
        
        for base_name, old_prop_uri in single_properties.items():
            _, domain, label, prop_type = property_info[old_prop_uri]
            
            # Generate new simplified URI
            old_uri_parts = old_prop_uri.split("#")
            if len(old_uri_parts) != 2:
                continue
            
            namespace = old_uri_parts[0] + "#"
            new_prop_uri = namespace + base_name
            
            # Skip if new URI already exists
            if (URIRef(new_prop_uri), RDF.type, OWL.ObjectProperty) in graph or \
               (URIRef(new_prop_uri), RDF.type, OWL.DatatypeProperty) in graph:
                continue
            
            old_prop_ref = URIRef(old_prop_uri)
            new_prop_ref = URIRef(new_prop_uri)
            
            # Copy all triples from old property to new property
            for s, p, o in graph.triples((old_prop_ref, None, None)):
                graph.add((new_prop_ref, p, o))
            
            # Update all references to the old property
            for s, p, o in list(graph.triples((None, old_prop_ref, None))):
                graph.remove((s, p, o))
                graph.add((s, p, new_prop_ref))
            
            for s, p, o in list(graph.triples((None, None, old_prop_ref))):
                graph.remove((s, p, o))
                graph.add((s, p, new_prop_ref))
            
            # Remove old property
            for s, p, o in list(graph.triples((old_prop_ref, None, None))):
                graph.remove((s, p, o))
            
            logger.debug(f"Simplified property: {old_prop_uri} -> {new_prop_uri}")
    
    def _create_super_properties(self, graph, properties_by_base_name: dict, property_info: dict, builder: OWLBuilder):
        """
        Create super-properties for groups of scoped properties.
        
        Args:
            graph: RDF graph
            properties_by_base_name: Dictionary mapping base names to property URI lists
            property_info: Dictionary mapping property URIs to (base_name, domain, label, type)
            builder: OWL builder instance
        """
        from rdflib import URIRef, Literal
        from rdflib.namespace import RDF, RDFS, OWL
        
        # Find groups with more than one property
        property_groups = {
            base_name: props 
            for base_name, props in properties_by_base_name.items() 
            if len(props) > 1
        }
        
        if not property_groups:
            return
        
        logger.debug(f"Creating super-properties for {len(property_groups)} property groups")
        
        for base_name, prop_uris in property_groups.items():
            # Determine property type (all should be the same type)
            prop_types = set(property_info[uri][3] for uri in prop_uris)
            if len(prop_types) != 1:
                logger.warning(f"Mixed property types for {base_name}, skipping super-property creation")
                continue
            
            prop_type = prop_types.pop()
            
            # Get label from first property (they should all have the same label)
            label = property_info[prop_uris[0]][2]
            
            # Generate super-property URI
            # Use namespace from first property
            first_uri_parts = prop_uris[0].split("#")
            if len(first_uri_parts) != 2:
                continue
            
            namespace = first_uri_parts[0] + "#"
            super_prop_uri = namespace + base_name
            
            # Check if super-property already exists
            super_prop_ref = URIRef(super_prop_uri)
            if (super_prop_ref, RDF.type, OWL.ObjectProperty) in graph or \
               (super_prop_ref, RDF.type, OWL.DatatypeProperty) in graph:
                # Super-property already exists, just add sub-property relationships
                pass
            else:
                # Create super-property
                if prop_type == "ObjectProperty":
                    graph.add((super_prop_ref, RDF.type, OWL.ObjectProperty))
                else:
                    graph.add((super_prop_ref, RDF.type, OWL.DatatypeProperty))
                
                # Add label
                graph.add((super_prop_ref, RDFS.label, Literal(label)))
            
            # Add sub-property relationships
            for prop_uri in prop_uris:
                prop_ref = URIRef(prop_uri)
                graph.add((prop_ref, RDFS.subPropertyOf, super_prop_ref))
            
            logger.debug(f"Created super-property {super_prop_uri} for {len(prop_uris)} properties")


# Export main class
__all__ = ["ReverseEngine"]
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


# Export main class
__all__ = ["ReverseEngine"]
"""
Transformation Engine

This module implements the main transformation engine that coordinates the transformation process.
"""

from typing import Dict, Any, List, Optional
from .model import OntologyModel
from .config import TransformationConfig
from .visitor import TransformationRule, CompositeVisitor
from .builder import SchemaBuilder


class TransformationEngine:
    """Main engine for transforming OWL ontologies to JSON Schema."""
    
    def __init__(self, config: Optional[TransformationConfig] = None):
        """
        Initialize the transformation engine.
        
        Args:
            config: Configuration for the transformation
        """
        self.config = config or TransformationConfig()
        self.rules: List[TransformationRule] = []
        self.schema_builder = SchemaBuilder()
        self._initialize_rules()
    
    def _initialize_rules(self):
        """Initialize transformation rules based on configuration."""
        # Import rule implementations
        from .rules.class_rules import ClassToObjectRule, ClassHierarchyRule, ClassRestrictionsRule
        from .rules.property_rules import ObjectPropertyRule, DatatypePropertyRule, PropertyCardinalityRule
        from .rules.annotation_rules import LabelsToTitlesRule, CommentsToDescriptionsRule
        from .rules.advanced_rules import EnumerationToEnumRule, UnionToAnyOfRule, IntersectionToAllOfRule
        from .rules.structural_rules import OntologyMetadataRule
        
        # Map rule IDs to rule classes
        rule_classes = {
            "class_to_object": ClassToObjectRule,
            "class_hierarchy": ClassHierarchyRule,
            "class_restrictions": ClassRestrictionsRule,  # Added this!
            "object_property": ObjectPropertyRule,
            "datatype_property": DatatypePropertyRule,
            "property_cardinality": PropertyCardinalityRule,
            "labels_to_titles": LabelsToTitlesRule,
            "comments_to_descriptions": CommentsToDescriptionsRule,
            "enumeration_to_enum": EnumerationToEnumRule,
            "union_to_anyOf": UnionToAnyOfRule,
            "intersection_to_allOf": IntersectionToAllOfRule,
            "ontology_metadata": OntologyMetadataRule
        }
        
        # Create and add rules based on configuration
        for rule_id, rule_class in rule_classes.items():
            rule_config = self.config.get_rule_config(rule_id)
            rule = rule_class(rule_id, rule_config)
            self.add_rule(rule)
    
    def add_rule(self, rule: TransformationRule):
        """
        Add a transformation rule to the engine.
        
        Args:
            rule: The transformation rule to add
        """
        self.rules.append(rule)
    
    def remove_rule(self, rule_id: str):
        """
        Remove a transformation rule from the engine.
        
        Args:
            rule_id: The ID of the rule to remove
        """
        self.rules = [r for r in self.rules if r.rule_id != rule_id]
    
    def get_rule(self, rule_id: str) -> Optional[TransformationRule]:
        """
        Get a transformation rule by its ID.
        
        Args:
            rule_id: The ID of the rule
        
        Returns:
            The transformation rule or None if not found
        """
        for rule in self.rules:
            if rule.rule_id == rule_id:
                return rule
        return None
    
    def transform(self, ontology: OntologyModel) -> Dict[str, Any]:
        """
        Transform an ontology to JSON Schema.
        
        Args:
            ontology: The ontology model to transform
        
        Returns:
            The resulting JSON Schema
        """
        # Reset the schema builder
        self.schema_builder = SchemaBuilder()
        
        # Apply each enabled rule
        for rule in self.rules:
            if rule.is_enabled():
                # Reset rule state
                rule.reset()
                
                # Apply the rule to the ontology
                result = ontology.accept(rule)
                
                # Process the result
                if result is not None:
                    self._process_rule_result(rule.rule_id, result)
        
        # Build and return the final schema
        return self.schema_builder.build()
    
    def _process_rule_result(self, rule_id: str, result: Any):
        """
        Process the result from a transformation rule.
        
        Args:
            rule_id: The ID of the rule that produced the result
            result: The result from the rule
        """
        # Different rules produce different types of results
        # We need to handle them appropriately
        
        if rule_id == "class_to_object":
            # Classes become definitions
            if isinstance(result, list):
                for schema in result:
                    if "title" in schema:
                        self.schema_builder.add_definition(schema["title"], schema)
            elif isinstance(result, dict):
                if "definitions" in result:
                    for name, schema in result["definitions"].items():
                        self.schema_builder.add_definition(name, schema)
        
        elif rule_id == "class_restrictions":
            # Class restrictions add properties to existing class definitions
            if isinstance(result, list):
                # Result is a list of restrictions per class
                for class_restrictions in result:
                    if isinstance(class_restrictions, dict) and "class" in class_restrictions:
                        class_name = class_restrictions["class"]
                        if "properties" in class_restrictions:
                            for prop_name, prop_schema in class_restrictions["properties"].items():
                                self.schema_builder.add_property_to_class(class_name, prop_name, prop_schema)
                        if "required" in class_restrictions:
                            for prop_name in class_restrictions["required"]:
                                self.schema_builder.add_required_to_class(class_name, prop_name)
            elif isinstance(result, dict) and "class" in result:
                # Result is a single class's restrictions with class context
                class_name = result["class"]
                if "properties" in result:
                    for prop_name, prop_schema in result["properties"].items():
                        self.schema_builder.add_property_to_class(class_name, prop_name, prop_schema)
                if "required" in result:
                    for prop_name in result["required"]:
                        self.schema_builder.add_required_to_class(class_name, prop_name)
        
        elif rule_id == "class_hierarchy":
            # Class hierarchy updates modify existing definitions with allOf
            if isinstance(result, dict) and "hierarchy_updates" in result:
                for class_name, hierarchy_info in result["hierarchy_updates"].items():
                    # Merge hierarchy information into existing definition
                    clean_name = self.schema_builder._clean_definition_name(class_name)
                    if clean_name in self.schema_builder.definitions:
                        # Merge the hierarchy info (typically allOf) with existing definition
                        for key, value in hierarchy_info.items():
                            self.schema_builder.definitions[clean_name][key] = value
                    else:
                        # Create new definition with hierarchy info
                        self.schema_builder.add_definition(class_name, hierarchy_info)
        
        elif rule_id == "labels_to_titles":
            # Title updates add titles to existing definitions
            if isinstance(result, dict) and "title_updates" in result:
                for key, title_info in result["title_updates"].items():
                    if key.startswith("class:"):
                        class_name = key[6:]  # Remove "class:" prefix
                        clean_name = self.schema_builder._clean_definition_name(class_name)
                        if clean_name in self.schema_builder.definitions:
                            if "title" in title_info:
                                self.schema_builder.definitions[clean_name]["title"] = title_info["title"]
                    # Property titles are handled within their definitions
        
        elif rule_id == "enumeration_to_enum":
            # Enumerations replace class definitions with enum schemas
            if isinstance(result, dict) and "enum_updates" in result:
                for class_name, enum_schema in result["enum_updates"].items():
                    # Replace the class definition with the enum schema
                    self.schema_builder.add_definition(class_name, enum_schema)
        
        elif rule_id == "ontology_metadata":
            # Metadata goes into the root schema
            if isinstance(result, dict):
                # Only add valid JSON Schema root properties
                valid_root_properties = {
                    "title", "description", "$id", "$comment",
                    "$defs", "additionalProperties", "type"
                }
                for key, value in result.items():
                    if key in valid_root_properties:
                        self.schema_builder.add_to_root(key, value)
        
        elif rule_id in ["object_property", "datatype_property"]:
            # Properties are added to their respective classes
            if isinstance(result, list):
                for prop_def in result:
                    if "class" in prop_def and "property" in prop_def:
                        self.schema_builder.add_property_to_class(
                            prop_def["class"],
                            prop_def["property"]["name"],
                            prop_def["property"]["schema"]
                        )
        
        # Note: We don't have a generic else clause that adds arbitrary results
        # All rule results must be explicitly handled to ensure valid JSON Schema output
    
    def transform_with_composite(self, ontology: OntologyModel) -> Dict[str, Any]:
        """
        Transform an ontology using a composite visitor.
        
        This method applies all rules in a single traversal of the ontology.
        
        Args:
            ontology: The ontology model to transform
        
        Returns:
            The resulting JSON Schema
        """
        # Create a composite visitor with all enabled rules
        composite = CompositeVisitor()
        for rule in self.rules:
            if rule.is_enabled():
                composite.add_visitor(rule)
        
        # Apply the composite visitor
        results = ontology.accept(composite)
        
        # Process all results
        for rule_id, result in results.items():
            self._process_rule_result(rule_id, result)
        
        # Build and return the final schema
        return self.schema_builder.build()
    
    def enable_rule(self, rule_id: str):
        """
        Enable a specific rule.
        
        Args:
            rule_id: The ID of the rule to enable
        """
        rule = self.get_rule(rule_id)
        if rule:
            rule.enable()
            self.config.enable_rule(rule_id)
    
    def disable_rule(self, rule_id: str):
        """
        Disable a specific rule.
        
        Args:
            rule_id: The ID of the rule to disable
        """
        rule = self.get_rule(rule_id)
        if rule:
            rule.disable()
            self.config.disable_rule(rule_id)
    
    def get_enabled_rules(self) -> List[str]:
        """Get list of enabled rule IDs."""
        return [rule.rule_id for rule in self.rules if rule.is_enabled()]
    
    def get_disabled_rules(self) -> List[str]:
        """Get list of disabled rule IDs."""
        return [rule.rule_id for rule in self.rules if not rule.is_enabled()]
    
    def __repr__(self) -> str:
        """String representation of the engine."""
        enabled = len(self.get_enabled_rules())
        disabled = len(self.get_disabled_rules())
        return f"TransformationEngine(rules={len(self.rules)}, enabled={enabled}, disabled={disabled})"
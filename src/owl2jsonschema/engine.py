"""
Transformation Engine

This module implements the main transformation engine that coordinates the transformation process.
"""

from typing import Dict, Any, List, Optional
from .model import OntologyModel
from .config import TransformationConfig
from .visitor import TransformationRule, CompositeVisitor
from .builder import SchemaBuilder
from .class_name_disambiguator import ClassNameDisambiguator


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
        # Get schema format from configuration
        output_config = self.config.get_output_config()
        schema_format = output_config.get("format", "json-schema-draft-07")
        self.schema_builder = SchemaBuilder(schema_format)
        self._initialize_rules()
    
    def _initialize_rules(self):
        """Initialize transformation rules based on configuration."""
        # Import rule implementations
        from .rules.class_rules import (ClassToObjectRule, ClassHierarchyRule, ClassRestrictionsRule,
                                        IndividualsToEnumRule, IndividualsToLabelEnumRule)
        from .rules.property_rules import ObjectPropertyRule, DatatypePropertyRule, PropertyCardinalityRule
        from .rules.annotation_rules import LabelsToTitlesRule, CommentsToDescriptionsRule
        from .rules.advanced_rules import EnumerationToEnumRule, UnionToAnyOfRule, IntersectionToAllOfRule, DisjointClassesRule
        from .rules.structural_rules import OntologyMetadataRule, ThingWithUriRule
        
        # Map rule IDs to rule classes
        rule_classes = {
            "class_to_object": ClassToObjectRule,
            "class_hierarchy": ClassHierarchyRule,
            "class_restrictions": ClassRestrictionsRule,
            "individuals_to_enum": IndividualsToEnumRule,  # URI-based (disabled by default)
            "individuals_to_label_enum": IndividualsToLabelEnumRule,  # Label-based (enabled by default)
            "object_property": ObjectPropertyRule,
            "datatype_property": DatatypePropertyRule,
            "property_cardinality": PropertyCardinalityRule,
            "labels_to_titles": LabelsToTitlesRule,
            "comments_to_descriptions": CommentsToDescriptionsRule,
            "enumeration_to_enum": EnumerationToEnumRule,
            "union_to_anyOf": UnionToAnyOfRule,
            "intersection_to_allOf": IntersectionToAllOfRule,
            "disjoint_classes": DisjointClassesRule,
            "ontology_metadata": OntologyMetadataRule,
            "thing_with_uri": ThingWithUriRule
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
        # Reset the schema builder with the configured schema format
        output_config = self.config.get_output_config()
        schema_format = output_config.get("format", "json-schema-draft-07")
        self.schema_builder = SchemaBuilder(schema_format)
        
        # Initialize class name disambiguator if collision handling is enabled
        class_naming_config = self.config.config.get("class_naming", {})
        handle_collisions = class_naming_config.get("handle_collisions", True)
        maximalist = class_naming_config.get("maximalist_suffixes", False)
        
        disambiguator = None
        if handle_collisions:
            # Collect all imported ontology URIs (including secondary imports)
            # Start with explicit imports from ontology.imports (which now includes all imports
            # from all ontologies thanks to the updated parser)
            imported_uris = set(ontology.imports)
            
            # Also extract distinct namespace bases from class URIs to identify
            # all ontologies that have classes in the merged graph
            # This ensures we catch ontologies that are referenced but might not
            # have explicit import statements
            namespace_bases = set()
            for owl_class in ontology.classes:
                class_uri = owl_class.uri
                # Extract namespace base from class URI
                if '#' in class_uri:
                    namespace_base = class_uri.rsplit('#', 1)[0] + '#'
                elif '/' in class_uri:
                    namespace_base = class_uri.rsplit('/', 1)[0] + '/'
                else:
                    continue
                
                # Add if it's different from main ontology and not already in imports
                if namespace_base != ontology.uri:
                    namespace_bases.add(namespace_base)
            
            # Combine explicit imports with namespace bases found in classes
            # This ensures we have all ontologies that contribute classes
            all_imported_uris = imported_uris | namespace_bases
            
            # Get primary imports (directly imported by main ontology)
            # These might be file URIs (like file:///path/to/pop.ttl)
            primary_import_file_uris = ontology.annotations.get("_primary_imports", ontology.imports)
            
            # Get all ontology namespace URIs from the graph (from owl:Ontology declarations)
            all_ontology_namespace_uris = set(ontology.annotations.get("_all_ontology_namespace_uris", []))
            
            # Get secondary ontology namespace URIs (imported by other imported ontologies)
            secondary_ontology_namespace_uris = set(ontology.annotations.get("_secondary_ontology_namespace_uris", []))
            
            # Get the mapping from import file URIs to ontology namespace URIs
            # This was built during parsing when imports were resolved
            import_file_to_ontology_uri = getattr(ontology, '_import_file_to_ontology_uri', {})
            # Also try to get it from annotations if stored there
            if not import_file_to_ontology_uri:
                import_file_to_ontology_uri = ontology.annotations.get("_import_file_to_ontology_uri", {})
            
            # Build primary_imports list: include both file URIs and namespace URIs
            # that correspond to primary imports (NOT secondary imports or references)
            primary_imports_set = set(primary_import_file_uris)
            
            # Map primary import file URIs to their ontology namespace URIs
            # This allows the disambiguator to match class URIs to primary imports
            for primary_file_uri in primary_import_file_uris:
                mapped_namespace_uri = import_file_to_ontology_uri.get(primary_file_uri)
                if mapped_namespace_uri:
                    primary_imports_set.add(mapped_namespace_uri)
            
            # Add namespace bases that correspond to primary imports
            # Primary imports are ontology namespace URIs that are NOT secondary imports
            # (secondary imports/references are detected by the parser and stored in
            # secondary_ontology_namespace_uris)
            for namespace_base in namespace_bases:
                # Only include if it's an ontology namespace URI AND not a secondary import
                if namespace_base in all_ontology_namespace_uris:
                    if namespace_base not in secondary_ontology_namespace_uris:
                        # This is a primary import namespace URI
                        primary_imports_set.add(namespace_base)
                        print(f"DEBUG: Added {namespace_base} to primary_imports (not in secondary)")
                    else:
                        print(f"DEBUG: Excluded {namespace_base} from primary_imports (is secondary)")
                else:
                    print(f"DEBUG: {namespace_base} is not an ontology namespace URI")
            
            primary_imports = list(primary_imports_set)
            
            disambiguator = ClassNameDisambiguator(
                main_ontology_uri=ontology.uri,
                imported_ontology_uris=list(all_imported_uris),
                primary_imports=primary_imports,
                maximalist=maximalist
            )
            
            # Register all classes first to detect collisions
            for owl_class in ontology.classes:
                local_name = disambiguator.extract_local_name(owl_class.uri)
                disambiguator.register_class(owl_class.uri, local_name)
            
            # Set disambiguator on all rules
            for rule in self.rules:
                rule.disambiguator = disambiguator
        
        # Check if ThingWithUriRule is enabled
        thing_rule = self.get_rule("thing_with_uri")
        
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
        
        # If ThingWithUriRule is enabled, apply inheritance to all class definitions
        if thing_rule and thing_rule.is_enabled():
            self._apply_thing_inheritance(thing_rule)
        
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
                        # Handle OWL class URI
                        output_config = self.config.get_output_config()
                        if "uri" in schema:
                            owl_uri = schema.pop("uri")  # Remove from schema
                            if output_config.get("include_uri", False):
                                # Add as custom metadata field in the schema
                                schema["$comment"] = f"OWL Class URI: {owl_uri}"
                        
                        
                        self.schema_builder.add_definition(schema["title"], schema)
            elif isinstance(result, dict):
                if "definitions" in result:
                    for name, schema in result["definitions"].items():
                        # Handle OWL class URI
                        output_config = self.config.get_output_config()
                        if "uri" in schema:
                            owl_uri = schema.pop("uri")  # Remove from schema
                            if output_config.get("include_uri", False):
                                # Add as custom metadata field in the schema
                                schema["$comment"] = f"OWL Class URI: {owl_uri}"
                        
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
        
        elif rule_id == "individuals_to_enum":
            # Individuals add enum constraints to the uri property of their class definitions
            if isinstance(result, dict) and "individuals_constraints" in result:
                for class_name, property_constraints in result["individuals_constraints"].items():
                    clean_class_name = self.schema_builder._clean_definition_name(class_name)
                    if clean_class_name in self.schema_builder.definitions:
                        # Get existing class definition
                        class_def = self.schema_builder.definitions[clean_class_name]
                        
                        # Ensure properties dict exists
                        if "properties" not in class_def:
                            class_def["properties"] = {}
                        
                        # Update each property with its constraint
                        for prop_name, constraint in property_constraints.items():
                            if prop_name in class_def["properties"]:
                                # Merge constraint with existing property definition
                                class_def["properties"][prop_name].update(constraint)
                            else:
                                # Add new property with constraint
                                class_def["properties"][prop_name] = constraint
        
        elif rule_id == "individuals_to_label_enum":
            # Individuals create label-based enums (replaces entire class definition)
            if isinstance(result, dict) and "individuals_label_constraints" in result:
                for class_name, enum_schema in result["individuals_label_constraints"].items():
                    # Replace the class definition with the label-based enum
                    self.schema_builder.add_definition(class_name, enum_schema)
        
        elif rule_id == "ontology_metadata":
            # Metadata goes into the root schema
            if isinstance(result, dict):
                # Add both standard JSON Schema properties and our custom metadata fields
                valid_root_properties = {
                    "title", "description", "$id", "$comment",
                    "$defs", "additionalProperties", "type"
                }
                # Also allow our custom metadata fields and Draft 7 compliant extensions
                custom_metadata_properties = {
                    "$metadata", "$schema-version", "$schema-author",
                    "$schema-created", "$schema-modified", "$schema-license",
                    "x-metadata",  # Draft 7 compliant custom property
                    "info"  # For OpenAPI-style metadata grouping
                }
                allowed_properties = valid_root_properties | custom_metadata_properties
                
                for key, value in result.items():
                    if key in allowed_properties or key.startswith("x-"):
                        self.schema_builder.add_to_root(key, value)
        
        elif rule_id == "thing_with_uri":
            # Add _Thing base object to definitions
            if isinstance(result, dict) and "definitions" in result:
                for name, schema in result["definitions"].items():
                    self.schema_builder.add_definition(name, schema)
        
        elif rule_id == "disjoint_classes":
            # Handle disjoint class unions
            if isinstance(result, dict) and "disjoint_unions" in result:
                for superclass_name, union_info in result["disjoint_unions"].items():
                    clean_name = self.schema_builder._clean_definition_name(superclass_name)
                    if clean_name in self.schema_builder.definitions:
                        # Merge the disjoint union info with existing definition
                        # Preserve existing properties and hierarchy while adding the oneOf constraint
                        existing_def = self.schema_builder.definitions[clean_name]
                        
                        # If the existing definition has allOf (inheritance), merge with it
                        if "allOf" in existing_def:
                            # Add the oneOf constraint to the existing allOf
                            # Extract the oneOf from union_info's allOf
                            if "allOf" in union_info:
                                for item in union_info["allOf"]:
                                    if "oneOf" in item:
                                        # Add the oneOf constraint to the existing allOf
                                        existing_def["allOf"].append(item)
                                        break
                            # Preserve title and description from union_info
                            if "title" in union_info:
                                existing_def["title"] = union_info["title"]
                            if "description" in union_info:
                                existing_def["description"] = union_info["description"]
                        else:
                            # No existing allOf, use the union_info but preserve properties
                            preserved_properties = existing_def.get("properties", {})
                            preserved_required = existing_def.get("required", [])
                            preserved_type = existing_def.get("type")
                            preserved_title = existing_def.get("title")
                            preserved_comment = existing_def.get("$comment")
                            
                            # Replace with the union schema
                            self.schema_builder.definitions[clean_name] = union_info
                            
                            # Restore preserved fields
                            if preserved_properties:
                                # Add properties to the appropriate place in allOf
                                if "allOf" in self.schema_builder.definitions[clean_name]:
                                    # Find or create the properties object in allOf
                                    found_props = False
                                    for item in self.schema_builder.definitions[clean_name]["allOf"]:
                                        if "type" in item and item["type"] == "object":
                                            if "properties" not in item:
                                                item["properties"] = {}
                                            item["properties"].update(preserved_properties)
                                            found_props = True
                                            break
                                    if not found_props:
                                        # Add a new object with properties
                                        self.schema_builder.definitions[clean_name]["allOf"].insert(0, {
                                            "type": "object",
                                            "properties": preserved_properties
                                        })
                            
                            if preserved_required:
                                self.schema_builder.definitions[clean_name]["required"] = preserved_required
                            
                            # Restore original title and comment if not present
                            if preserved_title and "title" not in self.schema_builder.definitions[clean_name]:
                                self.schema_builder.definitions[clean_name]["title"] = preserved_title
                            if preserved_comment and "$comment" not in self.schema_builder.definitions[clean_name]:
                                self.schema_builder.definitions[clean_name]["$comment"] = preserved_comment
        
        elif rule_id in ["object_property", "datatype_property"]:
            # Properties are added to their respective classes
            if isinstance(result, list):
                for prop_def in result:
                    if "class" in prop_def and "property" in prop_def:
                        property_schema = prop_def["property"]["schema"]
                        
                        # Add OWL property URI as metadata if configured
                        output_config = self.config.get_output_config()
                        if output_config.get("include_uri", False) and "uri" in prop_def["property"]:
                            property_uri = prop_def["property"]["uri"]
                            # Add the URI as a $comment in the property schema
                            property_schema["$comment"] = f"OWL Property URI: {property_uri}"
                        
                        self.schema_builder.add_property_to_class(
                            prop_def["class"],
                            prop_def["property"]["name"],
                            property_schema
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
    
    def _apply_thing_inheritance(self, thing_rule: TransformationRule):
        """Apply _Thing inheritance to all class definitions."""
        # Create a copy of definitions to modify
        updated_definitions = {}
        
        for class_name, class_schema in self.schema_builder.definitions.items():
            # Skip _Thing itself
            if class_name == "_Thing":
                updated_definitions[class_name] = class_schema
                continue
            
            # Apply inheritance using the rule's method
            inherited_schema = thing_rule.apply_inheritance(class_schema)
            updated_definitions[class_name] = inherited_schema
        
        # Replace definitions with inherited versions
        self.schema_builder.definitions = updated_definitions
    
    def __repr__(self) -> str:
        """String representation of the engine."""
        enabled = len(self.get_enabled_rules())
        disabled = len(self.get_disabled_rules())
        return f"TransformationEngine(rules={len(self.rules)}, enabled={enabled}, disabled={disabled})"
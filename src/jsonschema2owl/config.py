"""
Configuration System for JSON Schema to OWL2 Reverse Transformation

This module handles the configuration of the reverse transformation engine and rules.
"""

import json
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List


class ReverseTransformationConfig:
    """Configuration class for the JSON Schema → OWL reverse transformation engine."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the reverse transformation configuration.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config or self._get_default_config()
    
    @classmethod
    def from_file(cls, file_path: str) -> "ReverseTransformationConfig":
        """
        Load configuration from a file.
        
        Args:
            file_path: Path to the configuration file (JSON or YAML)
        
        Returns:
            ReverseTransformationConfig instance
        """
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {file_path}")
        
        with open(path, 'r') as f:
            if path.suffix in ['.yaml', '.yml']:
                config = yaml.safe_load(f)
            elif path.suffix == '.json':
                config = json.load(f)
            else:
                raise ValueError(f"Unsupported configuration file format: {path.suffix}")
        
        return cls(config)
    
    def to_file(self, file_path: str):
        """
        Save configuration to a file.
        
        Args:
            file_path: Path to save the configuration file
        """
        path = Path(file_path)
        
        with open(path, 'w') as f:
            if path.suffix in ['.yaml', '.yml']:
                yaml.dump(self.config, f, default_flow_style=False)
            elif path.suffix == '.json':
                json.dump(self.config, f, indent=2)
            else:
                raise ValueError(f"Unsupported configuration file format: {path.suffix}")
    
    def get_namespace_config(self) -> Dict[str, Any]:
        """Get namespace configuration."""
        return self.config.get("namespace", {})
    
    def get_base_namespace(self) -> str:
        """Get the base namespace URI."""
        return self.get_namespace_config().get("base", "https://cdm.ovh/examples/")
    
    def set_base_namespace(self, namespace: str):
        """
        Set the base namespace URI.
        
        Args:
            namespace: Base namespace URI to set
        """
        if "namespace" not in self.config:
            self.config["namespace"] = {}
        self.config["namespace"]["base"] = namespace
    
    def get_namespace_prefixes(self) -> Dict[str, str]:
        """Get namespace prefix mappings."""
        return self.get_namespace_config().get("prefixes", {})
    
    def get_uri_generation_config(self) -> Dict[str, Any]:
        """Get URI generation configuration."""
        return self.config.get("uri_generation", {})
    
    def get_property_naming_strategy(self) -> str:
        """
        Get the property naming strategy.
        
        Returns:
            Property naming strategy: "scoped", "reverse_scoped", or "global"
        """
        return self.get_uri_generation_config().get("property_naming_strategy", "scoped")
    
    def set_property_naming_strategy(self, strategy: str):
        """
        Set the property naming strategy.
        
        Args:
            strategy: One of "scoped", "reverse_scoped", or "global"
        """
        valid_strategies = ["scoped", "reverse_scoped", "global"]
        if strategy not in valid_strategies:
            raise ValueError(f"Invalid property naming strategy: {strategy}. Must be one of {valid_strategies}")
        
        if "uri_generation" not in self.config:
            self.config["uri_generation"] = {}
        self.config["uri_generation"]["property_naming_strategy"] = strategy
    
    def get_ambiguity_resolution_config(self) -> Dict[str, Any]:
        """Get ambiguity resolution configuration."""
        return self.config.get("ambiguity_resolution", {})
    
    def get_array_handling_strategy(self) -> str:
        """Get array handling strategy."""
        return self.get_ambiguity_resolution_config().get(
            "array_handling", "non_functional_property"
        )
    
    def get_allof_interpretation_strategy(self) -> str:
        """Get allOf interpretation strategy."""
        return self.get_ambiguity_resolution_config().get(
            "allof_interpretation", "inheritance"
        )
    
    def get_oneof_interpretation_strategy(self) -> str:
        """Get oneOf interpretation strategy."""
        return self.get_ambiguity_resolution_config().get(
            "oneof_interpretation", "union"
        )
    
    def get_property_domain_handling_config(self) -> Dict[str, Any]:
        """Get property domain handling configuration."""
        return self.config.get("property_domain_handling", {})
    
    def get_multiple_domain_strategy(self) -> str:
        """
        Get the strategy for handling properties with multiple domains.
        
        Returns:
            Strategy: "union_of" (default) or "split_properties"
        """
        return self.get_property_domain_handling_config().get(
            "multiple_domain_strategy", "union_of"
        )
    
    def set_multiple_domain_strategy(self, strategy: str):
        """
        Set the strategy for handling properties with multiple domains.
        
        Args:
            strategy: One of "union_of" or "split_properties"
        """
        valid_strategies = ["union_of", "split_properties"]
        if strategy not in valid_strategies:
            raise ValueError(
                f"Invalid multiple domain strategy: {strategy}. "
                f"Must be one of {valid_strategies}"
            )
        
        if "property_domain_handling" not in self.config:
            self.config["property_domain_handling"] = {}
        self.config["property_domain_handling"]["multiple_domain_strategy"] = strategy
    
    def should_create_super_properties(self) -> bool:
        """
        Check if super-properties should be created for groups of scoped properties.
        
        Returns:
            True if super-properties should be created
        """
        return self.get_property_domain_handling_config().get(
            "create_super_properties", False
        )
    
    def set_create_super_properties(self, enabled: bool):
        """
        Enable or disable creation of super-properties for property groups.
        
        Args:
            enabled: True to create super-properties, False otherwise
        """
        if "property_domain_handling" not in self.config:
            self.config["property_domain_handling"] = {}
        self.config["property_domain_handling"]["create_super_properties"] = enabled
    
    def should_simplify_single_properties(self) -> bool:
        """
        Check if single properties should be simplified by removing _ClassName suffix.
        
        Returns:
            True if single properties should be simplified
        """
        return self.get_property_domain_handling_config().get(
            "simplify_single_properties", False
        )
    
    def set_simplify_single_properties(self, enabled: bool):
        """
        Enable or disable simplification of single properties.
        
        Args:
            enabled: True to simplify single properties, False otherwise
        """
        if "property_domain_handling" not in self.config:
            self.config["property_domain_handling"] = {}
        self.config["property_domain_handling"]["simplify_single_properties"] = enabled
    
    def get_rule_config(self, rule_id: str) -> Dict[str, Any]:
        """
        Get configuration for a specific rule.
        
        Args:
            rule_id: The ID of the rule
        
        Returns:
            Rule configuration dictionary
        """
        return self.config.get("rules", {}).get(rule_id, {})
    
    def is_rule_enabled(self, rule_id: str) -> bool:
        """
        Check if a rule is enabled.
        
        Args:
            rule_id: The ID of the rule
        
        Returns:
            True if the rule is enabled, False otherwise
        """
        rule_config = self.get_rule_config(rule_id)
        return rule_config.get("enabled", True)
    
    def enable_rule(self, rule_id: str):
        """Enable a specific rule."""
        if "rules" not in self.config:
            self.config["rules"] = {}
        if rule_id not in self.config["rules"]:
            self.config["rules"][rule_id] = {}
        self.config["rules"][rule_id]["enabled"] = True
    
    def disable_rule(self, rule_id: str):
        """Disable a specific rule."""
        if "rules" not in self.config:
            self.config["rules"] = {}
        if rule_id not in self.config["rules"]:
            self.config["rules"][rule_id] = {}
        self.config["rules"][rule_id]["enabled"] = False
    
    def set_rule_option(self, rule_id: str, option: str, value: Any):
        """
        Set an option for a specific rule.
        
        Args:
            rule_id: The ID of the rule
            option: The option name
            value: The option value
        """
        if "rules" not in self.config:
            self.config["rules"] = {}
        if rule_id not in self.config["rules"]:
            self.config["rules"][rule_id] = {}
        if "options" not in self.config["rules"][rule_id]:
            self.config["rules"][rule_id]["options"] = {}
        self.config["rules"][rule_id]["options"][option] = value
    
    def get_output_config(self) -> Dict[str, Any]:
        """Get output configuration."""
        return self.config.get("output", {})
    
    def get_output_format(self) -> str:
        """Get the output format (turtle, rdfxml, jsonld)."""
        return self.get_output_config().get("format", "turtle")
    
    def get_validation_config(self) -> Dict[str, Any]:
        """Get validation configuration."""
        return self.config.get("validation", {})
    
    def is_strict_mode(self) -> bool:
        """Check if strict mode is enabled."""
        return self.get_validation_config().get("strict_mode", False)
    
    def should_warn_on_ambiguity(self) -> bool:
        """Check if warnings should be issued for ambiguous patterns."""
        return self.get_validation_config().get("warn_on_ambiguity", True)
    
    def should_fail_on_unsupported(self) -> bool:
        """Check if transformation should fail on unsupported features."""
        return self.get_validation_config().get("fail_on_unsupported", False)
    
    def get_enabled_rules(self) -> List[str]:
        """Get list of enabled rule IDs."""
        rules = self.config.get("rules", {})
        return [rule_id for rule_id, rule_config in rules.items() 
                if rule_config.get("enabled", True)]
    
    def get_disabled_rules(self) -> List[str]:
        """Get list of disabled rule IDs."""
        rules = self.config.get("rules", {})
        return [rule_id for rule_id, rule_config in rules.items() 
                if not rule_config.get("enabled", True)]
    
    @staticmethod
    def _get_default_config() -> Dict[str, Any]:
        """Get the default configuration for reverse transformation."""
        return {
            "namespace": {
                "base": "https://cdm.ovh/examples/",
                "prefixes": {
                    "owl": "http://www.w3.org/2002/07/owl#",
                    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
                    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
                    "xsd": "http://www.w3.org/2001/XMLSchema#"
                }
            },
            
            "uri_generation": {
                "class_pattern": "{base}{name}",
                "property_pattern": "{base}{name}",
                "individual_pattern": "{base}{name}",
                # Property naming strategy to avoid URI collisions
                # "scoped" (default): ClassName_propertyName
                # "reverse_scoped": propertyName_ClassName
                # "global": propertyName (old behavior, may cause conflicts)
                "property_naming_strategy": "scoped"
            },
            
            "ambiguity_resolution": {
                # How to handle arrays: "non_functional_property" or "rdf_list"
                "array_handling": "non_functional_property",
                
                # How to interpret allOf: "inheritance" or "intersection"
                "allof_interpretation": "inheritance",
                
                # How to interpret oneOf: "union" or "disjoint_union"
                "oneof_interpretation": "union"
            },
            
            "property_domain_handling": {
                # Properties with multiple domains are always split into separate properties
                # Format: propertyName_ClassName (e.g., "requiredProcesses_TripAllocationConstraintDef")
                # Label remains as original property name for grouping
                "multiple_domain_strategy": "split_properties",
                
                # Option 1: Create super-properties for groups of scoped properties
                # When multiple properties share the same base name, create a super-property
                # with identifier = propertyName (e.g., "requiredProcesses")
                "create_super_properties": False,
                
                # Option 2: Simplify single properties by removing _ClassName suffix
                # When a property is the only one with its base name, remove the suffix
                # (e.g., "someProperty_SomeClass" -> "someProperty")
                # Warning: May cause future naming collisions if new properties are added
                "simplify_single_properties": False
            },
            
            "rules": {
                # Phase 1: Basic transformations
                "definition_to_class": {
                    "enabled": True,
                    "priority": 20
                },
                "type_to_property": {
                    "enabled": True,
                    "priority": 30
                },
                "object_ref_to_property": {
                    "enabled": True,
                    "priority": 30
                },
                "required_to_cardinality": {
                    "enabled": True,
                    "priority": 40
                },
                "labels_rule": {
                    "enabled": True,
                    "priority": 10
                },
                "comments_rule": {
                    "enabled": True,
                    "priority": 10
                },
                
                # Phase 2: Constraint transformations
                "array_to_cardinality": {
                    "enabled": True,
                    "priority": 40
                },
                "items_to_range": {
                    "enabled": True,
                    "priority": 40
                },
                "enum_to_individuals": {
                    "enabled": True,
                    "priority": 60
                },
                "enum_to_restriction": {
                    "enabled": True,
                    "priority": 40
                },
                "const_to_hasvalue": {
                    "enabled": True,
                    "priority": 40
                },
                
                # Phase 3: Composition transformations
                "allof_to_hierarchy": {
                    "enabled": True,
                    "priority": 50
                },
                "allof_to_intersection": {
                    "enabled": True,
                    "priority": 50
                },
                "oneof_to_union": {
                    "enabled": True,
                    "priority": 50
                },
                "not_to_complement": {
                    "enabled": True,
                    "priority": 50
                },
                
                # Phase 4: Metadata transformations
                "schema_metadata": {
                    "enabled": True,
                    "priority": 10
                },
                "custom_fields": {
                    "enabled": True,
                    "priority": 10
                }
            },
            
            "output": {
                "format": "turtle",  # turtle, rdfxml, jsonld
                "pretty_print": True,
                "include_comments": True
            },
            
            "validation": {
                "strict_mode": False,
                "warn_on_ambiguity": True,
                "fail_on_unsupported": False
            }
        }
    
    def __repr__(self) -> str:
        """String representation of the configuration."""
        enabled_rules = self.get_enabled_rules()
        disabled_rules = self.get_disabled_rules()
        return (f"ReverseTransformationConfig("
                f"base_namespace='{self.get_base_namespace()}', "
                f"enabled_rules={len(enabled_rules)}, "
                f"disabled_rules={len(disabled_rules)})")
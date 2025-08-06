"""
Configuration System

This module handles the configuration of the transformation engine and rules.
"""

import json
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List


class TransformationConfig:
    """Configuration class for the transformation engine."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the transformation configuration.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config or self._get_default_config()
    
    @classmethod
    def from_file(cls, file_path: str) -> "TransformationConfig":
        """
        Load configuration from a file.
        
        Args:
            file_path: Path to the configuration file (JSON or YAML)
        
        Returns:
            TransformationConfig instance
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
        """Get the default configuration."""
        return {
            "rules": {
                # Class transformations
                "class_to_object": {
                    "enabled": True,
                    "options": {}
                },
                "class_hierarchy": {
                    "enabled": True,
                    "options": {}
                },
                "class_restrictions": {
                    "enabled": True,
                    "options": {}
                },
                
                # Property transformations
                "object_property": {
                    "enabled": True,
                    "options": {}
                },
                "datatype_property": {
                    "enabled": True,
                    "options": {}
                },
                "property_cardinality": {
                    "enabled": True,
                    "options": {
                        "use_arrays": True
                    }
                },
                "property_restrictions": {
                    "enabled": True,
                    "options": {}
                },
                
                # Annotation transformations
                "labels_to_titles": {
                    "enabled": True,
                    "options": {
                        "language": "en"
                    }
                },
                "comments_to_descriptions": {
                    "enabled": True,
                    "options": {
                        "language": "en"
                    }
                },
                "annotations_to_metadata": {
                    "enabled": False,
                    "options": {}
                },
                
                # Advanced transformations
                "enumeration_to_enum": {
                    "enabled": True,
                    "options": {
                        "use_labels": True
                    }
                },
                "union_to_anyOf": {
                    "enabled": True,
                    "options": {}
                },
                "intersection_to_allOf": {
                    "enabled": True,
                    "options": {}
                },
                "complement_to_not": {
                    "enabled": True,
                    "options": {}
                },
                "equivalent_classes": {
                    "enabled": True,
                    "options": {}
                },
                "disjoint_classes": {
                    "enabled": False,
                    "options": {}
                },
                
                # Structural transformations
                "ontology_to_document": {
                    "enabled": True,
                    "options": {}
                },
                "individuals_to_examples": {
                    "enabled": False,
                    "options": {}
                },
                "ontology_metadata": {
                    "enabled": True,
                    "options": {}
                }
            },
            
            "output": {
                "format": "json-schema-draft-07",
                "indent": 2,
                "include_metadata": True,
                "include_definitions": True,
                "namespace_handling": "preserve"
            }
        }
    
    def __repr__(self) -> str:
        """String representation of the configuration."""
        enabled_rules = self.get_enabled_rules()
        disabled_rules = self.get_disabled_rules()
        return (f"TransformationConfig("
                f"enabled_rules={len(enabled_rules)}, "
                f"disabled_rules={len(disabled_rules)})")
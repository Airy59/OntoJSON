"""
Configuration Service

Service for managing transformation configurations across different platforms.
"""

import json
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, asdict
from copy import deepcopy

from ..config import TransformationConfig


@dataclass
class ConfigurationProfile:
    """Represents a reusable configuration profile."""
    name: str
    description: str
    config: Dict[str, Any]
    is_default: bool = False
    created_by: Optional[str] = None
    created_at: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConfigurationProfile":
        """Create from dictionary."""
        return cls(**data)


class ConfigurationService:
    """
    Service for managing transformation configurations.
    
    This service provides configuration management that can be used
    across CLI, GUI, and Web interfaces.
    """
    
    def __init__(self, profiles_dir: Optional[Path] = None):
        """
        Initialize configuration service.
        
        Args:
            profiles_dir: Directory for storing configuration profiles
        """
        if profiles_dir:
            self.profiles_dir = Path(profiles_dir)
        else:
            # Use a default location in user's home directory
            self.profiles_dir = Path.home() / ".ontojson" / "profiles"
        
        self.profiles_dir.mkdir(parents=True, exist_ok=True)
        self.profiles: Dict[str, ConfigurationProfile] = {}
        self._load_profiles()
        
        # Default configuration
        self.default_config = self._create_default_config()
    
    def _create_default_config(self) -> Dict[str, Any]:
        """Create the default configuration."""
        return {
            "rules": {
                "class_to_object": {"enabled": True},
                "class_hierarchy": {"enabled": True},
                "class_restrictions": {"enabled": True},
                "object_property": {"enabled": True},
                "datatype_property": {"enabled": True},
                "property_cardinality": {"enabled": True},
                "labels_to_titles": {
                    "enabled": True,
                    "language": "en",
                    "fallback_to_uri": True
                },
                "comments_to_descriptions": {
                    "enabled": True,
                    "language": "en"
                },
                "enumeration_to_enum": {"enabled": True},
                "union_to_anyOf": {"enabled": True},
                "intersection_to_allOf": {"enabled": True},
                "disjoint_classes": {"enabled": True},
                "ontology_metadata": {"enabled": True},
                "thing_with_uri": {"enabled": False}
            },
            "output": {
                "include_uri": False,
                "format": "json",
                "indent": 2
            }
        }
    
    def _load_profiles(self):
        """Load saved configuration profiles."""
        profile_files = self.profiles_dir.glob("*.json")
        for profile_file in profile_files:
            try:
                data = json.loads(profile_file.read_text())
                profile = ConfigurationProfile.from_dict(data)
                self.profiles[profile.name] = profile
            except Exception:
                continue  # Skip invalid profiles
    
    def save_profile(self, profile: ConfigurationProfile) -> bool:
        """
        Save a configuration profile.
        
        Args:
            profile: Configuration profile to save
            
        Returns:
            True if saved successfully
        """
        try:
            profile_file = self.profiles_dir / f"{profile.name}.json"
            profile_file.write_text(json.dumps(profile.to_dict(), indent=2))
            self.profiles[profile.name] = profile
            return True
        except Exception:
            return False
    
    def load_profile(self, name: str) -> Optional[ConfigurationProfile]:
        """
        Load a configuration profile by name.
        
        Args:
            name: Profile name
            
        Returns:
            Configuration profile or None if not found
        """
        return self.profiles.get(name)
    
    def list_profiles(self) -> List[ConfigurationProfile]:
        """Get list of all configuration profiles."""
        return list(self.profiles.values())
    
    def delete_profile(self, name: str) -> bool:
        """
        Delete a configuration profile.
        
        Args:
            name: Profile name
            
        Returns:
            True if deleted successfully
        """
        try:
            if name in self.profiles:
                profile_file = self.profiles_dir / f"{name}.json"
                if profile_file.exists():
                    profile_file.unlink()
                del self.profiles[name]
                return True
            return False
        except Exception:
            return False
    
    def create_config_from_dict(
        self,
        config_dict: Optional[Dict[str, Any]] = None
    ) -> TransformationConfig:
        """
        Create a TransformationConfig from a dictionary.
        
        Args:
            config_dict: Configuration dictionary
            
        Returns:
            TransformationConfig instance
        """
        if config_dict is None:
            config_dict = self.default_config
        else:
            # Merge with defaults
            merged = deepcopy(self.default_config)
            self._deep_merge(merged, config_dict)
            config_dict = merged
        
        return TransformationConfig(config_dict)
    
    def create_config_from_profile(
        self,
        profile_name: str
    ) -> Optional[TransformationConfig]:
        """
        Create a TransformationConfig from a saved profile.
        
        Args:
            profile_name: Name of the profile
            
        Returns:
            TransformationConfig instance or None if profile not found
        """
        profile = self.load_profile(profile_name)
        if profile:
            return self.create_config_from_dict(profile.config)
        return None
    
    def create_config_from_file(
        self,
        file_path: Path
    ) -> TransformationConfig:
        """
        Create a TransformationConfig from a file.
        
        Args:
            file_path: Path to configuration file (JSON or YAML)
            
        Returns:
            TransformationConfig instance
        """
        file_path = Path(file_path)
        content = file_path.read_text()
        
        if file_path.suffix in ['.yaml', '.yml']:
            config_dict = yaml.safe_load(content)
        else:
            config_dict = json.loads(content)
        
        return self.create_config_from_dict(config_dict)
    
    def export_config(
        self,
        config: TransformationConfig,
        file_path: Path,
        format: str = "json"
    ) -> bool:
        """
        Export a configuration to a file.
        
        Args:
            config: TransformationConfig to export
            file_path: Path to save the configuration
            format: Export format ("json" or "yaml")
            
        Returns:
            True if exported successfully
        """
        try:
            file_path = Path(file_path)
            
            if format == "yaml":
                content = yaml.dump(config.config, default_flow_style=False)
            else:
                content = json.dumps(config.config, indent=2)
            
            file_path.write_text(content)
            return True
        except Exception:
            return False
    
    def validate_config(
        self,
        config_dict: Dict[str, Any]
    ) -> Tuple[bool, List[str]]:
        """
        Validate a configuration dictionary.
        
        Args:
            config_dict: Configuration to validate
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Check for required sections
        if "rules" not in config_dict:
            errors.append("Missing 'rules' section")
        
        # Check rule configurations
        if "rules" in config_dict:
            for rule_id, rule_config in config_dict["rules"].items():
                if not isinstance(rule_config, dict):
                    errors.append(f"Rule '{rule_id}' config must be a dictionary")
                elif "enabled" in rule_config:
                    if not isinstance(rule_config["enabled"], bool):
                        errors.append(f"Rule '{rule_id}' 'enabled' must be boolean")
        
        # Check output configuration
        if "output" in config_dict:
            output = config_dict["output"]
            if not isinstance(output, dict):
                errors.append("'output' section must be a dictionary")
            else:
                if "format" in output:
                    if output["format"] not in ["json", "yaml"]:
                        errors.append("Output format must be 'json' or 'yaml'")
                
                if "indent" in output:
                    if not isinstance(output["indent"], int) or output["indent"] < 0:
                        errors.append("Output indent must be a non-negative integer")
        
        return len(errors) == 0, errors
    
    def merge_configs(
        self,
        base_config: Dict[str, Any],
        override_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Merge two configuration dictionaries.
        
        Args:
            base_config: Base configuration
            override_config: Configuration to override with
            
        Returns:
            Merged configuration
        """
        result = deepcopy(base_config)
        self._deep_merge(result, override_config)
        return result
    
    def _deep_merge(self, base: Dict, override: Dict):
        """
        Deep merge override into base dictionary.
        
        Args:
            base: Base dictionary (modified in place)
            override: Override dictionary
        """
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value
    
    def get_rule_defaults(self, rule_id: str) -> Dict[str, Any]:
        """
        Get default configuration for a specific rule.
        
        Args:
            rule_id: Rule identifier
            
        Returns:
            Default configuration for the rule
        """
        defaults = {
            "class_to_object": {
                "enabled": True,
                "include_uri": False
            },
            "class_hierarchy": {
                "enabled": True,
                "use_allOf": True
            },
            "class_restrictions": {
                "enabled": True,
                "strict_cardinality": False
            },
            "object_property": {
                "enabled": True,
                "reference_format": "$ref"
            },
            "datatype_property": {
                "enabled": True,
                "type_mapping": "strict"
            },
            "property_cardinality": {
                "enabled": True,
                "use_minItems": True,
                "use_maxItems": True
            },
            "labels_to_titles": {
                "enabled": True,
                "language": "en",
                "fallback_to_uri": True
            },
            "comments_to_descriptions": {
                "enabled": True,
                "language": "en",
                "max_length": None
            },
            "enumeration_to_enum": {
                "enabled": True,
                "sort_values": False
            },
            "union_to_anyOf": {
                "enabled": True
            },
            "intersection_to_allOf": {
                "enabled": True
            },
            "disjoint_classes": {
                "enabled": True,
                "use_oneOf": True
            },
            "ontology_metadata": {
                "enabled": True,
                "include_version": True,
                "include_authors": True
            },
            "thing_with_uri": {
                "enabled": False,
                "uri_property": "@id"
            }
        }
        
        return defaults.get(rule_id, {"enabled": True})
    
    def create_web_session_config(
        self,
        session_id: str,
        base_config: Optional[Dict[str, Any]] = None
    ) -> TransformationConfig:
        """
        Create a configuration for a web session.
        
        Args:
            session_id: Web session identifier
            base_config: Base configuration to use
            
        Returns:
            TransformationConfig for the session
        """
        # Start with base or default config
        config_dict = base_config or self.default_config
        
        # Add session-specific metadata
        config_dict["session"] = {
            "id": session_id,
            "created_at": self._get_timestamp()
        }
        
        return self.create_config_from_dict(config_dict)
    
    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        from datetime import datetime
        return datetime.utcnow().isoformat()


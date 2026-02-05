"""
Configuration for JSON Schema to OWL transformation.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional


@dataclass
class JsonSchema2OwlConfig:
    """Configuration for the schema2owl transformer."""

    base_uri: str = "http://example.org/ns#"
    namespace_prefix: str = "ns"
    ontology_title: Optional[str] = None
    ontology_comment: Optional[str] = None
    enabled_rule_ids: Optional[List[str]] = None  # None = all enabled
    rule_options: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    # Naming: 'pascal', 'camel', 'as_is'
    class_naming: str = "pascal"
    property_naming: str = "as_is"

    def is_rule_enabled(self, rule_id: str) -> bool:
        if self.enabled_rule_ids is None:
            return True
        return rule_id in self.enabled_rule_ids

    def get_rule_option(self, rule_id: str, key: str, default: Any = None) -> Any:
        opts = self.rule_options.get(rule_id, {})
        return opts.get(key, default)

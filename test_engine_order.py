#!/usr/bin/env python3
"""Debug the order of rule processing and property assignment."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from owl2jsonschema import TransformationEngine, TransformationConfig, OntologyParser
from owl2jsonschema.builder import SchemaBuilder
import json

# Monkey patch the builder to log operations
original_add_definition = SchemaBuilder.add_definition
original_add_property_to_class = SchemaBuilder.add_property_to_class

def logged_add_definition(self, name, schema):
    print(f"[ADD_DEF] {name}")
    if name == "RollingStock":
        print(f"  Schema keys: {list(schema.keys())}")
    return original_add_definition(self, name, schema)

def logged_add_property_to_class(self, class_name, property_name, property_schema):
    print(f"[ADD_PROP] {property_name} -> {class_name}")
    clean_name = self._clean_definition_name(class_name)
    if clean_name not in self.definitions:
        print(f"  WARNING: Class {clean_name} not in definitions yet!")
    return original_add_property_to_class(self, class_name, property_name, property_schema)

SchemaBuilder.add_definition = logged_add_definition
SchemaBuilder.add_property_to_class = logged_add_property_to_class

# Also monkey patch engine's _process_rule_result
from owl2jsonschema.engine import TransformationEngine as OrigEngine
original_process = OrigEngine._process_rule_result

def logged_process_rule_result(self, rule_id, result):
    print(f"\n[RULE] Processing {rule_id}")
    if rule_id == "disjoint_classes":
        print(f"  Disjoint result: {json.dumps(result, indent=2)[:500]}")
    return original_process(self, rule_id, result)

OrigEngine._process_rule_result = logged_process_rule_result

def test_engine_order():
    """Test the order of rule processing."""
    
    test_file = Path("Documentation/test ontology for OWL to JSON schema transformation.ttl")
    
    print("=" * 80)
    print("Testing Engine Processing Order")
    print("=" * 80)
    print()
    
    # Parse ontology
    parser = OntologyParser()
    ontology = parser.parse(str(test_file))
    
    # Create configuration - minimal set of rules
    config_dict = {
        "rules": {
            "class_to_object": {"enabled": True},
            "object_property": {"enabled": True},
            "disjoint_classes": {"enabled": True, "options": {"enforcement": "oneOf"}},
        },
        "output": {
            "include_uri": False,
            "use_arrays": True
        }
    }
    
    config = TransformationConfig(config_dict)
    engine = TransformationEngine(config)
    
    print("Enabled rules:", engine.get_enabled_rules())
    print()
    
    result = engine.transform(ontology)
    
    print("\n" + "=" * 80)
    print("Final Result for RollingStock")
    print("=" * 80)
    
    if "definitions" in result and "RollingStock" in result["definitions"]:
        rolling_stock = result["definitions"]["RollingStock"]
        print(json.dumps(rolling_stock, indent=2))
        
        # Check for properties
        all_props = []
        if "properties" in rolling_stock:
            all_props.extend(rolling_stock["properties"].keys())
        if "allOf" in rolling_stock:
            for item in rolling_stock["allOf"]:
                if "properties" in item:
                    all_props.extend(item["properties"].keys())
        
        print(f"\nAll properties found: {all_props}")
        if "partOf" not in all_props:
            print("❌ partOf is missing!")
        else:
            print("✅ partOf is present")

if __name__ == "__main__":
    test_engine_order()
#!/usr/bin/env python3
"""
Test with GUI default configuration to reproduce the missing partOf issue.
"""

import json
from pathlib import Path
from src.owl2jsonschema import TransformationEngine, TransformationConfig, OntologyParser
from src.owl2jsonschema_gui.main_window import RulesConfigDialog

def test_with_default_config():
    """Test with the same default configuration as the GUI."""
    
    # Get the default configuration from the GUI dialog
    dialog = RulesConfigDialog(None)
    default_config = dialog.get_default_config()
    
    print("Default GUI Configuration:")
    print("=" * 80)
    for rule_id, rule_settings in default_config.items():
        if rule_settings.get("enabled", False):
            print(f"✓ {rule_id}: {rule_settings.get('name', rule_id)}")
    
    # Parse the ontology
    test_file = Path("Documentation/test ontology for OWL to JSON schema transformation.ttl")
    parser = OntologyParser()
    ontology = parser.parse(str(test_file))
    
    print(f"\n\nOntology Properties:")
    print("=" * 80)
    for prop in ontology.object_properties:
        prop_name = prop.uri.split('#')[-1] if '#' in prop.uri else prop.uri
        print(f"\n{prop_name}:")
        print(f"  Domain: {prop.domain}")
        print(f"  Range: {prop.range}")
        print(f"  Inverse: {prop.inverse_of}")
    
    # Build configuration matching GUI defaults
    rules_config = {}
    for rule_id, rule_settings in default_config.items():
        rules_config[rule_id] = {"enabled": rule_settings.get("enabled", False)}
    
    config = {
        "rules": rules_config,
        "output": {
            "include_uri": False,  # GUI default
            "use_arrays": True
        }
    }
    
    # Transform
    engine = TransformationEngine(TransformationConfig(config))
    schema = engine.transform(ontology)
    
    print(f"\n\nProperties in Generated Schema:")
    print("=" * 80)
    
    definitions = schema.get("definitions", {})
    
    # Check each class for properties
    for class_name, class_schema in definitions.items():
        if class_name == "_Thing":
            continue
            
        # Collect all properties
        properties = {}
        if "properties" in class_schema:
            properties.update(class_schema["properties"])
        if "allOf" in class_schema:
            for item in class_schema["allOf"]:
                if isinstance(item, dict) and "properties" in item:
                    properties.update(item["properties"])
        
        if properties:
            print(f"\n{class_name}:")
            for prop_name in properties:
                print(f"  - {prop_name}")
    
    # Specific check for partOf
    print(f"\n\nChecking for 'partOf' property:")
    print("=" * 80)
    
    partof_found = False
    for class_name, class_schema in definitions.items():
        # Check in all levels
        if "properties" in class_schema and "partOf" in class_schema["properties"]:
            partof_found = True
            print(f"✓ Found in {class_name} (direct)")
        if "allOf" in class_schema:
            for item in class_schema["allOf"]:
                if isinstance(item, dict) and "properties" in item and "partOf" in item["properties"]:
                    partof_found = True
                    print(f"✓ Found in {class_name} (in allOf)")
    
    if not partof_found:
        print("✗ 'partOf' NOT FOUND in schema!")
        print("\nPossible reason: partOf has no explicit domain, relies on inverse inference")
        print("The ObjectPropertyRule might need domain inference from inverse properties")
    
    # Save the schema for inspection
    output_file = Path("test_output/gui_default_schema.json")
    with open(output_file, 'w') as f:
        json.dump(schema, f, indent=2)
    print(f"\nSchema saved to: {output_file}")

if __name__ == "__main__":
    test_with_default_config()
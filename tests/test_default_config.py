#!/usr/bin/env python3
"""
Test with default configuration to reproduce the missing partOf issue.
"""

import json
from pathlib import Path
from owl2jsonschema import TransformationEngine, TransformationConfig, OntologyParser

def test_with_default_config():
    """Test with default configuration."""
    
    # Use default configuration (all rules enabled by default)
    print("Testing with default configuration (all rules enabled)")
    print("=" * 80)
    
    # Parse the ontology
    test_file = Path("Documentation/test ontology for OWL to JSON schema transformation.ttl")
    parser = OntologyParser()
    ontology = parser.parse(str(test_file))
    
    print(f"\nObject Properties in Ontology:")
    print("-" * 40)
    for prop in ontology.object_properties:
        prop_name = prop.uri.split('#')[-1] if '#' in prop.uri else prop.uri
        domain = [d.split('#')[-1] for d in prop.domain] if prop.domain else []
        print(f"{prop_name}:")
        print(f"  Domain: {domain if domain else 'None (no explicit domain)'}")
        if prop.inverse_of:
            inverse_name = prop.inverse_of.split('#')[-1] if '#' in prop.inverse_of else prop.inverse_of
            print(f"  Inverse: {inverse_name}")
    
    # Transform with default config
    config = TransformationConfig()  # Uses defaults
    engine = TransformationEngine(config)
    schema = engine.transform(ontology)
    
    print(f"\n\nProperties in Generated Schema:")
    print("=" * 80)
    
    definitions = schema.get("definitions", {})
    
    # Check each class for properties
    all_properties = {}
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
                all_properties[prop_name] = class_name
    
    # Check for missing properties
    print(f"\n\nProperty Assignment Check:")
    print("=" * 80)
    
    expected_properties = ["composedOf", "partOf", "ofType", "creationDate"]
    for prop in expected_properties:
        if prop in all_properties:
            print(f"✓ '{prop}' found in {all_properties[prop]}")
        else:
            print(f"✗ '{prop}' NOT FOUND")
    
    # Diagnose partOf issue
    if "partOf" not in all_properties:
        print("\n\nDiagnosing missing 'partOf':")
        print("-" * 40)
        print("partOf has no explicit domain in the OWL.")
        print("It's defined as inverse of composedOf.")
        print("composedOf has range: RollingStock")
        print("Therefore, partOf should be inferred to have domain: RollingStock")
        print("\nChecking if domain inference from inverse is working...")
        
        # Check if the ObjectPropertyRule is inferring domain from inverse
        for prop in ontology.object_properties:
            if 'partOf' in prop.uri:
                print(f"\npartOf property in ontology model:")
                print(f"  URI: {prop.uri}")
                print(f"  Domain: {prop.domain}")
                print(f"  Range: {prop.range}")
                print(f"  Inverse: {prop.inverse_of}")
                
                if not prop.domain:
                    print("\n⚠️ ISSUE: partOf has no domain!")
                    print("The ObjectPropertyRule needs to infer domain from inverse relationship.")
    
    # Save for inspection
    output_file = Path("test_output/default_config_schema.json")
    with open(output_file, 'w') as f:
        json.dump(schema, f, indent=2)
    print(f"\nSchema saved to: {output_file}")

if __name__ == "__main__":
    test_with_default_config()
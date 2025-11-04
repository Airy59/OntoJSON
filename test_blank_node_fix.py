#!/usr/bin/env python3
"""
Test script to verify blank node handling in property restrictions.

This tests that when a restriction uses an anonymous class expression (blank node) like:
    isSettingFor only ('Intermodal Transport Unit' or Wagon)

The system properly expands the union inline as a oneOf construct instead of 
creating an undefined reference.
"""

import json
from src.owl2jsonschema.parser import OntologyParser
from src.owl2jsonschema.engine import TransformationEngine

def test_blank_node_union():
    """Test that union expressions in restrictions are expanded inline."""
    print("Testing blank node union handling...")
    
    # Parse the test ontology
    parser = OntologyParser()
    ontology = parser.parse("test_blank_node_union.ttl")
    
    print(f"\nParsed ontology with {len(ontology.classes)} classes")
    
    # Find the SpecialSetting class
    special_setting = None
    for cls in ontology.classes:
        if cls.uri.endswith("SpecialSetting"):
            special_setting = cls
            break
    
    if not special_setting:
        print("ERROR: SpecialSetting class not found!")
        return False
    
    print(f"\nFound SpecialSetting class with {len(special_setting.restrictions)} restrictions")
    
    # Check restrictions
    for restriction in special_setting.restrictions:
        print(f"\nRestriction on property: {restriction.property_uri}")
        print(f"  Type: {restriction.restriction_type}")
        print(f"  Filler: {restriction.filler}")
        
        # Check if filler is a complex expression
        if isinstance(restriction.filler, dict):
            if "unionOf" in restriction.filler:
                print(f"  ✓ Union detected with {len(restriction.filler['unionOf'])} classes:")
                for class_uri in restriction.filler['unionOf']:
                    print(f"    - {class_uri}")
            elif "intersectionOf" in restriction.filler:
                print(f"  ✓ Intersection detected with {len(restriction.filler['intersectionOf'])} classes:")
                for class_uri in restriction.filler['intersectionOf']:
                    print(f"    - {class_uri}")
    
    # Build the JSON Schema
    print("\n" + "="*60)
    print("Building JSON Schema...")
    print("="*60)
    
    engine = TransformationEngine()
    schema = engine.transform(ontology)
    
    # Pretty print the schema
    print("\nGenerated JSON Schema:")
    print(json.dumps(schema, indent=2))
    
    # Verify the schema structure
    print("\n" + "="*60)
    print("Verification:")
    print("="*60)
    
    if "definitions" not in schema:
        print("ERROR: No definitions in schema!")
        return False
    
    if "SpecialSetting" not in schema["definitions"]:
        print("ERROR: SpecialSetting not in definitions!")
        return False
    
    special_setting_schema = schema["definitions"]["SpecialSetting"]
    print(f"\nSpecialSetting schema keys: {list(special_setting_schema.keys())}")
    
    # Check if isSettingFor property exists
    if "properties" in special_setting_schema:
        props = special_setting_schema["properties"]
        print(f"Properties in SpecialSetting: {list(props.keys())}")
        
        if "isSettingFor" in props:
            setting_prop = props["isSettingFor"]
            print(f"\nisSettingFor property schema:")
            print(json.dumps(setting_prop, indent=2))
            
            # Check that it's an array with items that have oneOf
            if "type" in setting_prop and setting_prop["type"] == "array":
                items = setting_prop.get("items", {})
                if "oneOf" in items:
                    print("\n✓ SUCCESS: Union is properly expanded inline as oneOf!")
                    print(f"  Number of options in oneOf: {len(items['oneOf'])}")
                    
                    # Verify the references
                    for i, option in enumerate(items['oneOf']):
                        print(f"\n  Option {i+1}:")
                        print(f"    {json.dumps(option, indent=6)}")
                    
                    # Check that we don't have any undefined blank node references
                    schema_str = json.dumps(schema)
                    if "#/definitions/n" in schema_str and "b" in schema_str:
                        # Look for patterns like n81deb6fe...
                        print("\n⚠ WARNING: Possible blank node references still present")
                        return False
                    
                    return True
                else:
                    print("\n✗ FAILED: No oneOf construct found in items")
                    return False
            else:
                print(f"\n✗ FAILED: Expected array type, got: {setting_prop.get('type', 'none')}")
                return False
        else:
            print("\n✗ FAILED: isSettingFor property not found")
            return False
    else:
        print("\n✗ FAILED: No properties in SpecialSetting")
        return False

if __name__ == "__main__":
    try:
        success = test_blank_node_union()
        if success:
            print("\n" + "="*60)
            print("✓ All tests PASSED!")
            print("="*60)
            exit(0)
        else:
            print("\n" + "="*60)
            print("✗ Tests FAILED")
            print("="*60)
            exit(1)
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
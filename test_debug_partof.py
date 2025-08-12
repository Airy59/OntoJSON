#!/usr/bin/env python3
"""Debug why partOf is not appearing in the schema."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from owl2jsonschema import TransformationEngine, TransformationConfig, OntologyParser
from owl2jsonschema.rules.property_rules import ObjectPropertyRule
import json

def debug_partof():
    """Debug why partOf is not appearing."""
    
    test_file = Path("Documentation/test ontology for OWL to JSON schema transformation.ttl")
    
    print("=" * 80)
    print("Debugging partOf property")
    print("=" * 80)
    print()
    
    # Parse ontology
    parser = OntologyParser()
    ontology = parser.parse(str(test_file))
    
    # Find partOf property
    partof_prop = None
    composedof_prop = None
    
    for prop in ontology.object_properties:
        if 'partOf' in prop.uri:
            partof_prop = prop
        if 'composedOf' in prop.uri:
            composedof_prop = prop
    
    if partof_prop:
        print("Found partOf property:")
        print(f"  URI: {partof_prop.uri}")
        print(f"  Domain: {partof_prop.domain}")
        print(f"  Range: {partof_prop.range}")
        print(f"  Inverse of: {partof_prop.inverse_of}")
        print(f"  Functional: {partof_prop.functional}")
        print()
    else:
        print("partOf property not found!")
        print()
    
    if composedof_prop:
        print("Found composedOf property:")
        print(f"  URI: {composedof_prop.uri}")
        print(f"  Domain: {composedof_prop.domain}")
        print(f"  Range: {composedof_prop.range}")
        print(f"  Inverse of: {composedof_prop.inverse_of}")
        print(f"  Functional: {composedof_prop.functional}")
        print()
    
    # Create a test rule and process partOf
    config = {"enabled": True, "options": {"language": "en", "use_arrays": True}}
    rule = ObjectPropertyRule("object_property", config)
    
    # Process the ontology
    results = rule.visit_ontology(ontology)
    
    print("ObjectPropertyRule results:")
    if results:
        partof_found = False
        for result in results:
            if 'partOf' in str(result):
                print(f"  Found partOf result: {json.dumps(result, indent=2)}")
                partof_found = True
        if not partof_found:
            print("  No partOf in results")
            print(f"  Total results: {len(results)}")
            for i, result in enumerate(results):
                if 'property' in result:
                    prop_info = result.get('property', {})
                    prop_name = prop_info.get('name', 'unknown')
                    print(f"  Result {i}: property={prop_name}, class={result.get('class', 'unknown')}")
    else:
        print("  No results from ObjectPropertyRule")
    print()
    
    # Now test with full transformation
    print("=" * 80)
    print("Full transformation with default config")
    print("=" * 80)
    
    config_dict = {
        "rules": {
            "object_property": {"enabled": True},
            "class_to_object": {"enabled": True},
            "class_hierarchy": {"enabled": True},
            "class_restrictions": {"enabled": True},
        },
        "output": {
            "include_uri": False,
            "use_arrays": True
        }
    }
    
    config = TransformationConfig(config_dict)
    engine = TransformationEngine(config)
    result = engine.transform(ontology)
    
    # Check for partOf in the result
    definitions = result.get('definitions', {})
    found_partof = False
    
    for class_name, class_def in definitions.items():
        if 'properties' in class_def:
            if 'partOf' in class_def['properties']:
                print(f"✓ Found partOf in {class_name}")
                print(f"  Schema: {json.dumps(class_def['properties']['partOf'], indent=4)}")
                found_partof = True
            
            # Also check allOf sections
            if 'allOf' in class_def:
                for allof_item in class_def['allOf']:
                    if 'properties' in allof_item and 'partOf' in allof_item['properties']:
                        print(f"✓ Found partOf in {class_name} (in allOf)")
                        print(f"  Schema: {json.dumps(allof_item['properties']['partOf'], indent=4)}")
                        found_partof = True
    
    if not found_partof:
        print("✗ partOf not found in any class")
        
        # Print all properties found
        print("\nAll properties found:")
        for class_name, class_def in definitions.items():
            all_props = []
            
            # Direct properties
            if 'properties' in class_def:
                all_props.extend(class_def['properties'].keys())
            
            # Properties in allOf
            if 'allOf' in class_def:
                for allof_item in class_def['allOf']:
                    if 'properties' in allof_item:
                        all_props.extend(allof_item['properties'].keys())
            
            if all_props:
                print(f"  {class_name}: {', '.join(all_props)}")

if __name__ == "__main__":
    debug_partof()
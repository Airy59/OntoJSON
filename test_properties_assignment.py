#!/usr/bin/env python3
"""
Test script to verify that properties are assigned to the correct classes.
"""

import json
from pathlib import Path
from src.owl2jsonschema import TransformationEngine, TransformationConfig, OntologyParser

def check_properties():
    """Check property assignments in the generated schema."""
    
    # Parse the ontology
    test_file = Path("Documentation/test ontology for OWL to JSON schema transformation.ttl")
    parser = OntologyParser()
    ontology = parser.parse(str(test_file))
    
    print("Object Properties in Ontology:")
    print("=" * 80)
    for prop in ontology.object_properties:
        prop_name = prop.uri.split('#')[-1] if '#' in prop.uri else prop.uri
        domain = [d.split('#')[-1] if '#' in d else d for d in prop.domain] if prop.domain else ["No domain"]
        range_cls = [r.split('#')[-1] if '#' in r else r for r in prop.range] if prop.range else ["No range"]
        print(f"\n{prop_name}:")
        print(f"  Domain: {', '.join(domain)}")
        print(f"  Range: {', '.join(range_cls)}")
        print(f"  Functional: {prop.functional}")
        if prop.inverse_of:
            inverse_name = prop.inverse_of.split('#')[-1] if '#' in prop.inverse_of else prop.inverse_of
            print(f"  Inverse of: {inverse_name}")
    
    # Transform to JSON Schema
    config = TransformationConfig()
    engine = TransformationEngine(config)
    schema = engine.transform(ontology)
    
    print("\n\nProperties in Generated JSON Schema:")
    print("=" * 80)
    
    definitions = schema.get("definitions", {})
    
    # Check each class for properties
    for class_name, class_schema in definitions.items():
        if class_name == "_Thing":
            continue
            
        # Collect all properties (handling allOf structure)
        properties = {}
        
        # Check direct properties
        if "properties" in class_schema:
            properties.update(class_schema["properties"])
        
        # Check properties in allOf structures
        if "allOf" in class_schema:
            for item in class_schema["allOf"]:
                if isinstance(item, dict) and "properties" in item:
                    properties.update(item["properties"])
        
        if properties:
            print(f"\n{class_name}:")
            for prop_name in properties:
                print(f"  - {prop_name}")
    
    # Check specifically for partOf and composedOf
    print("\n\nSpecific Property Check:")
    print("=" * 80)
    
    # Check partOf
    partof_found = False
    partof_location = []
    for class_name, class_schema in definitions.items():
        # Check in all levels of the schema
        if "properties" in class_schema and "partOf" in class_schema["properties"]:
            partof_found = True
            partof_location.append(class_name)
        if "allOf" in class_schema:
            for item in class_schema["allOf"]:
                if isinstance(item, dict) and "properties" in item and "partOf" in item["properties"]:
                    partof_found = True
                    partof_location.append(class_name)
    
    if partof_found:
        print(f"✓ 'partOf' property found in: {', '.join(set(partof_location))}")
    else:
        print("✗ 'partOf' property NOT FOUND")
    
    # Check composedOf
    composedof_found = False
    composedof_location = []
    for class_name, class_schema in definitions.items():
        # Check in all levels of the schema
        if "properties" in class_schema and "composedOf" in class_schema["properties"]:
            composedof_found = True
            composedof_location.append(class_name)
        if "allOf" in class_schema:
            for item in class_schema["allOf"]:
                if isinstance(item, dict) and "properties" in item and "composedOf" in item["properties"]:
                    composedof_found = True
                    composedof_location.append(class_name)
    
    if composedof_found:
        print(f"✓ 'composedOf' property found in: {', '.join(set(composedof_location))}")
    else:
        print("✗ 'composedOf' property NOT FOUND")
    
    # Check if properties are in the expected classes based on domain
    print("\n\nDomain Verification:")
    print("=" * 80)
    
    # partOf should be in classes that can be part of something
    # Since composedOf has range RollingStock and is inverse of partOf,
    # partOf should have domain RollingStock (or its subclasses)
    if partof_found and "RollingStock" in partof_location:
        print("✓ 'partOf' correctly assigned to RollingStock")
    else:
        print("✗ 'partOf' should be in RollingStock")
    
    # composedOf should be in Formation based on the restriction
    if composedof_found and "Formation" in composedof_location:
        print("✓ 'composedOf' correctly assigned to Formation")
    else:
        print("✗ 'composedOf' should be in Formation")

if __name__ == "__main__":
    check_properties()
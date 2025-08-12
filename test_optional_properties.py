#!/usr/bin/env python3
"""
Test script to verify that properties are optional by default
unless there's an explicit minimum cardinality constraint.
"""

import json
from pathlib import Path
from src.owl2jsonschema import TransformationEngine, TransformationConfig, OntologyParser

def test_property_requirements():
    """Test that properties are handled correctly as optional/required."""
    
    # Test with the main test ontology
    test_file = Path("Documentation/test ontology for OWL to JSON schema transformation.ttl")
    
    if not test_file.exists():
        print(f"Test file not found: {test_file}")
        return
    
    print(f"Testing with: {test_file}")
    print("=" * 80)
    
    # Parse the ontology
    parser = OntologyParser()
    ontology = parser.parse(str(test_file))
    
    print(f"Parsed ontology:")
    print(f"  - Classes: {len(ontology.classes)}")
    print(f"  - Object Properties: {len(ontology.object_properties)}")
    print(f"  - Datatype Properties: {len(ontology.datatype_properties)}")
    print()
    
    # Create transformation engine with default config
    config = TransformationConfig()
    engine = TransformationEngine(config)
    
    # Transform to JSON Schema
    schema = engine.transform(ontology)
    
    # Check each class definition
    print("Checking property requirements in JSON Schema:")
    print("-" * 80)
    
    definitions = schema.get("definitions", {})
    
    for class_name, class_schema in definitions.items():
        print(f"\nClass: {class_name}")
        
        # Handle both direct properties and properties in allOf structures
        properties = {}
        required_props = []
        
        # Check direct properties
        if "properties" in class_schema:
            properties.update(class_schema["properties"])
        if "required" in class_schema:
            required_props.extend(class_schema["required"])
        
        # Check properties in allOf structures
        if "allOf" in class_schema:
            for item in class_schema["allOf"]:
                if isinstance(item, dict):
                    if "properties" in item:
                        properties.update(item["properties"])
                    if "required" in item:
                        required_props.extend(item["required"])
                    # Check nested allOf (for inherited properties)
                    if "allOf" in item:
                        for nested_item in item["allOf"]:
                            if isinstance(nested_item, dict):
                                if "properties" in nested_item:
                                    properties.update(nested_item["properties"])
                                if "required" in nested_item:
                                    required_props.extend(nested_item["required"])
        
        if properties:
            print(f"  Properties:")
            for prop_name, prop_schema in properties.items():
                is_required = prop_name in required_props
                status = "REQUIRED" if is_required else "optional"
                print(f"    - {prop_name}: {status}")
        else:
            print(f"  No properties (excluding inherited)")
        
        # Special check for Vehicle class
        if class_name == "Vehicle":
            print("\n  Special check for Vehicle class:")
            print(f"    - Has 'ofType' property: {'ofType' in properties}")
            print(f"    - 'ofType' is required: {'ofType' in required_props}")
            
            # Check the restriction that makes it required
            if hasattr(ontology, 'classes'):
                for owl_class in ontology.classes:
                    if 'Vehicle' in owl_class.uri:
                        print(f"    - Vehicle class URI: {owl_class.uri}")
                        if owl_class.restrictions:
                            print(f"    - Has {len(owl_class.restrictions)} restrictions:")
                            for r in owl_class.restrictions:
                                print(f"        {r}")
    
    # Save the schema for inspection
    output_file = Path("test_output/property_requirements_schema.json")
    output_file.parent.mkdir(exist_ok=True)
    
    with open(output_file, 'w') as f:
        json.dump(schema, f, indent=2)
    
    print(f"\n\nJSON Schema saved to: {output_file}")
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY:")
    print("-" * 80)
    
    total_classes = len(definitions)
    classes_with_required = sum(1 for d in definitions.values() if "required" in d and d["required"])
    
    print(f"Total classes: {total_classes}")
    print(f"Classes with required properties: {classes_with_required}")
    
    # Check specific expected behaviors
    print("\nExpected behaviors:")
    
    # Vehicle should have ofType as required (due to someValuesFrom restriction)
    vehicle_schema = definitions.get("Vehicle", {})
    
    # Gather required properties from Vehicle schema (checking allOf structure)
    vehicle_required = []
    if "required" in vehicle_schema:
        vehicle_required.extend(vehicle_schema["required"])
    if "allOf" in vehicle_schema:
        for item in vehicle_schema["allOf"]:
            if isinstance(item, dict) and "required" in item:
                vehicle_required.extend(item["required"])
    
    if "ofType" in vehicle_required:
        print("✓ Vehicle.ofType is correctly marked as REQUIRED (due to someValuesFrom)")
    else:
        print("✗ Vehicle.ofType should be REQUIRED but is not")
    
    # Other properties without cardinality restrictions should be optional
    for class_name, class_schema in definitions.items():
        # Gather all properties and required fields from the class schema
        properties = {}
        required_props = []
        
        # Check direct properties
        if "properties" in class_schema:
            properties.update(class_schema["properties"])
        if "required" in class_schema:
            required_props.extend(class_schema["required"])
        
        # Check properties in allOf structures
        if "allOf" in class_schema:
            for item in class_schema["allOf"]:
                if isinstance(item, dict):
                    if "properties" in item:
                        properties.update(item["properties"])
                    if "required" in item:
                        required_props.extend(item["required"])
        
        for prop_name in properties:
            if prop_name in required_props:
                # Check if this is expected
                if not (class_name == "Vehicle" and prop_name == "ofType"):
                    print(f"⚠ {class_name}.{prop_name} is REQUIRED - verify this is intentional")

if __name__ == "__main__":
    test_property_requirements()
#!/usr/bin/env python3
"""
Test script for unionOf range handling in properties.

This script verifies that properties with unionOf ranges are correctly
transformed into JSON Schema with oneOf constructs.
"""

import json
from src.owl2jsonschema.parser import OntologyParser
from src.owl2jsonschema.engine import TransformationEngine

def test_unionof_range():
    """Test that unionOf ranges are correctly transformed."""
    print("Testing unionOf range handling...")
    print("-" * 60)
    
    # Parse the test ontology
    parser = OntologyParser()
    ontology = parser.parse("test_unionof_range.ttl", format="turtle")
    
    print(f"\nParsed ontology: {ontology.uri}")
    print(f"Classes: {len(ontology.classes)}")
    print(f"Object Properties: {len(ontology.object_properties)}")
    
    # Check the hasJourneySection property
    has_journey_section = None
    for prop in ontology.object_properties:
        if "hasJourneySection" in prop.uri:
            has_journey_section = prop
            break
    
    if has_journey_section:
        print(f"\nFound property: {has_journey_section.uri}")
        print(f"  Label: {has_journey_section.label}")
        print(f"  Domain: {has_journey_section.domain}")
        print(f"  Range: {has_journey_section.range}")
        print(f"  Range type: {type(has_journey_section.range[0]) if has_journey_section.range else 'None'}")
        
        if has_journey_section.range and isinstance(has_journey_section.range[0], dict):
            print(f"  Range is a complex expression!")
            print(f"  Range content: {json.dumps(has_journey_section.range[0], indent=2)}")
    else:
        print("\nERROR: Could not find hasJourneySection property!")
        return False
    
    # Transform to JSON Schema
    print("\n" + "=" * 60)
    print("Transforming to JSON Schema...")
    print("=" * 60)
    
    engine = TransformationEngine()
    schema = engine.transform(ontology)
    
    # Save the schema
    output_file = "test_unionof_schema.json"
    with open(output_file, "w") as f:
        json.dump(schema, f, indent=2)
    
    print(f"\nSchema saved to: {output_file}")
    
    # Check the JourneySchedule class for the hasJourneySection property
    if "definitions" in schema and "JourneySchedule" in schema["definitions"]:
        journey_schedule = schema["definitions"]["JourneySchedule"]
        print("\nJourneySchedule definition found!")
        
        # Properties might be in allOf structure
        has_journey_section_schema = None
        if "properties" in journey_schedule:
            has_journey_section_schema = journey_schedule["properties"].get("hasJourneySection")
        elif "allOf" in journey_schedule:
            # Look for properties in allOf items
            for item in journey_schedule["allOf"]:
                if "properties" in item and "hasJourneySection" in item["properties"]:
                    has_journey_section_schema = item["properties"]["hasJourneySection"]
                    break
        
        if has_journey_section_schema:
            print("\nhasJourneySection property schema:")
            print(json.dumps(has_journey_section_schema, indent=2))
            
            # Verify it's an array (non-functional property)
            if has_journey_section_schema.get("type") == "array":
                print("\n✓ Correctly defined as array (non-functional)")
                
                items = has_journey_section_schema.get("items", {})
                
                # Check if items has oneOf with multiple class options
                if "oneOf" in items:
                    print(f"✓ Items has oneOf with {len(items['oneOf'])} options")
                    
                    # Each option should have another oneOf for full object vs @id
                    all_have_nested_oneof = all(
                        "oneOf" in option 
                        for option in items["oneOf"]
                    )
                    
                    if all_have_nested_oneof:
                        print("✓ Each union option has nested oneOf for object/@id pattern")
                        
                        # Extract the class names being referenced
                        class_names = []
                        for option in items["oneOf"]:
                            for nested in option["oneOf"]:
                                if "$ref" in nested:
                                    ref = nested["$ref"]
                                    class_name = ref.split("/")[-1]
                                    if class_name not in class_names:
                                        class_names.append(class_name)
                        
                        print(f"✓ Union references classes: {', '.join(class_names)}")
                        
                        expected_classes = {"JourneySection", "StaticSection"}
                        if set(class_names) == expected_classes:
                            print("✓ CORRECT: All expected classes in union!")
                            return True
                        else:
                            print(f"✗ ERROR: Expected {expected_classes}, got {set(class_names)}")
                            return False
                    else:
                        print("✗ ERROR: Not all union options have nested oneOf")
                        return False
                else:
                    print("✗ ERROR: Items doesn't have oneOf (unionOf not properly handled)")
                    print(f"Items content: {json.dumps(items, indent=2)}")
                    return False
            else:
                print(f"✗ ERROR: Not an array, type is: {has_journey_section_schema.get('type')}")
                return False
        else:
            print("✗ ERROR: hasJourneySection not found in JourneySchedule properties!")
            if "properties" in journey_schedule:
                print(f"Available properties: {list(journey_schedule['properties'].keys())}")
            return False
    else:
        print("✗ ERROR: JourneySchedule not found in schema definitions!")
        if "definitions" in schema:
            print(f"Available definitions: {list(schema['definitions'].keys())}")
        return False

if __name__ == "__main__":
    success = test_unionof_range()
    print("\n" + "=" * 60)
    if success:
        print("TEST PASSED ✓")
    else:
        print("TEST FAILED ✗")
    print("=" * 60)
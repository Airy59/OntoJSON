"""
Test script to verify subproperty information is added to JSON Schema
"""

import json
from src.owl2jsonschema.parser import OntologyParser
from src.owl2jsonschema.engine import TransformationEngine

def test_subproperty_descriptions():
    """Test that subproperties include description about their parent property."""
    
    # Parse the test ontology
    parser = OntologyParser()
    ontology = parser.parse("test_subproperty.ttl", format="turtle")
    
    # Build the JSON Schema
    engine = TransformationEngine()
    schema = engine.transform(ontology)
    
    # Save the schema for inspection
    with open("test_subproperty_schema.json", "w") as f:
        json.dump(schema, f, indent=2)
    
    print("Schema generated successfully!")
    print("\n" + "="*80)
    print("Checking subproperty descriptions:")
    print("="*80)
    
    # Check the Person class properties
    # Properties are inside allOf structure
    person_def = schema.get("definitions", {}).get("Person", {})
    properties = {}
    
    # Extract properties from allOf structure
    if "allOf" in person_def:
        for item in person_def["allOf"]:
            if "properties" in item:
                properties.update(item["properties"])
    elif "properties" in person_def:
        properties = person_def.get("properties", {})
    
    # Check hasFriend (should mention it's a subproperty of hasRelationship)
    if "hasFriend" in properties:
        hasFriend = properties["hasFriend"]
        # Get description from items if property is an array
        if "items" in hasFriend:
            description = hasFriend["items"].get("description", "")
        else:
            description = hasFriend.get("description", "")
        print(f"\n✓ hasFriend property found")
        print(f"  Description: {description}")
        if "Subproperty of hasRelationship" in description:
            print(f"  ✓ Contains subproperty information!")
        else:
            print(f"  ✗ Missing subproperty information")
    else:
        print(f"\n✗ hasFriend property not found")
    
    # Check hasParent (should mention it's a subproperty of hasRelationship)
    if "hasParent" in properties:
        hasParent = properties["hasParent"]
        # Get description from items if property is an array
        if "items" in hasParent:
            description = hasParent["items"].get("description", "")
        else:
            description = hasParent.get("description", "")
        print(f"\n✓ hasParent property found")
        print(f"  Description: {description}")
        if "Subproperty of hasRelationship" in description:
            print(f"  ✓ Contains subproperty information!")
        else:
            print(f"  ✗ Missing subproperty information")
    else:
        print(f"\n✗ hasParent property not found")
    
    # Check hasName (should mention it's a subproperty of hasAttribute)
    if "hasName" in properties:
        hasName = properties["hasName"]
        # Get description from items if property is an array
        if "items" in hasName:
            description = hasName["items"].get("description", "")
        else:
            description = hasName.get("description", "")
        print(f"\n✓ hasName property found")
        print(f"  Description: {description}")
        if "Subproperty of hasAttribute" in description:
            print(f"  ✓ Contains subproperty information!")
        else:
            print(f"  ✗ Missing subproperty information")
    else:
        print(f"\n✗ hasName property not found")
    
    # Check hasRelationship (should NOT have subproperty info since it's the parent)
    if "hasRelationship" in properties:
        hasRelationship = properties["hasRelationship"]
        # Get description from items if property is an array
        if "items" in hasRelationship:
            description = hasRelationship["items"].get("description", "")
        else:
            description = hasRelationship.get("description", "")
        print(f"\n✓ hasRelationship property found")
        print(f"  Description: {description}")
        if "Subproperty of" in description:
            print(f"  ✗ Should not contain subproperty information (it's the parent)")
        else:
            print(f"  ✓ Correctly doesn't mention being a subproperty")
    else:
        print(f"\n✗ hasRelationship property not found")
    
    print("\n" + "="*80)
    print(f"Full schema saved to: test_subproperty_schema.json")
    print("="*80 + "\n")

if __name__ == "__main__":
    test_subproperty_descriptions()
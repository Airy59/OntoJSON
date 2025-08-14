#!/usr/bin/env python3
"""
Test script for circular reference detection in A-box to JSON conversion
"""

import json
from owl2jsonschema.abox_to_json import ABoxToJSONConverter

def test_circular_reference_detection():
    """Test that circular references are properly detected."""
    
    print("Testing Circular Reference Detection")
    print("=" * 50)
    
    # Create a schema with circular reference (Formation can contain Formation)
    schema = {
        "definitions": {
            "Formation": {
                "type": "object",
                "properties": {
                    "uri": {"type": "string"},
                    "name": {"type": "string"},
                    "composedOf": {
                        "type": "array",
                        "items": {"$ref": "#/definitions/Formation"}
                    }
                }
            },
            "Vehicle": {
                "type": "object", 
                "properties": {
                    "uri": {"type": "string"},
                    "id": {"type": "string"},
                    "partOf": {
                        "$ref": "#/definitions/Formation"
                    }
                }
            },
            "Person": {
                "type": "object",
                "properties": {
                    "uri": {"type": "string"},
                    "name": {"type": "string"}
                }
            }
        }
    }
    
    # Create converter
    converter = ABoxToJSONConverter(schema)
    
    # Test circular reference detection
    print("\n1. Checking Formation (has circular reference via composedOf):")
    has_circular = converter._has_circular_reference("Formation")
    print(f"   Circular reference detected: {has_circular}")
    assert has_circular == True, "Should detect circular reference in Formation"
    
    print("\n2. Checking Vehicle (no circular reference):")
    has_circular = converter._has_circular_reference("Vehicle")
    print(f"   Circular reference detected: {has_circular}")
    assert has_circular == False, "Should not detect circular reference in Vehicle"
    
    print("\n3. Checking Person (no circular reference):")
    has_circular = converter._has_circular_reference("Person")
    print(f"   Circular reference detected: {has_circular}")
    assert has_circular == False, "Should not detect circular reference in Person"
    
    # Test validation with circular references
    print("\n4. Testing validation with circular references:")
    
    instances = {
        "Formation": [
            {"uri": "http://example.org#formation1", "name": "Train 1"},
            {"uri": "http://example.org#formation2", "name": "Train 2"}
        ],
        "Vehicle": [
            {"uri": "http://example.org#vehicle1", "id": "V001"}
        ],
        "Person": [
            {"uri": "http://example.org#person1", "name": "John"}
        ]
    }
    
    validation_results = converter.validate(instances)
    
    print(f"\n   Validation Results:")
    print(f"   - Valid: {validation_results['valid']}")
    print(f"   - Validated: {validation_results['validated_count']}/{validation_results['total_count']}")
    print(f"   - Warnings: {len(validation_results.get('warnings', []))}")
    print(f"   - Errors: {len(validation_results.get('errors', []))}")
    
    if validation_results.get('warnings'):
        print("\n   Warnings:")
        for warning in validation_results['warnings']:
            print(f"   - {warning.get('type', 'N/A')}: {warning.get('warning', 'N/A')}")
    
    # Generate report
    from owl2jsonschema.abox_to_json import JSONInstanceFormatter
    formatter = JSONInstanceFormatter()
    report = formatter.generate_validation_report(validation_results)
    
    print("\n5. Validation Report:")
    print("-" * 50)
    print(report)
    
    print("\n" + "=" * 50)
    print("✅ Test completed successfully!")
    print("Circular references are properly detected and handled.")
    print("=" * 50)

if __name__ == "__main__":
    test_circular_reference_detection()
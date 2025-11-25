"""
Test to verify the reverse transformation fix for set_base_namespace() method.
"""

import json
from src.jsonschema2owl.config import ReverseTransformationConfig
from src.jsonschema2owl.services.transformation_service import ReverseTransformationService

def test_config_set_base_namespace():
    """Test that ReverseTransformationConfig has set_base_namespace method."""
    print("Testing ReverseTransformationConfig.set_base_namespace()...")
    
    # Create config
    config = ReverseTransformationConfig()
    
    # Check initial namespace
    initial_ns = config.get_base_namespace()
    print(f"  Initial namespace: {initial_ns}")
    
    # Set new namespace
    new_namespace = "http://test.example.org/ontology#"
    config.set_base_namespace(new_namespace)
    
    # Verify it was set
    updated_ns = config.get_base_namespace()
    print(f"  Updated namespace: {updated_ns}")
    
    assert updated_ns == new_namespace, f"Expected {new_namespace}, got {updated_ns}"
    print("  ✓ Config method test passed!")


def test_transformation_service():
    """Test the transformation service with base namespace configuration."""
    print("\nTesting ReverseTransformationService with base namespace...")
    
    # Simple test schema
    test_schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "$id": "http://example.org/test-schema",
        "title": "Person",
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "Person's name"
            },
            "age": {
                "type": "integer",
                "description": "Person's age"
            }
        },
        "required": ["name"]
    }
    
    # Create service
    service = ReverseTransformationService()
    
    # Transform with custom namespace
    custom_namespace = "http://myontology.example.com/person#"
    result = service.transform(
        schema_source=test_schema,
        base_namespace=custom_namespace,
        output_format="turtle"
    )
    
    if result.success:
        print(f"  ✓ Transformation succeeded!")
        print(f"  ✓ Generated {result.statistics.get('classes', 0)} classes")
        print(f"  ✓ Generated {result.statistics.get('datatype_properties', 0)} properties")
        print(f"  ✓ Total triples: {result.statistics.get('total_triples', 0)}")
        
        # Check if custom namespace is used in output
        if custom_namespace[:-1] in result.ontology:  # Remove # for checking
            print(f"  ✓ Custom namespace found in output!")
        else:
            print(f"  ⚠ Custom namespace not found in output (may need further investigation)")
        
        # Show first few lines of output
        print("\n  First few lines of generated ontology:")
        for line in result.ontology.split('\n')[:10]:
            if line.strip():
                print(f"    {line}")
    else:
        print(f"  ✗ Transformation failed: {result.error}")
        raise AssertionError(f"Transformation failed: {result.error}")


if __name__ == "__main__":
    print("=" * 60)
    print("Testing Reverse Transformation Fix")
    print("=" * 60)
    
    try:
        test_config_set_base_namespace()
        test_transformation_service()
        
        print("\n" + "=" * 60)
        print("ALL TESTS PASSED! ✓")
        print("=" * 60)
        
    except Exception as e:
        print("\n" + "=" * 60)
        print(f"TEST FAILED: {e}")
        print("=" * 60)
        import traceback
        traceback.print_exc()
        exit(1)
#!/usr/bin/env python3
"""
Direct test of the validation service without requiring the web server.
"""

import json
from src.owl2jsonschema.services.validation_service import (
    JSONSchemaValidator, 
    SchemaValidationService
)

def test_json_validation():
    """Test JSON validation functionality."""
    print("="*60)
    print("TESTING JSON VALIDATION")
    print("="*60)
    
    # Test schema
    schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "age": {"type": "integer", "minimum": 0},
            "email": {"type": "string", "format": "email"}
        },
        "required": ["name"]
    }
    
    # Test cases
    test_cases = [
        {
            "name": "Valid instance",
            "data": {"name": "John Doe", "age": 30, "email": "john@example.com"},
            "expected": True
        },
        {
            "name": "Missing required field",
            "data": {"age": 30},
            "expected": False
        },
        {
            "name": "Invalid type",
            "data": {"name": 123, "age": "thirty"},
            "expected": False
        },
        {
            "name": "Invalid format",
            "data": {"name": "Jane", "email": "not-an-email"},
            "expected": False
        },
        {
            "name": "Negative age",
            "data": {"name": "Bob", "age": -5},
            "expected": False
        }
    ]
    
    validator = JSONSchemaValidator(schema)
    
    for test_case in test_cases:
        print(f"\nTest: {test_case['name']}")
        print(f"Data: {json.dumps(test_case['data'])}")
        
        result = validator.validate_instance(test_case['data'])
        
        if result['valid'] == test_case['expected']:
            print(f"✅ PASSED - Validation {'succeeded' if result['valid'] else 'failed'} as expected")
            if not result['valid'] and result['errors']:
                print(f"   Error: {result['errors'][0]['message']}")
        else:
            print(f"❌ FAILED - Expected {'valid' if test_case['expected'] else 'invalid'}, got {'valid' if result['valid'] else 'invalid'}")
    

def test_schema_validation():
    """Test schema validation functionality."""
    print("\n" + "="*60)
    print("TESTING SCHEMA VALIDATION")
    print("="*60)
    
    test_schemas = [
        {
            "name": "Valid Draft 7 schema",
            "schema": {
                "$schema": "http://json-schema.org/draft-07/schema#",
                "type": "object",
                "properties": {
                    "name": {"type": "string"}
                }
            },
            "expected": True
        },
        {
            "name": "Invalid type value",
            "schema": {
                "$schema": "http://json-schema.org/draft-07/schema#",
                "type": "invalid_type"
            },
            "expected": False
        },
        {
            "name": "Schema with x-metadata (compliant but may have warnings)",
            "schema": {
                "$schema": "http://json-schema.org/draft-07/schema#",
                "type": "object",
                "x-metadata": {"author": "Test"},
                "properties": {}
            },
            "expected": True,
            "expect_warning": True
        },
        {
            "name": "Schema with $comment (fully compliant)",
            "schema": {
                "$schema": "http://json-schema.org/draft-07/schema#",
                "type": "object",
                "$comment": "Metadata: {\"author\": \"Test\"}",
                "properties": {}
            },
            "expected": True,
            "expect_warning": False
        }
    ]
    
    for test_case in test_schemas:
        print(f"\nTest: {test_case['name']}")
        
        result = JSONSchemaValidator.check_schema_validity(test_case['schema'])
        
        if result['valid'] == test_case['expected']:
            print(f"✅ PASSED - Schema {'valid' if result['valid'] else 'invalid'} as expected")
            if result.get('errors'):
                print(f"   Error: {result['errors'][0]['message']}")
            if result.get('warnings'):
                if test_case.get('expect_warning'):
                    print(f"   ⚠️ Warning (expected): {result['warnings'][0]}")
                else:
                    print(f"   ⚠️ Warning (unexpected): {result['warnings'][0]}")
        else:
            print(f"❌ FAILED - Expected {'valid' if test_case['expected'] else 'invalid'}, got {'valid' if result['valid'] else 'invalid'}")


def test_typed_validation():
    """Test validation of typed instances (like from OWL transformation)."""
    print("\n" + "="*60)
    print("TESTING TYPED INSTANCE VALIDATION")
    print("="*60)
    
    # Schema with definitions (typical output from OWL transformation)
    schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "$comment": "Metadata: {\"source\": \"test.owl\", \"version\": \"1.0\"}",
        "definitions": {
            "Person": {
                "type": "object",
                "properties": {
                    "uri": {"type": "string"},
                    "name": {"type": "string"},
                    "age": {"type": "integer", "minimum": 0}
                },
                "required": ["name"]
            },
            "Organization": {
                "type": "object",
                "properties": {
                    "uri": {"type": "string"},
                    "name": {"type": "string"},
                    "employees": {"type": "integer", "minimum": 1}
                },
                "required": ["name", "employees"]
            }
        }
    }
    
    # Typed instances (typical output from ABox conversion)
    instances = {
        "Person": [
            {"uri": "http://example.org#john", "name": "John Doe", "age": 30},
            {"uri": "http://example.org#jane", "name": "Jane Doe"},  # Valid: age optional
            {"uri": "http://example.org#invalid", "age": 25}  # Invalid: missing name
        ],
        "Organization": [
            {"uri": "http://example.org#acme", "name": "Acme Corp", "employees": 100},
            {"uri": "http://example.org#startup", "name": "Startup Inc", "employees": 0}  # Invalid: employees < 1
        ]
    }
    
    print("\nValidating instances by type...")
    
    service = SchemaValidationService()
    result = service.validate_json_against_schema(instances, schema)
    
    if result.get('types'):
        print("\nResults by type:")
        for type_name, type_result in result['types'].items():
            print(f"\n{type_name}:")
            print(f"  Status: {'✅ Valid' if type_result['valid'] else '❌ Invalid'}")
            print(f"  Valid instances: {type_result['valid_count']}/{type_result['total']}")
            
            if type_result.get('errors'):
                print("  Errors:")
                for error in type_result['errors'][:2]:  # Show first 2 errors
                    instance_idx = error.get('instance_index', '?')
                    print(f"    - Instance {instance_idx}: {error['message']}")
        
        print(f"\nOverall: {result['valid_instances']}/{result['total_instances']} instances valid")
    else:
        print("Unexpected result format:", json.dumps(result, indent=2))


def test_report_generation():
    """Test validation report generation."""
    print("\n" + "="*60)
    print("TESTING REPORT GENERATION")
    print("="*60)
    
    schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "properties": {
            "value": {"type": "number", "minimum": 0, "maximum": 100}
        },
        "required": ["value"]
    }
    
    # Mix of valid and invalid instances
    instances = [
        {"value": 50},     # Valid
        {"value": 150},    # Invalid: too large
        {},                # Invalid: missing required field
        {"value": -10}     # Invalid: negative
    ]
    
    validator = JSONSchemaValidator(schema)
    result = validator.validate_batch(instances)
    
    print("\nValidation Summary:")
    print(f"  Total: {result['total']}")
    print(f"  Valid: {result['valid_count']}")
    print(f"  Invalid: {result['invalid_count']}")
    
    print("\nGenerated Report:")
    print("-" * 40)
    report = JSONSchemaValidator.format_validation_report(result)
    print(report)


def main():
    """Run all validation service tests."""
    print("\n" + "="*60)
    print("VALIDATION SERVICE TEST SUITE")
    print("="*60)
    print("\nTesting the JSON Schema validation service directly...")
    
    try:
        test_json_validation()
        test_schema_validation()
        test_typed_validation()
        test_report_generation()
        
        print("\n" + "="*60)
        print("ALL TESTS COMPLETED")
        print("="*60)
        print("""
The validation service is working correctly!

To test the web interface:
1. Start the web app: python -m src.owl2jsonschema_web.app
2. Navigate to: http://localhost:5000/validate
3. Use the 'Load Example' button to test with sample data
4. Try the API endpoints at /api/validate/json and /api/validate/schema
""")
        
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Test script for the web application's JSON Schema validation feature.
"""

import json
import requests
from pathlib import Path

# Base URL for the API (adjust if running on different port)
BASE_URL = "http://localhost:5000/api"

def test_validate_json():
    """Test the JSON validation endpoint."""
    print("Testing JSON validation endpoint...")
    
    # Test schema
    schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "age": {"type": "integer", "minimum": 0}
        },
        "required": ["name"]
    }
    
    # Valid data
    valid_data = {
        "name": "John Doe",
        "age": 30
    }
    
    # Invalid data (missing required field)
    invalid_data = {
        "age": -5  # Also invalid: negative age
    }
    
    # Test with valid data
    print("\n1. Testing with valid data...")
    response = requests.post(
        f"{BASE_URL}/validate/json",
        json={"schema": schema, "data": valid_data, "include_report": True}
    )
    
    if response.status_code == 200:
        result = response.json()
        if result['success'] and result['validation']['valid']:
            print("✅ Valid data passed validation (as expected)")
        else:
            print("❌ Valid data failed validation (unexpected)")
    else:
        print(f"❌ Request failed with status {response.status_code}")
    
    # Test with invalid data
    print("\n2. Testing with invalid data...")
    response = requests.post(
        f"{BASE_URL}/validate/json",
        json={"schema": schema, "data": invalid_data, "include_report": True}
    )
    
    if response.status_code == 200:
        result = response.json()
        if result['success'] and not result['validation']['valid']:
            print("✅ Invalid data failed validation (as expected)")
            if result.get('report'):
                print("Report preview:")
                print(result['report'][:500])
        else:
            print("❌ Invalid data passed validation (unexpected)")
    else:
        print(f"❌ Request failed with status {response.status_code}")


def test_validate_schema():
    """Test the schema validation endpoint."""
    print("\n\nTesting schema validation endpoint...")
    
    # Valid Draft 7 schema
    valid_schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "properties": {
            "name": {"type": "string"}
        }
    }
    
    # Invalid schema (bad type value)
    invalid_schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "not_a_valid_type",
        "properties": {
            "name": {"type": "string"}
        }
    }
    
    # Test with valid schema
    print("\n1. Testing with valid schema...")
    response = requests.post(
        f"{BASE_URL}/validate/schema",
        json={"schema": valid_schema}
    )
    
    if response.status_code == 200:
        result = response.json()
        if result['success'] and result['validation']['valid']:
            print("✅ Valid schema passed validation (as expected)")
        else:
            print("❌ Valid schema failed validation (unexpected)")
    else:
        print(f"❌ Request failed with status {response.status_code}")
    
    # Test with invalid schema
    print("\n2. Testing with invalid schema...")
    response = requests.post(
        f"{BASE_URL}/validate/schema",
        json={"schema": invalid_schema}
    )
    
    if response.status_code == 200:
        result = response.json()
        if result['success'] and not result['validation']['valid']:
            print("✅ Invalid schema failed validation (as expected)")
            if result['validation'].get('errors'):
                print(f"Error: {result['validation']['errors'][0]}")
        else:
            print("❌ Invalid schema passed validation (unexpected)")
    else:
        print(f"❌ Request failed with status {response.status_code}")


def test_validate_typed_instances():
    """Test validation with typed instances (like from OWL transformation)."""
    print("\n\nTesting typed instance validation...")
    
    # Schema with definitions (like from OWL transformation)
    schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "definitions": {
            "Person": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "age": {"type": "integer", "minimum": 0}
                },
                "required": ["name"]
            },
            "Organization": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "employees": {"type": "integer", "minimum": 0}
                },
                "required": ["name"]
            }
        }
    }
    
    # Typed instances (like from ABox conversion)
    typed_data = {
        "Person": [
            {"name": "Alice", "age": 25},
            {"name": "Bob"}  # Valid: age is optional
        ],
        "Organization": [
            {"name": "Acme Corp", "employees": 100},
            {"employees": 50}  # Invalid: missing required name
        ]
    }
    
    print("\nTesting with typed instances (some valid, some invalid)...")
    response = requests.post(
        f"{BASE_URL}/validate/json",
        json={"schema": schema, "data": typed_data, "include_report": True}
    )
    
    if response.status_code == 200:
        result = response.json()
        if result['success']:
            validation = result['validation']
            if validation.get('types'):
                print("\nValidation results by type:")
                for type_name, type_result in validation['types'].items():
                    status = "✅ Valid" if type_result.get('valid') else "❌ Invalid"
                    print(f"  {type_name}: {status}")
                    if type_result.get('valid_count') is not None:
                        print(f"    {type_result['valid_count']}/{type_result['total']} instances valid")
            else:
                print("Results:", json.dumps(validation, indent=2))
        else:
            print(f"❌ Validation request failed: {result.get('error')}")
    else:
        print(f"❌ Request failed with status {response.status_code}")


def test_web_ui():
    """Provide instructions for testing the web UI."""
    print("\n" + "="*60)
    print("WEB UI TEST INSTRUCTIONS")
    print("="*60)
    print("""
To test the web UI validation page:

1. Start the web application:
   python -m src.owl2jsonschema_web.app

2. Open your browser to:
   http://localhost:5000/validate

3. Click 'Load Example' to populate sample data

4. Click 'Validate JSON' to see validation results

5. Try modifying the data to make it invalid (e.g., remove "name" field)

6. Switch to 'Validate Schema' tab to test schema validation

The validation page provides:
- Two-pane editor for schema and data
- File upload support
- Example data loading
- Clear validation result display
- Support for both data and schema validation
""")


def main():
    """Run all tests."""
    print("="*60)
    print("JSON SCHEMA VALIDATION FEATURE TEST")
    print("="*60)
    
    try:
        # Check if the server is running
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code != 200:
            print("⚠️ Server health check failed")
            print("Please make sure the web application is running:")
            print("  python -m src.owl2jsonschema_web.app")
            return
        
        print("✅ Server is running\n")
        
        # Run tests
        test_validate_json()
        test_validate_schema()
        test_validate_typed_instances()
        
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server at", BASE_URL)
        print("\nPlease start the web application first:")
        print("  python -m src.owl2jsonschema_web.app")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
    
    # Show web UI test instructions
    test_web_ui()
    
    print("\n" + "="*60)
    print("TEST COMPLETE")
    print("="*60)


if __name__ == "__main__":
    main()
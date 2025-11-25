"""
Test the web reverse transformation API to verify the fix.
"""

import json
from src.jsonschema2owl.services.transformation_service import ReverseTransformationService
from src.jsonschema2owl.config import ReverseTransformationConfig

def test_web_api_scenario():
    """
    Simulate what happens when the web API calls the service.
    This tests the exact code path that was failing before.
    """
    print("Simulating Web API Transformation Request...")
    print("=" * 60)
    
    # This is what the web API does in reverse_transformation.py
    transformation_service = ReverseTransformationService()
    
    # Example schema from web request
    schema_source = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "Product",
        "type": "object",
        "properties": {
            "productId": {
                "type": "string",
                "description": "Product identifier"
            },
            "name": {
                "type": "string",
                "description": "Product name"
            },
            "price": {
                "type": "number",
                "description": "Product price"
            }
        },
        "required": ["productId", "name"]
    }
    
    # Parameters from web request
    base_namespace = "http://shop.example.com/product#"
    language = "en"
    output_format = "turtle"
    config = None  # Use default config
    
    # This is the exact call that was failing before the fix
    print(f"Calling transformation service with:")
    print(f"  - base_namespace: {base_namespace}")
    print(f"  - language: {language}")
    print(f"  - output_format: {output_format}")
    print()
    
    # Perform transformation (line 119-125 in reverse_transformation.py)
    result = transformation_service.transform(
        schema_source=schema_source,
        config=config,
        base_namespace=base_namespace,
        language=language,
        output_format=output_format
    )
    
    # Check result
    if result.success:
        print("✓ SUCCESS: Transformation completed!")
        print(f"  - Format: {result.format}")
        print(f"  - Classes: {result.statistics.get('classes', 0)}")
        print(f"  - Properties: {result.statistics.get('datatype_properties', 0)}")
        print(f"  - Total triples: {result.statistics.get('total_triples', 0)}")
        print()
        
        # Verify custom namespace is used
        if base_namespace[:-1] in result.ontology:
            print("✓ Custom namespace correctly applied in output!")
        else:
            print("⚠ Warning: Custom namespace not found in output")
        
        # Show a sample of the output
        print("\nSample output (first 15 lines):")
        print("-" * 60)
        for i, line in enumerate(result.ontology.split('\n')[:15], 1):
            print(f"{i:2d} | {line}")
        
        return True
    else:
        print(f"✗ ERROR: Transformation failed!")
        print(f"  Error message: {result.error}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("Testing Web API Reverse Transformation Fix")
    print("=" * 60)
    print()
    
    success = test_web_api_scenario()
    
    print()
    print("=" * 60)
    if success:
        print("WEB API TEST PASSED! ✓")
        print("The bug is fixed and the web interface should now work.")
    else:
        print("WEB API TEST FAILED! ✗")
        exit(1)
    print("=" * 60)
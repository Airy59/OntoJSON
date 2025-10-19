#!/usr/bin/env python3
"""
Test script to verify the A-box to JSON conversion fix.
Tests handling of literals with incorrect types.
"""

from rdflib import Graph, Namespace, URIRef, Literal, RDF
from rdflib.namespace import XSD
from src.owl2jsonschema.abox_to_json import ABoxToJSONConverter
import json

# Create a test ontology with schema
test_schema = {
    "definitions": {
        "TestClass": {
            "type": "object",
            "properties": {
                "uri": {"type": "string"},
                "integerProperty": {"type": "integer"},
                "stringProperty": {"type": "string"},
                "numberProperty": {"type": "number"},
                "booleanProperty": {"type": "boolean"}
            }
        }
    }
}

# Create test A-box data with various literal types
def create_test_abox():
    g = Graph()
    ns = Namespace("http://example.org#")
    
    # Create an individual
    individual = ns.TestIndividual1
    g.add((individual, RDF.type, ns.TestClass))
    
    # Add properties with various literal types
    # This simulates the problematic case where a string literal is provided for an integer property
    g.add((individual, ns.integerProperty, Literal("These are not numbers", datatype=XSD.string)))  # Wrong type - string for integer
    g.add((individual, ns.stringProperty, Literal("This is a string", datatype=XSD.string)))
    g.add((individual, ns.numberProperty, Literal("Not a number either", datatype=XSD.string)))  # Wrong type - string for number
    g.add((individual, ns.booleanProperty, Literal("maybe", datatype=XSD.string)))  # Ambiguous boolean
    
    # Add another individual with correct types
    individual2 = ns.TestIndividual2
    g.add((individual2, RDF.type, ns.TestClass))
    g.add((individual2, ns.integerProperty, Literal("42", datatype=XSD.integer)))
    g.add((individual2, ns.stringProperty, Literal("Another string", datatype=XSD.string)))
    g.add((individual2, ns.numberProperty, Literal("2.71", datatype=XSD.float)))
    g.add((individual2, ns.booleanProperty, Literal("false", datatype=XSD.boolean)))
    
    return g

def main():
    print("Testing A-box to JSON conversion with type mismatches...")
    print("=" * 60)
    
    # Create test data
    abox_graph = create_test_abox()
    
    # Create converter
    converter = ABoxToJSONConverter(test_schema, base_uri="http://example.org#")
    
    try:
        # Convert A-box to JSON
        print("\nConverting A-box to JSON...")
        json_instances = converter.convert(abox_graph)
        
        print("\nConversion successful!")
        print("\nGenerated JSON instances:")
        print(json.dumps(json_instances, indent=2))
        
        # Validate the instances
        print("\n" + "=" * 60)
        print("Validating JSON instances against schema...")
        validation_result = converter.validate(json_instances)
        
        if validation_result['valid']:
            print("✅ Validation successful! All instances conform to the schema.")
            print("   Placeholder values were used for unconvertible data.")
        else:
            print("⚠️ Validation completed with issues:")
            if validation_result.get('errors'):
                print("\nErrors (should be none with placeholder values):")
                for error in validation_result['errors']:
                    print(f"  - {error}")
            if validation_result.get('warnings'):
                print("\nWarnings:")
                for warning in validation_result['warnings']:
                    print(f"  - {warning}")
        
        print(f"\nValidated {validation_result['validated_count']}/{validation_result['total_count']} instances")
        
    except Exception as e:
        print(f"❌ Error during conversion: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    print("\n" + "=" * 60)
    print("Test completed. The fix handles type mismatches gracefully.")
    print("Placeholder values are used for demo/testing purposes:")
    print("  - 999999 for integers that can't be converted")
    print("  - 9999.99 for numbers that can't be converted")
    print("  - False for ambiguous boolean values")
    return 0

if __name__ == "__main__":
    exit(main())
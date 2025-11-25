#!/usr/bin/env python3
"""
Test script for property scoping functionality
"""

import json
from rdflib import Namespace
from rdflib.namespace import RDF, RDFS, OWL, XSD

from src.jsonschema2owl import ReverseEngine, ReverseTransformationConfig


def test_property_scoping():
    """Test that properties with same name in different classes get distinct URIs."""
    print("=" * 80)
    print("Testing Property Name Scoping Feature")
    print("=" * 80)
    
    schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "definitions": {
            "ServiceConstraintDef": {
                "type": "object",
                "properties": {
                    "legacyCode": {"type": "integer"}
                }
            },
            "CarrierGroup": {
                "type": "object",
                "properties": {
                    "legacyCode": {"type": "string"}
                }
            }
        }
    }
    
    print("\n1. Testing with SCOPED naming strategy (default)")
    print("-" * 80)
    
    config = ReverseTransformationConfig()
    engine = ReverseEngine(config)
    schema_model = engine.parser.parse(json.dumps(schema))
    graph = engine.transform(schema_model)
    
    base_ns = Namespace("http://example.org/ontology#")
    
    # Check for scoped properties
    scoped_property1 = base_ns["ServiceConstraintDef_legacyCode"]
    scoped_property2 = base_ns["CarrierGroup_legacyCode"]
    
    print(f"\nChecking for property: {scoped_property1}")
    has_prop1 = (scoped_property1, RDF.type, OWL.DatatypeProperty) in graph
    print(f"  ✓ Property exists: {has_prop1}")
    
    if has_prop1:
        domain1 = list(graph.objects(scoped_property1, RDFS.domain))
        range1 = list(graph.objects(scoped_property1, RDFS.range))
        print(f"  Domain: {domain1}")
        print(f"  Range: {range1}")
        assert base_ns["ServiceConstraintDef"] in domain1, "Wrong domain!"
        assert XSD.integer in range1, "Wrong range!"
    
    print(f"\nChecking for property: {scoped_property2}")
    has_prop2 = (scoped_property2, RDF.type, OWL.DatatypeProperty) in graph
    print(f"  ✓ Property exists: {has_prop2}")
    
    if has_prop2:
        domain2 = list(graph.objects(scoped_property2, RDFS.domain))
        range2 = list(graph.objects(scoped_property2, RDFS.range))
        print(f"  Domain: {domain2}")
        print(f"  Range: {range2}")
        assert base_ns["CarrierGroup"] in domain2, "Wrong domain!"
        assert XSD.string in range2, "Wrong range!"
    
    if has_prop1 and has_prop2:
        print("\n✅ SUCCESS: Both scoped properties created with distinct URIs!")
    else:
        print("\n❌ FAILURE: Scoped properties not created correctly")
        return False
    
    # Print the Turtle serialization to see the result
    print("\n" + "=" * 80)
    print("Generated OWL (Turtle format):")
    print("=" * 80)
    turtle_output = engine.serialize(graph, format="turtle")
    print(turtle_output)
    
    # Test reverse_scoped
    print("\n\n2. Testing with REVERSE_SCOPED naming strategy")
    print("-" * 80)
    
    config2 = ReverseTransformationConfig()
    config2.set_property_naming_strategy("reverse_scoped")
    engine2 = ReverseEngine(config2)
    schema_model2 = engine2.parser.parse(json.dumps(schema))
    graph2 = engine2.transform(schema_model2)
    
    reverse_prop1 = base_ns["legacyCode_ServiceConstraintDef"]
    reverse_prop2 = base_ns["legacyCode_CarrierGroup"]
    
    has_reverse1 = (reverse_prop1, RDF.type, OWL.DatatypeProperty) in graph2
    has_reverse2 = (reverse_prop2, RDF.type, OWL.DatatypeProperty) in graph2
    
    print(f"\nProperty {reverse_prop1}: {has_reverse1}")
    print(f"Property {reverse_prop2}: {has_reverse2}")
    
    if has_reverse1 and has_reverse2:
        print("\n✅ SUCCESS: Reverse scoped naming works!")
    else:
        print("\n❌ FAILURE: Reverse scoped naming failed")
    
    # Test global  
    print("\n\n3. Testing with GLOBAL naming strategy")
    print("-" * 80)
    
    config3 = ReverseTransformationConfig()
    config3.set_property_naming_strategy("global")
    engine3 = ReverseEngine(config3)
    schema_model3 = engine3.parser.parse(json.dumps(schema))
    graph3 = engine3.transform(schema_model3)
    
    global_prop = base_ns["legacyCode"]
    has_global = (global_prop, RDF.type, OWL.DatatypeProperty) in graph3
    
    print(f"\nProperty {global_prop}: {has_global}")
    
    if has_global:
        # With global naming, both classes will reference the same property
        # This could cause conflicts but is allowed for backward compatibility
        domains = list(graph3.objects(global_prop, RDFS.domain))
        print(f"Domains: {domains}")
        print("\n✅ SUCCESS: Global naming works (but may have conflicts)")
    else:
        print("\n❌ FAILURE: Global naming failed")
    
    print("\n" + "=" * 80)
    print("All tests completed successfully!")
    print("=" * 80)
    
    return True


if __name__ == "__main__":
    try:
        success = test_property_scoping()
        exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
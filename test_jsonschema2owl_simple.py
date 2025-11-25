"""
Simple validation script for JSON Schema to OWL2 transformation.
Tests basic functionality without requiring pytest.
"""

import json
import sys
from rdflib import Namespace, URIRef, Literal
from rdflib.namespace import RDF, RDFS, OWL, XSD

# Add src to path
sys.path.insert(0, 'src')

from jsonschema2owl import ReverseEngine, ReverseTransformationConfig


def test_simple_transformation():
    """Test simple class transformation."""
    print("\n=== Testing Simple Class Transformation ===")
    
    schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "$id": "http://example.org/test-schema",
        "title": "Test Schema",
        "description": "A test schema",
        "definitions": {
            "Person": {
                "type": "object",
                "title": "Person",
                "description": "A human being",
                "properties": {
                    "name": {
                        "type": "string",
                        "title": "Name"
                    },
                    "age": {
                        "type": "integer",
                        "title": "Age"
                    }
                },
                "required": ["name"]
            }
        }
    }
    
    engine = ReverseEngine()
    schema_str = json.dumps(schema)
    schema_model = engine.parser.parse(schema_str)
    
    graph = engine.transform(schema_model)
    
    # Check ontology
    ontology_uri = URIRef("http://example.org/test-schema")
    assert (ontology_uri, RDF.type, OWL.Ontology) in graph
    print("✓ Ontology created")
    
    # Check Person class
    base_ns = Namespace("http://example.org/ontology#")
    person_class = base_ns["Person"]
    assert (person_class, RDF.type, OWL.Class) in graph
    assert (person_class, RDFS.label, Literal("Person")) in graph
    print("✓ Person class created with label")
    
    # Check properties
    name_prop = base_ns["name"]
    age_prop = base_ns["age"]
    assert (name_prop, RDF.type, OWL.DatatypeProperty) in graph
    assert (age_prop, RDF.type, OWL.DatatypeProperty) in graph
    print("✓ Datatype properties created")
    
    # Check datatypes
    assert (name_prop, RDFS.range, XSD.string) in graph
    assert (age_prop, RDFS.range, XSD.integer) in graph
    print("✓ Property ranges correctly set")
    
    print(f"\nGraph contains {len(graph)} triples")
    print("\n✓ Simple transformation test PASSED")
    return True


def test_object_property():
    """Test object property transformation."""
    print("\n=== Testing Object Property Transformation ===")
    
    schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "definitions": {
            "Person": {
                "type": "object",
                "properties": {
                    "employer": {
                        "$ref": "#/definitions/Organization"
                    }
                }
            },
            "Organization": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"}
                }
            }
        }
    }
    
    engine = ReverseEngine()
    schema_str = json.dumps(schema)
    schema_model = engine.parser.parse(schema_str)
    
    graph = engine.transform(schema_model)
    
    base_ns = Namespace("http://example.org/ontology#")
    employer_prop = base_ns["employer"]
    person_class = base_ns["Person"]
    org_class = base_ns["Organization"]
    
    # Check object property
    assert (employer_prop, RDF.type, OWL.ObjectProperty) in graph
    print("✓ Object property created")
    
    # Check domain and range
    assert (employer_prop, RDFS.domain, person_class) in graph
    assert (employer_prop, RDFS.range, org_class) in graph
    print("✓ Domain and range correctly set")
    
    print("\n✓ Object property test PASSED")
    return True


def test_enumeration():
    """Test enumeration transformation."""
    print("\n=== Testing Enumeration Transformation ===")
    
    schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "definitions": {
            "Color": {
                "type": "string",
                "title": "Color",
                "enum": ["red", "green", "blue"]
            }
        }
    }
    
    engine = ReverseEngine()
    schema_str = json.dumps(schema)
    schema_model = engine.parser.parse(schema_str)
    
    graph = engine.transform(schema_model)
    
    base_ns = Namespace("http://example.org/ontology#")
    color_class = base_ns["Color"]
    
    # Check Color class
    assert (color_class, RDF.type, OWL.Class) in graph
    print("✓ Enumeration class created")
    
    # Check individuals
    individuals = list(graph.subjects(RDF.type, OWL.NamedIndividual))
    assert len(individuals) == 3
    print(f"✓ Created {len(individuals)} individuals")
    
    print("\n✓ Enumeration test PASSED")
    return True


def test_serialization():
    """Test graph serialization."""
    print("\n=== Testing Serialization ===")
    
    schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "definitions": {
            "Person": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"}
                }
            }
        }
    }
    
    engine = ReverseEngine()
    schema_str = json.dumps(schema)
    schema_model = engine.parser.parse(schema_str)
    
    graph = engine.transform(schema_model)
    
    # Test Turtle serialization
    turtle = engine.serialize(graph, format="turtle")
    assert turtle is not None
    assert len(turtle) > 0
    assert "@prefix" in turtle
    assert "owl:" in turtle
    print("✓ Turtle serialization works")
    
    # Print first 500 chars
    print("\nFirst 500 characters of Turtle output:")
    print("-" * 60)
    print(turtle[:500])
    print("-" * 60)
    
    print("\n✓ Serialization test PASSED")
    return True


def main():
    """Run all tests."""
    print("="*70)
    print("JSON Schema to OWL2 Transformation - Validation Tests")
    print("="*70)
    
    tests = [
        test_simple_transformation,
        test_object_property,
        test_enumeration,
        test_serialization
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
        except AssertionError as e:
            print(f"\n✗ Test FAILED: {test.__name__}")
            print(f"  Error: {e}")
            failed += 1
        except Exception as e:
            print(f"\n✗ Test ERROR: {test.__name__}")
            print(f"  Error: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "="*70)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("="*70)
    
    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
#!/usr/bin/env python3
"""
Test script for the base object inheritance feature with ThingWithUriRule.
"""

import json
from src.owl2jsonschema.parser import OntologyParser
from src.owl2jsonschema.engine import TransformationEngine
from src.owl2jsonschema.config import TransformationConfig

def test_thing_inheritance():
    """Test the ThingWithUriRule base object inheritance."""
    
    # Sample OWL content
    owl_content = """<?xml version="1.0"?>
<rdf:RDF xmlns="http://example.org/test#"
         xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
         xmlns:owl="http://www.w3.org/2002/07/owl#"
         xmlns:rdfs="http://www.w3.org/2000/01/rdf-schema#">
    
    <owl:Ontology rdf:about="http://example.org/test"/>
    
    <owl:Class rdf:about="http://example.org/test#Person">
        <rdfs:label>Person</rdfs:label>
    </owl:Class>
    
    <owl:Class rdf:about="http://example.org/test#Organization">
        <rdfs:label>Organization</rdfs:label>
    </owl:Class>
    
    <owl:DatatypeProperty rdf:about="http://example.org/test#name">
        <rdfs:domain rdf:resource="http://example.org/test#Person"/>
        <rdfs:range rdf:resource="http://www.w3.org/2001/XMLSchema#string"/>
    </owl:DatatypeProperty>
</rdf:RDF>"""
    
    # Parse OWL
    parser = OntologyParser()
    ontology = parser.parse_string(owl_content)
    
    # Test 1: With ThingWithUriRule disabled
    config = TransformationConfig()
    config.enable_rule("class_to_object")
    config.enable_rule("labels_to_titles")
    config.disable_rule("thing_with_uri")
    
    engine = TransformationEngine(config)
    schema_without_thing = engine.transform(ontology)
    
    print("=" * 60)
    print("Test 1: Without Base Object Inheritance")
    print("=" * 60)
    print(json.dumps(schema_without_thing, indent=2))
    
    # Verify no _Thing in definitions
    assert "_Thing" not in schema_without_thing.get("definitions", {})
    # Verify no allOf in class definitions
    for class_name, class_def in schema_without_thing.get("definitions", {}).items():
        assert "allOf" not in class_def, f"Class {class_name} should not have allOf without ThingWithUriRule"
    
    print("\n✓ No base object inheritance when disabled")
    
    # Test 2: With ThingWithUriRule enabled
    config.enable_rule("thing_with_uri")
    engine = TransformationEngine(config)
    schema_with_thing = engine.transform(ontology)
    
    print("\n" + "=" * 60)
    print("Test 2: With Base Object Inheritance")
    print("=" * 60)
    print(json.dumps(schema_with_thing, indent=2))
    
    # Verify _Thing exists in definitions
    assert "_Thing" in schema_with_thing.get("definitions", {}), "_Thing should be in definitions"
    
    # Verify _Thing has uri property
    thing_def = schema_with_thing["definitions"]["_Thing"]
    assert "properties" in thing_def, "_Thing should have properties"
    assert "uri" in thing_def["properties"], "_Thing should have uri property"
    
    # Verify other classes inherit from _Thing
    for class_name, class_def in schema_with_thing.get("definitions", {}).items():
        if class_name != "_Thing":
            assert "allOf" in class_def, f"Class {class_name} should inherit from _Thing using allOf"
            # Check that the first element references _Thing
            assert class_def["allOf"][0] == {"$ref": "#/definitions/_Thing"}, \
                f"Class {class_name} should reference _Thing as first allOf element"
    
    print("\n✓ Base object inheritance correctly applied when enabled")
    print("\n✓ All tests passed!")

if __name__ == "__main__":
    test_thing_inheritance()
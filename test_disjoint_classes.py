#!/usr/bin/env python3
"""
Test script for the DisjointClassesRule functionality.
"""

import json
from src.owl2jsonschema.parser import OntologyParser
from src.owl2jsonschema.engine import TransformationEngine
from src.owl2jsonschema.config import TransformationConfig

def test_disjoint_classes():
    """Test the DisjointClassesRule with a sample ontology."""
    
    # Sample OWL content with disjoint classes
    owl_content = """<?xml version="1.0"?>
<rdf:RDF xmlns="http://example.org/transport#"
         xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
         xmlns:owl="http://www.w3.org/2002/07/owl#"
         xmlns:rdfs="http://www.w3.org/2000/01/rdf-schema#">
    
    <owl:Ontology rdf:about="http://example.org/transport"/>
    
    <!-- Superclass -->
    <owl:Class rdf:about="http://example.org/transport#RollingStock">
        <rdfs:label>Rolling Stock</rdfs:label>
        <rdfs:comment>Base class for all rolling stock</rdfs:comment>
    </owl:Class>
    
    <!-- Disjoint subclasses -->
    <owl:Class rdf:about="http://example.org/transport#Vehicle">
        <rdfs:label>Vehicle</rdfs:label>
        <rdfs:subClassOf rdf:resource="http://example.org/transport#RollingStock"/>
        <owl:disjointWith rdf:resource="http://example.org/transport#Formation"/>
    </owl:Class>
    
    <owl:Class rdf:about="http://example.org/transport#Formation">
        <rdfs:label>Formation</rdfs:label>
        <rdfs:subClassOf rdf:resource="http://example.org/transport#RollingStock"/>
        <owl:disjointWith rdf:resource="http://example.org/transport#Vehicle"/>
    </owl:Class>
</rdf:RDF>"""
    
    # Parse OWL
    parser = OntologyParser()
    ontology = parser.parse_string(owl_content)
    
    # Test 1: Without DisjointClassesRule
    config = TransformationConfig()
    config.enable_rule("class_to_object")
    config.enable_rule("class_hierarchy")
    config.enable_rule("labels_to_titles")
    config.disable_rule("disjoint_classes")
    
    engine = TransformationEngine(config)
    schema_without_disjoint = engine.transform(ontology)
    
    print("=" * 60)
    print("Test 1: Without Disjoint Classes Rule")
    print("=" * 60)
    print(json.dumps(schema_without_disjoint, indent=2))
    
    # Verify no oneOf in RollingStock
    rolling_stock = schema_without_disjoint.get("definitions", {}).get("RollingStock", {})
    assert "oneOf" not in rolling_stock, "RollingStock should not have oneOf without DisjointClassesRule"
    
    print("\n✓ No oneOf when disjoint classes rule is disabled")
    
    # Test 2: With DisjointClassesRule
    config.enable_rule("disjoint_classes")
    engine = TransformationEngine(config)
    schema_with_disjoint = engine.transform(ontology)
    
    print("\n" + "=" * 60)
    print("Test 2: With Disjoint Classes Rule")
    print("=" * 60)
    print(json.dumps(schema_with_disjoint, indent=2))
    
    # Verify oneOf in RollingStock (it will be nested in allOf due to _Thing inheritance)
    rolling_stock = schema_with_disjoint.get("definitions", {}).get("RollingStock", {})
    print(f"\nRollingStock definition: {json.dumps(rolling_stock, indent=2)}")
    
    # Check if oneOf is present either directly or nested in allOf
    has_one_of = False
    one_of = None
    
    if "oneOf" in rolling_stock:
        has_one_of = True
        one_of = rolling_stock["oneOf"]
    elif "allOf" in rolling_stock:
        # Check within allOf structure (due to _Thing inheritance)
        for item in rolling_stock["allOf"]:
            if isinstance(item, dict) and "oneOf" in item:
                has_one_of = True
                one_of = item["oneOf"]
                break
    
    assert has_one_of, "RollingStock should have oneOf with DisjointClassesRule"
    assert one_of is not None, "Could not find oneOf structure"
    
    # Verify the oneOf contains references to Vehicle and Formation
    assert len(one_of) == 2, "oneOf should have exactly 2 options"
    
    refs = [item.get("$ref", "") for item in one_of]
    assert "#/definitions/Vehicle" in refs or "#/definitions/Formation" in refs, "oneOf should reference Vehicle and/or Formation"
    
    print("\n✓ Disjoint classes correctly transformed to oneOf")
    print("\n✓ All tests passed!")

if __name__ == "__main__":
    test_disjoint_classes()
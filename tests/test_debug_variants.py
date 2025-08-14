#!/usr/bin/env python3
"""
Debug script to understand why cardinality restrictions aren't marking properties as required.
"""

import json
from pathlib import Path
from owl2jsonschema import TransformationEngine, TransformationConfig, OntologyParser
from owl2jsonschema.rules.class_rules import ClassRestrictionsRule

def debug_restrictions(file_path, variant_name):
    """Debug restrictions processing for a specific variant."""
    print(f"\n{'='*80}")
    print(f"Debugging {variant_name}")
    print(f"File: {file_path}")
    print('='*80)
    
    if not file_path.exists():
        print(f"ERROR: File not found: {file_path}")
        return
    
    # Parse the ontology
    parser = OntologyParser()
    ontology = parser.parse(str(file_path))
    
    # Find Vehicle class
    vehicle_class = None
    for owl_class in ontology.classes:
        if 'Vehicle' in owl_class.uri and 'VehicleType' not in owl_class.uri:
            vehicle_class = owl_class
            break
    
    if not vehicle_class:
        print("Vehicle class not found")
        return
    
    print(f"\nVehicle class found: {vehicle_class.uri}")
    print(f"Number of restrictions: {len(vehicle_class.restrictions)}")
    
    # Process restrictions manually
    rule = ClassRestrictionsRule("test", {"enabled": True})
    
    for i, restriction in enumerate(vehicle_class.restrictions):
        print(f"\nRestriction {i+1}:")
        print(f"  Type: {type(restriction).__name__}")
        print(f"  Property: {restriction.property_uri}")
        
        from owl2jsonschema.model import CardinalityRestriction
        if isinstance(restriction, CardinalityRestriction):
            print(f"  Min cardinality: {restriction.min_cardinality}")
            print(f"  Max cardinality: {restriction.max_cardinality}")
            print(f"  Exact cardinality: {restriction.exact_cardinality}")
        
        # Process the restriction
        result = rule._process_restriction(restriction)
        if result:
            print(f"  Processed result:")
            print(f"    Property: {result.get('property')}")
            print(f"    Required: {result.get('required', False)}")
            print(f"    Schema: {result.get('schema', {})}")
    
    # Now process all restrictions together
    print(f"\nProcessing all restrictions together:")
    class_result = rule._process_class_restrictions(vehicle_class)
    if class_result:
        print(f"  Class: {class_result.get('class')}")
        print(f"  Properties: {list(class_result.get('properties', {}).keys())}")
        print(f"  Required: {class_result.get('required', [])}")

def main():
    """Debug all three variants."""
    variants = [
        (
            Path("Documentation/test ontology for OWL to JSON schema transformation, variant.ttl"),
            "Variant 1 (minCardinality/maxCardinality)"
        ),
        (
            Path("Documentation/test ontology for OWL to JSON schema transformation, other variant.ttl"),
            "Variant 2 (minQualifiedCardinality/maxQualifiedCardinality)"
        )
    ]
    
    for file_path, variant_name in variants:
        debug_restrictions(file_path, variant_name)

if __name__ == "__main__":
    main()
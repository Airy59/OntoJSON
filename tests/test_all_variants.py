#!/usr/bin/env python
"""
Test script to verify that all three variants of expressing
property requirements are correctly handled.
"""

import json
from pathlib import Path
from owl2jsonschema import TransformationEngine, TransformationConfig, OntologyParser

def test_variant(file_path, variant_name):
    """Test a specific variant of the ontology."""
    print(f"\n{'='*80}")
    print(f"Testing {variant_name}")
    print(f"File: {file_path}")
    print('='*80)
    
    if not file_path.exists():
        print(f"ERROR: File not found: {file_path}")
        return None
    
    # Parse the ontology
    parser = OntologyParser()
    ontology = parser.parse(str(file_path))
    
    # Create transformation engine with default config
    config = TransformationConfig()
    engine = TransformationEngine(config)
    
    # Transform to JSON Schema
    schema = engine.transform(ontology)
    
    # Check Vehicle class
    definitions = schema.get("definitions", {})
    vehicle_schema = definitions.get("Vehicle", {})
    
    if not vehicle_schema:
        print("ERROR: Vehicle class not found in schema")
        return None
    
    # Extract properties and required fields (handling allOf structure)
    properties = {}
    required_props = []
    
    # Check direct properties
    if "properties" in vehicle_schema:
        properties.update(vehicle_schema["properties"])
    if "required" in vehicle_schema:
        required_props.extend(vehicle_schema["required"])
    
    # Check properties in allOf structures
    if "allOf" in vehicle_schema:
        for item in vehicle_schema["allOf"]:
            if isinstance(item, dict):
                if "properties" in item:
                    properties.update(item["properties"])
                if "required" in item:
                    required_props.extend(item["required"])
    
    # Check for ofType property
    has_oftype = "ofType" in properties
    oftype_required = "ofType" in required_props
    
    print(f"\nVehicle class analysis:")
    print(f"  - Has 'ofType' property: {has_oftype}")
    print(f"  - 'ofType' is required: {oftype_required}")
    
    # Check the specific restriction that makes it required
    if hasattr(ontology, 'classes'):
        for owl_class in ontology.classes:
            if 'Vehicle' in owl_class.uri:
                if owl_class.restrictions:
                    print(f"  - Restrictions found: {len(owl_class.restrictions)}")
                    for r in owl_class.restrictions:
                        if 'ofType' in str(r.property_uri):
                            print(f"    • {r.restriction_type if hasattr(r, 'restriction_type') else 'Cardinality'}: ", end="")
                            if hasattr(r, 'min_cardinality'):
                                print(f"min={r.min_cardinality}", end=" ")
                            if hasattr(r, 'max_cardinality'):
                                print(f"max={r.max_cardinality}", end=" ")
                            if hasattr(r, 'exact_cardinality'):
                                print(f"exact={r.exact_cardinality}", end=" ")
                            if hasattr(r, 'filler'):
                                print(f"filler={r.filler.split('#')[-1] if '#' in r.filler else r.filler}", end=" ")
                            print()
    
    # Save output for inspection
    output_file = Path(f"test_output/{variant_name.replace(' ', '_')}_schema.json")
    output_file.parent.mkdir(exist_ok=True)
    
    with open(output_file, 'w') as f:
        json.dump(schema, f, indent=2)
    
    print(f"\nSchema saved to: {output_file}")
    
    return {
        "has_oftype": has_oftype,
        "oftype_required": oftype_required,
        "success": has_oftype and oftype_required
    }

def main():
    """Test all three variants."""
    print("Testing all three variants of expressing property requirements")
    print("="*80)
    
    variants = [
        (
            Path("Documentation/test ontology for OWL to JSON schema transformation.ttl"),
            "Original (someValuesFrom)"
        ),
        (
            Path("Documentation/test ontology for OWL to JSON schema transformation, variant.ttl"),
            "Variant 1 (minCardinality/maxCardinality)"
        ),
        (
            Path("Documentation/test ontology for OWL to JSON schema transformation, other variant.ttl"),
            "Variant 2 (minQualifiedCardinality/maxQualifiedCardinality)"
        )
    ]
    
    results = []
    
    for file_path, variant_name in variants:
        result = test_variant(file_path, variant_name)
        if result:
            results.append((variant_name, result))
    
    # Summary
    print(f"\n{'='*80}")
    print("SUMMARY")
    print('='*80)
    
    all_passed = True
    
    for variant_name, result in results:
        status = "✓ PASS" if result["success"] else "✗ FAIL"
        print(f"\n{variant_name}:")
        print(f"  Status: {status}")
        print(f"  - Has 'ofType' property: {result['has_oftype']}")
        print(f"  - 'ofType' is required: {result['oftype_required']}")
        
        if not result["success"]:
            all_passed = False
    
    print(f"\n{'='*80}")
    if all_passed:
        print("✓ All variants correctly handle property requirements!")
    else:
        print("✗ Some variants failed - review the results above")
    
    # Additional checks for other properties
    print(f"\n{'='*80}")
    print("Additional property checks (should all be optional):")
    print('='*80)
    
    # Test the first variant for other properties
    file_path = variants[0][0]
    parser = OntologyParser()
    ontology = parser.parse(str(file_path))
    config = TransformationConfig()
    engine = TransformationEngine(config)
    schema = engine.transform(ontology)
    definitions = schema.get("definitions", {})
    
    optional_props = [
        ("LegalEntity", "creationDate"),
        ("Formation", "composedOf"),
        ("RollingStock", "partOf"),
    ]
    
    for class_name, prop_name in optional_props:
        class_schema = definitions.get(class_name, {})
        
        # Check in allOf structure
        required_props = []
        if "required" in class_schema:
            required_props.extend(class_schema["required"])
        if "allOf" in class_schema:
            for item in class_schema["allOf"]:
                if isinstance(item, dict) and "required" in item:
                    required_props.extend(item["required"])
        
        is_required = prop_name in required_props
        status = "✗ ERROR - should be optional" if is_required else "✓ Correctly optional"
        print(f"  {class_name}.{prop_name}: {status}")

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Check if properties are correctly marked as optional/required.
"""

import json
from pathlib import Path
from owl2jsonschema import TransformationEngine, TransformationConfig, OntologyParser

def check_required_properties():
    """Check which properties are marked as required."""
    
    # Parse the ontology
    test_file = Path("Documentation/test ontology for OWL to JSON schema transformation.ttl")
    parser = OntologyParser()
    ontology = parser.parse(str(test_file))
    
    print("Restrictions in Ontology:")
    print("=" * 80)
    for cls in ontology.classes:
        if cls.restrictions:
            class_name = cls.uri.split('#')[-1] if '#' in cls.uri else cls.uri
            print(f"\n{class_name}:")
            for r in cls.restrictions:
                prop_name = r.property_uri.split('#')[-1] if '#' in r.property_uri else r.property_uri
                print(f"  - Property: {prop_name}")
                print(f"    Type: {r.restriction_type}")
                if hasattr(r, 'filler'):
                    filler_name = r.filler.split('#')[-1] if '#' in r.filler else r.filler
                    print(f"    Filler: {filler_name}")
    
    # Transform to JSON Schema
    config = TransformationConfig()
    engine = TransformationEngine(config)
    schema = engine.transform(ontology)
    
    print("\n\nRequired Properties in JSON Schema:")
    print("=" * 80)
    
    definitions = schema.get("definitions", {})
    
    for class_name, class_schema in definitions.items():
        if class_name == "_Thing":
            continue
        
        # Collect required properties
        required_props = []
        
        # Check direct required
        if "required" in class_schema:
            required_props.extend(class_schema["required"])
        
        # Check required in allOf structures
        if "allOf" in class_schema:
            for item in class_schema["allOf"]:
                if isinstance(item, dict) and "required" in item:
                    required_props.extend(item["required"])
        
        if required_props:
            print(f"\n{class_name}:")
            for prop in required_props:
                print(f"  - {prop} (REQUIRED)")
        else:
            # Check what properties exist but are optional
            properties = {}
            if "properties" in class_schema:
                properties.update(class_schema["properties"])
            if "allOf" in class_schema:
                for item in class_schema["allOf"]:
                    if isinstance(item, dict) and "properties" in item:
                        properties.update(item["properties"])
            
            if properties:
                print(f"\n{class_name}:")
                for prop in properties:
                    print(f"  - {prop} (optional)")
    
    print("\n\nAnalysis:")
    print("=" * 80)
    
    # Check specific expected behaviors
    print("\nExpected behaviors:")
    print("1. composedOf should be OPTIONAL (allValuesFrom doesn't imply required)")
    print("2. partOf should be OPTIONAL (no cardinality constraint)")
    print("3. ofType should be REQUIRED (someValuesFrom implies at least one)")
    print("4. creationDate should be OPTIONAL (no constraint)")
    
    # Verify
    formation_required = []
    if "Formation" in definitions:
        if "required" in definitions["Formation"]:
            formation_required.extend(definitions["Formation"]["required"])
        if "allOf" in definitions["Formation"]:
            for item in definitions["Formation"]["allOf"]:
                if isinstance(item, dict) and "required" in item:
                    formation_required.extend(item["required"])
    
    if "composedOf" in formation_required:
        print("\n✗ ERROR: composedOf is marked as REQUIRED but should be optional")
    else:
        print("\n✓ composedOf is correctly optional")

if __name__ == "__main__":
    check_required_properties()
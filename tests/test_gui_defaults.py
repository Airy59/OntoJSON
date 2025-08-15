#!/usr/bin/env python
"""Test transformation with GUI default configuration."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from owl2jsonschema import TransformationEngine, TransformationConfig, OntologyParser
import json

# Exact same default configuration as GUI
GUI_DEFAULT_CONFIG = {
    # Class Transformations
    "class_to_object": {"enabled": True},
    "class_hierarchy": {"enabled": True},
    "class_restrictions": {"enabled": True},
    
    # Property Transformations
    "object_property": {"enabled": True},
    "datatype_property": {"enabled": True},
    "property_cardinality": {"enabled": True},
    "property_restrictions": {"enabled": True},
    
    # Annotation Transformations
    "labels_to_titles": {"enabled": True, "options": {"language": "en"}},
    "comments_to_descriptions": {"enabled": True},
    "annotations_to_metadata": {"enabled": False},
    
    # Advanced Transformations
    "enumeration_to_enum": {"enabled": True},
    "union_to_anyOf": {"enabled": True},
    "intersection_to_allOf": {"enabled": True},
    "complement_to_not": {"enabled": False},
    "equivalent_classes": {"enabled": True},
    "disjoint_classes": {"enabled": True, "options": {"enforcement": "oneOf"}},
    
    # Structural Transformations
    "ontology_to_document": {"enabled": True},
    "individuals_to_examples": {"enabled": False},
    "ontology_metadata": {"enabled": True},
    "thing_with_uri": {"enabled": True}
}

def test_with_gui_defaults():
    """Test transformation with GUI default configuration."""
    
    test_file = Path("Documentation/test ontology for OWL to JSON schema transformation.ttl")
    
    print("=" * 80)
    print("Testing with GUI Default Configuration")
    print("=" * 80)
    print()
    
    # Parse ontology
    parser = OntologyParser()
    ontology = parser.parse(str(test_file))
    
    print(f"Parsed {len(ontology.classes)} classes:")
    for cls in ontology.classes:
        print(f"  - {cls.uri}")
    print()
    
    print(f"Parsed {len(ontology.object_properties)} object properties:")
    for prop in ontology.object_properties:
        print(f"  - {prop.uri}")
        if prop.domain:
            print(f"    Domain: {prop.domain}")
        if prop.range:
            print(f"    Range: {prop.range}")
        if prop.inverse_of:
            print(f"    Inverse of: {prop.inverse_of}")
    print()
    
    # Create configuration matching GUI defaults
    config_dict = {
        "rules": GUI_DEFAULT_CONFIG,
        "output": {
            "include_uri": False,  # GUI default is unchecked
            "use_arrays": True      # Always use arrays for multi-valued properties
        }
    }
    
    # Transform
    config = TransformationConfig(config_dict)
    engine = TransformationEngine(config)
    result = engine.transform(ontology)
    
    # Print result
    print("\n" + "=" * 80)
    print("Transformation Result")
    print("=" * 80)
    print(json.dumps(result, indent=2))
    
    # Check for partOf property
    print("\n" + "=" * 80)
    print("Checking for 'partOf' property")
    print("=" * 80)
    
    definitions = result.get('definitions', {})
    
    # Check each class for partOf
    found_partof = False
    for class_name, class_def in definitions.items():
        # Check direct properties
        if 'properties' in class_def:
            if 'partOf' in class_def['properties']:
                print(f"✓ Found 'partOf' in {class_name} (direct properties)")
                print(f"  Definition: {json.dumps(class_def['properties']['partOf'], indent=4)}")
                found_partof = True
        
        # Check properties inside allOf structures
        if 'allOf' in class_def:
            for i, allof_item in enumerate(class_def['allOf']):
                if 'properties' in allof_item and 'partOf' in allof_item['properties']:
                    print(f"✓ Found 'partOf' in {class_name} (allOf[{i}].properties)")
                    print(f"  Definition: {json.dumps(allof_item['properties']['partOf'], indent=4)}")
                    found_partof = True
    
    if not found_partof:
        print("✗ 'partOf' not found in any class")
        print("\nChecking all properties in all classes:")
        for class_name, class_def in definitions.items():
            if 'properties' in class_def:
                print(f"\n{class_name} properties:")
                for prop_name in class_def['properties'].keys():
                    print(f"  - {prop_name}")
    
    # Check if _Thing is present and has uri property
    if '_Thing' in definitions:
        print("\n✓ '_Thing' base class found")
        if 'properties' in definitions['_Thing']:
            if 'uri' in definitions['_Thing']['properties']:
                print("  ✓ Has 'uri' property (enabled by 'thing_with_uri' rule)")
    
    return result

if __name__ == "__main__":
    test_with_gui_defaults()
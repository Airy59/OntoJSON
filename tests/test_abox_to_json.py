#!/usr/bin/env python
"""
Test script for A-box to JSON conversion functionality
"""

import json
from pathlib import Path
from rdflib import Graph, Namespace, RDF, RDFS, OWL, Literal, URIRef
from owl2jsonschema import TransformationEngine, TransformationConfig, OntologyParser
from owl2jsonschema.abox_generator import ABoxGenerator
from owl2jsonschema.abox_to_json import ABoxToJSONConverter

def test_abox_to_json():
    """Test the complete workflow: T-box -> JSON Schema -> A-box -> JSON instances"""
    
    print("=" * 60)
    print("Testing A-box to JSON Conversion Workflow")
    print("=" * 60)
    
    # Step 1: Load and transform T-box
    print("\n1. Loading Railway ontology...")
    ontology_path = "examples/railway_ontology.ttl"
    
    if not Path(ontology_path).exists():
        print(f"   Warning: {ontology_path} not found, using person ontology instead")
        ontology_path = "examples/person_ontology.owl"
    
    parser = OntologyParser()
    ontology = parser.parse(ontology_path)
    print(f"   Loaded: {len(ontology.classes)} classes, {len(ontology.object_properties)} object properties")
    
    # Step 2: Transform to JSON Schema
    print("\n2. Transforming T-box to JSON Schema...")
    config = TransformationConfig({
        "rules": {
            "class_to_object": {"enabled": True},
            "class_hierarchy": {"enabled": True},
            "object_property": {"enabled": True},
            "datatype_property": {"enabled": True},
            "property_cardinality": {"enabled": True},
            "disjoint_classes": {"enabled": True, "options": {"enforcement": "oneOf"}},
            "labels_to_titles": {"enabled": True, "options": {"language": "en"}}
        }
    })
    
    engine = TransformationEngine(config)
    json_schema = engine.transform(ontology)
    print(f"   Generated schema with {len(json_schema.get('definitions', {}))} definitions")
    
    # Step 3: Generate A-box
    print("\n3. Generating A-box instances...")
    base_uri = "https://example.org/railway#"
    generator = ABoxGenerator(ontology, base_uri)
    abox_graph = generator.generate(min_instances=2, max_instances=4)
    
    # Count individuals
    individuals = list(abox_graph.subjects(RDF.type, None))
    print(f"   Generated {len(individuals)} individuals")
    
    # Step 4: Convert A-box to JSON
    print("\n4. Converting A-box to JSON instances...")
    converter = ABoxToJSONConverter(json_schema, base_uri)
    json_instances = converter.convert(abox_graph)
    
    if isinstance(json_instances, list):
        print(f"   Converted {len(json_instances)} JSON instances")
    else:
        print(f"   Converted 1 JSON instance")
    
    # Step 5: Validate JSON against schema
    print("\n5. Validating JSON instances against schema...")
    validation_results = converter.validate(json_instances)
    
    if validation_results['valid']:
        print(f"   ✅ All {validation_results['validated_count']} instances are valid!")
    else:
        print(f"   ❌ Validation errors found: {len(validation_results['errors'])} errors")
        for error in validation_results['errors'][:5]:  # Show first 5 errors
            print(f"      - Type: {error.get('type')}, Error: {error.get('error')}")
    
    # Display sample instance
    print("\n6. Sample JSON instance:")
    print("-" * 40)
    if isinstance(json_instances, list) and json_instances:
        sample = json_instances[0]
    else:
        sample = json_instances
    print(json.dumps(sample, indent=2)[:1000])  # Show first 1000 chars
    
    # Step 6: Generate JSON-LD
    print("\n7. Converting to JSON-LD format...")
    jsonld_instances = converter.to_jsonld(json_instances)
    print("   JSON-LD context generated")
    
    print("\n" + "=" * 60)
    print("Test completed successfully!")
    print("=" * 60)
    
    return json_instances, json_schema

if __name__ == "__main__":
    try:
        instances, schema = test_abox_to_json()
        
        # Optional: Save results
        print("\nSaving results...")
        with open("test_schema.json", "w") as f:
            json.dump(schema, f, indent=2)
        with open("test_instances.json", "w") as f:
            json.dump(instances, f, indent=2)
        print("Results saved to test_schema.json and test_instances.json")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
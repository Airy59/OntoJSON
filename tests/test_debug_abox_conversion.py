#!/usr/bin/env python3
"""
Debug script to understand A-box to JSON conversion issues
"""

import json
from pathlib import Path
from rdflib import Graph, Namespace, RDF, RDFS, OWL, Literal, URIRef
from owl2jsonschema import TransformationEngine, TransformationConfig, OntologyParser
from owl2jsonschema.abox_generator import ABoxGenerator
from owl2jsonschema.abox_to_json import ABoxToJSONConverter

def debug_abox_conversion():
    """Debug the A-box to JSON conversion to see what's happening."""
    
    print("=" * 60)
    print("Debugging A-box to JSON Conversion")
    print("=" * 60)
    
    # Step 1: Load and transform T-box
    print("\n1. Loading ontology...")
    ontology_path = "examples/person_ontology.owl"
    parser = OntologyParser()
    ontology = parser.parse(ontology_path)
    print(f"   Loaded: {len(ontology.classes)} classes")
    
    # Step 2: Transform to JSON Schema
    print("\n2. Transforming T-box to JSON Schema...")
    config = TransformationConfig({
        "rules": {
            "class_to_object": {"enabled": True},
            "class_hierarchy": {"enabled": True},
            "object_property": {"enabled": True},
            "datatype_property": {"enabled": True},
            "property_cardinality": {"enabled": True},
            "labels_to_titles": {"enabled": True, "options": {"language": "en"}}
        }
    })
    
    engine = TransformationEngine(config)
    json_schema = engine.transform(ontology)
    
    # Show what properties are expected in the schema
    print("\n3. Properties defined in JSON Schema:")
    for def_name, def_schema in json_schema.get('definitions', {}).items():
        if 'properties' in def_schema:
            props = list(def_schema['properties'].keys())
            print(f"   {def_name}: {props}")
    
    # Step 3: Generate A-box
    print("\n4. Generating A-box instances...")
    base_uri = "https://example.org#"
    generator = ABoxGenerator(ontology, base_uri)
    abox_graph = generator.generate(min_instances=1, max_instances=2)
    
    # Show what's actually in the RDF graph
    print("\n5. Analyzing RDF graph contents:")
    
    # Find all individuals
    individuals = set()
    for s in abox_graph.subjects(RDF.type, None):
        if isinstance(s, URIRef) and not ((s, RDF.type, OWL.Class) in abox_graph):
            individuals.add(s)
    
    print(f"   Found {len(individuals)} individuals")
    
    # For each individual, show all their triples
    for individual in list(individuals)[:2]:  # Show first 2 individuals
        print(f"\n   Individual: {individual}")
        print("   Properties:")
        for predicate, obj in abox_graph.predicate_objects(individual):
            pred_name = str(predicate).split('#')[-1] if '#' in str(predicate) else str(predicate).split('/')[-1]
            obj_str = str(obj)[:50] + "..." if len(str(obj)) > 50 else str(obj)
            print(f"     {pred_name}: {obj_str}")
    
    # Step 4: Convert A-box to JSON
    print("\n6. Converting A-box to JSON instances...")
    converter = ABoxToJSONConverter(json_schema, base_uri)
    json_instances = converter.convert(abox_graph)
    
    # Show the converted JSON
    print("\n7. Converted JSON instances:")
    for type_name, instances in json_instances.items():
        print(f"\n   {type_name}:")
        for i, instance in enumerate(instances[:2]):  # Show first 2 instances
            print(f"   Instance {i+1}:")
            for key, value in instance.items():
                value_str = str(value)[:50] + "..." if len(str(value)) > 50 else str(value)
                print(f"     {key}: {value_str}")
    
    # Check if properties are missing
    print("\n8. Property extraction analysis:")
    missing_properties = False
    for type_name, instances in json_instances.items():
        if type_name in json_schema.get('definitions', {}):
            expected_props = set(json_schema['definitions'][type_name].get('properties', {}).keys())
            for instance in instances:
                actual_props = set(instance.keys())
                missing = expected_props - actual_props - {'uri'}  # Exclude uri from missing
                if missing:
                    print(f"   ❌ {type_name} instance missing properties: {missing}")
                    missing_properties = True
    
    if not missing_properties:
        print("   ✅ All expected properties are present!")
    
    # Save for inspection
    with open("debug_schema.json", "w") as f:
        json.dump(json_schema, f, indent=2)
    with open("debug_instances.json", "w") as f:
        json.dump(json_instances, f, indent=2)
    
    # Save RDF graph for inspection
    with open("debug_abox.ttl", "w") as f:
        f.write(abox_graph.serialize(format='turtle'))
    
    print("\n" + "=" * 60)
    print("Debug files saved:")
    print("  - debug_schema.json")
    print("  - debug_instances.json")
    print("  - debug_abox.ttl")
    print("=" * 60)
    
    return json_instances, json_schema

if __name__ == "__main__":
    debug_abox_conversion()
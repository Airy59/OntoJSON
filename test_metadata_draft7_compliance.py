#!/usr/bin/env python3
"""
Test script demonstrating Draft 7 compliant metadata handling.

This script shows different ways to handle metadata in JSON Schema Draft 7
to avoid validation warnings about unrecognized attributes like $metadata.
"""

import json
from src.owl2jsonschema.config import TransformationConfig
from src.owl2jsonschema.engine import TransformationEngine
from src.owl2jsonschema.parser import OntologyParser
from pathlib import Path

def test_metadata_placement_options():
    """Test different metadata placement options for Draft 7 compliance."""
    
    # Sample ontology file (adjust path as needed)
    ontology_file = "test_ontology.ttl"
    
    if not Path(ontology_file).exists():
        print(f"Warning: {ontology_file} not found. Creating a sample ontology...")
        # Create a simple test ontology
        with open(ontology_file, 'w') as f:
            f.write("""
@prefix : <http://example.org/test#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix dc: <http://purl.org/dc/elements/1.1/> .
@prefix dcterms: <http://purl.org/dc/terms/> .

: a owl:Ontology ;
    dc:title "Test Ontology" ;
    dc:description "A test ontology for metadata handling" ;
    dc:creator "Test Author" ;
    dcterms:license "MIT" ;
    owl:versionInfo "1.0.0" ;
    dcterms:created "2024-01-01" ;
    dcterms:modified "2024-01-15" .

:Person a owl:Class ;
    rdfs:label "Person" ;
    rdfs:comment "Represents a person" .

:name a owl:DatatypeProperty ;
    rdfs:domain :Person ;
    rdfs:range xsd:string ;
    rdfs:label "name" ;
    rdfs:comment "The name of the person" .
""")
    
    # Parse the ontology
    parser = OntologyParser()
    ontology = parser.parse(ontology_file)
    
    # Test different metadata placement options
    placement_options = [
        ("x-metadata", "Use x-metadata extension (Draft 7 compliant - recommended)"),
        ("comment", "Store metadata in $comment field (fully Draft 7 compliant)"),
        ("defs", "Store metadata in $defs/_metadata (Draft 7 compliant)"),
        ("info", "Group metadata under 'info' field (OpenAPI-style)"),
        ("none", "Exclude metadata entirely"),
        ("root", "Legacy mode with $metadata (causes validation warnings)")
    ]
    
    print("=" * 80)
    print("JSON Schema Draft 7 Metadata Placement Options")
    print("=" * 80)
    
    for placement, description in placement_options:
        print(f"\n{placement.upper()}: {description}")
        print("-" * 40)
        
        # Create configuration with the specified placement
        config = TransformationConfig()
        config.set_rule_option("ontology_metadata", "placement", placement)
        
        # Transform the ontology
        engine = TransformationEngine(config)
        schema = engine.transform(ontology)
        
        # Show relevant parts of the schema
        if placement == "x-metadata" and "x-metadata" in schema:
            print("Generated metadata field:")
            print(json.dumps({"x-metadata": schema["x-metadata"]}, indent=2))
        elif placement == "comment" and "$comment" in schema:
            print("Generated comment field:")
            print(json.dumps({"$comment": schema["$comment"]}, indent=2))
        elif placement == "defs" and "$defs" in schema and "_metadata" in schema.get("$defs", {}):
            print("Generated $defs/_metadata:")
            print(json.dumps({"$defs": {"_metadata": schema["$defs"]["_metadata"]}}, indent=2))
        elif placement == "info" and "info" in schema:
            print("Generated info field:")
            print(json.dumps({"info": schema["info"]}, indent=2))
        elif placement == "none":
            print("No metadata fields generated (metadata excluded)")
        elif placement == "root":
            metadata_fields = {k: v for k, v in schema.items() 
                             if k.startswith("$") and k not in ["$schema", "$id", "$comment"]}
            if metadata_fields:
                print("Generated metadata fields (causes validation warnings):")
                print(json.dumps(metadata_fields, indent=2))
        
        # Check Draft 7 compliance
        non_compliant_fields = []
        for key in schema.keys():
            if key.startswith("$") and key not in ["$schema", "$id", "$ref", "$comment", "$defs"]:
                non_compliant_fields.append(key)
        
        if non_compliant_fields:
            print(f"⚠️  WARNING: Non-compliant fields found: {', '.join(non_compliant_fields)}")
        else:
            print("✅ Schema is Draft 7 compliant (no validation warnings expected)")
    
    # Show how to use a custom configuration file
    print("\n" + "=" * 80)
    print("CONFIGURATION FILE EXAMPLE")
    print("=" * 80)
    print("\nTo set the metadata placement permanently, create a config file:")
    print("\nconfig.json:")
    config_example = {
        "rules": {
            "ontology_metadata": {
                "enabled": True,
                "options": {
                    "placement": "x-metadata"  # or "comment", "defs", "info", "none"
                }
            }
        }
    }
    print(json.dumps(config_example, indent=2))
    
    print("\nThen use it with:")
    print("  config = TransformationConfig.from_file('config.json')")
    print("  engine = TransformationEngine(config)")
    
    # Cleanup
    if Path(ontology_file).stat().st_size < 1000:  # Only remove if it's our test file
        Path(ontology_file).unlink(missing_ok=True)
        print(f"\n(Test file {ontology_file} removed)")

def main():
    """Main function."""
    print("\nJSON Schema Draft 7 Metadata Compliance Test")
    print("This demonstrates how to avoid validation warnings from $metadata")
    print()
    
    test_metadata_placement_options()
    
    print("\n" + "=" * 80)
    print("RECOMMENDATION:")
    print("=" * 80)
    print("""
For Draft 7 compliance and to avoid validation warnings:

1. USE 'x-metadata' (default): Stores metadata in x-metadata field
   - Fully Draft 7 compliant
   - Preserves all metadata
   - Recognized as custom extension by validators

2. USE 'comment': Stores metadata as JSON string in $comment
   - Fully Draft 7 compliant
   - May be less readable for complex metadata
   
3. USE 'defs': Stores metadata in $defs/_metadata
   - Fully Draft 7 compliant
   - Keeps metadata separate from schema structure

4. USE 'none': Excludes metadata entirely
   - No validation warnings
   - But loses ontology metadata

AVOID 'root': This uses $metadata and other $ prefixed fields that
are not recognized by Draft 7 and will cause validation warnings.
""")

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Test script to verify metadata persistence in JSON Schema
"""

import json
import tempfile
from pathlib import Path
from src.owl2jsonschema.composite_builder import CompositeOntologyBuilder
from src.owl2jsonschema.parser import OntologyParser
from src.owl2jsonschema.engine import TransformationEngine
from src.owl2jsonschema.config import TransformationConfig

def test_metadata_persistence():
    """Test that metadata from composite ontology is persisted in JSON Schema."""
    
    print("=" * 60)
    print("Testing Metadata Persistence in JSON Schema")
    print("=" * 60)
    
    # Step 1: Create a simple test ontology file
    test_ontology = """
@prefix : <http://example.org/test#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

<http://example.org/test> a owl:Ontology ;
    rdfs:label "Test Ontology" .

:TestClass a owl:Class ;
    rdfs:label "Test Class" ;
    rdfs:comment "A simple test class" .
"""
    
    # Save test ontology to temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.ttl', delete=False) as f:
        f.write(test_ontology)
        test_file = f.name
    
    print(f"Created test ontology: {test_file}")
    
    try:
        # Step 2: Create composite ontology with metadata
        metadata = {
            "title": "My Composite Ontology",
            "version": "1.0.0",
            "author": "Test Author",
            "description": "This is a test composite ontology",
            "comment": "Additional test comments"
        }
        
        print("\nMetadata to add:")
        for key, value in metadata.items():
            print(f"  {key}: {value}")
        
        # Create composite ontology
        builder = CompositeOntologyBuilder.create_composite(
            [test_file],
            metadata=metadata
        )
        
        # Save composite to temp file
        composite_file = builder.save_to_temp_file(format="turtle")
        print(f"\nCreated composite ontology: {composite_file}")
        
        # Step 3: Parse the composite ontology
        parser = OntologyParser()
        ontology_model = parser.parse(composite_file, format="turtle")
        
        print("\nParsed ontology annotations:")
        for key, value in ontology_model.annotations.items():
            print(f"  {key}: {value[:50]}..." if len(str(value)) > 50 else f"  {key}: {value}")
        
        # Step 4: Transform to JSON Schema
        config = TransformationConfig()
        # Enable ontology metadata rule
        config.enable_rule("ontology_metadata")
        
        engine = TransformationEngine(config)
        json_schema = engine.transform(ontology_model)
        
        # Step 5: Check if metadata is in JSON Schema
        print("\n" + "=" * 60)
        print("JSON Schema Output:")
        print("=" * 60)
        print(json.dumps(json_schema, indent=2)[:1000] + "...")
        
        # Verify metadata presence
        print("\n" + "=" * 60)
        print("Metadata Verification:")
        print("=" * 60)
        
        checks = {
            "Title in schema": "title" in json_schema,
            "Description in schema": "description" in json_schema,
            "Metadata field present": "$metadata" in json_schema,
            "Schema version field": "$schema-version" in json_schema,
            "Schema author field": "$schema-author" in json_schema,
        }
        
        for check, result in checks.items():
            status = "✓" if result else "✗"
            print(f"  {status} {check}: {result}")
        
        # Print actual metadata if present
        if "$metadata" in json_schema:
            print("\nExtracted metadata:")
            for key, value in json_schema["$metadata"].items():
                print(f"  {key}: {value}")
        
        # Check if title and description are at root level
        if "title" in json_schema:
            print(f"\nRoot title: {json_schema['title']}")
        if "description" in json_schema:
            print(f"Root description: {json_schema['description']}")
        
        # Overall result
        all_passed = all(checks.values())
        print("\n" + "=" * 60)
        if all_passed:
            print("SUCCESS: All metadata was persisted in JSON Schema! ✓")
        else:
            print("PARTIAL: Some metadata was persisted, but not all fields")
        print("=" * 60)
        
        return all_passed
        
    finally:
        # Clean up temp files
        Path(test_file).unlink(missing_ok=True)
        if 'composite_file' in locals():
            Path(composite_file).unlink(missing_ok=True)

if __name__ == "__main__":
    success = test_metadata_persistence()
    exit(0 if success else 1)
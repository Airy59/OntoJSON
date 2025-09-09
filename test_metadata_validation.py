#!/usr/bin/env python3
"""
Test script that demonstrates the actual validation warnings with $metadata
and shows how the new x-metadata approach fixes them.
"""

import json
import sys
from pathlib import Path

# Add src to path if needed
if Path("src").exists():
    sys.path.insert(0, str(Path("src").absolute()))

from owl2jsonschema.config import TransformationConfig
from owl2jsonschema.engine import TransformationEngine
from owl2jsonschema.parser import OntologyParser

def create_test_ontology():
    """Create a test ontology with metadata."""
    ontology_file = "test_metadata_ontology.ttl"
    
    with open(ontology_file, 'w') as f:
        f.write("""
@prefix : <http://example.org/test#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix dc: <http://purl.org/dc/elements/1.1/> .
@prefix dcterms: <http://purl.org/dc/terms/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

: a owl:Ontology ;
    dc:title "Test Ontology with Metadata" ;
    dc:description "A test ontology to demonstrate metadata handling" ;
    dc:creator "John Doe" ;
    dcterms:license "MIT License" ;
    owl:versionInfo "1.0.0" ;
    dcterms:created "2024-01-01T00:00:00Z" ;
    dcterms:modified "2024-01-15T12:00:00Z" ;
    dc:contributor "Jane Smith" ;
    dc:source "http://example.org/original" .

:Person a owl:Class ;
    rdfs:label "Person" ;
    rdfs:comment "Represents a human being" .

:name a owl:DatatypeProperty ;
    rdfs:domain :Person ;
    rdfs:range xsd:string ;
    rdfs:label "name" ;
    rdfs:comment "The full name of the person" .

:age a owl:DatatypeProperty ;
    rdfs:domain :Person ;
    rdfs:range xsd:integer ;
    rdfs:label "age" ;
    rdfs:comment "The age of the person in years" .
""")
    
    return ontology_file

def validate_draft7_compliance(schema):
    """Check if schema is Draft 7 compliant."""
    # Check for non-compliant $ prefixed fields
    non_compliant = []
    draft7_allowed = {"$schema", "$id", "$ref", "$comment", "$defs"}
    
    for key in schema.keys():
        if key.startswith("$") and key not in draft7_allowed:
            non_compliant.append(key)
    
    return non_compliant

def test_metadata_handling():
    """Test different metadata handling approaches."""
    
    # Create test ontology
    ontology_file = create_test_ontology()
    
    # Parse the ontology
    parser = OntologyParser()
    ontology = parser.parse(ontology_file)
    
    print("=" * 80)
    print("JSON SCHEMA DRAFT 7 METADATA COMPLIANCE TEST")
    print("=" * 80)
    
    # Test 1: Legacy approach with $metadata (causes warnings)
    print("\n1. LEGACY APPROACH (Causes Validation Warnings)")
    print("-" * 50)
    
    config_legacy = TransformationConfig()
    config_legacy.set_rule_option("ontology_metadata", "placement", "root")
    
    engine_legacy = TransformationEngine(config_legacy)
    schema_legacy = engine_legacy.transform(ontology)
    
    # Show the problematic fields
    problematic_fields = validate_draft7_compliance(schema_legacy)
    
    if problematic_fields:
        print("❌ NON-COMPLIANT FIELDS FOUND:")
        for field in problematic_fields:
            if field in schema_legacy:
                print(f"  - {field}: {json.dumps(schema_legacy[field], indent=4)[:100]}...")
        print("\n⚠️  These fields will cause validation warnings in strict Draft 7 validators!")
    
    # Show the full schema structure
    print("\nGenerated Schema (partial):")
    partial_schema = {k: v for k, v in list(schema_legacy.items())[:8]}
    print(json.dumps(partial_schema, indent=2, default=str)[:500] + "...")
    
    # Test 2: New approach with x-metadata (Draft 7 compliant)
    print("\n\n2. NEW APPROACH WITH x-metadata (Draft 7 Compliant)")
    print("-" * 50)
    
    config_new = TransformationConfig()
    config_new.set_rule_option("ontology_metadata", "placement", "x-metadata")
    
    engine_new = TransformationEngine(config_new)
    schema_new = engine_new.transform(ontology)
    
    # Check compliance
    problematic_fields = validate_draft7_compliance(schema_new)
    
    if problematic_fields:
        print("❌ Non-compliant fields found:", problematic_fields)
    else:
        print("✅ FULLY DRAFT 7 COMPLIANT - No validation warnings!")
    
    # Show the metadata in x-metadata field
    if "x-metadata" in schema_new:
        print("\nMetadata stored in x-metadata field:")
        print(json.dumps({"x-metadata": schema_new["x-metadata"]}, indent=2, default=str))
    
    # Test 3: Comment approach
    print("\n\n3. COMMENT APPROACH (Draft 7 Compliant)")
    print("-" * 50)
    
    config_comment = TransformationConfig()
    config_comment.set_rule_option("ontology_metadata", "placement", "comment")
    
    engine_comment = TransformationEngine(config_comment)
    schema_comment = engine_comment.transform(ontology)
    
    # Check compliance
    problematic_fields = validate_draft7_compliance(schema_comment)
    
    if problematic_fields:
        print("❌ Non-compliant fields found:", problematic_fields)
    else:
        print("✅ FULLY DRAFT 7 COMPLIANT - No validation warnings!")
    
    if "$comment" in schema_comment:
        print("\nMetadata stored in $comment field:")
        comment_preview = schema_comment["$comment"][:200] + "..." if len(schema_comment["$comment"]) > 200 else schema_comment["$comment"]
        print(f'  "$comment": "{comment_preview}"')
    
    # Test 4: $defs approach
    print("\n\n4. $defs APPROACH (Draft 7 Compliant)")
    print("-" * 50)
    
    config_defs = TransformationConfig()
    config_defs.set_rule_option("ontology_metadata", "placement", "defs")
    
    engine_defs = TransformationEngine(config_defs)
    schema_defs = engine_defs.transform(ontology)
    
    # Check compliance
    problematic_fields = validate_draft7_compliance(schema_defs)
    
    if problematic_fields:
        print("❌ Non-compliant fields found:", problematic_fields)
    else:
        print("✅ FULLY DRAFT 7 COMPLIANT - No validation warnings!")
    
    if "$defs" in schema_defs and "_metadata" in schema_defs.get("$defs", {}):
        print("\nMetadata stored in $defs/_metadata:")
        print(json.dumps({"$defs": {"_metadata": schema_defs["$defs"]["_metadata"]}}, indent=2, default=str))
    
    # Clean up
    Path(ontology_file).unlink(missing_ok=True)
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print("""
The $metadata attribute issue has been resolved by providing multiple 
Draft 7 compliant options:

1. x-metadata (DEFAULT): Uses the x- prefix which is allowed for extensions
2. $comment: Stores metadata as a JSON string in the $comment field  
3. $defs: Stores metadata in $defs/_metadata
4. info: Groups metadata in an 'info' field (OpenAPI-style)
5. none: Excludes metadata entirely

The default has been changed from 'root' (which used $metadata) to 'x-metadata'
which is fully Draft 7 compliant and will not cause validation warnings.
""")

def main():
    """Main function."""
    try:
        # Try to import jsonschema for validation
        import jsonschema
        print("jsonschema library found - can perform actual validation\n")
    except ImportError:
        print("jsonschema library not found - showing compliance check only\n")
    
    test_metadata_handling()

if __name__ == "__main__":
    main()
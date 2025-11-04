"""
Test the label-based enum rule for individuals.
"""

from rdflib import Graph, Namespace, RDF, OWL, RDFS, Literal
from src.owl2jsonschema.parser import OntologyParser
from src.owl2jsonschema.engine import TransformationEngine
from src.owl2jsonschema.config import TransformationConfig
import json


def create_test_ontology():
    """Create a test ontology with classes and individuals with labels."""
    g = Graph()
    
    # Define namespace
    ex = Namespace("http://example.org/test#")
    g.bind("ex", ex)
    
    # Create ontology
    g.add((ex.TestOntology, RDF.type, OWL.Ontology))
    
    # Create a class
    g.add((ex.Priority, RDF.type, OWL.Class))
    g.add((ex.Priority, RDFS.label, Literal("Priority Level")))
    
    # Create individuals with English labels
    g.add((ex.High, RDF.type, OWL.NamedIndividual))
    g.add((ex.High, RDF.type, ex.Priority))
    g.add((ex.High, RDFS.label, Literal("High", lang="en")))
    g.add((ex.High, RDFS.label, Literal("Élevée", lang="fr")))
    
    g.add((ex.Medium, RDF.type, OWL.NamedIndividual))
    g.add((ex.Medium, RDF.type, ex.Priority))
    g.add((ex.Medium, RDFS.label, Literal("Medium", lang="en")))
    g.add((ex.Medium, RDFS.label, Literal("Moyenne", lang="fr")))
    
    g.add((ex.Low, RDF.type, OWL.NamedIndividual))
    g.add((ex.Low, RDF.type, ex.Priority))
    g.add((ex.Low, RDFS.label, Literal("Low", lang="en")))
    g.add((ex.Low, RDFS.label, Literal("Basse", lang="fr")))
    
    return g


def test_label_enum():
    """Test that individuals are converted to label-based enums."""
    print("=" * 60)
    print("Testing Label-Based Enum for Individuals")
    print("=" * 60)
    
    # Create test ontology
    print("\n1. Creating test ontology...")
    g = create_test_ontology()
    
    # Save to file
    test_file = "test_label_enum_ontology.ttl"
    g.serialize(test_file, format="turtle")
    print(f"   Saved to {test_file}")
    
    # Parse
    print("\n2. Parsing ontology...")
    parser = OntologyParser()
    ontology = parser.parse(test_file, format="turtle")
    print(f"   Found {len(ontology.individuals)} individuals")
    
    # Configure - use label-based enum (default)
    print("\n3. Configuring transformation...")
    config = TransformationConfig()
    # The individuals_to_label_enum rule should be enabled by default
    
    # Transform
    print("\n4. Transforming to JSON Schema...")
    engine = TransformationEngine(config)
    schema = engine.transform(ontology)
    
    # Display
    print("\n5. Generated JSON Schema:")
    print("-" * 60)
    schema_json = json.dumps(schema, indent=2)
    print(schema_json)
    
    # Save
    schema_file = "test_label_enum_schema.json"
    with open(schema_file, 'w') as f:
        f.write(schema_json)
    print(f"\nSaved to {schema_file}")
    
    # Verify
    print("\n6. Verification:")
    print("-" * 60)
    
    success = True
    if "definitions" in schema and "Priority" in schema["definitions"]:
        priority_def = schema["definitions"]["Priority"]
        print(f"Priority definition: {json.dumps(priority_def, indent=2)}")
        
        # Check if enum is at top level or in allOf structure
        enum_values = None
        enum_uris = None
        
        if "enum" in priority_def:
            enum_values = priority_def["enum"]
            enum_uris = priority_def.get("x-enum-uris")
        elif "allOf" in priority_def:
            # Check in allOf structure
            for item in priority_def["allOf"]:
                if "enum" in item:
                    enum_values = item["enum"]
                    enum_uris = item.get("x-enum-uris")
                    break
        
        if enum_values:
            print(f"\n✓ Found enum values: {enum_values}")
            
            # Should have English labels, not URIs
            expected_labels = ["High", "Medium", "Low"]
            if all(label in enum_values for label in expected_labels):
                print("✅ SUCCESS: Enum uses English labels (not URIs)!")
            else:
                print(f"❌ FAILED: Expected labels {expected_labels}, got {enum_values}")
                success = False
            
            # Check for URI mapping
            if enum_uris:
                print(f"✓ URI mapping preserved: {enum_uris}")
        else:
            print("❌ FAILED: No enum found in Priority definition")
            success = False
    else:
        print("❌ FAILED: Priority class not found")
        success = False
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 TEST PASSED!")
    else:
        print("⚠️  TEST FAILED")
    print("=" * 60)
    
    return success


if __name__ == "__main__":
    test_label_enum()
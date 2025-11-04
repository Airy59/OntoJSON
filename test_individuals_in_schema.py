"""
Test script to verify that individuals are included in generated JSON schemas.
"""

from rdflib import Graph, Namespace, RDF, OWL, RDFS, Literal
from src.owl2jsonschema.parser import OntologyParser
from src.owl2jsonschema.engine import TransformationEngine
from src.owl2jsonschema.config import TransformationConfig
import json


def create_test_ontology():
    """Create a test ontology with classes and individuals."""
    g = Graph()
    
    # Define namespace
    ex = Namespace("http://example.org/test#")
    g.bind("ex", ex)
    
    # Create ontology
    g.add((ex.TestOntology, RDF.type, OWL.Ontology))
    
    # Create a class
    g.add((ex.Color, RDF.type, OWL.Class))
    g.add((ex.Color, RDFS.label, Literal("Color")))
    g.add((ex.Color, RDFS.comment, Literal("A color class")))
    
    # Create individuals of the Color class
    g.add((ex.Red, RDF.type, OWL.NamedIndividual))
    g.add((ex.Red, RDF.type, ex.Color))
    g.add((ex.Red, RDFS.label, Literal("Red")))
    
    g.add((ex.Blue, RDF.type, OWL.NamedIndividual))
    g.add((ex.Blue, RDF.type, ex.Color))
    g.add((ex.Blue, RDFS.label, Literal("Blue")))
    
    g.add((ex.Green, RDF.type, OWL.NamedIndividual))
    g.add((ex.Green, RDF.type, ex.Color))
    g.add((ex.Green, RDFS.label, Literal("Green")))
    
    # Create another class with individuals
    g.add((ex.Status, RDF.type, OWL.Class))
    g.add((ex.Status, RDFS.label, Literal("Status")))
    
    g.add((ex.Active, RDF.type, OWL.NamedIndividual))
    g.add((ex.Active, RDF.type, ex.Status))
    g.add((ex.Active, RDFS.label, Literal("Active")))
    
    g.add((ex.Inactive, RDF.type, OWL.NamedIndividual))
    g.add((ex.Inactive, RDF.type, ex.Status))
    g.add((ex.Inactive, RDFS.label, Literal("Inactive")))
    
    return g


def test_individuals_in_schema():
    """Test that individuals are included in the JSON schema."""
    print("=" * 60)
    print("Testing Individuals in JSON Schema")
    print("=" * 60)
    
    # Create test ontology
    print("\n1. Creating test ontology with classes and individuals...")
    g = create_test_ontology()
    
    # Save to file for inspection
    test_file = "test_individuals_ontology.ttl"
    g.serialize(test_file, format="turtle")
    print(f"   Saved test ontology to {test_file}")
    
    # Parse the ontology
    print("\n2. Parsing ontology...")
    parser = OntologyParser()
    ontology = parser.parse(test_file, format="turtle")
    
    print(f"   Found {len(ontology.classes)} classes")
    print(f"   Found {len(ontology.individuals)} individuals")
    
    for individual in ontology.individuals:
        print(f"   - Individual: {individual.uri} (types: {individual.types})")
    
    # Configure transformation with individuals_to_enum rule enabled
    print("\n3. Configuring transformation engine...")
    config = TransformationConfig()
    config.enable_rule("individuals_to_enum")
    
    # Create engine and transform
    print("\n4. Transforming to JSON Schema...")
    engine = TransformationEngine(config)
    schema = engine.transform(ontology)
    
    # Display the schema
    print("\n5. Generated JSON Schema:")
    print("-" * 60)
    schema_json = json.dumps(schema, indent=2)
    print(schema_json)
    
    # Save schema to file
    schema_file = "test_individuals_schema.json"
    with open(schema_file, 'w') as f:
        f.write(schema_json)
    print(f"\nSaved schema to {schema_file}")
    
    # Verify individuals are in the schema
    print("\n6. Verification:")
    print("-" * 60)
    
    def get_uri_property(class_def):
        """Helper to find uri property in a class definition (may be in allOf structure)."""
        # Check direct properties
        if "properties" in class_def and "uri" in class_def["properties"]:
            return class_def["properties"]["uri"]
        
        # Check in allOf structure
        if "allOf" in class_def:
            for item in class_def["allOf"]:
                if "properties" in item and "uri" in item["properties"]:
                    return item["properties"]["uri"]
        
        return None
    
    if "definitions" in schema:
        for class_name, class_def in schema["definitions"].items():
            print(f"\nClass: {class_name}")
            uri_prop = get_uri_property(class_def)
            if uri_prop:
                if "enum" in uri_prop:
                    print(f"  ✓ Closed set (enum): {uri_prop['enum']}")
                    if "x-enum-labels" in uri_prop:
                        print(f"  ✓ Has enum labels: {uri_prop['x-enum-labels']}")
                elif "x-known-individuals" in uri_prop:
                    print(f"  ✓ Open set (known individuals): {uri_prop['x-known-individuals']}")
                    if "x-known-individual-labels" in uri_prop:
                        print(f"  ✓ Has individual labels: {uri_prop['x-known-individual-labels']}")
                else:
                    print(f"  - No individuals defined")
            else:
                print(f"  - No uri property")
    
    # Check specific classes - expecting open sets (not closed enums)
    success = True
    if "Color" in schema.get("definitions", {}):
        color_def = schema["definitions"]["Color"]
        uri_prop = get_uri_property(color_def)
        if uri_prop:
            # Check for either closed enum or open set
            expected_colors = ["http://example.org/test#Red", "http://example.org/test#Blue", "http://example.org/test#Green"]
            
            if "enum" in uri_prop:
                # Closed set
                if all(color in uri_prop["enum"] for color in expected_colors):
                    print("\n✅ SUCCESS: Color class has all expected individuals (closed enum)!")
                else:
                    print("\n❌ FAILED: Color class missing some individuals")
                    success = False
            elif "x-known-individuals" in uri_prop:
                # Open set
                if all(color in uri_prop["x-known-individuals"] for color in expected_colors):
                    print("\n✅ SUCCESS: Color class has all expected individuals (open set)!")
                else:
                    print("\n❌ FAILED: Color class missing some individuals")
                    print(f"   Expected: {expected_colors}")
                    print(f"   Got: {uri_prop['x-known-individuals']}")
                    success = False
            else:
                print("\n❌ FAILED: Color class has no individuals defined")
                success = False
        else:
            print("\n❌ FAILED: Color class has no uri property")
            success = False
    else:
        print("\n❌ FAILED: Color class not found in schema")
        success = False
    
    if "Status" in schema.get("definitions", {}):
        status_def = schema["definitions"]["Status"]
        uri_prop = get_uri_property(status_def)
        if uri_prop:
            expected_statuses = ["http://example.org/test#Active", "http://example.org/test#Inactive"]
            
            if "enum" in uri_prop:
                # Closed set
                if all(status in uri_prop["enum"] for status in expected_statuses):
                    print("✅ SUCCESS: Status class has all expected individuals (closed enum)!")
                else:
                    print("❌ FAILED: Status class missing some individuals")
                    success = False
            elif "x-known-individuals" in uri_prop:
                # Open set
                if all(status in uri_prop["x-known-individuals"] for status in expected_statuses):
                    print("✅ SUCCESS: Status class has all expected individuals (open set)!")
                else:
                    print("❌ FAILED: Status class missing some individuals")
                    print(f"   Expected: {expected_statuses}")
                    print(f"   Got: {uri_prop['x-known-individuals']}")
                    success = False
            else:
                print("❌ FAILED: Status class has no individuals defined")
                success = False
        else:
            print("❌ FAILED: Status class has no uri property")
            success = False
    else:
        print("❌ FAILED: Status class not found in schema")
        success = False
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 ALL TESTS PASSED!")
    else:
        print("⚠️  SOME TESTS FAILED")
    print("=" * 60)
    
    return success


if __name__ == "__main__":
    test_individuals_in_schema()
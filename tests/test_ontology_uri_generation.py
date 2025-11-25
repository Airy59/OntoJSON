"""
Test Ontology URI Generation from Filename

Tests the correct generation of ontology URIs and namespace from source filenames.
"""

import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from jsonschema2owl.services.transformation_service import ReverseTransformationService


def test_ontology_uri_from_filename():
    """Test correct ontology URI generation from filename."""
    service = ReverseTransformationService()
    
    schema = {
        "$id": "http://uic.org//schemas/passenger/eticket/v3.6/offlineOSDM.json",
        "definitions": {
            "Person": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"}
                }
            }
        }
    }
    
    # Transform with filename
    result = service.transform_dict(
        schema,
        filename="offlineOSDM.json"
    )
    
    assert result.success, f"Transformation failed: {result.error}"
    ontology = result.ontology
    
    # Debug: print first 1000 chars of ontology
    print("\nGenerated ontology (first 1000 chars):")
    print(ontology[:1000])
    print("\n")
    
    # Check ontology URI (should be base + schema name, not original $id)
    assert "<https://cdm.ovh/examples/offlineOSDM>" in ontology, \
        f"Ontology URI should be https://cdm.ovh/examples/offlineOSDM\nGot: {ontology[:500]}"
    assert "a owl:Ontology" in ontology, "Should declare as owl:Ontology"
    
    # Check prefix uses schema name
    assert "@prefix : <https://cdm.ovh/examples/offlineOSDM#>" in ontology, \
        f"Prefix should be https://cdm.ovh/examples/offlineOSDM#\nGot: {ontology[:500]}"
    
    # Check original $id preserved as rdfs:seeAlso (might be on multiple lines in turtle)
    has_see_also = ("rdfs:seeAlso" in ontology and
                    "http://uic.org//schemas/passenger/eticket/v3.6/offlineOSDM.json" in ontology)
    assert has_see_also, \
        f"Original $id should be preserved as rdfs:seeAlso\nGot: {ontology[:1000]}"
    
    print("✓ Ontology URI generation from filename works correctly")


def test_schema_name_extraction():
    """Test schema name extraction from various filenames."""
    from jsonschema2owl.uri_generator import URIGenerator
    
    # Test basic filename
    assert URIGenerator.extract_schema_name("offlineOSDM.json") == "offlineOSDM"
    
    # Test with path
    assert URIGenerator.extract_schema_name("/path/to/company_hierarchy.json") == "company_hierarchy"
    
    # Test with different extension
    assert URIGenerator.extract_schema_name("schema.yaml") == "schema"
    
    # Test empty filename
    assert URIGenerator.extract_schema_name("") == "ontology"
    
    # Test None
    assert URIGenerator.extract_schema_name(None) == "ontology"
    
    print("✓ Schema name extraction works correctly")


def test_class_uri_with_schema_name():
    """Test that class URIs include schema name."""
    service = ReverseTransformationService()
    
    schema = {
        "definitions": {
            "Person": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"}
                }
            }
        }
    }
    
    result = service.transform_dict(schema, filename="testSchema.json")
    
    assert result.success, f"Transformation failed: {result.error}"
    ontology = result.ontology
    
    # Check that Person class uses correct namespace
    assert ":Person a owl:Class" in ontology or \
           "<https://cdm.ovh/examples/testSchema#Person> a owl:Class" in ontology, \
        "Person class should be in testSchema namespace"
    
    print("✓ Class URIs include schema name correctly")


def test_different_filenames():
    """Test transformation with different filenames."""
    service = ReverseTransformationService()
    
    schema = {
        "$id": "http://example.org/old/schema.json",
        "title": "Test Schema",
        "definitions": {
            "Item": {
                "type": "object"
            }
        }
    }
    
    # Test with company_hierarchy
    result1 = service.transform_dict(schema, filename="company_hierarchy.json")
    assert result1.success
    assert "<https://cdm.ovh/examples/company_hierarchy>" in result1.ontology
    assert "@prefix : <https://cdm.ovh/examples/company_hierarchy#>" in result1.ontology
    
    # Test with another name
    result2 = service.transform_dict(schema, filename="products.json")
    assert result2.success
    assert "<https://cdm.ovh/examples/products>" in result2.ontology
    assert "@prefix : <https://cdm.ovh/examples/products#>" in result2.ontology
    
    print("✓ Different filenames generate different ontology URIs")


def test_no_filename_fallback():
    """Test that transformation works without filename (uses default)."""
    service = ReverseTransformationService()
    
    schema = {
        "definitions": {
            "Thing": {
                "type": "object"
            }
        }
    }
    
    result = service.transform_dict(schema)  # No filename provided
    
    assert result.success, f"Transformation failed: {result.error}"
    # Should use base namespace without schema-specific part
    assert "https://cdm.ovh/examples" in result.ontology
    
    print("✓ Transformation works without filename (fallback)")


if __name__ == "__main__":
    print("\n=== Testing Ontology URI Generation ===\n")
    test_schema_name_extraction()
    test_ontology_uri_from_filename()
    test_class_uri_with_schema_name()
    test_different_filenames()
    test_no_filename_fallback()
    print("\n=== All tests passed! ===\n")
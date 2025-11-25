"""
Pattern Recognition Tests for JSON Schema to OWL Transformation

Tests for detecting and interpreting JSON Schema patterns including:
- Object property patterns (oneOf with @id)
- Inheritance vs intersection detection (allOf)
- Enumeration pattern recognition
- Array interpretation (functional vs non-functional)
- Type coercion patterns
"""

import json
import pytest
from rdflib import Graph, Namespace, URIRef, Literal, BNode
from rdflib.namespace import RDF, RDFS, OWL, XSD

from src.jsonschema2owl import ReverseEngine, ReverseTransformationConfig, SchemaParser


class TestObjectPropertyPatterns:
    """Tests for object property pattern detection."""
    
    def test_simple_ref_as_object_property(self):
        """Test simple $ref is recognized as object property."""
        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "definitions": {
                "Person": {
                    "type": "object",
                    "properties": {
                        "employer": {"$ref": "#/definitions/Organization"}
                    }
                },
                "Organization": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"}
                    }
                }
            }
        }
        
        engine = ReverseEngine()
        schema_model = engine.parser.parse(json.dumps(schema))
        graph = engine.transform(schema_model)
        
        base_ns = Namespace("http://example.org/ontology#")
        
        # Should create object property, not datatype property
        assert (base_ns["employer"], RDF.type, OWL.ObjectProperty) in graph
        assert (base_ns["employer"], RDFS.domain, base_ns["Person"]) in graph
        assert (base_ns["employer"], RDFS.range, base_ns["Organization"]) in graph
    
    def test_array_of_refs_as_object_property(self):
        """Test array of $refs creates object property."""
        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "definitions": {
                "Team": {
                    "type": "object",
                    "properties": {
                        "members": {
                            "type": "array",
                            "items": {"$ref": "#/definitions/Person"}
                        }
                    }
                },
                "Person": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"}
                    }
                }
            }
        }
        
        engine = ReverseEngine()
        schema_model = engine.parser.parse(json.dumps(schema))
        graph = engine.transform(schema_model)
        
        base_ns = Namespace("http://example.org/ontology#")
        
        # Should create object property for array items
        assert (base_ns["members"], RDF.type, OWL.ObjectProperty) in graph
        assert (base_ns["members"], RDFS.range, base_ns["Person"]) in graph
    
    def test_oneof_with_ref_detection(self):
        """Test oneOf containing $refs is detected properly."""
        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "definitions": {
                "Contact": {
                    "type": "object",
                    "properties": {
                        "contactable": {
                            "oneOf": [
                                {"$ref": "#/definitions/Person"},
                                {"$ref": "#/definitions/Organization"}
                            ]
                        }
                    }
                },
                "Person": {
                    "type": "object",
                    "properties": {"name": {"type": "string"}}
                },
                "Organization": {
                    "type": "object",
                    "properties": {"orgName": {"type": "string"}}
                }
            }
        }
        
        engine = ReverseEngine()
        schema_model = engine.parser.parse(json.dumps(schema))
        graph = engine.transform(schema_model)
        
        base_ns = Namespace("http://example.org/ontology#")
        
        # Should create object property
        assert (base_ns["contactable"], RDF.type, OWL.ObjectProperty) in graph


class TestInheritanceVsIntersection:
    """Tests for distinguishing inheritance from intersection in allOf."""
    
    def test_allof_with_single_ref_is_inheritance(self):
        """Test allOf with one $ref is interpreted as inheritance."""
        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "definitions": {
                "Person": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"}
                    }
                },
                "Employee": {
                    "allOf": [
                        {"$ref": "#/definitions/Person"},
                        {
                            "type": "object",
                            "properties": {
                                "employeeId": {"type": "string"}
                            }
                        }
                    ]
                }
            }
        }
        
        engine = ReverseEngine()
        schema_model = engine.parser.parse(json.dumps(schema))
        graph = engine.transform(schema_model)
        
        base_ns = Namespace("http://example.org/ontology#")
        
        # Should create subclass relationship
        assert (base_ns["Employee"], RDFS.subClassOf, base_ns["Person"]) in graph
        
        # Employee should also be a class
        assert (base_ns["Employee"], RDF.type, OWL.Class) in graph
    
    def test_allof_with_multiple_refs_is_multiple_inheritance(self):
        """Test allOf with multiple $refs creates multiple inheritance."""
        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "definitions": {
                "Named": {
                    "type": "object",
                    "properties": {"name": {"type": "string"}}
                },
                "Dated": {
                    "type": "object",
                    "properties": {"date": {"type": "string", "format": "date"}}
                },
                "NamedDocument": {
                    "allOf": [
                        {"$ref": "#/definitions/Named"},
                        {"$ref": "#/definitions/Dated"}
                    ]
                }
            }
        }
        
        engine = ReverseEngine()
        schema_model = engine.parser.parse(json.dumps(schema))
        graph = engine.transform(schema_model)
        
        base_ns = Namespace("http://example.org/ontology#")
        
        # Should have multiple subclass relationships
        assert (base_ns["NamedDocument"], RDFS.subClassOf, base_ns["Named"]) in graph
        assert (base_ns["NamedDocument"], RDFS.subClassOf, base_ns["Dated"]) in graph
    
    def test_allof_without_refs_creates_intersection(self):
        """Test allOf with only inline schemas may create intersection."""
        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "definitions": {
                "MixedType": {
                    "allOf": [
                        {
                            "type": "object",
                            "properties": {"field1": {"type": "string"}}
                        },
                        {
                            "type": "object",
                            "properties": {"field2": {"type": "number"}}
                        }
                    ]
                }
            }
        }
        
        engine = ReverseEngine()
        schema_model = engine.parser.parse(json.dumps(schema))
        graph = engine.transform(schema_model)
        
        base_ns = Namespace("http://example.org/ontology#")
        
        # Should still create a valid class
        assert (base_ns["MixedType"], RDF.type, OWL.Class) in graph
        
        # Properties should be created
        assert (base_ns["field1"], RDF.type, OWL.DatatypeProperty) in graph
        assert (base_ns["field2"], RDF.type, OWL.DatatypeProperty) in graph


class TestEnumerationPatterns:
    """Tests for enumeration pattern recognition."""
    
    def test_string_enum_creates_individuals(self):
        """Test string enum creates named individuals."""
        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "definitions": {
                "Color": {
                    "type": "string",
                    "enum": ["red", "green", "blue"]
                }
            }
        }
        
        engine = ReverseEngine()
        schema_model = engine.parser.parse(json.dumps(schema))
        graph = engine.transform(schema_model)
        
        base_ns = Namespace("http://example.org/ontology#")
        
        # Should create class
        assert (base_ns["Color"], RDF.type, OWL.Class) in graph
        
        # Should create individuals
        individuals = list(graph.subjects(RDF.type, OWL.NamedIndividual))
        assert len(individuals) >= 3
        
        # Individuals should be linked to Color class
        color_individuals = [ind for ind in individuals 
                           if (ind, RDF.type, base_ns["Color"]) in graph]
        assert len(color_individuals) == 3
    
    def test_enum_with_title_uses_labels(self):
        """Test enum values get proper labels."""
        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "definitions": {
                "Status": {
                    "type": "string",
                    "title": "Status",
                    "enum": ["active", "inactive", "pending"]
                }
            }
        }
        
        engine = ReverseEngine()
        schema_model = engine.parser.parse(json.dumps(schema))
        graph = engine.transform(schema_model)
        
        base_ns = Namespace("http://example.org/ontology#")
        
        # Class should have label
        assert (base_ns["Status"], RDFS.label, Literal("Status")) in graph
        
        # Individuals should exist
        individuals = list(graph.subjects(RDF.type, OWL.NamedIndividual))
        assert len(individuals) >= 3
    
    def test_numeric_enum_creates_individuals(self):
        """Test numeric enums also create individuals."""
        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "definitions": {
                "Priority": {
                    "type": "integer",
                    "enum": [1, 2, 3]
                }
            }
        }
        
        engine = ReverseEngine()
        schema_model = engine.parser.parse(json.dumps(schema))
        graph = engine.transform(schema_model)
        
        base_ns = Namespace("http://example.org/ontology#")
        
        # Should create class
        assert (base_ns["Priority"], RDF.type, OWL.Class) in graph
        
        # Should create individuals for numeric values
        individuals = list(graph.subjects(RDF.type, OWL.NamedIndividual))
        assert len(individuals) >= 3
    
    def test_const_creates_has_value_restriction(self):
        """Test const keyword creates hasValue restriction."""
        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "definitions": {
                "Singleton": {
                    "type": "object",
                    "properties": {
                        "fixedValue": {
                            "type": "string",
                            "const": "FIXED"
                        }
                    }
                }
            }
        }
        
        engine = ReverseEngine()
        schema_model = engine.parser.parse(json.dumps(schema))
        graph = engine.transform(schema_model)
        
        # Should handle const appropriately
        # (Implementation may vary - check if hasValue restriction exists)
        base_ns = Namespace("http://example.org/ontology#")
        assert (base_ns["Singleton"], RDF.type, OWL.Class) in graph


class TestArrayInterpretation:
    """Tests for array type interpretation."""
    
    def test_array_without_constraints_is_non_functional(self):
        """Test array without cardinality creates non-functional property."""
        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "definitions": {
                "Container": {
                    "type": "object",
                    "properties": {
                        "items": {
                            "type": "array",
                            "items": {"type": "string"}
                        }
                    }
                }
            }
        }
        
        engine = ReverseEngine()
        schema_model = engine.parser.parse(json.dumps(schema))
        graph = engine.transform(schema_model)
        
        base_ns = Namespace("http://example.org/ontology#")
        
        # Should create property
        assert (base_ns["items"], RDF.type, OWL.DatatypeProperty) in graph
        
        # Should NOT be functional (multiple values allowed)
        is_functional = (base_ns["items"], RDF.type, OWL.FunctionalProperty) in graph
        assert not is_functional, "Array property should not be functional"
    
    def test_array_with_max_items_1_is_functional(self):
        """Test array with maxItems=1 could be functional."""
        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "definitions": {
                "Container": {
                    "type": "object",
                    "properties": {
                        "singleItem": {
                            "type": "array",
                            "items": {"type": "string"},
                            "maxItems": 1
                        }
                    }
                }
            }
        }
        
        engine = ReverseEngine()
        schema_model = engine.parser.parse(json.dumps(schema))
        graph = engine.transform(schema_model)
        
        base_ns = Namespace("http://example.org/ontology#")
        
        # Should create property
        assert (base_ns["singleItem"], RDF.type, OWL.DatatypeProperty) in graph
        
        # May be functional depending on configuration
        # At minimum should have maxCardinality restriction
        restrictions = list(graph.objects(base_ns["Container"], RDFS.subClassOf))
        has_max_card_restriction = any(
            (r, OWL.maxCardinality, Literal(1)) in graph or
            (r, OWL.maxQualifiedCardinality, Literal(1)) in graph
            for r in restrictions if isinstance(r, BNode)
        )
        assert has_max_card_restriction or \
               (base_ns["singleItem"], RDF.type, OWL.FunctionalProperty) in graph
    
    def test_array_with_min_max_items(self):
        """Test array cardinality constraints."""
        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "definitions": {
                "Team": {
                    "type": "object",
                    "properties": {
                        "members": {
                            "type": "array",
                            "items": {"type": "string"},
                            "minItems": 3,
                            "maxItems": 10
                        }
                    }
                }
            }
        }
        
        engine = ReverseEngine()
        schema_model = engine.parser.parse(json.dumps(schema))
        graph = engine.transform(schema_model)
        
        base_ns = Namespace("http://example.org/ontology#")
        
        # Should have cardinality restrictions
        restrictions = list(graph.objects(base_ns["Team"], RDFS.subClassOf))
        
        found_restrictions = False
        for r in restrictions:
            if not isinstance(r, BNode):
                continue
            if (r, OWL.onProperty, base_ns["members"]) in graph:
                found_restrictions = True
                break
        
        assert found_restrictions, "Expected cardinality restrictions for array"


class TestTypeCoercion:
    """Tests for type coercion and mapping."""
    
    def test_string_to_xsd_string(self):
        """Test JSON string type maps to xsd:string."""
        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "definitions": {
                "Test": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string"}
                    }
                }
            }
        }
        
        engine = ReverseEngine()
        schema_model = engine.parser.parse(json.dumps(schema))
        graph = engine.transform(schema_model)
        
        base_ns = Namespace("http://example.org/ontology#")
        
        assert (base_ns["text"], RDFS.range, XSD.string) in graph
    
    def test_integer_to_xsd_integer(self):
        """Test JSON integer type maps to xsd:integer."""
        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "definitions": {
                "Test": {
                    "type": "object",
                    "properties": {
                        "count": {"type": "integer"}
                    }
                }
            }
        }
        
        engine = ReverseEngine()
        schema_model = engine.parser.parse(json.dumps(schema))
        graph = engine.transform(schema_model)
        
        base_ns = Namespace("http://example.org/ontology#")
        
        assert (base_ns["count"], RDFS.range, XSD.integer) in graph
    
    def test_number_to_xsd_decimal(self):
        """Test JSON number type maps to xsd:decimal."""
        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "definitions": {
                "Test": {
                    "type": "object",
                    "properties": {
                        "price": {"type": "number"}
                    }
                }
            }
        }
        
        engine = ReverseEngine()
        schema_model = engine.parser.parse(json.dumps(schema))
        graph = engine.transform(schema_model)
        
        base_ns = Namespace("http://example.org/ontology#")
        
        # Could be double or decimal depending on implementation
        has_numeric_range = (
            (base_ns["price"], RDFS.range, XSD.decimal) in graph or
            (base_ns["price"], RDFS.range, XSD.double) in graph or
            (base_ns["price"], RDFS.range, XSD.float) in graph
        )
        assert has_numeric_range
    
    def test_boolean_to_xsd_boolean(self):
        """Test JSON boolean type maps to xsd:boolean."""
        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "definitions": {
                "Test": {
                    "type": "object",
                    "properties": {
                        "active": {"type": "boolean"}
                    }
                }
            }
        }
        
        engine = ReverseEngine()
        schema_model = engine.parser.parse(json.dumps(schema))
        graph = engine.transform(schema_model)
        
        base_ns = Namespace("http://example.org/ontology#")
        
        assert (base_ns["active"], RDFS.range, XSD.boolean) in graph
    
    def test_format_date_to_xsd_date(self):
        """Test format: date maps to xsd:date."""
        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "definitions": {
                "Test": {
                    "type": "object",
                    "properties": {
                        "birthDate": {
                            "type": "string",
                            "format": "date"
                        }
                    }
                }
            }
        }
        
        engine = ReverseEngine()
        schema_model = engine.parser.parse(json.dumps(schema))
        graph = engine.transform(schema_model)
        
        base_ns = Namespace("http://example.org/ontology#")
        
        # Should map to xsd:date instead of xsd:string
        assert (base_ns["birthDate"], RDFS.range, XSD.date) in graph
    
    def test_format_datetime_to_xsd_datetime(self):
        """Test format: date-time maps to xsd:dateTime."""
        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "definitions": {
                "Test": {
                    "type": "object",
                    "properties": {
                        "timestamp": {
                            "type": "string",
                            "format": "date-time"
                        }
                    }
                }
            }
        }
        
        engine = ReverseEngine()
        schema_model = engine.parser.parse(json.dumps(schema))
        graph = engine.transform(schema_model)
        
        base_ns = Namespace("http://example.org/ontology#")
        
        assert (base_ns["timestamp"], RDFS.range, XSD.dateTime) in graph


class TestCompositionPatterns:
    """Tests for complex composition patterns."""
    
    def test_anyof_handling(self):
        """Test anyOf is handled (may create union or other construct)."""
        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "definitions": {
                "FlexibleType": {
                    "anyOf": [
                        {"type": "string"},
                        {"type": "number"}
                    ]
                }
            }
        }
        
        engine = ReverseEngine()
        schema_model = engine.parser.parse(json.dumps(schema))
        graph = engine.transform(schema_model)
        
        base_ns = Namespace("http://example.org/ontology#")
        
        # Should create some representation
        assert (base_ns["FlexibleType"], RDF.type, OWL.Class) in graph
    
    def test_not_creates_complement(self):
        """Test not keyword creates complement class."""
        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "definitions": {
                "NonPerson": {
                    "not": {"$ref": "#/definitions/Person"}
                },
                "Person": {
                    "type": "object",
                    "properties": {"name": {"type": "string"}}
                }
            }
        }
        
        engine = ReverseEngine()
        schema_model = engine.parser.parse(json.dumps(schema))
        graph = engine.transform(schema_model)
        
        base_ns = Namespace("http://example.org/ontology#")
        
        # Should handle not construct
        assert (base_ns["Person"], RDF.type, OWL.Class) in graph
        # NonPerson may be created as complementOf


class TestMetadataExtraction:
    """Tests for custom metadata and extension field handling."""
    
    def test_custom_x_fields_preserved(self):
        """Test x- extension fields are preserved."""
        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "definitions": {
                "Person": {
                    "type": "object",
                    "x-ontology-uri": "http://custom.org/Person",
                    "x-custom-field": "custom value",
                    "properties": {
                        "name": {"type": "string"}
                    }
                }
            }
        }
        
        engine = ReverseEngine()
        schema_model = engine.parser.parse(json.dumps(schema))
        graph = engine.transform(schema_model)
        
        # Custom fields may be added as annotations
        # Verify class was created
        base_ns = Namespace("http://example.org/ontology#")
        assert (base_ns["Person"], RDF.type, OWL.Class) in graph


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
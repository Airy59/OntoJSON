"""
Integration Tests for JSON Schema to OWL2 Transformation

Comprehensive end-to-end tests covering complex scenarios like:
- Nested object structures
- Multiple inheritance (allOf)
- Union types (oneOf)
- Enumerations
- Complex cardinality constraints
- Round-trip testing
"""

import json
import pytest
from rdflib import Graph, Namespace, URIRef, Literal, BNode
from rdflib.namespace import RDF, RDFS, OWL, XSD

from src.jsonschema2owl import ReverseEngine, ReverseTransformationConfig, SchemaParser


class TestComplexObjectStructures:
    """Tests for nested and complex object structures."""
    
    def test_nested_objects(self):
        """Test transformation of nested object structures."""
        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "$id": "http://example.org/nested-schema",
            "definitions": {
                "Address": {
                    "type": "object",
                    "title": "Address",
                    "properties": {
                        "street": {"type": "string"},
                        "city": {"type": "string"},
                        "zipCode": {"type": "string"}
                    },
                    "required": ["city"]
                },
                "Person": {
                    "type": "object",
                    "title": "Person",
                    "properties": {
                        "name": {"type": "string"},
                        "homeAddress": {"$ref": "#/definitions/Address"},
                        "workAddress": {"$ref": "#/definitions/Address"}
                    },
                    "required": ["name", "homeAddress"]
                }
            }
        }
        
        engine = ReverseEngine()
        schema_model = engine.parser.parse(json.dumps(schema))
        graph = engine.transform(schema_model)
        
        base_ns = Namespace("http://example.org/ontology#")
        
        # Verify classes exist
        assert (base_ns["Person"], RDF.type, OWL.Class) in graph
        assert (base_ns["Address"], RDF.type, OWL.Class) in graph
        
        # Verify object properties exist
        assert (base_ns["homeAddress"], RDF.type, OWL.ObjectProperty) in graph
        assert (base_ns["workAddress"], RDF.type, OWL.ObjectProperty) in graph
        
        # Verify domains and ranges
        assert (base_ns["homeAddress"], RDFS.domain, base_ns["Person"]) in graph
        assert (base_ns["homeAddress"], RDFS.range, base_ns["Address"]) in graph
        
        # Verify required property has cardinality constraint
        person_restrictions = list(graph.objects(base_ns["Person"], RDFS.subClassOf))
        has_home_address_restriction = any(
            (r, OWL.onProperty, base_ns["homeAddress"]) in graph
            for r in person_restrictions if isinstance(r, BNode)
        )
        assert has_home_address_restriction


class TestInheritancePatterns:
    """Tests for inheritance patterns using allOf."""
    
    def test_simple_inheritance(self):
        """Test simple class inheritance via allOf."""
        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "definitions": {
                "Person": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "age": {"type": "integer"}
                    }
                },
                "Employee": {
                    "allOf": [
                        {"$ref": "#/definitions/Person"},
                        {
                            "type": "object",
                            "properties": {
                                "employeeId": {"type": "string"},
                                "department": {"type": "string"}
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
        
        # Verify both classes exist
        assert (base_ns["Person"], RDF.type, OWL.Class) in graph
        assert (base_ns["Employee"], RDF.type, OWL.Class) in graph
        
        # Verify inheritance relationship
        assert (base_ns["Employee"], RDFS.subClassOf, base_ns["Person"]) in graph
        
        # Verify Employee has its own properties
        assert (base_ns["employeeId"], RDF.type, OWL.DatatypeProperty) in graph
        assert (base_ns["department"], RDF.type, OWL.DatatypeProperty) in graph
    
    def test_multiple_inheritance(self):
        """Test multiple inheritance via allOf with multiple $refs."""
        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "definitions": {
                "Named": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"}
                    }
                },
                "Timestamped": {
                    "type": "object",
                    "properties": {
                        "createdAt": {"type": "string", "format": "date-time"},
                        "updatedAt": {"type": "string", "format": "date-time"}
                    }
                },
                "Document": {
                    "allOf": [
                        {"$ref": "#/definitions/Named"},
                        {"$ref": "#/definitions/Timestamped"},
                        {
                            "type": "object",
                            "properties": {
                                "content": {"type": "string"}
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
        
        # Verify all classes exist
        assert (base_ns["Named"], RDF.type, OWL.Class) in graph
        assert (base_ns["Timestamped"], RDF.type, OWL.Class) in graph
        assert (base_ns["Document"], RDF.type, OWL.Class) in graph
        
        # Verify multiple inheritance
        assert (base_ns["Document"], RDFS.subClassOf, base_ns["Named"]) in graph
        assert (base_ns["Document"], RDFS.subClassOf, base_ns["Timestamped"]) in graph


class TestUnionTypes:
    """Tests for union type patterns using oneOf."""
    
    def test_oneof_union(self):
        """Test oneOf creates union class."""
        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "definitions": {
                "Car": {
                    "type": "object",
                    "properties": {
                        "wheels": {"type": "integer"}
                    }
                },
                "Boat": {
                    "type": "object",
                    "properties": {
                        "draft": {"type": "number"}
                    }
                },
                "Vehicle": {
                    "oneOf": [
                        {"$ref": "#/definitions/Car"},
                        {"$ref": "#/definitions/Boat"}
                    ]
                }
            }
        }
        
        engine = ReverseEngine()
        schema_model = engine.parser.parse(json.dumps(schema))
        graph = engine.transform(schema_model)
        
        base_ns = Namespace("http://example.org/ontology#")
        
        # Verify all classes exist
        assert (base_ns["Car"], RDF.type, OWL.Class) in graph
        assert (base_ns["Boat"], RDF.type, OWL.Class) in graph
        assert (base_ns["Vehicle"], RDF.type, OWL.Class) in graph
        
        # Check for unionOf construct
        has_union = False
        for s, p, o in graph.triples((base_ns["Vehicle"], OWL.unionOf, None)):
            has_union = True
            break
        
        assert has_union, "Expected Vehicle to have unionOf construct"


class TestEnumerations:
    """Tests for enumeration patterns."""
    
    def test_string_enum(self):
        """Test string enumeration creates individuals."""
        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "definitions": {
                "Status": {
                    "type": "string",
                    "title": "Status",
                    "enum": ["draft", "published", "archived"]
                }
            }
        }
        
        engine = ReverseEngine()
        schema_model = engine.parser.parse(json.dumps(schema))
        graph = engine.transform(schema_model)
        
        base_ns = Namespace("http://example.org/ontology#")
        
        # Verify Status class exists
        assert (base_ns["Status"], RDF.type, OWL.Class) in graph
        
        # Verify individuals exist
        individuals = list(graph.subjects(RDF.type, OWL.NamedIndividual))
        assert len(individuals) >= 3
        
        # Check for oneOf enumeration pattern
        has_oneof = False
        for equiv_class in graph.objects(base_ns["Status"], OWL.equivalentClass):
            if (equiv_class, OWL.oneOf, None) in graph:
                has_oneof = True
                break
        
        assert has_oneof, "Expected Status to have oneOf enumeration"
    
    def test_integer_enum(self):
        """Test integer enumeration."""
        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "definitions": {
                "Priority": {
                    "type": "integer",
                    "title": "Priority Level",
                    "enum": [1, 2, 3, 4, 5]
                }
            }
        }
        
        engine = ReverseEngine()
        schema_model = engine.parser.parse(json.dumps(schema))
        graph = engine.transform(schema_model)
        
        base_ns = Namespace("http://example.org/ontology#")
        
        # Verify Priority class exists
        assert (base_ns["Priority"], RDF.type, OWL.Class) in graph
        
        # Verify individuals exist (one for each enum value)
        individuals = list(graph.subjects(RDF.type, OWL.NamedIndividual))
        assert len(individuals) >= 5


class TestCardinalityConstraints:
    """Tests for complex cardinality constraints."""
    
    def test_array_cardinality(self):
        """Test array min/max items translates to cardinality."""
        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "definitions": {
                "Team": {
                    "type": "object",
                    "properties": {
                        "members": {
                            "type": "array",
                            "items": {"$ref": "#/definitions/Person"},
                            "minItems": 2,
                            "maxItems": 5
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
        
        # Find restrictions on Team class
        restrictions = list(graph.objects(base_ns["Team"], RDFS.subClassOf))
        
        # Look for cardinality restrictions on members property
        found_min = False
        found_max = False
        
        for restriction in restrictions:
            if not isinstance(restriction, BNode):
                continue
            
            # Check if this restriction is about members property
            on_property = list(graph.objects(restriction, OWL.onProperty))
            if base_ns["members"] not in on_property:
                continue
            
            # Check for min/max cardinality
            min_card = list(graph.objects(restriction, OWL.minQualifiedCardinality))
            if not min_card:
                min_card = list(graph.objects(restriction, OWL.minCardinality))
            
            max_card = list(graph.objects(restriction, OWL.maxQualifiedCardinality))
            if not max_card:
                max_card = list(graph.objects(restriction, OWL.maxCardinality))
            
            if min_card and Literal(2) in min_card:
                found_min = True
            if max_card and Literal(5) in max_card:
                found_max = True
        
        assert found_min, "Expected to find minCardinality of 2"
        assert found_max, "Expected to find maxCardinality of 5"
    
    def test_required_property_exact_cardinality(self):
        """Test required property gets exact cardinality of 1."""
        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "definitions": {
                "Person": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "email": {"type": "string"}
                    },
                    "required": ["name"]
                }
            }
        }
        
        engine = ReverseEngine()
        schema_model = engine.parser.parse(json.dumps(schema))
        graph = engine.transform(schema_model)
        
        base_ns = Namespace("http://example.org/ontology#")
        
        # Find cardinality restriction for name property
        restrictions = list(graph.objects(base_ns["Person"], RDFS.subClassOf))
        
        found_name_cardinality = False
        for restriction in restrictions:
            if not isinstance(restriction, BNode):
                continue
            
            on_property = list(graph.objects(restriction, OWL.onProperty))
            if base_ns["name"] not in on_property:
                continue
            
            # Check for exact cardinality of 1
            exact_card = list(graph.objects(restriction, OWL.cardinality))
            if Literal(1) in exact_card:
                found_name_cardinality = True
                break
        
        assert found_name_cardinality, "Expected exact cardinality of 1 for required 'name' property"


class TestRoundTripTransformation:
    """Tests for round-trip consistency (JSON Schema → OWL → JSON Schema)."""
    
    def test_basic_class_preservation(self):
        """Test basic classes are preserved in round-trip."""
        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "definitions": {
                "Person": {
                    "type": "object",
                    "title": "Person",
                    "description": "A human being",
                    "properties": {
                        "name": {"type": "string"},
                        "age": {"type": "integer"}
                    }
                }
            }
        }
        
        # Transform to OWL
        engine = ReverseEngine()
        schema_model = engine.parser.parse(json.dumps(schema))
        graph = engine.transform(schema_model)
        
        # Verify essential elements are in RDF graph
        base_ns = Namespace("http://example.org/ontology#")
        
        # Class preservation
        assert (base_ns["Person"], RDF.type, OWL.Class) in graph
        assert (base_ns["Person"], RDFS.label, Literal("Person")) in graph
        assert (base_ns["Person"], RDFS.comment, Literal("A human being")) in graph
        
        # Property preservation
        assert (base_ns["name"], RDF.type, OWL.DatatypeProperty) in graph
        assert (base_ns["age"], RDF.type, OWL.DatatypeProperty) in graph


class TestEdgeCases:
    """Tests for edge cases and special scenarios."""
    
    def test_empty_definitions(self):
        """Test schema with empty definitions object."""
        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "definitions": {}
        }
        
        engine = ReverseEngine()
        schema_model = engine.parser.parse(json.dumps(schema))
        graph = engine.transform(schema_model)
        
        # Should create valid ontology even with no classes
        ontology_nodes = list(graph.subjects(RDF.type, OWL.Ontology))
        assert len(ontology_nodes) > 0
    
    def test_root_level_properties(self):
        """Test schema with root-level properties (no definitions)."""
        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "value": {"type": "number"}
            }
        }
        
        engine = ReverseEngine()
        schema_model = engine.parser.parse(json.dumps(schema))
        graph = engine.transform(schema_model)
        
        # Should handle gracefully
        ontology_nodes = list(graph.subjects(RDF.type, OWL.Ontology))
        assert len(ontology_nodes) > 0
    
    def test_circular_references(self):
        """Test schema with circular references."""
        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "definitions": {
                "Node": {
                    "type": "object",
                    "properties": {
                        "value": {"type": "string"},
                        "next": {"$ref": "#/definitions/Node"}
                    }
                }
            }
        }
        
        engine = ReverseEngine()
        schema_model = engine.parser.parse(json.dumps(schema))
        graph = engine.transform(schema_model)
        
        base_ns = Namespace("http://example.org/ontology#")
        
        # Should create self-referencing property
        assert (base_ns["Node"], RDF.type, OWL.Class) in graph
        assert (base_ns["next"], RDF.type, OWL.ObjectProperty) in graph
        assert (base_ns["next"], RDFS.domain, base_ns["Node"]) in graph
        assert (base_ns["next"], RDFS.range, base_ns["Node"]) in graph
    
    def test_special_characters_in_names(self):
        """Test handling of special characters in property names."""
        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "definitions": {
                "Test": {
                    "type": "object",
                    "properties": {
                        "property-with-dashes": {"type": "string"},
                        "property_with_underscores": {"type": "string"},
                        "propertyWithCamelCase": {"type": "string"}
                    }
                }
            }
        }
        
        engine = ReverseEngine()
        schema_model = engine.parser.parse(json.dumps(schema))
        graph = engine.transform(schema_model)
        
        # Should create valid URIs for all properties
        base_ns = Namespace("http://example.org/ontology#")
        assert (base_ns["Test"], RDF.type, OWL.Class) in graph
        
        # Properties should exist (URI generation may normalize names)
        properties = list(graph.subjects(RDF.type, OWL.DatatypeProperty))
        assert len(properties) >= 3


class TestComplexRealWorldScenarios:
    """Tests using realistic, complex schemas."""
    
    def test_company_hierarchy_schema(self):
        """Test complex company hierarchy with multiple relationships."""
        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "$id": "http://example.org/company-schema",
            "definitions": {
                "Organization": {
                    "type": "object",
                    "title": "Organization",
                    "properties": {
                        "name": {"type": "string"},
                        "founded": {"type": "string", "format": "date"}
                    },
                    "required": ["name"]
                },
                "Department": {
                    "allOf": [
                        {
                            "type": "object",
                            "properties": {
                                "departmentCode": {"type": "string"},
                                "budget": {"type": "number"}
                            }
                        }
                    ]
                },
                "Employee": {
                    "type": "object",
                    "title": "Employee",
                    "properties": {
                        "employeeId": {"type": "string"},
                        "name": {"type": "string"},
                        "position": {
                            "type": "string",
                            "enum": ["engineer", "manager", "director", "executive"]
                        },
                        "worksFor": {"$ref": "#/definitions/Organization"},
                        "manages": {
                            "type": "array",
                            "items": {"$ref": "#/definitions/Employee"}
                        }
                    },
                    "required": ["employeeId", "name", "worksFor"]
                }
            }
        }
        
        engine = ReverseEngine()
        schema_model = engine.parser.parse(json.dumps(schema))
        graph = engine.transform(schema_model)
        
        base_ns = Namespace("http://example.org/ontology#")
        
        # Verify all classes
        assert (base_ns["Organization"], RDF.type, OWL.Class) in graph
        assert (base_ns["Department"], RDF.type, OWL.Class) in graph
        assert (base_ns["Employee"], RDF.type, OWL.Class) in graph
        
        # Verify object properties
        assert (base_ns["worksFor"], RDF.type, OWL.ObjectProperty) in graph
        assert (base_ns["manages"], RDF.type, OWL.ObjectProperty) in graph
        
        # Verify enumeration created individuals
        individuals = list(graph.subjects(RDF.type, OWL.NamedIndividual))
        assert len(individuals) >= 4  # At least 4 position types
        
        # Verify required properties have constraints
        restrictions = list(graph.objects(base_ns["Employee"], RDFS.subClassOf))
        assert len(restrictions) > 0


class TestConfigurationOptions:
    """Tests for different configuration options."""
    
    def test_custom_namespace(self):
        """Test using custom namespace."""
        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "definitions": {
                "Test": {
                    "type": "object",
                    "properties": {
                        "value": {"type": "string"}
                    }
                }
            }
        }
        
        config = ReverseTransformationConfig({
            "namespace": {
                "base": "http://custom.org/myonto#"
            }
        })
        
        engine = ReverseEngine(config)
        schema_model = engine.parser.parse(json.dumps(schema))
        graph = engine.transform(schema_model)
        
        # Verify custom namespace is used
        custom_ns = Namespace("http://custom.org/myonto#")
        assert (custom_ns["Test"], RDF.type, OWL.Class) in graph
    
    def test_different_output_formats(self):
        """Test different serialization formats."""
        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "definitions": {
                "Test": {"type": "object"}
            }
        }
        
        engine = ReverseEngine()
        schema_model = engine.parser.parse(json.dumps(schema))
        graph = engine.transform(schema_model)
        
        # Test multiple formats
        formats = ["turtle", "xml", "json-ld", "nt"]
        for fmt in formats:
            serialized = engine.serialize(graph, format=fmt)
            assert serialized is not None
            assert len(serialized) > 0
            
            # Verify it can be parsed back
            test_graph = Graph()
            test_graph.parse(data=serialized, format=fmt)
            assert len(test_graph) > 0


class TestLargeSchemas:
    """Performance and correctness tests for large schemas."""
    
    def test_many_definitions(self):
        """Test schema with many definitions."""
        # Create schema with 50 classes
        definitions = {}
        for i in range(50):
            definitions[f"Class{i}"] = {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "value": {"type": "number"}
                }
            }
        
        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "definitions": definitions
        }
        
        engine = ReverseEngine()
        schema_model = engine.parser.parse(json.dumps(schema))
        graph = engine.transform(schema_model)
        
        # Verify all classes were created
        classes = list(graph.subjects(RDF.type, OWL.Class))
        assert len(classes) >= 50
    
    def test_deeply_nested_structure(self):
        """Test deeply nested object structure."""
        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "definitions": {
                "Level0": {
                    "type": "object",
                    "properties": {
                        "child": {"$ref": "#/definitions/Level1"}
                    }
                },
                "Level1": {
                    "type": "object",
                    "properties": {
                        "child": {"$ref": "#/definitions/Level2"}
                    }
                },
                "Level2": {
                    "type": "object",
                    "properties": {
                        "child": {"$ref": "#/definitions/Level3"}
                    }
                },
                "Level3": {
                    "type": "object",
                    "properties": {
                        "value": {"type": "string"}
                    }
                }
            }
        }
        
        engine = ReverseEngine()
        schema_model = engine.parser.parse(json.dumps(schema))
        graph = engine.transform(schema_model)
        
        base_ns = Namespace("http://example.org/ontology#")
        
        # Verify all levels exist
        for i in range(4):
            assert (base_ns[f"Level{i}"], RDF.type, OWL.Class) in graph

class TestPropertyNameScoping:
    """Tests for property name scoping to avoid URI collisions."""
    
    def test_same_property_name_different_classes_scoped(self):
        """Test that properties with same name in different classes get distinct scoped URIs."""
        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "definitions": {
                "ServiceConstraintDef": {
                    "type": "object",
                    "properties": {
                        "legacyCode": {"type": "integer"}
                    }
                },
                "CarrierGroup": {
                    "type": "object",
                    "properties": {
                        "legacyCode": {"type": "string"}
                    }
                }
            }
        }
        
        # Use default scoped naming strategy
        config = ReverseTransformationConfig()
        engine = ReverseEngine(config)
        schema_model = engine.parser.parse(json.dumps(schema))
        graph = engine.transform(schema_model)
        
        base_ns = Namespace("http://example.org/ontology#")
        
        # Verify both classes exist
        assert (base_ns["ServiceConstraintDef"], RDF.type, OWL.Class) in graph
        assert (base_ns["CarrierGroup"], RDF.type, OWL.Class) in graph
        
        # Verify distinct scoped properties exist with ClassName_propertyName pattern
        assert (base_ns["ServiceConstraintDef_legacyCode"], RDF.type, OWL.DatatypeProperty) in graph
        assert (base_ns["CarrierGroup_legacyCode"], RDF.type, OWL.DatatypeProperty) in graph
        
        # Verify each property has correct domain
        assert (base_ns["ServiceConstraintDef_legacyCode"], RDFS.domain, base_ns["ServiceConstraintDef"]) in graph
        assert (base_ns["CarrierGroup_legacyCode"], RDFS.domain, base_ns["CarrierGroup"]) in graph
        
        # Verify each property has correct range
        assert (base_ns["ServiceConstraintDef_legacyCode"], RDFS.range, XSD.integer) in graph
        assert (base_ns["CarrierGroup_legacyCode"], RDFS.range, XSD.string) in graph
    
    def test_same_property_name_different_classes_reverse_scoped(self):
        """Test reverse scoped naming strategy: propertyName_ClassName."""
        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "definitions": {
                "Employee": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"}
                    }
                },
                "Department": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"}
                    }
                }
            }
        }
        
        # Use reverse_scoped naming strategy
        config = ReverseTransformationConfig()
        config.set_property_naming_strategy("reverse_scoped")
        
        engine = ReverseEngine(config)
        schema_model = engine.parser.parse(json.dumps(schema))
        graph = engine.transform(schema_model)
        
        base_ns = Namespace("http://example.org/ontology#")
        
        # Verify reverse scoped properties exist with propertyName_ClassName pattern
        assert (base_ns["id_Employee"], RDF.type, OWL.DatatypeProperty) in graph
        assert (base_ns["id_Department"], RDF.type, OWL.DatatypeProperty) in graph
        
        # Verify domains
        assert (base_ns["id_Employee"], RDFS.domain, base_ns["Employee"]) in graph
        assert (base_ns["id_Department"], RDFS.domain, base_ns["Department"]) in graph
    
    def test_global_naming_strategy(self):
        """Test global naming strategy (no scoping, potential conflicts)."""
        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "definitions": {
                "Person": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "age": {"type": "integer"}
                    }
                }
            }
        }
        
        # Use global naming strategy
        config = ReverseTransformationConfig()
        config.set_property_naming_strategy("global")
        
        engine = ReverseEngine(config)
        schema_model = engine.parser.parse(json.dumps(schema))
        graph = engine.transform(schema_model)
        
        base_ns = Namespace("http://example.org/ontology#")
        
        # Verify properties use global names (no class prefix)
        assert (base_ns["name"], RDF.type, OWL.DatatypeProperty) in graph
        assert (base_ns["age"], RDF.type, OWL.DatatypeProperty) in graph
        
        # Verify domains are still set
        assert (base_ns["name"], RDFS.domain, base_ns["Person"]) in graph
        assert (base_ns["age"], RDFS.domain, base_ns["Person"]) in graph
    
    def test_object_properties_scoped(self):
        """Test that object properties also get scoped URIs."""
        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "definitions": {
                "Person": {
                    "type": "object",
                    "properties": {
                        "address": {"$ref": "#/definitions/Address"}
                    }
                },
                "Company": {
                    "type": "object",
                    "properties": {
                        "address": {"$ref": "#/definitions/Address"}
                    }
                },
                "Address": {
                    "type": "object",
                    "properties": {
                        "street": {"type": "string"}
                    }
                }
            }
        }
        
        config = ReverseTransformationConfig()
        engine = ReverseEngine(config)
        schema_model = engine.parser.parse(json.dumps(schema))
        graph = engine.transform(schema_model)
        
        base_ns = Namespace("http://example.org/ontology#")
        
        # Verify distinct scoped object properties
        assert (base_ns["Person_address"], RDF.type, OWL.ObjectProperty) in graph
        assert (base_ns["Company_address"], RDF.type, OWL.ObjectProperty) in graph
        
        # Verify correct domains
        assert (base_ns["Person_address"], RDFS.domain, base_ns["Person"]) in graph
        assert (base_ns["Company_address"], RDFS.domain, base_ns["Company"]) in graph
        
        # Verify both have same range
        assert (base_ns["Person_address"], RDFS.range, base_ns["Address"]) in graph
        assert (base_ns["Company_address"], RDFS.range, base_ns["Address"]) in graph
    
    def test_required_properties_with_scoping(self):
        """Test that required properties work correctly with scoped URIs."""
        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "definitions": {
                "Product": {
                    "type": "object",
                    "properties": {
                        "code": {"type": "string"}
                    },
                    "required": ["code"]
                },
                "Order": {
                    "type": "object",
                    "properties": {
                        "code": {"type": "string"}
                    },
                    "required": ["code"]
                }
            }
        }
        
        config = ReverseTransformationConfig()
        engine = ReverseEngine(config)
        schema_model = engine.parser.parse(json.dumps(schema))
        graph = engine.transform(schema_model)
        
        base_ns = Namespace("http://example.org/ontology#")
        
        # Check cardinality restrictions use scoped property URIs
        product_restrictions = list(graph.objects(base_ns["Product"], RDFS.subClassOf))
        order_restrictions = list(graph.objects(base_ns["Order"], RDFS.subClassOf))
        
        # Find cardinality restriction for Product.code
        found_product_code = False
        for restriction in product_restrictions:
            if not isinstance(restriction, BNode):
                continue
            
            on_property = list(graph.objects(restriction, OWL.onProperty))
            if base_ns["Product_code"] in on_property:
                # Check for exact cardinality of 1
                exact_card = list(graph.objects(restriction, OWL.cardinality))
                if Literal(1) in exact_card:
                    found_product_code = True
                    break
        
        assert found_product_code, "Expected cardinality restriction on Product_code"
        
        # Find cardinality restriction for Order.code
        found_order_code = False
        for restriction in order_restrictions:
            if not isinstance(restriction, BNode):
                continue
            
            on_property = list(graph.objects(restriction, OWL.onProperty))
            if base_ns["Order_code"] in on_property:
                exact_card = list(graph.objects(restriction, OWL.cardinality))
                if Literal(1) in exact_card:
                    found_order_code = True
                    break
        
        assert found_order_code, "Expected cardinality restriction on Order_code"
    
    def test_multiple_properties_same_class(self):
        """Test that multiple properties in same class all get scoped correctly."""
        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "definitions": {
                "Vehicle": {
                    "type": "object",
                    "properties": {
                        "manufacturer": {"type": "string"},
                        "model": {"type": "string"},
                        "year": {"type": "integer"}
                    }
                }
            }
        }
        
        config = ReverseTransformationConfig()
        engine = ReverseEngine(config)
        schema_model = engine.parser.parse(json.dumps(schema))
        graph = engine.transform(schema_model)
        
        base_ns = Namespace("http://example.org/ontology#")
        
        # All properties should be scoped with class name
        assert (base_ns["Vehicle_manufacturer"], RDF.type, OWL.DatatypeProperty) in graph
        assert (base_ns["Vehicle_model"], RDF.type, OWL.DatatypeProperty) in graph
        assert (base_ns["Vehicle_year"], RDF.type, OWL.DatatypeProperty) in graph
        
        # All should have same domain
        assert (base_ns["Vehicle_manufacturer"], RDFS.domain, base_ns["Vehicle"]) in graph
        assert (base_ns["Vehicle_model"], RDFS.domain, base_ns["Vehicle"]) in graph
        assert (base_ns["Vehicle_year"], RDFS.domain, base_ns["Vehicle"]) in graph
    
    def test_property_naming_strategy_validation(self):
        """Test that invalid naming strategies are rejected."""
        config = ReverseTransformationConfig()
        
        # Valid strategies should work
        config.set_property_naming_strategy("scoped")
        assert config.get_property_naming_strategy() == "scoped"
        
        config.set_property_naming_strategy("reverse_scoped")
        assert config.get_property_naming_strategy() == "reverse_scoped"
        
        config.set_property_naming_strategy("global")
        assert config.get_property_naming_strategy() == "global"
        
        # Invalid strategy should raise ValueError
        with pytest.raises(ValueError, match="Invalid property naming strategy"):
            config.set_property_naming_strategy("invalid_strategy")




if __name__ == "__main__":
    pytest.main([__file__, "-v"])
"""
Validation and Edge Case Tests for JSON Schema to OWL Transformation

Tests for:
- Configuration validation
- Error handling
- Edge cases
- Invalid schemas
- Large schema handling
- Performance considerations
"""

import json
import pytest
import time
from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import RDF, RDFS, OWL

from src.jsonschema2owl import ReverseEngine, ReverseTransformationConfig, SchemaParser
from src.jsonschema2owl.config import ReverseTransformationConfig


class TestConfigurationValidation:
    """Tests for configuration validation."""
    
    def test_default_configuration(self):
        """Test default configuration values."""
        config = ReverseTransformationConfig()
        
        assert config.get_base_namespace() is not None
        assert config.get_output_format() in ["turtle", "xml", "json-ld", "nt"]
        assert config.get_array_handling_strategy() in ["functional_property", "non_functional_property"]
        assert config.get_allof_interpretation_strategy() in ["inheritance", "intersection", "auto"]
    
    def test_custom_namespace_configuration(self):
        """Test custom namespace configuration."""
        custom_config = {
            "namespace": {
                "base": "http://mycompany.org/ontology#"
            }
        }
        config = ReverseTransformationConfig(custom_config)
        
        assert config.get_base_namespace() == "http://mycompany.org/ontology#"
    
    def test_output_format_configuration(self):
        """Test output format configuration."""
        custom_config = {
            "output": {
                "format": "json-ld"
            }
        }
        config = ReverseTransformationConfig(custom_config)
        
        assert config.get_output_format() == "json-ld"
    
    def test_rule_enabling_disabling(self):
        """Test enabling and disabling rules."""
        config = ReverseTransformationConfig()
        
        # Initially enabled
        assert config.is_rule_enabled("definition_to_class")
        
        # Disable
        config.disable_rule("definition_to_class")
        assert not config.is_rule_enabled("definition_to_class")
        
        # Re-enable
        config.enable_rule("definition_to_class")
        assert config.is_rule_enabled("definition_to_class")
    
    def test_invalid_configuration_handled(self):
        """Test that invalid configuration is handled gracefully."""
        # Empty config should work
        config = ReverseTransformationConfig({})
        assert config is not None
        
        # Config with unknown keys should work
        config = ReverseTransformationConfig({"unknown_key": "value"})
        assert config is not None


class TestSchemaValidation:
    """Tests for JSON Schema validation."""
    
    def test_valid_schema_parses(self):
        """Test that valid schema parses successfully."""
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
        
        parser = SchemaParser()
        model = parser.parse(json.dumps(schema))
        
        assert model is not None
        assert "Test" in model.definitions
    
    def test_schema_without_version(self):
        """Test schema without $schema version."""
        schema = {
            "definitions": {
                "Test": {
                    "type": "object",
                    "properties": {
                        "value": {"type": "string"}
                    }
                }
            }
        }
        
        parser = SchemaParser()
        model = parser.parse(json.dumps(schema))
        
        # Should still parse with default version
        assert model is not None
    
    def test_malformed_json_raises_error(self):
        """Test that malformed JSON raises appropriate error."""
        malformed_json = "{ invalid json }"
        
        parser = SchemaParser()
        with pytest.raises(json.JSONDecodeError):
            parser.parse(malformed_json)
    
    def test_non_dict_schema_raises_error(self):
        """Test that non-dictionary schema raises error."""
        schema_list = ["not", "a", "dict"]
        
        parser = SchemaParser()
        with pytest.raises(ValueError):
            parser.parse_dict(schema_list)


class TestEdgeCases:
    """Tests for edge cases."""
    
    def test_empty_schema(self):
        """Test transformation of empty schema."""
        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#"
        }
        
        engine = ReverseEngine()
        schema_model = engine.parser.parse(json.dumps(schema))
        graph = engine.transform(schema_model)
        
        # Should create valid ontology
        ontologies = list(graph.subjects(RDF.type, OWL.Ontology))
        assert len(ontologies) > 0
    
    def test_empty_definitions(self):
        """Test schema with empty definitions object."""
        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "definitions": {}
        }
        
        engine = ReverseEngine()
        schema_model = engine.parser.parse(json.dumps(schema))
        graph = engine.transform(schema_model)
        
        # Should create valid ontology even without classes
        ontologies = list(graph.subjects(RDF.type, OWL.Ontology))
        assert len(ontologies) > 0
    
    def test_definition_without_properties(self):
        """Test definition with no properties."""
        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "definitions": {
                "Empty": {
                    "type": "object"
                }
            }
        }
        
        engine = ReverseEngine()
        schema_model = engine.parser.parse(json.dumps(schema))
        graph = engine.transform(schema_model)
        
        base_ns = Namespace("http://example.org/ontology#")
        
        # Should still create class
        assert (base_ns["Empty"], RDF.type, OWL.Class) in graph
    
    def test_property_without_type(self):
        """Test property without type specification."""
        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "definitions": {
                "Test": {
                    "type": "object",
                    "properties": {
                        "untyped": {}
                    }
                }
            }
        }
        
        engine = ReverseEngine()
        schema_model = engine.parser.parse(json.dumps(schema))
        graph = engine.transform(schema_model)
        
        # Should handle gracefully (may create property or skip)
        base_ns = Namespace("http://example.org/ontology#")
        assert (base_ns["Test"], RDF.type, OWL.Class) in graph
    
    def test_circular_reference(self):
        """Test handling of circular references."""
        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "definitions": {
                "Node": {
                    "type": "object",
                    "properties": {
                        "value": {"type": "string"},
                        "next": {"$ref": "#/definitions/Node"},
                        "prev": {"$ref": "#/definitions/Node"}
                    }
                }
            }
        }
        
        engine = ReverseEngine()
        schema_model = engine.parser.parse(json.dumps(schema))
        graph = engine.transform(schema_model)
        
        base_ns = Namespace("http://example.org/ontology#")
        
        # Should create self-referencing properties
        assert (base_ns["Node"], RDF.type, OWL.Class) in graph
        assert (base_ns["next"], RDF.type, OWL.ObjectProperty) in graph
        assert (base_ns["prev"], RDF.type, OWL.ObjectProperty) in graph
    
    def test_deep_circular_reference(self):
        """Test deeper circular reference pattern."""
        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "definitions": {
                "A": {
                    "type": "object",
                    "properties": {
                        "refToB": {"$ref": "#/definitions/B"}
                    }
                },
                "B": {
                    "type": "object",
                    "properties": {
                        "refToC": {"$ref": "#/definitions/C"}
                    }
                },
                "C": {
                    "type": "object",
                    "properties": {
                        "refToA": {"$ref": "#/definitions/A"}
                    }
                }
            }
        }
        
        engine = ReverseEngine()
        schema_model = engine.parser.parse(json.dumps(schema))
        graph = engine.transform(schema_model)
        
        base_ns = Namespace("http://example.org/ontology#")
        
        # All classes should be created
        assert (base_ns["A"], RDF.type, OWL.Class) in graph
        assert (base_ns["B"], RDF.type, OWL.Class) in graph
        assert (base_ns["C"], RDF.type, OWL.Class) in graph
    
    def test_special_characters_in_names(self):
        """Test handling of special characters in names."""
        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "definitions": {
                "Test-Class": {
                    "type": "object",
                    "properties": {
                        "property-with-dashes": {"type": "string"},
                        "property_with_underscores": {"type": "string"},
                        "property.with.dots": {"type": "string"}
                    }
                }
            }
        }
        
        engine = ReverseEngine()
        schema_model = engine.parser.parse(json.dumps(schema))
        graph = engine.transform(schema_model)
        
        # Should create valid URIs (may normalize names)
        classes = list(graph.subjects(RDF.type, OWL.Class))
        properties = list(graph.subjects(RDF.type, OWL.DatatypeProperty))
        
        assert len(classes) > 0
        assert len(properties) >= 3
    
    def test_unicode_characters(self):
        """Test handling of Unicode characters in schema."""
        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "definitions": {
                "Personne": {
                    "type": "object",
                    "title": "Personne française",
                    "description": "Une personne avec des caractères accentués",
                    "properties": {
                        "prénom": {
                            "type": "string",
                            "title": "Prénom"
                        },
                        "âge": {
                            "type": "integer",
                            "title": "Âge"
                        }
                    }
                }
            }
        }
        
        engine = ReverseEngine()
        schema_model = engine.parser.parse(json.dumps(schema))
        graph = engine.transform(schema_model)
        
        # Should handle Unicode in labels/comments
        base_ns = Namespace("http://example.org/ontology#")
        assert (base_ns["Personne"], RDF.type, OWL.Class) in graph


class TestErrorHandling:
    """Tests for error handling."""
    
    def test_invalid_ref_handled(self):
        """Test handling of invalid $ref."""
        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "definitions": {
                "Test": {
                    "type": "object",
                    "properties": {
                        "invalid": {"$ref": "#/definitions/NonExistent"}
                    }
                }
            }
        }
        
        engine = ReverseEngine()
        schema_model = engine.parser.parse(json.dumps(schema))
        
        # Should handle gracefully (may warn or skip)
        graph = engine.transform(schema_model)
        assert graph is not None
    
    def test_unsupported_json_schema_features(self):
        """Test handling of unsupported features."""
        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "definitions": {
                "Test": {
                    "type": "object",
                    "properties": {
                        "conditional": {
                            "if": {"type": "string"},
                            "then": {"minLength": 5},
                            "else": {"minLength": 1}
                        }
                    }
                }
            }
        }
        
        engine = ReverseEngine()
        schema_model = engine.parser.parse(json.dumps(schema))
        graph = engine.transform(schema_model)
        
        # Should handle gracefully
        assert graph is not None
    
    def test_transformation_with_warnings(self):
        """Test that warnings are captured."""
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
        
        engine = ReverseEngine()
        schema_model = engine.parser.parse(json.dumps(schema))
        graph = engine.transform(schema_model)
        
        # Should complete successfully
        assert graph is not None
        assert len(graph) > 0


class TestLargeSchemas:
    """Tests for large schema handling."""
    
    def test_many_definitions(self):
        """Test schema with many definitions."""
        definitions = {}
        num_classes = 100
        
        for i in range(num_classes):
            definitions[f"Class{i}"] = {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
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
        
        # Measure transformation time
        start_time = time.time()
        graph = engine.transform(schema_model)
        duration = time.time() - start_time
        
        # Verify all classes were created
        classes = list(graph.subjects(RDF.type, OWL.Class))
        assert len(classes) >= num_classes
        
        # Performance check (should complete in reasonable time)
        assert duration < 30.0, f"Transformation took {duration}s (too slow)"
    
    def test_many_properties(self):
        """Test class with many properties."""
        properties = {}
        num_properties = 200
        
        for i in range(num_properties):
            properties[f"property{i}"] = {
                "type": "string" if i % 2 == 0 else "number"
            }
        
        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "definitions": {
                "LargeClass": {
                    "type": "object",
                    "properties": properties
                }
            }
        }
        
        engine = ReverseEngine()
        schema_model = engine.parser.parse(json.dumps(schema))
        graph = engine.transform(schema_model)
        
        # Verify properties were created
        properties_created = list(graph.subjects(RDF.type, OWL.DatatypeProperty))
        assert len(properties_created) >= num_properties
    
    def test_deeply_nested_allof(self):
        """Test deeply nested allOf structures."""
        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "definitions": {
                "Base": {
                    "type": "object",
                    "properties": {"base": {"type": "string"}}
                },
                "Level1": {
                    "allOf": [
                        {"$ref": "#/definitions/Base"},
                        {"properties": {"level1": {"type": "string"}}}
                    ]
                },
                "Level2": {
                    "allOf": [
                        {"$ref": "#/definitions/Level1"},
                        {"properties": {"level2": {"type": "string"}}}
                    ]
                },
                "Level3": {
                    "allOf": [
                        {"$ref": "#/definitions/Level2"},
                        {"properties": {"level3": {"type": "string"}}}
                    ]
                },
                "Level4": {
                    "allOf": [
                        {"$ref": "#/definitions/Level3"},
                        {"properties": {"level4": {"type": "string"}}}
                    ]
                }
            }
        }
        
        engine = ReverseEngine()
        schema_model = engine.parser.parse(json.dumps(schema))
        graph = engine.transform(schema_model)
        
        base_ns = Namespace("http://example.org/ontology#")
        
        # Verify inheritance chain
        assert (base_ns["Level4"], RDFS.subClassOf, base_ns["Level3"]) in graph
        assert (base_ns["Level3"], RDFS.subClassOf, base_ns["Level2"]) in graph
        assert (base_ns["Level2"], RDFS.subClassOf, base_ns["Level1"]) in graph
        assert (base_ns["Level1"], RDFS.subClassOf, base_ns["Base"]) in graph


class TestSerializationFormats:
    """Tests for different serialization formats."""
    
    def test_turtle_serialization(self):
        """Test Turtle format serialization."""
        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "definitions": {
                "Test": {
                    "type": "object",
                    "properties": {"value": {"type": "string"}}
                }
            }
        }
        
        engine = ReverseEngine()
        schema_model = engine.parser.parse(json.dumps(schema))
        graph = engine.transform(schema_model)
        
        turtle = engine.serialize(graph, format="turtle")
        assert turtle is not None
        assert len(turtle) > 0
        assert "@prefix" in turtle
        
        # Verify it can be parsed back
        test_graph = Graph()
        test_graph.parse(data=turtle, format="turtle")
        assert len(test_graph) > 0
    
    def test_rdfxml_serialization(self):
        """Test RDF/XML format serialization."""
        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "definitions": {
                "Test": {
                    "type": "object",
                    "properties": {"value": {"type": "string"}}
                }
            }
        }
        
        engine = ReverseEngine()
        schema_model = engine.parser.parse(json.dumps(schema))
        graph = engine.transform(schema_model)
        
        rdfxml = engine.serialize(graph, format="xml")
        assert rdfxml is not None
        assert len(rdfxml) > 0
        assert "<?xml" in rdfxml or "<rdf:RDF" in rdfxml
        
        # Verify it can be parsed back
        test_graph = Graph()
        test_graph.parse(data=rdfxml, format="xml")
        assert len(test_graph) > 0
    
    def test_jsonld_serialization(self):
        """Test JSON-LD format serialization."""
        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "definitions": {
                "Test": {
                    "type": "object",
                    "properties": {"value": {"type": "string"}}
                }
            }
        }
        
        engine = ReverseEngine()
        schema_model = engine.parser.parse(json.dumps(schema))
        graph = engine.transform(schema_model)
        
        jsonld = engine.serialize(graph, format="json-ld")
        assert jsonld is not None
        assert len(jsonld) > 0
        
        # Verify it's valid JSON
        parsed_json = json.loads(jsonld)
        assert parsed_json is not None


class TestFileOperations:
    """Tests for file read/write operations."""
    
    def test_parse_from_file(self, tmp_path):
        """Test parsing schema from file."""
        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "definitions": {
                "Test": {
                    "type": "object",
                    "properties": {"value": {"type": "string"}}
                }
            }
        }
        
        # Write to temporary file
        schema_file = tmp_path / "test_schema.json"
        with open(schema_file, 'w') as f:
            json.dump(schema, f)
        
        # Parse from file
        parser = SchemaParser()
        model = parser.parse_file(str(schema_file))
        
        assert model is not None
        assert "Test" in model.definitions
    
    def test_parse_nonexistent_file_raises_error(self):
        """Test that parsing nonexistent file raises error."""
        parser = SchemaParser()
        
        with pytest.raises(FileNotFoundError):
            parser.parse_file("/nonexistent/path/schema.json")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
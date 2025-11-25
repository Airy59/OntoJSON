"""
Unit tests for JSON Schema to OWL2 transformation.

Tests basic functionality of the reverse transformation engine.
"""

import json
import pytest
from rdflib import Graph, Namespace, URIRef, Literal
from rdflib.namespace import RDF, RDFS, OWL, XSD

from src.jsonschema2owl import ReverseEngine, ReverseTransformationConfig, SchemaParser


# Test fixtures
@pytest.fixture
def simple_schema():
    """Simple JSON Schema with one class and properties."""
    return {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "$id": "http://example.org/test-schema",
        "title": "Test Schema",
        "description": "A test schema",
        "definitions": {
            "Person": {
                "type": "object",
                "title": "Person",
                "description": "A human being",
                "properties": {
                    "name": {
                        "type": "string",
                        "title": "Name"
                    },
                    "age": {
                        "type": "integer",
                        "title": "Age"
                    }
                },
                "required": ["name"]
            }
        }
    }


@pytest.fixture
def object_property_schema():
    """Schema with object property references."""
    return {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "definitions": {
            "Person": {
                "type": "object",
                "properties": {
                    "employer": {
                        "$ref": "#/definitions/Organization"
                    }
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


@pytest.fixture
def cardinality_schema():
    """Schema with cardinality constraints."""
    return {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "definitions": {
            "Team": {
                "type": "object",
                "properties": {
                    "members": {
                        "type": "array",
                        "items": {"$ref": "#/definitions/Person"},
                        "minItems": 1,
                        "maxItems": 10
                    }
                },
                "required": ["members"]
            },
            "Person": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"}
                }
            }
        }
    }


@pytest.fixture
def enum_schema():
    """Schema with enumeration."""
    return {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "definitions": {
            "Color": {
                "type": "string",
                "title": "Color",
                "enum": ["red", "green", "blue"]
            }
        }
    }


class TestSchemaParser:
    """Test JSON Schema parser."""
    
    def test_parse_simple_schema(self, simple_schema):
        """Test parsing a simple schema."""
        parser = SchemaParser()
        schema_str = json.dumps(simple_schema)
        model = parser.parse(schema_str)
        
        assert model.schema_id == "http://example.org/test-schema"
        assert model.title == "Test Schema"
        assert model.description == "A test schema"
        assert "Person" in model.definitions
        
        person = model.definitions["Person"]
        assert person.name == "Person"
        assert person.title == "Person"
        assert person.description == "A human being"
        assert "name" in person.properties
        assert "age" in person.properties
        assert "name" in person.required
    
    def test_parse_properties(self, simple_schema):
        """Test parsing properties."""
        parser = SchemaParser()
        schema_str = json.dumps(simple_schema)
        model = parser.parse(schema_str)
        
        person = model.definitions["Person"]
        name_prop = person.properties["name"]
        age_prop = person.properties["age"]
        
        assert name_prop.type == "string"
        assert name_prop.title == "Name"
        assert age_prop.type == "integer"
        assert age_prop.title == "Age"


class TestReverseEngine:
    """Test reverse transformation engine."""
    
    def test_engine_initialization(self):
        """Test engine initializes correctly."""
        engine = ReverseEngine()
        assert engine.config is not None
        assert engine.parser is not None
        assert engine.uri_generator is not None
        assert len(engine.rule_registry) > 0
    
    def test_simple_class_transformation(self, simple_schema):
        """Test transforming a simple class."""
        engine = ReverseEngine()
        schema_str = json.dumps(simple_schema)
        schema_model = engine.parser.parse(schema_str)
        
        graph = engine.transform(schema_model)
        
        # Check ontology exists
        ontology_uri = URIRef("http://example.org/test-schema")
        assert (ontology_uri, RDF.type, OWL.Ontology) in graph
        
        # Check Person class exists
        base_ns = Namespace("http://example.org/ontology#")
        person_class = base_ns["Person"]
        assert (person_class, RDF.type, OWL.Class) in graph
        assert (person_class, RDFS.label, Literal("Person")) in graph
        assert (person_class, RDFS.comment, Literal("A human being")) in graph
    
    def test_datatype_property_transformation(self, simple_schema):
        """Test transforming datatype properties."""
        engine = ReverseEngine()
        schema_str = json.dumps(simple_schema)
        schema_model = engine.parser.parse(schema_str)
        
        graph = engine.transform(schema_model)
        
        base_ns = Namespace("http://example.org/ontology#")
        name_prop = base_ns["name"]
        age_prop = base_ns["age"]
        
        # Check properties exist
        assert (name_prop, RDF.type, OWL.DatatypeProperty) in graph
        assert (age_prop, RDF.type, OWL.DatatypeProperty) in graph
        
        # Check ranges
        assert (name_prop, RDFS.range, XSD.string) in graph
        assert (age_prop, RDFS.range, XSD.integer) in graph
        
        # Check functional properties (single-valued)
        assert (name_prop, RDF.type, OWL.FunctionalProperty) in graph
        assert (age_prop, RDF.type, OWL.FunctionalProperty) in graph
    
    def test_object_property_transformation(self, object_property_schema):
        """Test transforming object properties."""
        engine = ReverseEngine()
        schema_str = json.dumps(object_property_schema)
        schema_model = engine.parser.parse(schema_str)
        
        graph = engine.transform(schema_model)
        
        base_ns = Namespace("http://example.org/ontology#")
        employer_prop = base_ns["employer"]
        person_class = base_ns["Person"]
        org_class = base_ns["Organization"]
        
        # Check object property exists
        assert (employer_prop, RDF.type, OWL.ObjectProperty) in graph
        
        # Check domain and range
        assert (employer_prop, RDFS.domain, person_class) in graph
        assert (employer_prop, RDFS.range, org_class) in graph
    
    def test_cardinality_constraints(self, cardinality_schema):
        """Test cardinality restriction transformation."""
        engine = ReverseEngine()
        schema_str = json.dumps(cardinality_schema)
        schema_model = engine.parser.parse(schema_str)
        
        graph = engine.transform(schema_model)
        
        base_ns = Namespace("http://example.org/ontology#")
        team_class = base_ns["Team"]
        
        # Check that Team has restrictions (use SPARQL or iterate)
        restrictions = list(graph.objects(team_class, RDFS.subClassOf))
        
        # Should have at least one restriction
        assert len(restrictions) > 0
        
        # Check for blank node restrictions
        has_restriction = False
        for restriction in restrictions:
            if isinstance(restriction, URIRef):
                continue
            # It's a blank node
            if (restriction, RDF.type, OWL.Restriction) in graph:
                has_restriction = True
                # Check for cardinality constraints
                min_card = list(graph.objects(restriction, OWL.minCardinality))
                max_card = list(graph.objects(restriction, OWL.maxCardinality))
                
                if min_card or max_card:
                    break
        
        assert has_restriction, "Expected to find cardinality restrictions"
    
    def test_enumeration_transformation(self, enum_schema):
        """Test enumeration to individuals transformation."""
        engine = ReverseEngine()
        schema_str = json.dumps(enum_schema)
        schema_model = engine.parser.parse(schema_str)
        
        graph = engine.transform(schema_model)
        
        base_ns = Namespace("http://example.org/ontology#")
        color_class = base_ns["Color"]
        
        # Check Color class exists
        assert (color_class, RDF.type, OWL.Class) in graph
        
        # Check individuals exist
        individuals = list(graph.subjects(RDF.type, OWL.NamedIndividual))
        assert len(individuals) == 3, f"Expected 3 individuals, found {len(individuals)}"
    
    def test_serialization(self, simple_schema):
        """Test graph serialization."""
        engine = ReverseEngine()
        schema_str = json.dumps(simple_schema)
        schema_model = engine.parser.parse(schema_str)
        
        graph = engine.transform(schema_model)
        
        # Test Turtle serialization
        turtle = engine.serialize(graph, format="turtle")
        assert turtle is not None
        assert len(turtle) > 0
        assert "@prefix" in turtle
        assert "owl:" in turtle
        
        # Verify it's valid by parsing it back
        test_graph = Graph()
        test_graph.parse(data=turtle, format="turtle")
        assert len(test_graph) > 0
    
    def test_required_property_cardinality(self, simple_schema):
        """Test that required properties get min cardinality of 1."""
        engine = ReverseEngine()
        schema_str = json.dumps(simple_schema)
        schema_model = engine.parser.parse(schema_str)
        
        graph = engine.transform(schema_model)
        
        base_ns = Namespace("http://example.org/ontology#")
        person_class = base_ns["Person"]
        
        # Check restrictions on Person class
        restrictions = list(graph.objects(person_class, RDFS.subClassOf))
        
        # Should have restriction for required "name" property
        has_name_restriction = False
        for restriction in restrictions:
            if isinstance(restriction, URIRef):
                continue
            
            # Check if this restriction is about the "name" property
            on_property = list(graph.objects(restriction, OWL.onProperty))
            if on_property and base_ns["name"] in on_property:
                # Check for cardinality = 1 (exact)
                exact_card = list(graph.objects(restriction, OWL.cardinality))
                if exact_card and Literal(1) in exact_card:
                    has_name_restriction = True
                    break
        
        assert has_name_restriction, "Expected exact cardinality restriction for required property 'name'"


class TestConfiguration:
    """Test configuration system."""
    
    def test_default_config(self):
        """Test default configuration."""
        config = ReverseTransformationConfig()
        
        assert config.get_base_namespace() == "http://example.org/ontology#"
        assert config.get_output_format() == "turtle"
        assert config.get_array_handling_strategy() == "non_functional_property"
        assert config.get_allof_interpretation_strategy() == "inheritance"
    
    def test_custom_namespace(self):
        """Test custom namespace configuration."""
        custom_config = {
            "namespace": {
                "base": "http://custom.org/onto#"
            }
        }
        config = ReverseTransformationConfig(custom_config)
        
        assert config.get_base_namespace() == "http://custom.org/onto#"
    
    def test_rule_enabling(self):
        """Test enabling/disabling rules."""
        config = ReverseTransformationConfig()
        
        # Test initial state
        assert config.is_rule_enabled("definition_to_class")
        
        # Disable a rule
        config.disable_rule("definition_to_class")
        assert not config.is_rule_enabled("definition_to_class")
        
        # Re-enable
        config.enable_rule("definition_to_class")
        assert config.is_rule_enabled("definition_to_class")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
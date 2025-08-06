"""
Tests for the transformation engine.
"""

import pytest
from owl2jsonschema import TransformationEngine, TransformationConfig
from owl2jsonschema.model import (
    OntologyModel,
    OntologyClass,
    ObjectProperty,
    DatatypeProperty
)


def test_engine_initialization():
    """Test that the engine initializes correctly."""
    engine = TransformationEngine()
    assert engine is not None
    assert engine.config is not None
    assert len(engine.rules) > 0


def test_engine_with_config():
    """Test engine initialization with custom configuration."""
    config = TransformationConfig({
        "rules": {
            "class_to_object": {"enabled": True},
            "labels_to_titles": {"enabled": False}
        }
    })
    engine = TransformationEngine(config)
    assert engine.config == config


def test_transform_empty_ontology():
    """Test transforming an empty ontology."""
    ontology = OntologyModel(uri="http://example.org/test")
    engine = TransformationEngine()
    result = engine.transform(ontology)
    
    assert result is not None
    assert "$schema" in result
    assert result["$schema"] == "http://json-schema.org/draft-07/schema#"


def test_transform_simple_class():
    """Test transforming a simple OWL class."""
    ontology = OntologyModel(uri="http://example.org/test")
    owl_class = OntologyClass(
        uri="http://example.org/test#Person",
        label="Person",
        comment="A human being"
    )
    ontology.classes.append(owl_class)
    
    config = TransformationConfig({
        "rules": {
            "class_to_object": {"enabled": True},
            "labels_to_titles": {"enabled": True},
            "comments_to_descriptions": {"enabled": True}
        }
    })
    
    engine = TransformationEngine(config)
    result = engine.transform(ontology)
    
    assert result is not None
    assert "definitions" in result
    assert "Person" in result["definitions"]
    
    person_schema = result["definitions"]["Person"]
    assert person_schema["type"] == "object"
    # Note: Labels and comments would be added by their respective rules


def test_transform_class_with_properties():
    """Test transforming a class with properties."""
    ontology = OntologyModel(uri="http://example.org/test")
    
    # Create a class
    person_class = OntologyClass(
        uri="http://example.org/test#Person",
        label="Person"
    )
    ontology.classes.append(person_class)
    
    # Create a datatype property
    name_property = DatatypeProperty(
        uri="http://example.org/test#name",
        label="Name",
        domain=["http://example.org/test#Person"],
        range=["http://www.w3.org/2001/XMLSchema#string"]
    )
    ontology.datatype_properties.append(name_property)
    
    config = TransformationConfig({
        "rules": {
            "class_to_object": {"enabled": True},
            "datatype_property": {"enabled": True}
        }
    })
    
    engine = TransformationEngine(config)
    result = engine.transform(ontology)
    
    assert result is not None
    assert "definitions" in result
    assert "Person" in result["definitions"]


def test_enable_disable_rules():
    """Test enabling and disabling rules."""
    engine = TransformationEngine()
    
    # Test enabling a rule
    engine.enable_rule("class_to_object")
    assert "class_to_object" in engine.get_enabled_rules()
    
    # Test disabling a rule
    engine.disable_rule("class_to_object")
    assert "class_to_object" in engine.get_disabled_rules()
    
    # Re-enable for other tests
    engine.enable_rule("class_to_object")
    assert "class_to_object" in engine.get_enabled_rules()


def test_class_hierarchy():
    """Test transforming class hierarchy."""
    ontology = OntologyModel(uri="http://example.org/test")
    
    # Create parent class
    animal_class = OntologyClass(
        uri="http://example.org/test#Animal",
        label="Animal"
    )
    ontology.classes.append(animal_class)
    
    # Create child class
    dog_class = OntologyClass(
        uri="http://example.org/test#Dog",
        label="Dog",
        super_classes=["http://example.org/test#Animal"]
    )
    ontology.classes.append(dog_class)
    
    config = TransformationConfig({
        "rules": {
            "class_to_object": {"enabled": True},
            "class_hierarchy": {"enabled": True}
        }
    })
    
    engine = TransformationEngine(config)
    result = engine.transform(ontology)
    
    assert result is not None
    assert "definitions" in result
    assert "Animal" in result["definitions"]
    assert "Dog" in result["definitions"]


def test_object_property():
    """Test transforming object properties."""
    ontology = OntologyModel(uri="http://example.org/test")
    
    # Create classes
    person_class = OntologyClass(uri="http://example.org/test#Person")
    address_class = OntologyClass(uri="http://example.org/test#Address")
    ontology.classes.extend([person_class, address_class])
    
    # Create object property
    has_address = ObjectProperty(
        uri="http://example.org/test#hasAddress",
        label="Has Address",
        domain=["http://example.org/test#Person"],
        range=["http://example.org/test#Address"]
    )
    ontology.object_properties.append(has_address)
    
    config = TransformationConfig({
        "rules": {
            "class_to_object": {"enabled": True},
            "object_property": {"enabled": True}
        }
    })
    
    engine = TransformationEngine(config)
    result = engine.transform(ontology)
    
    assert result is not None
    assert "definitions" in result
    assert "Person" in result["definitions"]
    assert "Address" in result["definitions"]
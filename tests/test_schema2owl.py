"""Tests for JSON Schema to OWL transformation (jsonschema2owl package)."""

import json
import sys
import unittest
from pathlib import Path

# Ensure src is on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from jsonschema2owl import SchemaParser, JsonSchema2OwlTransformer, JsonSchema2OwlConfig
from rdflib.namespace import RDF, RDFS, OWL
from rdflib import Literal


class TestSchema2Owl(unittest.TestCase):
    """Tests for jsonschema2owl."""

    def test_parse_minimal_schema(self):
        """Parse a minimal JSON Schema and check model has root object."""
        schema = {
            "type": "object",
            "title": "Person",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"},
            },
        }
        parser = SchemaParser()
        model = parser.parse(schema)
        self.assertIsNotNone(model.root)
        self.assertEqual(model.root.node_type, "object")
        self.assertEqual(model.root.title, "Person")
        self.assertIn("name", model.root.properties)
        self.assertIn("age", model.root.properties)
        self.assertEqual(model.root.properties["name"].json_type, "string")
        self.assertEqual(model.root.properties["age"].json_type, "integer")

    def test_transform_produces_owl_class_and_properties(self):
        """Transform minimal schema and assert graph contains expected OWL triples."""
        schema = {
        "type": "object",
        "title": "Person",
        "properties": {
            "name": {"type": "string"},
            "age": {"type": "integer"},
        },
        }
        parser = SchemaParser()
        model = parser.parse(schema)
        transformer = JsonSchema2OwlTransformer(base_uri="http://example.org/ns#")
        graph = transformer.transform(model)

        # Should have ontology, one class (Person), two datatype properties
        ns = "http://example.org/ns#"
        person_uri = ns + "Person"
        name_uri = ns + "name"
        age_uri = ns + "age"

        classes = list(graph.subjects(RDF.type, OWL.Class))
        self.assertTrue(any(str(c) == person_uri for c in classes))

        datatype_props = list(graph.subjects(RDF.type, OWL.DatatypeProperty))
        self.assertTrue(any(str(p) == name_uri for p in datatype_props))
        self.assertTrue(any(str(p) == age_uri for p in datatype_props))

        labels = list(graph.objects(transformer.namespace.Person, RDFS.label))
        self.assertIn(Literal("Person"), labels)

    def test_transform_enum_produces_individuals(self):
        """Schema with enum should produce OWL class and named individuals."""
        schema = {
            "type": "object",
            "title": "Status",
            "properties": {
                "code": {"type": "string", "enum": ["active", "inactive"]},
            },
        }
        parser = SchemaParser()
        model = parser.parse(schema)
        transformer = JsonSchema2OwlTransformer(base_uri="http://test.org/ns#")
        graph = transformer.transform(model)

        classes = list(graph.subjects(RDF.type, OWL.Class))
        self.assertGreaterEqual(len(classes), 1)
        individuals = list(graph.subjects(RDF.type, OWL.NamedIndividual))
        self.assertGreaterEqual(len(individuals), 2)

    def test_serialize_turtle(self):
        """Transform and serialize to Turtle; output should contain expected strings."""
        schema = {"type": "object", "title": "Foo", "properties": {"x": {"type": "string"}}}
        transformer = JsonSchema2OwlTransformer(base_uri="http://example.org/ns#")
        out = transformer.transform_string(json.dumps(schema), output_format="turtle")
        self.assertIn("owl:Class", out)
        self.assertTrue("Foo" in out or "foo" in out)
        self.assertIn("owl:DatatypeProperty", out)

    def test_property_used_by_two_classes_has_union_domain(self):
        """When two classes A and B both have property X, domain of X must be unionOf(A, B)."""
        from rdflib.namespace import OWL
        schema = {
            "definitions": {
                "Person": {"type": "object", "title": "Person", "properties": {"name": {"type": "string"}}},
                "Organization": {"type": "object", "title": "Organization", "properties": {"name": {"type": "string"}}},
            },
            "type": "object",
            "properties": {
                "owner": {"$ref": "#/definitions/Person"},
                "org": {"$ref": "#/definitions/Organization"},
            },
        }
        parser = SchemaParser()
        model = parser.parse(schema)
        transformer = JsonSchema2OwlTransformer(base_uri="http://example.org/ns#")
        graph = transformer.transform(model)
        # Find all rdfs:domain triples for the "name" property (used by Person and Organization)
        name_uri = transformer.namespace["name"]
        domains = list(graph.objects(name_uri, RDFS.domain))
        self.assertEqual(len(domains), 1, "Property 'name' should have exactly one domain axiom")
        domain = domains[0]
        # Domain should be an owl:Class (either Person, or a union blank node)
        types = list(graph.objects(domain, RDF.type))
        self.assertIn(OWL.Class, types)
        # If it's a union, it has owl:unionOf
        union_of = list(graph.objects(domain, OWL.unionOf))
        self.assertEqual(len(union_of), 1, "Domain should be a union (owl:unionOf)")
        # The list should contain Person and Organization
        from rdflib.collection import Collection
        list_head = union_of[0]
        coll = Collection(graph, list_head)
        class_uris = list(coll)
        self.assertEqual(len(class_uris), 2, "Union should have two classes")


if __name__ == "__main__":
    unittest.main()

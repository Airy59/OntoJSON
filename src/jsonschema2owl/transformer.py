"""
JSON Schema to OWL transformer: applies rules to a SchemaModel and produces an RDF graph.
"""

from typing import Any, Dict, List, Optional

from rdflib import Graph, Namespace, URIRef, Literal
from rdflib.namespace import RDF, RDFS, OWL

from .model import SchemaModel, SchemaNode
from .config import JsonSchema2OwlConfig
from .rules import RuleRegistry, TransformationRule


def _collect_nodes(node: SchemaNode, out: List[SchemaNode]) -> None:
    out.append(node)
    for child in node.children:
        _collect_nodes(child, out)
    for prop_node in node.properties.values():
        if prop_node not in out:
            _collect_nodes(prop_node, out)
    if node.items:
        _collect_nodes(node.items, out)


class JsonSchema2OwlTransformer:
    """
    Transforms a parsed JSON Schema (SchemaModel) into an OWL ontology (rdflib.Graph)
    using a rule registry.
    """

    def __init__(
        self,
        base_uri: str = "http://example.org/ns#",
        namespace_prefix: str = "ns",
        ontology_title: Optional[str] = None,
        ontology_comment: Optional[str] = None,
        config: Optional[JsonSchema2OwlConfig] = None,
    ):
        self.base_uri = base_uri.rstrip("#") + "#" if "#" not in base_uri else base_uri
        self.namespace = Namespace(self.base_uri)
        self.namespace_prefix = namespace_prefix
        self.ontology_title = ontology_title or "Ontology from JSON Schema"
        self.ontology_comment = ontology_comment or "Generated from JSON Schema"
        self.config = config or JsonSchema2OwlConfig(base_uri=base_uri)
        self.rule_registry = RuleRegistry()

    def transform(self, model: SchemaModel) -> Graph:
        graph = Graph()
        graph.bind(self.namespace_prefix, self.namespace)
        graph.bind("owl", OWL)
        graph.bind("rdfs", RDFS)
        onto_uri = URIRef(self.base_uri)
        graph.add((onto_uri, RDF.type, OWL.Ontology))
        graph.add((onto_uri, RDFS.label, Literal(self.ontology_title or "")))
        graph.add((onto_uri, RDFS.comment, Literal(self.ontology_comment or "")))

        context = {
            "graph": graph,
            "namespace": self.namespace,
            "config": self.config,
            "model": model,
            "definitions": model.definitions,
            "class_uris": {},
            "node_to_uri": {},
            "ref_targets": {},
        }

        rules = self.rule_registry.get_enabled_rules(self.config)

        nodes_to_process: List[SchemaNode] = []
        for def_node in model.definitions.values():
            _collect_nodes(def_node, nodes_to_process)
        _collect_nodes(model.root, nodes_to_process)
        seen = set()
        unique_nodes = []
        for n in nodes_to_process:
            if id(n) not in seen:
                seen.add(id(n))
                unique_nodes.append(n)

        for node in unique_nodes:
            for rule in rules:
                if rule.applies_to(node.node_type):
                    rule.transform(node, context)

        return graph

    def transform_file(
        self,
        path: str,
        output_format: str = "turtle",
        active_rules: Optional[List[str]] = None,
    ) -> str:
        from .parser import SchemaParser
        parser = SchemaParser()
        model = parser.parse_file(path)
        if active_rules is not None:
            self.config.enabled_rule_ids = active_rules
        graph = self.transform(model)
        return graph.serialize(format=output_format)

    def transform_string(
        self,
        schema_content: str,
        output_format: str = "turtle",
        active_rules: Optional[List[str]] = None,
    ) -> str:
        from .parser import SchemaParser
        parser = SchemaParser()
        model = parser.parse(schema_content)
        if active_rules is not None:
            self.config.enabled_rule_ids = active_rules
        graph = self.transform(model)
        return graph.serialize(format=output_format)

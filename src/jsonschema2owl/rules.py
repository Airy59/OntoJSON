"""
Transformation rules for JSON Schema to OWL.
Each rule maps a schema construct to RDF triples (deterministic).
"""

from abc import ABC, abstractmethod
import re
from typing import Any, Dict, List, Optional

from rdflib import Graph, Namespace, URIRef, Literal, BNode
from rdflib.namespace import RDF, RDFS, OWL, XSD

from .model import SchemaModel, SchemaNode
from .config import JsonSchema2OwlConfig


def sanitize_uri_fragment(name: str, naming: str = "as_is") -> str:
    """Produce a safe URI fragment from a property/class name."""
    if not name:
        return "thing"
    s = name.strip()
    if naming == "pascal":
        s = s[0].upper() + s[1:] if len(s) > 1 else s.upper()
    elif naming == "camel":
        if s and len(s) > 1:
            s = s[0].lower() + s[1:]
    s = re.sub(r"[^\w\-.]", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s or "thing"


class TransformationRule(ABC):
    """Base class for JSON Schema -> OWL transformation rules."""

    def __init__(self, rule_id: str, name: str, description: str):
        self.rule_id = rule_id
        self.name = name
        self.description = description
        self.enabled = True
        self.priority = 50

    @abstractmethod
    def applies_to(self, node_type: str) -> bool:
        pass

    @abstractmethod
    def transform(self, node: SchemaNode, context: Dict[str, Any]) -> None:
        """Apply transformation; add triples to context['graph']."""
        pass

    def configure(self, parameters: Dict[str, Any]) -> None:
        pass


class ObjectToClassRule(TransformationRule):
    """Map JSON Schema object (or definition) to owl:Class."""

    def __init__(self):
        super().__init__(
            "object_to_class",
            "Object to OWL Class",
            "Maps JSON Schema object types to OWL classes",
        )
        self.priority = 90

    def applies_to(self, node_type: str) -> bool:
        return node_type == "object"

    def transform(self, node: SchemaNode, context: Dict[str, Any]) -> None:
        graph = context["graph"]
        ns = context["namespace"]
        config = context.get("config")
        naming = config.class_naming if config else "pascal"
        name = node.name or node.title or "Thing"
        fragment = sanitize_uri_fragment(name, naming)
        uri = ns[fragment]
        graph.add((uri, RDF.type, OWL.Class))
        if node.title:
            graph.add((uri, RDFS.label, Literal(node.title)))
        if node.description:
            graph.add((uri, RDFS.comment, Literal(node.description)))
        context.setdefault("class_uris", {})[name] = uri
        context.setdefault("node_to_uri", {})[id(node)] = uri


class PropertyToOwlPropertyRule(TransformationRule):
    """Map JSON Schema properties to owl:DatatypeProperty or owl:ObjectProperty."""

    def __init__(self):
        super().__init__(
            "property_to_owl_property",
            "Property to OWL Property",
            "Maps schema properties to datatype or object properties",
        )
        self.priority = 80

    def applies_to(self, node_type: str) -> bool:
        return node_type in ("primitive", "object", "ref", "array", "enum")

    def transform(self, node: SchemaNode, context: Dict[str, Any]) -> None:
        if not node.name or not node.parent:
            return
        graph = context["graph"]
        ns = context["namespace"]
        config = context.get("config")
        prop_naming = config.property_naming if config else "as_is"
        domain_uri = context.get("node_to_uri", {}).get(id(node.parent))
        if not domain_uri and node.parent.node_type == "object":
            naming = config.class_naming if config else "pascal"
            parent_name = node.parent.name or node.parent.title or "Thing"
            domain_uri = ns[sanitize_uri_fragment(parent_name, naming)]
        fragment = sanitize_uri_fragment(node.name, prop_naming)
        prop_uri = ns[fragment]
        if node.node_type == "object" or node.node_type == "ref":
            graph.add((prop_uri, RDF.type, OWL.ObjectProperty))
            range_name = (node.title or node.name or "Thing").strip()
            range_fragment = sanitize_uri_fragment(
                range_name, config.class_naming if config else "pascal"
            )
            graph.add((prop_uri, RDFS.range, ns[range_fragment]))
        else:
            graph.add((prop_uri, RDF.type, OWL.DatatypeProperty))
            xsd_type = self._json_type_to_xsd(node.json_type, node.node_type)
            graph.add((prop_uri, RDFS.range, xsd_type))
        if node.title:
            graph.add((prop_uri, RDFS.label, Literal(node.title)))
        if node.description:
            graph.add((prop_uri, RDFS.comment, Literal(node.description)))
        # Do NOT add rdfs:domain here: multiple domain axioms mean intersection in OWL.
        # Collect domains per property; transformer will add a single domain (union) in a post-pass.
        if domain_uri:
            context.setdefault("property_domains", {}).setdefault(prop_uri, set()).add(domain_uri)

    @staticmethod
    def _json_type_to_xsd(json_type: Optional[str], node_type: str):
        if node_type == "array":
            return RDFS.Resource
        mapping = {
            "string": XSD.string,
            "number": XSD.double,
            "integer": XSD.integer,
            "boolean": XSD.boolean,
            "null": XSD.string,
        }
        return mapping.get(json_type, XSD.string) if json_type else XSD.string


class EnumToIndividualsRule(TransformationRule):
    """Map JSON Schema enum to OWL enumerated class (oneOf) or named individuals."""

    def __init__(self):
        super().__init__(
            "enum_to_individuals",
            "Enum to Individuals",
            "Maps schema enums to OWL individuals or enumerated class",
        )
        self.priority = 75

    def applies_to(self, node_type: str) -> bool:
        return node_type == "enum"

    def transform(self, node: SchemaNode, context: Dict[str, Any]) -> None:
        graph = context["graph"]
        ns = context["namespace"]
        name = node.name or node.title or "Enum"
        class_fragment = sanitize_uri_fragment(name, "pascal")
        class_uri = ns[class_fragment]
        graph.add((class_uri, RDF.type, OWL.Class))
        if node.title:
            graph.add((class_uri, RDFS.label, Literal(node.title)))
        for i, val in enumerate(node.enum_values):
            ind_fragment = sanitize_uri_fragment(str(val), "as_is")
            if not ind_fragment or ind_fragment == "thing":
                ind_fragment = f"value_{i}"
            ind_uri = ns[ind_fragment]
            graph.add((ind_uri, RDF.type, OWL.NamedIndividual))
            graph.add((ind_uri, RDF.type, class_uri))
            if isinstance(val, str):
                graph.add((ind_uri, RDFS.label, Literal(val)))
        context.setdefault("node_to_uri", {})[id(node)] = class_uri


class RefToRangeRule(TransformationRule):
    """Ensure $ref targets are classes and property ranges point to them."""

    def __init__(self):
        super().__init__(
            "ref_to_range",
            "Ref to Range",
            "Resolves $ref to OWL class for range",
        )
        self.priority = 70

    def applies_to(self, node_type: str) -> bool:
        return node_type == "ref"

    def transform(self, node: SchemaNode, context: Dict[str, Any]) -> None:
        if not node.ref_target:
            return
        ref = node.ref_target
        if ref.startswith("#/"):
            path = ref[2:].replace("/", ".")
            def_node = context.get("definitions", {}).get(path)
            if def_node:
                name = def_node.name or def_node.title or path.split(".")[-1]
                context.setdefault("ref_targets", {})[ref] = name


class RuleRegistry:
    """Registry of transformation rules."""

    def __init__(self) -> None:
        self._rules: Dict[str, TransformationRule] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        for rule in [
            ObjectToClassRule(),
            PropertyToOwlPropertyRule(),
            EnumToIndividualsRule(),
            RefToRangeRule(),
        ]:
            self.register_rule(rule)

    def register_rule(self, rule: TransformationRule) -> None:
        self._rules[rule.rule_id] = rule

    def get_rule(self, rule_id: str) -> Optional[TransformationRule]:
        return self._rules.get(rule_id)

    def get_all_rules(self) -> List[TransformationRule]:
        return list(self._rules.values())

    def get_enabled_rules(self, config: Optional[JsonSchema2OwlConfig] = None) -> List[TransformationRule]:
        rules = [r for r in self._rules.values() if r.enabled]
        if config and config.enabled_rule_ids is not None:
            rules = [r for r in rules if r.rule_id in config.enabled_rule_ids]
        return sorted(rules, key=lambda r: -r.priority)

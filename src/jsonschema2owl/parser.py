"""
Parse JSON Schema (file or dict) into an in-memory SchemaModel.
Handles definitions/$defs and in-document $ref.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from .model import SchemaModel, SchemaNode


def _normalize_fragment(ref: str) -> str:
    """Return fragment part of $ref (e.g. #/definitions/Foo -> definitions/Foo)."""
    if ref.startswith("#/"):
        return ref[2:].replace("/", ".")
    return ref


def _get_nested(d: Dict[str, Any], path: str) -> Any:
    """Get value at path like 'definitions.Foo' or 'definitions.Foo.properties.bar'."""
    parts = path.split(".")
    current = d
    for p in parts:
        current = current.get(p)
        if current is None:
            return None
    return current


def _parse_schema_node(
    data: Any,
    parent: Optional[SchemaNode],
    name: Optional[str],
    defs_map: Dict[str, Dict[str, Any]],
    defs_prefix: str = "",
) -> Optional[SchemaNode]:
    """Recursively build SchemaNode from JSON Schema dict."""
    if data is None:
        return None
    if not isinstance(data, dict):
        return SchemaNode(
            node_type="primitive",
            name=name,
            json_type=type(data).__name__ if data is not None else "null",
            parent=parent,
            raw={"const": data} if data is not None else {},
        )

    ref = data.get("$ref")
    if ref:
        fragment = _normalize_fragment(ref)
        target = defs_map.get(fragment) if defs_map else None
        if target is not None:
            child = _parse_schema_node(target, parent, name, defs_map, defs_prefix)
            if child:
                child.ref_target = ref
                child.node_type = "ref"
            return child
        return SchemaNode(
            node_type="ref",
            name=name,
            ref_target=ref,
            parent=parent,
            raw=data,
        )

    if "enum" in data:
        return SchemaNode(
            node_type="enum",
            name=name,
            title=data.get("title"),
            description=data.get("description"),
            enum_values=data["enum"],
            parent=parent,
            raw=data,
        )

    json_type = data.get("type")
    if json_type == "array":
        items = data.get("items")
        items_node = None
        if isinstance(items, dict):
            items_node = _parse_schema_node(items, None, "items", defs_map, defs_prefix)
        node = SchemaNode(
            node_type="array",
            name=name,
            title=data.get("title"),
            description=data.get("description"),
            json_type="array",
            parent=parent,
            raw=data,
        )
        if items_node:
            node.items = items_node
            items_node.parent = node
        return node

    if json_type == "object" or "properties" in data:
        node = SchemaNode(
            node_type="object",
            name=name,
            title=data.get("title"),
            description=data.get("description"),
            json_type="object",
            parent=parent,
            raw=data,
        )
        props = data.get("properties", {})
        for prop_name, prop_schema in props.items():
            if isinstance(prop_schema, dict):
                child = _parse_schema_node(
                    prop_schema, node, prop_name, defs_map, defs_prefix
                )
                if child:
                    node.properties[prop_name] = child
                    node.children.append(child)
        return node

    # primitive (string, number, integer, boolean, null) or type not specified
    return SchemaNode(
        node_type="primitive",
        name=name,
        title=data.get("title"),
        description=data.get("description"),
        json_type=json_type if isinstance(json_type, str) else None,
        parent=parent,
        raw=data,
    )


def _collect_definitions(schema: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Build a flat map of definition path -> schema dict (for $ref resolution)."""
    out = {}
    for key in ("definitions", "$defs"):
        defs = schema.get(key)
        if not isinstance(defs, dict):
            continue
        for def_name, def_schema in defs.items():
            if isinstance(def_schema, dict):
                out[def_name] = def_schema
                # Optional: recurse into nested definitions
                for sub_key in ("definitions", "$defs"):
                    sub = def_schema.get(sub_key)
                    if isinstance(sub, dict):
                        for sub_name, sub_schema in sub.items():
                            if isinstance(sub_schema, dict):
                                out[f"{def_name}.{sub_name}"] = sub_schema
    return out


class SchemaParser:
    """Parse JSON Schema from file or dict into SchemaModel."""

    def parse_file(self, path: Union[str, Path]) -> SchemaModel:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return self.parse(data, base_uri=f"file://{Path(path).absolute()}")

    def parse(
        self,
        schema: Union[Dict[str, Any], str],
        base_uri: Optional[str] = None,
    ) -> SchemaModel:
        if isinstance(schema, str):
            schema = json.loads(schema)
        if not isinstance(schema, dict):
            raise ValueError("Schema must be a dict or JSON string")
        defs_map = _collect_definitions(schema)
        root = _parse_schema_node(schema, None, None, defs_map)
        if root is None:
            root = SchemaNode(node_type="object", name=None, raw=schema)
        definitions = {}
        for def_path, def_dict in defs_map.items():
            def_node = _parse_schema_node(def_dict, None, def_path.split(".")[-1], defs_map)
            if def_node:
                definitions[def_path] = def_node
        return SchemaModel(
            root=root,
            definitions=definitions,
            base_uri=base_uri,
            raw_schema=schema,
        )

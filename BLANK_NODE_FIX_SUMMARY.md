# Blank Node Handling Fix - Summary

## Problem
When a restriction used an anonymous class expression (blank node) like:
```turtle
:isSettingFor only ('Intermodal Transport Unit' or Wagon)
```

The system would create an undefined reference like:
```json
{"$ref": "#/definitions/n81deb6fe48074accad8fb3b7cf17b3afb27"}
```

## Solution
The fix implements proper inline expansion of union/intersection expressions in property value constraints.

### Changes Made

#### 1. Parser Enhancement (`src/owl2jsonschema/parser.py`)

**Added `_parse_class_expression()` method:**
- Detects and parses complex class expressions from blank nodes
- Handles `owl:unionOf` and `owl:intersectionOf`
- Returns structured data (dict with 'unionOf' or 'intersectionOf' keys)

**Added `_parse_rdf_list()` helper method:**
- Parses RDF lists recursively
- Handles nested complex expressions

**Modified `_parse_restriction()` method:**
- Now detects when `allValuesFrom` or `someValuesFrom` points to a blank node
- Calls `_parse_class_expression()` to parse complex expressions
- Stores the structured expression in the `filler` field

#### 2. Class Rules Enhancement (`src/owl2jsonschema/rules/class_rules.py`)

**Updated `_create_type_reference()` method:**
- Changed signature from `(type_uri: str)` to `(type_uri: Any)`
- Added handling for dict-based complex expressions
- Recursively expands `unionOf` as `oneOf`
- Recursively expands `intersectionOf` as `allOf`

#### 3. Property Rules Enhancement (`src/owl2jsonschema/rules/property_rules.py`)

**Updated `_create_type_reference()` method:**
- Same changes as in class_rules.py
- Ensures consistency across both rule sets

### Result

Now when processing:
```turtle
:SpecialSetting rdfs:subClassOf [
    a owl:Restriction ;
    owl:onProperty :isSettingFor ;
    owl:allValuesFrom [
        a owl:Class ;
        owl:unionOf (:IntermodalTransportUnit :Wagon)
    ]
]
```

The system generates:
```json
{
  "isSettingFor": {
    "type": "array",
    "items": {
      "oneOf": [
        {
          "oneOf": [
            {"$ref": "#/definitions/IntermodalTransportUnit"},
            {"type": "object", "properties": {"@id": ...}}
          ]
        },
        {
          "oneOf": [
            {"$ref": "#/definitions/Wagon"},
            {"type": "object", "properties": {"@id": ...}}
          ]
        }
      ]
    }
  }
}
```

### Benefits

1. **No undefined references**: All class references are properly defined
2. **Inline expansion**: Complex expressions are expanded where they're used
3. **Recursive support**: Handles nested union/intersection expressions
4. **Consistent handling**: Works for both class restrictions and property restrictions
5. **Backward compatible**: Doesn't break existing simple type references

### Testing

Created comprehensive test case (`test_blank_node_fix.py`) that:
- Verifies blank node detection in the parser
- Confirms proper unionOf parsing
- Validates inline oneOf expansion in the generated schema
- Ensures no undefined blank node references remain

All tests pass successfully.
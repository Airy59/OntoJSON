# Property Requirements Fix - OWL to JSON Schema Transformation

## Issue
Properties in the JSON Schema were incorrectly being marked as required by default, which doesn't align with OWL semantics. In OWL, properties should be **optional by default** unless there's an explicit constraint that makes them required.

## OWL Semantics
In OWL, a property becomes required (must have at least one value) only when:
1. **Minimum cardinality >= 1**: `owl:minCardinality 1` or higher
2. **Exact cardinality >= 1**: `owl:cardinality 1` or higher  
3. **someValuesFrom restriction**: `owl:someValuesFrom` (implies at least one value)
4. **hasValue restriction**: `owl:hasValue` (must have a specific value)

## Changes Made

### 1. Fixed ClassRestrictionsRule (`src/owl2jsonschema/rules/class_rules.py`)

#### Cardinality Handling (lines 216-224)
```python
# Before: Only marked as required if exactly 1
if restriction.min_cardinality == 1:
    result["required"] = True

# After: Marked as required if 1 or more
if restriction.min_cardinality >= 1:
    result["required"] = True
```

#### someValuesFrom Handling (lines 257-264)
```python
# Before: Did not mark property as required
elif restriction.restriction_type == "someValuesFrom":
    # At least one value must be from the specified class/type
    filler_ref = self._create_type_reference(restriction.filler)
    schema["type"] = "array"
    schema["minItems"] = 1
    schema["items"] = filler_ref

# After: Correctly marks property as required
elif restriction.restriction_type == "someValuesFrom":
    # At least one value must be from the specified class/type
    # This makes the property required
    result["required"] = True
    filler_ref = self._create_type_reference(restriction.filler)
    schema["type"] = "array"
    schema["minItems"] = 1
    schema["items"] = filler_ref
```

## Test Results

Using the test ontology `Documentation/test ontology for OWL to JSON schema transformation.ttl`:

### Properties correctly marked as OPTIONAL:
- `Formation.composedOf` - optional (no cardinality constraint)
- `LegalEntity.creationDate` - optional (no cardinality constraint)
- `RollingStock.partOf` - optional (no cardinality constraint)
- `_Thing.uri` - optional (base object property)

### Properties correctly marked as REQUIRED:
- `Vehicle.ofType` - **REQUIRED** (has `someValuesFrom` restriction)

## JSON Schema Output Example

```json
{
  "Vehicle": {
    "allOf": [
      {
        "$ref": "#/definitions/_Thing"
      },
      {
        "type": "object",
        "properties": {
          "ofType": {
            "$ref": "#/definitions/VehicleType"
          }
        },
        "required": ["ofType"]  // Correctly required due to someValuesFrom
      }
    ]
  },
  "LegalEntity": {
    "allOf": [
      {
        "$ref": "#/definitions/_Thing"
      },
      {
        "type": "object",
        "properties": {
          "creationDate": {
            "type": "string",
            "format": "date-time"
          }
        }
        // No "required" array - property is optional
      }
    ]
  }
}
```

## Verification
Run `python3 test_optional_properties.py` to verify that:
1. Properties without explicit constraints are optional
2. Properties with min cardinality >= 1 are required
3. Properties with someValuesFrom restrictions are required

## Compatibility
This change ensures the transformation correctly reflects OWL semantics and is compatible with:
- OWL 2 DL
- OWL 2 RL (Reasoning Layer)
- Standard RDF/OWL reasoners

## Impact
This fix ensures that JSON Schema validation will correctly:
- Allow optional properties to be omitted
- Require properties only when OWL constraints mandate them
- Support proper data validation aligned with the ontology's intended semantics
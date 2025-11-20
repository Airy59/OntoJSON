# Subproperty Annotation Feature

## Overview
This feature adds automatic annotation of subproperty relationships in the generated JSON Schema. When a property is defined as a subproperty of another property in OWL, the JSON Schema will include this information in the property's description.

## Implementation

### Changes Made
Modified [`src/owl2jsonschema/rules/property_rules.py`](src/owl2jsonschema/rules/property_rules.py) to enhance both `ObjectPropertyRule` and `DatatypePropertyRule` classes:

1. **ObjectPropertyRule** (lines 213-228): Added logic to append subproperty information to property descriptions
2. **DatatypePropertyRule** (lines 335-355): Added same logic for datatype properties

### How It Works
- The parser already captures subproperty relationships via `super_properties` field in the property model
- When transforming properties to JSON Schema, the rule now checks if `property.super_properties` exists
- If subproperties exist, it appends text like "Subproperty of PropertyName" to the description
- Multiple super properties are comma-separated: "Subproperty of Prop1, Prop2"

### Example

**OWL Input:**
```turtle
:hasRelationship a owl:ObjectProperty ;
    rdfs:label "has relationship" ;
    rdfs:comment "A relationship between persons" .

:hasFriend a owl:ObjectProperty ;
    rdfs:label "has friend" ;
    rdfs:comment "A friendship relationship" ;
    rdfs:subPropertyOf :hasRelationship .
```

**JSON Schema Output:**
```json
{
  "hasFriend": {
    "type": "array",
    "items": {
      "title": "has friend",
      "description": "A friendship relationship. Subproperty of hasRelationship"
    }
  }
}
```

## Benefits
1. **Preserves Semantic Information**: Although JSON Schema cannot express subproperty relationships formally, this preserves the information for human readers
2. **Documentation**: Helps developers understand the property hierarchy when working with the schema
3. **Traceability**: Maintains connection to the original OWL ontology structure

## Testing
A comprehensive test was created in [`test_subproperty.py`](test_subproperty.py) with:
- Test ontology ([`test_subproperty.ttl`](test_subproperty.ttl)) containing object and datatype subproperties
- Verification that subproperties have the annotation
- Verification that parent properties do NOT have the annotation

All tests pass successfully! ✓

## Rationale
As noted in the original discussion:
> "If there is a property P with two subproperties P1 and P2, I guess that the 'sub' relationship will be ignored by JSON schema, since there is no way to express it. Instead, all three (P, P1, P2) will be displayed as ordinary properties."

This implementation addresses that limitation by documenting the relationship in the description field, making the ontology structure more transparent to schema users.
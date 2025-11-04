# Individuals in JSON Schema

## Overview

The OntoJSON library now includes support for representing OWL individuals (named instances) that are defined as part of the ontology's T-Box. The representation differs based on whether the class defines a **closed** or **open** set of individuals.

## T-Box vs A-Box

In OWL ontologies:
- **T-Box (Terminology Box)**: Contains the ontology schema - classes, properties, and pre-defined individuals that form part of the vocabulary
- **A-Box (Assertion Box)**: Contains instance data about specific entities

This feature handles **T-Box individuals** - those defined in the ontology itself.

## Closed vs Open Sets

### OWL Semantics

In OWL, a class with individuals can represent:

1. **Closed Set (Enumeration)**: When a class is `owl:equivalentClass` to (or subclass of) a `owl:oneOf` construct listing specific individuals, the set is closed - only those individuals are allowed.

2. **Open Set (Examples)**: When a class simply has some named individuals as instances, but is not defined as equivalent to their enumeration, other individuals can also exist.

### JSON Schema Limitations

JSON Schema's `enum` keyword creates a **closed enumeration** - only the listed values are allowed. There is no native construct to say "here are some known values, but others are also allowed."

### Our Approach

The `IndividualsToEnumRule` handles this semantic mismatch intelligently:

- **Closed enumerations** (classes with `owl:oneOf`): Uses `enum` constraint to enforce the closed set
- **Open sets** (classes with example individuals): Adds individuals as documentation via `x-known-individuals` without restricting to only those values

## Feature Description

When the `individuals_to_enum` rule is enabled, the transformation engine:

1. **Parses T-Box individuals** from the ontology (OWL NamedIndividuals)
2. **Groups them by class** based on their `rdf:type` declarations
3. **Adds enum constraints** to the `uri` property of each class that has individuals
4. **Includes labels** for each individual as metadata (`x-enum-labels`)

## Example

### Input Ontology (Turtle)

```turtle
@prefix ex: <http://example.org/test#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

ex:Color a owl:Class ;
    rdfs:label "Color" .

ex:Red a owl:NamedIndividual, ex:Color ;
    rdfs:label "Red" .

ex:Blue a owl:NamedIndividual, ex:Color ;
    rdfs:label "Blue" .

ex:Green a owl:NamedIndividual, ex:Color ;
    rdfs:label "Green" .
```

### Output JSON Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "definitions": {
    "Color": {
      "allOf": [
        {
          "$ref": "#/definitions/_Thing"
        },
        {
          "type": "object",
          "properties": {
            "uri": {
              "enum": [
                "http://example.org/test#Blue",
                "http://example.org/test#Green",
                "http://example.org/test#Red"
              ],
              "description": "Must be one of the defined Color individuals",
              "x-enum-labels": {
                "http://example.org/test#Blue": "Blue",
                "http://example.org/test#Green": "Green",
                "http://example.org/test#Red": "Red"
              }
            }
          }
        }
      ],
      "title": "Color",
      "description": "A color class"
    }
  }
}
```

## Usage

### Enabling the Rule

The `individuals_to_enum` rule is included in the default transformation rules. To ensure it's enabled:

```python
from src.owl2jsonschema.config import TransformationConfig
from src.owl2jsonschema.engine import TransformationEngine
from src.owl2jsonschema.parser import OntologyParser

# Parse ontology
parser = OntologyParser()
ontology = parser.parse("your_ontology.ttl", format="turtle")

# Configure with individuals rule enabled
config = TransformationConfig()
config.enable_rule("individuals_to_enum")

# Transform to JSON Schema
engine = TransformationEngine(config)
schema = engine.transform(ontology)
```

### JSON Schema Validation

The generated schema ensures that any JSON instance of a class with individuals must have a `uri` value that matches one of the defined individuals:

```json
{
  "uri": "http://example.org/test#Red",
  "@type": "Color"
}
```

This would be **valid** because `Red` is a defined individual of the `Color` class.

```json
{
  "uri": "http://example.org/test#Purple",
  "@type": "Color"
}
```

This would be **invalid** because `Purple` is not in the enum of defined individuals.

## Benefits

1. **Type Safety**: Ensures instances can only use URIs from the pre-defined set of individuals in the T-Box
2. **Documentation**: The `x-enum-labels` metadata provides human-readable names for each individual
3. **Validation**: Automatic validation of instance data against the ontology's terminological constraints
4. **Completeness**: The generated schema now fully represents the T-Box including classes, properties, and enumerated individuals
5. **Semantic Fidelity**: Preserves the closed-world semantics of enumerated types defined in the ontology

## Implementation Details

- **Rule Class**: [`IndividualsToEnumRule`](src/owl2jsonschema/rules/class_rules.py)
- **Engine Integration**: [`TransformationEngine._process_rule_result()`](src/owl2jsonschema/engine.py)
- **Parser Support**: Individuals are parsed by [`OntologyParser._parse_individuals()`](src/owl2jsonschema/parser.py)

## Testing

Run the test suite to verify the feature:

```bash
python test_individuals_in_schema.py
```

This creates a test ontology with classes and individuals, generates the JSON schema, and verifies that all individuals are correctly represented as enum constraints.

## Notes

- The feature works seamlessly with class inheritance (via `allOf`)
- Individuals can belong to multiple classes (each class will have the individual in its enum)
- Labels are extracted from `rdfs:label` annotations when available
- The feature is compatible with all JSON Schema draft versions supported by OntoJSON
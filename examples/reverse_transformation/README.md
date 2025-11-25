# JSON Schema → OWL Reverse Transformation Examples

This directory contains examples demonstrating how JSON Schema documents are transformed into OWL2 ontologies.

## Examples

### Example 1: Basic Class with Properties
- **Input:** [`example1_basic.json`](example1_basic.json)
- **Output:** [`example1_output.ttl`](example1_output.ttl)
- **Demonstrates:** Simple class with datatype properties, required fields, and basic type mappings

### Example 2: Inheritance
- **Input:** [`example2_inheritance.json`](example2_inheritance.json)
- **Output:** [`example2_output.ttl`](example2_output.ttl)
- **Demonstrates:** Class hierarchy using allOf, multiple inheritance, subClassOf relationships

### Example 3: Enumerations
- **Input:** [`example3_enums.json`](example3_enums.json)
- **Output:** [`example3_output.ttl`](example3_output.ttl)
- **Demonstrates:** Enum values as named individuals, oneOf enumeration classes

### Example 4: Object Properties
- **Input:** [`example4_object_props.json`](example4_object_props.json)
- **Output:** [`example4_output.ttl`](example4_output.ttl)
- **Demonstrates:** Object properties via $ref, domain and range, cardinality constraints

### Example 5: Complex Patterns
- **Input:** [`example5_complex.json`](example5_complex.json)
- **Output:** [`example5_complex.ttl`](example5_complex.ttl)
- **Demonstrates:** Union types, array cardinality, format mappings, circular references

## Transformation Patterns

### JSON Schema Type → OWL Datatype

| JSON Schema Type | OWL Datatype |
|-----------------|--------------|
| `"type": "string"` | `xsd:string` |
| `"type": "integer"` | `xsd:integer` |
| `"type": "number"` | `xsd:decimal` or `xsd:double` |
| `"type": "boolean"` | `xsd:boolean` |
| `"type": "string", "format": "date"` | `xsd:date` |
| `"type": "string", "format": "date-time"` | `xsd:dateTime` |
| `"type": "string", "format": "email"` | `xsd:string` (with annotation) |

### JSON Schema Constructs → OWL Patterns

| JSON Schema | OWL Equivalent |
|------------|----------------|
| Definition | `owl:Class` |
| Property with primitive type | `owl:DatatypeProperty` |
| Property with `$ref` | `owl:ObjectProperty` |
| `required: ["prop"]` | Exact cardinality of 1 on property |
| `allOf` with single `$ref` | `rdfs:subClassOf` (inheritance) |
| `allOf` with multiple `$ref` | Multiple `rdfs:subClassOf` (multiple inheritance) |
| `oneOf` with `$ref` | `owl:unionOf` |
| `enum: [...]` | Named individuals with `owl:oneOf` |
| `array` with `minItems`/`maxItems` | Cardinality restrictions |

## Running the Examples

### Using Python API

```python
from src.jsonschema2owl import ReverseEngine

# Create engine
engine = ReverseEngine()

# Transform from file
graph = engine.transform_from_file("example1_basic.json")

# Serialize to Turtle
turtle = engine.serialize(graph, format="turtle")
print(turtle)

# Save to file
with open("output.ttl", "w") as f:
    f.write(turtle)
```

### Using Command Line

```bash
# Transform a schema
python -m src.jsonschema2owl.cli transform example1_basic.json -o example1_output.ttl

# With custom namespace
python -m src.jsonschema2owl.cli transform example1_basic.json \
    --namespace http://myorg.org/ontology# \
    -o output.ttl

# Output in different format
python -m src.jsonschema2owl.cli transform example1_basic.json \
    --format json-ld \
    -o output.jsonld
```

## Configuration Options

Create a config file `reverse_config.json`:

```json
{
  "namespace": {
    "base": "http://example.org/ontology#"
  },
  "output": {
    "format": "turtle"
  },
  "transformation": {
    "array_handling": "non_functional_property",
    "allof_strategy": "inheritance",
    "create_individuals_for_enums": true
  }
}
```

Use it:

```python
from src.jsonschema2owl import ReverseEngine, ReverseTransformationConfig

config = ReverseTransformationConfig.from_file("reverse_config.json")
engine = ReverseEngine(config)
```

## Best Practices

1. **Use meaningful titles and descriptions** - They become `rdfs:label` and `rdfs:comment` in OWL
2. **Specify `$id` in schema** - Becomes the ontology URI
3. **Use `$ref` for object references** - Creates proper object properties
4. **Leverage enums for controlled vocabularies** - They become named individuals
5. **Use allOf for inheritance** - Creates proper class hierarchies
6. **Include format hints** - Helps map to appropriate XSD datatypes

## Common Issues and Solutions

### Issue: Properties not appearing as expected
**Solution:** Ensure properties are defined within a definition's `properties` object

### Issue: Inheritance not working
**Solution:** Use `allOf` with `$ref` to parent class

### Issue: Enums not creating individuals
**Solution:** Ensure enum is at top level of a definition, not nested in a property

### Issue: Circular references causing problems
**Solution:** The transformation handles circular refs correctly; they create self-referencing properties

## Validation

After transformation, validate the OWL ontology:

```python
from rdflib import Graph

# Load and validate
graph = Graph()
graph.parse("example1_output.ttl", format="turtle")

# Check it's valid
print(f"Valid RDF: {len(graph)} triples")

# Query for classes
classes = list(graph.subjects(RDF.type, OWL.Class))
print(f"Found {len(classes)} classes")
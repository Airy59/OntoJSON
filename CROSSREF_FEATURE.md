# Cross-Reference Feature for JSON Schema Generation

## Overview

The cross-reference feature enables the generation of modular JSON schemas from multiple ontologies while preserving the relationships between them. When transforming multiple ontologies into separate component schemas, the system automatically detects and resolves cross-ontology references, converting them to external JSON Schema `$ref` URIs.

## Key Features

### 1. **Automatic Cross-Reference Detection**
The system automatically identifies when a class in one ontology references a class from another ontology.

### 2. **External Reference Resolution**
Internal references (`#/definitions/ClassName`) are automatically rewritten to external references (`component_schema.json#/definitions/ClassName`) when the referenced class belongs to a different ontology.

### 3. **Modular Schema Organization**
Each ontology is transformed into a separate schema file, enabling:
- Independent schema reuse
- Clearer separation of concerns
- Better alignment with ontology import structure
- Easier maintenance and updates

## How It Works

### Architecture

The cross-reference resolution process involves three main components:

1. **CrossReferenceResolver**: Tracks which classes belong to which ontologies and rewrites references
2. **TransformationService**: Orchestrates the multi-ontology transformation process
3. **Component Schemas**: Individual JSON schemas for each source ontology

### Process Flow

1. **Parse and Register**: Parse all ontologies and register each class with its source ontology
2. **Transform**: Generate JSON schemas for each component independently
3. **Resolve**: Rewrite internal references to external references where appropriate
4. **Save**: Output separate schema files with proper cross-references

## Usage

### Basic Example

```python
from src.owl2jsonschema.services.transformation_service import TransformationService
from pathlib import Path

service = TransformationService()

# Transform multiple ontologies with cross-references
sources = [
    "ontology1.ttl",  # Contains: Person, Organization
    "ontology2.ttl"   # Contains: Driver (subclass of Person)
]

result = service.transform_multiple(
    sources=sources,
    transform_components=True  # Enable component schema generation
)

# Save the results
saved_files = service.save_transformation_results(
    result=result,
    output_dir=Path("output/schemas")
)
```

### Output Structure

After transformation, you'll get:

```
output/schemas/
├── composite_schema.json          # All classes in one file
├── ontology1_schema.json          # Classes from ontology1
└── ontology2_schema.json          # Classes from ontology2 with external refs
```

### Example: Cross-Reference in Action

**Input Ontologies:**

`ontology1.ttl`:
```turtle
:Person a owl:Class ;
    rdfs:label "Person" .
```

`ontology2.ttl`:
```turtle
@prefix ont1: <http://example.org/ontology1#> .

:Driver a owl:Class ;
    rdfs:label "Driver" ;
    rdfs:subClassOf ont1:Person .
```

**Output Schemas:**

`ontology1_schema.json`:
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "definitions": {
    "Person": {
      "type": "object",
      "title": "Person"
    }
  }
}
```

`ontology2_schema.json`:
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "definitions": {
    "Driver": {
      "type": "object",
      "title": "Driver",
      "allOf": [
        {
          "$ref": "ontology1_schema.json#/definitions/Person"
        }
      ]
    }
  }
}
```

Notice how the reference to `Person` in `Driver` uses an external reference: `"ontology1_schema.json#/definitions/Person"`.

## Benefits

### 1. **Modularity**
- Each ontology becomes a reusable schema module
- Changes to one ontology don't require regenerating all schemas
- Easier to maintain and version individual schemas

### 2. **Standards Compliance**
- Uses standard JSON Schema `$ref` mechanism
- Compatible with standard JSON Schema validators
- Follows JSON Schema best practices for multi-file schemas

### 3. **Ontology Alignment**
- Schema structure reflects ontology import structure
- Preserves the modular architecture of your ontology set
- Makes it easier to understand dependencies

### 4. **Validation Support**
- Multi-file JSON schema validation is supported by most validators
- Can validate instances against the appropriate component schema
- Validators automatically resolve external references

## Configuration

### Component Suffix

You can customize the suffix for component schema filenames:

```python
saved_files = service.save_transformation_results(
    result=result,
    output_dir=Path("output"),
    component_suffix="_schema.json"  # Default
)
```

### Composite Schema

The composite schema includes all classes from all ontologies in a single file, useful when you need a unified schema:

```python
result = service.transform_multiple(
    sources=sources,
    transform_components=True,  # Generate component schemas
    save_composite=True,        # Also save composite ontology
    composite_output_path=Path("composite.ttl")
)
```

## Advanced Features

### Dependency Analysis

The CrossReferenceResolver can analyze dependencies between components:

```python
from src.owl2jsonschema.crossref_resolver import CrossReferenceResolver

resolver = CrossReferenceResolver()
# ... after registering classes ...

# Get dependency graph
dependencies = resolver.generate_dependency_graph()
print(dependencies)
# Output: {'ontology2': ['ontology1'], 'ontology1': []}
```

### Reference Rewriting

You can manually rewrite references in a schema:

```python
resolver = CrossReferenceResolver()
# Register classes...

rewritten = resolver.rewrite_schema_references(
    schema=my_schema,
    current_source="ontology2",
    component_suffix="_schema.json"
)
```

## Implementation Details

### Class Registration

The system maintains several mappings:

- **class_to_source**: Maps class URI → source ontology name
- **class_name_to_source**: Maps cleaned class name → source ontology name
- **source_to_classes**: Maps source name → set of class URIs
- **source_to_class_names**: Maps source name → set of class names

### Reference Detection

References are detected using pattern matching:
- Internal references: `#/definitions/ClassName`
- External references: `component.json#/definitions/ClassName`

The resolver checks each `$ref` and rewrites it if the target class belongs to a different source ontology.

### Two-Pass Algorithm

1. **First Pass**: Transform all components and register all classes
2. **Second Pass**: Rewrite cross-references in all component schemas

This ensures all class-to-source mappings are known before resolving references.

## Testing

A comprehensive test suite is provided in `test_crossref_schemas.py`:

```bash
python test_crossref_schemas.py
```

This test:
- Creates multiple ontologies with cross-references
- Transforms them into component schemas
- Validates that external references are correctly resolved
- Displays a detailed analysis of the results

## Limitations and Considerations

### 1. **File Placement**
Component schema files must be in the same directory or have proper relative paths configured for `$ref` resolution to work with validators.

### 2. **Circular Dependencies**
While the system handles cross-references, circular dependencies between ontologies should be avoided or carefully managed.

### 3. **Validator Support**
Ensure your JSON Schema validator supports external `$ref` (most modern validators do, including ajv, jsonschema, etc.).

### 4. **URI Resolution**
The system uses relative file paths in `$ref`. For absolute URIs, additional configuration may be needed.

## Future Enhancements

Potential improvements for future versions:

1. **$id Support**: Add JSON Schema `$id` fields for proper URI-based resolution
2. **Circular Reference Detection**: Detect and warn about circular dependencies
3. **Reference Optimization**: Minimize redundant references
4. **Custom URI Schemes**: Support custom URI schemes for external references
5. **Dependency Visualization**: Generate visual dependency graphs

## API Reference

### CrossReferenceResolver

#### Methods

- `register_class(class_uri, class_name, source_name)`: Register a class from a source
- `get_source_for_class(class_name)`: Get source for a given class
- `is_external_reference(class_name, current_source)`: Check if reference is external
- `resolve_reference(class_name, current_source, component_suffix)`: Resolve a reference
- `rewrite_schema_references(schema, current_source, component_suffix)`: Rewrite all references in a schema

### TransformationService

#### Methods

- `transform_multiple(sources, transform_components=True, ...)`: Transform multiple ontologies
- `save_transformation_results(result, output_dir, ...)`: Save schemas to files
- `_clean_definition_name(name)`: Clean class names for use in schemas

## Examples

See the `test_crossref_schemas.py` file for complete working examples.

## Support

For issues or questions about the cross-reference feature, please:
1. Check this documentation
2. Review the test examples
3. Examine the source code in `src/owl2jsonschema/crossref_resolver.py`
4. Check the integration in `src/owl2jsonschema/services/transformation_service.py`

## Version History

- **v1.0** (2025-01-19): Initial implementation of cross-reference feature
  - Automatic cross-reference detection
  - External reference resolution
  - Two-pass transformation algorithm
  - Comprehensive test suite
# Component Schema Generation

## Overview

The OWL to JSON Schema transformation now supports generating separate JSON schemas for both the composite ontology and each individual component ontology. This allows you to work with the schemas at different levels of granularity.

## What Gets Generated

When transforming multiple ontologies, the system now creates:

1. **Composite Schema** - A JSON schema representing the merged/composite ontology that imports all source ontologies
2. **Component Schemas** - Individual JSON schemas for each source ontology

All schemas are saved to separate files for easy access and use.

## Key Features

- **Automatic Component Transformation** - Each input ontology is transformed independently
- **Flexible File Naming** - Customizable output filenames with prefixes and suffixes
- **Comprehensive Metadata** - Full tracking of source files, component counts, and transformation details
- **Error Resilience** - If one component fails, others continue processing with warnings
- **Separate File Output** - Each schema is saved to its own file for modular use

## Usage

### Python API

```python
from pathlib import Path
from src.owl2jsonschema.services.transformation_service import TransformationService
from src.owl2jsonschema.config import TransformationConfig

# Initialize service
service = TransformationService()

# Define your ontology sources
sources = [
    "ontology1.ttl",
    "ontology2.ttl",
    "ontology3.ttl"
]

# Configure transformation
config = TransformationConfig()

# Transform with component generation
result = service.transform_multiple(
    sources=sources,
    config=config,
    composite_metadata={
        "title": "My Composite Ontology",
        "description": "Combined ontology from multiple sources",
        "version": "1.0.0"
    },
    transform_components=True  # Enable component transformation
)

# Check if successful
if result.success:
    print(f"✅ Generated composite schema with {len(result.component_schemas)} components")
    
    # Save all schemas to files
    output_dir = Path("output/schemas")
    saved_files = service.save_transformation_results(
        result=result,
        output_dir=output_dir,
        composite_filename="composite_schema.json",
        component_suffix="_schema.json"
    )
    
    # Display saved files
    for schema_name, file_path in saved_files.items():
        print(f"  {schema_name}: {file_path}")
else:
    print(f"❌ Transformation failed: {result.error}")
```

### Result Structure

The `TransformationResult` object now includes:

```python
@dataclass
class TransformationResult:
    success: bool                                    # Overall success status
    schema: Optional[Dict[str, Any]]                 # Composite schema
    component_schemas: Dict[str, Dict[str, Any]]     # Component schemas by name
    error: Optional[str]                             # Error message if failed
    warnings: List[str]                              # Warnings from processing
    metadata: Dict[str, Any]                         # Transformation metadata
```

### Metadata Information

The result metadata includes:

- `is_composite`: Always `True` for multi-ontology transformations
- `source_count`: Number of source ontologies
- `sources`: List of source file paths
- `component_count`: Number of successfully transformed components
- `component_names`: List of component names
- `classes_count`: Total classes in composite ontology
- `properties_count`: Total properties in composite ontology

### File Naming

By default, the file naming convention is:

- **Composite**: `composite_schema.json`
- **Components**: `{ontology_name}_component_schema.json`

You can customize this:

```python
saved_files = service.save_transformation_results(
    result=result,
    output_dir="output",
    composite_filename="merged_ontology.json",
    component_prefix="ont_",
    component_suffix=".schema.json"
)
```

This would create:
- `merged_ontology.json` (composite)
- `ont_ontology1.schema.json` (component 1)
- `ont_ontology2.schema.json` (component 2)

## Example Output Structure

Given two ontologies (`person.ttl` and `vehicle.ttl`), you'll get:

```
output/
├── composite_schema.json              # Combined schema (Person + Vehicle + relationships)
├── person_component_schema.json       # Person ontology schema only
└── vehicle_component_schema.json      # Vehicle ontology schema only
```

### Composite Schema Example

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "My Composite Ontology",
  "description": "Combined ontology from multiple sources",
  "definitions": {
    "Person": { ... },
    "Organization": { ... },
    "Vehicle": { ... },
    "Car": { ... },
    "_Thing": { ... }
  }
}
```

### Component Schema Example (person_component_schema.json)

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "definitions": {
    "Person": { ... },
    "Organization": { ... },
    "_Thing": { ... }
  }
}
```

## Use Cases

1. **Modular Schema Management** - Work with individual domain schemas separately
2. **Selective Validation** - Validate data against specific component schemas
3. **Documentation** - Generate documentation for each ontology module
4. **Testing** - Test individual components before integration
5. **Version Control** - Track changes in specific ontology components

## Advanced Features

### Controlling Component Transformation

```python
# Transform only the composite (no components)
result = service.transform_multiple(
    sources=sources,
    transform_components=False
)
```

### Handling Warnings

```python
if result.warnings:
    print("⚠️  Warnings occurred:")
    for warning in result.warnings:
        print(f"  - {warning}")
```

### Accessing Individual Schemas

```python
# Access composite schema
composite = result.schema

# Access specific component
person_schema = result.component_schemas.get("person")
if person_schema:
    # Use the person schema
    pass
```

## Testing

Run the test script to verify the functionality:

```bash
python test_component_schemas.py
```

This will:
1. Create a composite ontology from test sources
2. Transform both composite and components
3. Save all schemas to `test_output/component_schemas/`
4. Verify all generated files are valid JSON

## Performance Considerations

- **Sequential Processing**: Components are transformed one at a time
- **Memory Usage**: Each schema is held in memory during transformation
- **File I/O**: All schemas are written to disk separately

For very large ontologies with many components, consider:
- Processing components in batches
- Using streaming for very large files
- Monitoring memory usage

## Error Handling

The system is designed to be resilient:

- If the composite transformation fails, the entire operation fails
- If a component transformation fails, it logs a warning and continues
- All errors include descriptive messages in the result

```python
if not result.success:
    print(f"Error: {result.error}")
    
for warning in result.warnings:
    print(f"Warning: {warning}")
```

## Integration with Other Tools

The generated component schemas can be used with:

- JSON Schema validators
- OpenAPI specifications
- Form generators
- Documentation tools
- Data validation frameworks

## Future Enhancements

Potential future features:
- Parallel component transformation
- Streaming output for large schemas
- Schema diff between components
- Dependency graph visualization
- Incremental updates

## See Also

- [`TransformationService`](src/owl2jsonschema/services/transformation_service.py) - Main transformation service
- [`CompositeOntologyBuilder`](src/owl2jsonschema/composite_builder.py) - Composite ontology creation
- [`TransformationConfig`](src/owl2jsonschema/config.py) - Configuration options
# JSON Schema Draft 7 Metadata Compliance

## Problem

The generated JSON schema contains the `$metadata` attribute, which is not recognized by the JSON Schema Draft 7 specification. This causes validation warnings when using strict JSON Schema validators.

## Solution

We've implemented multiple options for handling metadata in a Draft 7 compliant way. The default behavior has been changed to use `x-metadata` which is fully compliant with Draft 7.

## Configuration Options

You can configure how metadata is placed in the generated schema using the `ontology_metadata` rule's `placement` option:

### 1. **x-metadata** (Default - Recommended)
```json
{
  "rules": {
    "ontology_metadata": {
      "enabled": true,
      "options": {
        "placement": "x-metadata"
      }
    }
  }
}
```
- ✅ Fully Draft 7 compliant
- ✅ Preserves all metadata
- ✅ Recognized as custom extension by validators
- ✅ No validation warnings

Output example:
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "x-metadata": {
    "version": "1.0.0",
    "author": "John Doe",
    "license": "MIT"
  }
}
```

### 2. **comment**
```json
{
  "rules": {
    "ontology_metadata": {
      "enabled": true,
      "options": {
        "placement": "comment"
      }
    }
  }
}
```
- ✅ Fully Draft 7 compliant
- ✅ No validation warnings
- ⚠️ Metadata stored as JSON string (less readable)

Output example:
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$comment": "Metadata: {\"version\":\"1.0.0\",\"author\":\"John Doe\",\"license\":\"MIT\"}"
}
```

### 3. **defs**
```json
{
  "rules": {
    "ontology_metadata": {
      "enabled": true,
      "options": {
        "placement": "defs"
      }
    }
  }
}
```
- ✅ Fully Draft 7 compliant
- ✅ Keeps metadata separate from schema structure
- ✅ No validation warnings

Output example:
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$defs": {
    "_metadata": {
      "version": "1.0.0",
      "author": "John Doe",
      "license": "MIT"
    }
  }
}
```

### 4. **info**
```json
{
  "rules": {
    "ontology_metadata": {
      "enabled": true,
      "options": {
        "placement": "info"
      }
    }
  }
}
```
- ✅ OpenAPI-style metadata grouping
- ✅ No validation warnings
- ⚠️ Not a standard JSON Schema field (but allowed)

Output example:
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "info": {
    "version": "1.0.0",
    "author": "John Doe",
    "license": "MIT"
  }
}
```

### 5. **none**
```json
{
  "rules": {
    "ontology_metadata": {
      "enabled": true,
      "options": {
        "placement": "none"
      }
    }
  }
}
```
- ✅ No validation warnings
- ❌ Loses all ontology metadata

### 6. **root** (Legacy - Not Recommended)
```json
{
  "rules": {
    "ontology_metadata": {
      "enabled": true,
      "options": {
        "placement": "root"
      }
    }
  }
}
```
- ❌ Causes validation warnings
- ❌ Uses non-standard `$metadata`, `$schema-version`, etc. fields

## How to Apply the Workaround

### Option 1: Use the Default Configuration (Recommended)
The system now defaults to using `x-metadata` which is Draft 7 compliant. No action needed if you're using the latest version.

### Option 2: Programmatic Configuration
```python
from owl2jsonschema.config import TransformationConfig
from owl2jsonschema.engine import TransformationEngine

# Create configuration with desired placement
config = TransformationConfig()
config.set_rule_option("ontology_metadata", "placement", "x-metadata")

# Use the configuration
engine = TransformationEngine(config)
schema = engine.transform(ontology)
```

### Option 3: Configuration File
Create a `config.json` file:
```json
{
  "rules": {
    "ontology_metadata": {
      "enabled": true,
      "options": {
        "placement": "x-metadata"
      }
    }
  }
}
```

Then use it:
```python
from owl2jsonschema.config import TransformationConfig
from owl2jsonschema.engine import TransformationEngine

config = TransformationConfig.from_file('config.json')
engine = TransformationEngine(config)
schema = engine.transform(ontology)
```

### Option 4: Command Line (if using CLI)
```bash
owl2jsonschema --config config.json input.owl output.json
```

## Testing

Run the test script to see all options in action:
```bash
python test_metadata_draft7_compliance.py
```

This will demonstrate each placement option and show which ones are Draft 7 compliant.

## Migration from Previous Versions

If you were relying on the `$metadata` field in your applications:

1. **Update to use `x-metadata`**: Change your code to look for `schema["x-metadata"]` instead of `schema["$metadata"]`

2. **Use a migration script**:
```python
# Convert old schema to new format
if "$metadata" in schema:
    schema["x-metadata"] = schema.pop("$metadata")
```

3. **Keep using the legacy format**: If you must keep the old format, explicitly set:
```python
config.set_rule_option("ontology_metadata", "placement", "root")
```

## Validation

To validate your generated schema against Draft 7:

```python
import jsonschema
from jsonschema import Draft7Validator

# Your generated schema
schema = {...}

# Validate the schema itself
try:
    Draft7Validator.check_schema(schema)
    print("✅ Schema is valid Draft 7")
except jsonschema.SchemaError as e:
    print(f"❌ Schema validation error: {e}")
```

## Summary

- **Default behavior**: Now uses `x-metadata` (Draft 7 compliant)
- **No code changes needed**: Works automatically with the latest version
- **Backward compatibility**: Can still use old format if needed with `placement: "root"`
- **Multiple options**: Choose the metadata placement that best fits your needs

The recommended approach is to use the default `x-metadata` placement, which:
- Is fully Draft 7 compliant
- Causes no validation warnings
- Preserves all metadata information
- Is recognized as a valid extension by JSON Schema validators
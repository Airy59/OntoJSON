# OntoJSON Quick Start Guide

## 🚀 Getting Started in 5 Minutes

### For End Users (No Programming Required)

#### macOS
1. Download `OntoJSON.app` from releases
2. Double-click to open
3. Click "Browse" to select your OWL file
4. Click "Transform" to convert
5. Save the result

#### Windows
1. Download `OntoJSON.exe` from releases
2. Double-click to run
3. Browse for your OWL file
4. Click "Transform"
5. Save as JSON or YAML

### For Developers

#### Quick Install
```bash
git clone <repo-url>
cd OntoJSON
pip install -e ".[gui]"
```

#### Quick Run
```bash
# GUI
python owl2jsonschema_gui.py

# CLI
owl2jsonschema input.owl -o output.json
```

## 📋 Common Tasks

### 1. Convert OWL to JSON Schema (GUI)
1. Launch OntoJSON
2. File → Open → Select your .owl file
3. Configure rules (optional)
4. Click "Transform"
5. File → Save As → Choose location

### 2. Convert OWL to JSON Schema (CLI)
```bash
owl2jsonschema myontology.owl -o schema.json
```

### 3. Convert with Specific Rules
```bash
# Enable only specific rules
owl2jsonschema input.owl -o output.json \
  --enable-rule class_to_object \
  --enable-rule property_cardinality
```

### 4. Build Standalone App

#### Simple Method (macOS)
```bash
# Build the app bundle in project root
./create_app_bundle.sh
# App created at: ./OntoJSON.app
```

#### Advanced Build System (Self-Contained Apps)
```bash
# Non-interactive build (recommended)
python build_system/build_app.py --macos
# Creates: build_system/dist/OntoJSON.app (112MB, includes Python & all dependencies)

# Or interactive mode
python build_system/build_app.py
```

## 🎯 Rule Categories

### Essential Rules (Usually Keep Enabled)
- `class_to_object` - Convert OWL classes to JSON objects
- `property_domain_range` - Add property constraints
- `labels_to_titles` - Use rdfs:label as titles

### Cardinality Rules
- `property_cardinality` - Min/max occurrences
- `functional_properties` - Single-valued properties
- `inverse_functional` - Unique identifiers

### Annotation Rules
- `comments_to_descriptions` - Add descriptions
- `annotations_to_metadata` - Preserve metadata
- `deprecated_to_metadata` - Mark deprecated items

### Advanced Rules
- `union_to_anyof` - Union types → anyOf
- `intersection_to_allof` - Intersection → allOf
- `complement_to_not` - Negation support

## 🛠️ Configuration Examples

### Minimal Config
```yaml
rules:
  class_to_object:
    enabled: true
```

### Standard Config
```yaml
rules:
  class_to_object:
    enabled: true
  property_cardinality:
    enabled: true
  labels_to_titles:
    enabled: true
    options:
      language: "en"
output:
  format: "json-schema-draft-07"
  indent: 2
```

### Full-Featured Config
```yaml
rules:
  # Enable all class rules
  class_to_object:
    enabled: true
  class_hierarchy:
    enabled: true
  disjoint_classes:
    enabled: true
  
  # Enable all property rules
  property_domain_range:
    enabled: true
  property_cardinality:
    enabled: true
  functional_properties:
    enabled: true
  
  # Enable annotations
  labels_to_titles:
    enabled: true
  comments_to_descriptions:
    enabled: true
  
  # Enable advanced features
  union_to_anyof:
    enabled: true
  intersection_to_allof:
    enabled: true

output:
  format: "json-schema-draft-07"
  indent: 2
  include_metadata: true
```

## 📊 Example Transformation

### Input (OWL)
```xml
<owl:Class rdf:about="Person">
  <rdfs:label>Person</rdfs:label>
  <rdfs:comment>Represents a human being</rdfs:comment>
</owl:Class>

<owl:DatatypeProperty rdf:about="hasName">
  <rdfs:domain rdf:resource="Person"/>
  <rdfs:range rdf:resource="xsd:string"/>
  <owl:minCardinality>1</owl:minCardinality>
</owl:DatatypeProperty>
```

### Output (JSON Schema)
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "definitions": {
    "Person": {
      "type": "object",
      "title": "Person",
      "description": "Represents a human being",
      "properties": {
        "hasName": {
          "type": "string",
          "minItems": 1
        }
      },
      "required": ["hasName"]
    }
  }
}
```

## 🆘 Troubleshooting

### GUI Won't Start
```bash
# Check PyQt6 installation
pip install PyQt6

# Try virtual environment
python -m venv .venv
source .venv/bin/activate
pip install -e ".[gui]"
```

### Build Fails

#### For Simple App Bundle (macOS)
```bash
# Make sure script is executable
chmod +x create_app_bundle.sh

# Run the build script
./create_app_bundle.sh

# App will be at: ./OntoJSON.app
```

#### For Advanced Build System
```bash
# Install build dependencies (if not already installed)
pip install pyinstaller pillow

# Clean previous builds
rm -rf build_system/dist build_system/temp

# Run non-interactive build
python build_system/build_app.py --macos

# Output: build_system/dist/OntoJSON.app
```

### Import Errors
```bash
# Reinstall in development mode
pip install -e .

# Check Python path
python -c "import owl2jsonschema; print(owl2jsonschema.__file__)"
```

## 📚 Learn More

- [Full Documentation](README.md)
- [Transformation Rules](transformation_rules.md)
- [Architecture Guide](architecture.md)
- [Build System](build_system/README.md)

## 💡 Tips

1. **Start Simple**: Begin with just `class_to_object` rule
2. **Test Incrementally**: Enable rules one at a time
3. **Use GUI First**: Easier to experiment with rules
4. **Save Configs**: Export working configurations for reuse
5. **Check Logs**: Enable verbose logging for debugging
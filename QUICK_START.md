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
pip install -e ".[gui]"  # For GUI
pip install -e ".[web]"  # For Web App
```

#### Quick Run
```bash
# GUI
python owl2jsonschema_gui.py

# Web App (Browser-based)
python src/owl2jsonschema_web/launch_web.py
# Or with specific port:
python src/owl2jsonschema_web/app.py --port 8080

# CLI
owl2jsonschema input.owl -o output.json
```

## 📋 Common Tasks

### 1. Convert OWL to JSON Schema (Web App)

The web application provides a browser-based interface accessible from any device:

#### Starting the Web App
```bash
# Automatic port selection (avoids conflicts)
python src/owl2jsonschema_web/launch_web.py

# Manual port selection
python src/owl2jsonschema_web/app.py --port 8080

# Force-free a specific port if stuck
python src/owl2jsonschema_web/launch_web.py --port 8080 --force
```

**Note:** On macOS, port 5000 is used by AirPlay. The app defaults to port 9090 to avoid conflicts.

#### Using the Web Interface
1. Open your browser to `http://localhost:9090` (or the port shown in terminal)
2. **Upload** ontology files or enter URLs
3. **Configure** transformation options
4. **Transform** and view results in browser
5. **Download** JSON Schema, sample instances, or JSON-LD

#### REST API
The web app also provides a REST API:
```bash
# Transform a local file
curl -X POST -F "file=@ontology.ttl" http://localhost:9090/api/transform

# Transform from URL
curl -X POST -H "Content-Type: application/json" \
  -d '{"source": "http://example.com/ontology.ttl"}' \
  http://localhost:9090/api/transform
```

See [Web App Guide](WEB_APP_GUIDE.md) for full documentation.

### 2. Convert OWL to JSON Schema (GUI)

#### Single Ontology
1. Launch OntoJSON
2. Enter path or URI in the text editor (or use "Select Files" button)
3. Configure rules (optional)
4. Click "Transform T-box to JSON Schema"
5. File → Save JSON Schema

#### Multiple Ontologies (Composite Creation)
1. Launch OntoJSON
2. Add multiple sources to the text editor (one per line):
   - Use "Select Files" for local files
   - Use "Add URI" for remote ontologies
   - Or type/paste directly in the editor
3. When you click "Transform", a dialog appears for metadata
4. Enter composite ontology metadata (optional)
5. Click OK - composite is created automatically
6. **Save Options**:
   - File → Save JSON Schema (transformation result)
   - File → Save Ontology to... (save composite ontology with metadata)
7. The saved composite can be reused as input for future transformations

#### Complete T-box/A-box/JSON Workflow

The GUI supports a complete three-step workflow for generating test data:

**Step 1: T-box Transformation**
1. Load ontology sources (single or multiple)
2. Configure transformation rules
3. Click "Transform T-box to JSON Schema"
4. View results in the Schema tab
5. Check Statistics tab for transformation metrics

**Step 2: A-box Generation (Optional)**
1. After T-box is ready, navigate to "A-box Generation" tab
2. Configure generation settings:
   - Base URI (default: https://example.org#)
   - Min instances per class (1-10)
   - Max instances per class (1-20)
3. Click "Generate A-box"
4. Optionally validate with OWL Reasoner
5. Save A-box as Turtle, RDF/XML, or N-Triples

**Step 3: JSON Instance Generation (Optional)**
1. After A-box is generated, navigate to "JSON Instance Generation" tab
2. Choose reference style:
   - **Inline Objects**: Self-contained JSON documents
   - **URI References**: Linked data approach with @id references
3. Click "Transform A-box to JSON"
4. View side-by-side JSON and JSON-LD outputs
5. Validate against the generated schema
6. Save as JSON or JSON-LD

### 3. Convert OWL to JSON Schema (CLI)

#### Single Ontology
```bash
# Direct transformation - no modification to the ontology
owl2jsonschema myontology.owl -o schema.json
```

#### Multiple Ontologies
```bash
# Create a composite ontology first, then transform
# (Currently requires using Python API - see below)
```

### 4. Convert with Specific Rules
```bash
# Enable only specific rules
owl2jsonschema input.owl -o output.json \
  --enable-rule class_to_object \
  --enable-rule property_cardinality
```

### 5. Build Standalone App

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

## 🔄 Single vs. Multiple Ontologies

### Single Ontology Processing
- **Input**: One file path or URI
- **Processing**: Direct transformation
- **Output**: JSON Schema from the original ontology
- **Use case**: Simple, standalone ontologies

### Multiple Ontology Processing
- **Input**: Two or more file paths/URIs
- **Processing**:
  1. Creates composite ontology with `owl:imports`
  2. Adds user-provided metadata
  3. Transforms unified ontology
- **Output**: JSON Schema from composite ontology
- **Use case**: Multi-domain integration, modular ontologies

### GUI Input Methods

The new text editor interface supports flexible input with these features:

**Text Editor Controls:**
- 📁 **Select Files**: Browse and add local ontology files
- 🌐 **Add URI**: Input remote ontology URLs via dialog
- ➖ **Remove Line**: Delete line at cursor position
- 🗑️ **Clear All**: Reset the entire list

**Supported Input Formats:**
```
# Local files (Unix/Linux/macOS)
/path/to/ontology1.owl
~/Documents/myontology.ttl
./relative/path/ontology.rdf

# Local files (Windows)
C:\Users\Name\ontology2.ttl
D:\Ontologies\domain.owl

# Remote URIs
https://example.org/ontology3.rdf
http://purl.org/ontology4.owl
https://raw.githubusercontent.com/user/repo/main/onto.ttl

# File URIs
file:///home/user/ontology5.n3
file:///C:/Users/Name/Documents/onto.owl
```

**Smart Processing:**
- **1 source**: Direct transformation, no modification
- **2+ sources**: Automatic composite creation with imports
- **Mixed sources**: Combine local and remote in one transformation
- **Composite Persistence**: Save composite ontology with all metadata for reuse

**Live Status Indicator:**
- Counter shows "N ontologies" at bottom right
- Transform button enables when sources are present
- Real-time validation as you type/paste

## � Example Transformation

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

### Web App Issues

#### Port Already in Use
```bash
# Use the smart launcher to find available port
python src/owl2jsonschema_web/launch_web.py

# Or force-free a specific port
python src/owl2jsonschema_web/launch_web.py --port 8080 --force

# On macOS, avoid port 5000 (used by AirPlay)
```

#### Flask Not Found
```bash
# Install web dependencies
pip install -e ".[web]"
# Or manually:
pip install Flask flask-cors flask-session
```

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
- [Web App Guide](WEB_APP_GUIDE.md)
- [Transformation Rules](transformation_rules.md)
- [Architecture Guide](architecture.md)
- [Build System](build_system/README.md)

## 💡 Tips

1. **Start Simple**: Begin with just `class_to_object` rule
2. **Test Incrementally**: Enable rules one at a time
3. **Use GUI First**: Easier to experiment with rules
4. **Save Configs**: Export working configurations for reuse
5. **Check Logs**: Enable verbose logging for debugging
6. **Single vs. Multiple**:
   - Use single ontology for quick transformations
   - Use multiple when you need to combine domains
7. **Mix Sources**: Combine local files and remote URIs in one transformation
8. **Composite Benefits**: Automatic import resolution and dependency handling
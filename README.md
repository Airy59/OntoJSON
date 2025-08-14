# OntoJSON - OWL to JSON Schema Transformation Engine

A powerful, configurable transformation engine for converting RDF/OWL ontologies to JSON Schema with support for rule-based transformations using the visitor pattern. Includes both command-line tools and a user-friendly GUI application.

## 🚀 Features

- **Configurable Transformation Rules**: Enable or disable specific transformation rules based on your needs
- **Visitor Pattern Architecture**: Clean separation of concerns with extensible rule-based transformations
- **Comprehensive Rule Set**: Supports a wide range of OWL constructs and their JSON Schema equivalents
- **GUI Application**: User-friendly desktop application for easy ontology transformation
- **Standalone Distributions**: Pre-built applications for macOS, Windows, and Linux (no Python required)
- **Extensible Design**: Easy to add custom transformation rules and extend functionality
- **Multiple Output Formats**: Support for JSON Schema and YAML output

## 📦 Installation

### Option 1: Use Pre-built Applications (Recommended for End Users)

Download the standalone application for your platform:

- **macOS**: `OntoJSON.app` - Native macOS application
  - Download from releases page
  - Or build locally: See [Build System Documentation](#build-system)
  
- **Windows**: `OntoJSON.exe` - Windows executable
  - Download from releases page
  - Or build locally: See [Build System Documentation](#build-system)
  
- **Linux**: Coming soon

### Option 2: Python Package Installation

#### Basic Installation

```bash
# Clone the repository
git clone <repository-url>
cd OWLtoJSONschema

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install the package
pip install -e .
```

#### Installation with GUI Support

```bash
# Install with Qt6 GUI support
pip install -e ".[gui]"
```

#### Development Installation

```bash
# Install with all development dependencies
pip install -e ".[dev,gui]"
```

## 🖥️ Usage

### Graphical User Interface (GUI)

The OntoJSON GUI provides an intuitive interface for transforming ontologies:

#### Launching the GUI

**From Standalone App:**
- **macOS**: Double-click `OntoJSON.app`
- **Windows**: Double-click `OntoJSON.exe`
- **Linux**: Run `./OntoJSON`

**From Python Installation:**
```bash
# Launch the GUI application
python owl2jsonschema_gui.py

# Or if installed via pip
owl2jsonschema-gui

# Or using the launcher script
./launch_ontojson.py
```

#### GUI Features

- **File Management**:
  - Browse and select OWL/RDF input files
  - Choose output folders and filenames
  - Support for multiple file formats (.owl, .rdf, .ttl)

- **Rule Configuration**:
  - Enable/disable individual transformation rules via checkboxes
  - Organized into categories: Classes, Properties, Annotations, Advanced, Structural
  - Save and load custom rule configurations

- **Transformation Options**:
  - Language selection for labels and descriptions
  - Indentation control (2, 4 spaces, or tabs)
  - Output format selection (JSON or YAML)

- **Real-time Features**:
  - Live preview of generated JSON Schema
  - Transformation statistics and metrics
  - Detailed logging with error reporting
  - Progress indicators for long operations

- **Export Options**:
  - Save as JSON Schema
  - Export as YAML
  - Copy to clipboard

### Command Line Interface (CLI)

```bash
# Basic usage
owl2jsonschema input.owl -o output.json

# With custom configuration
owl2jsonschema input.owl -o output.json --config config.yaml

# Enable specific rules
owl2jsonschema input.owl -o output.json --enable-rule class_to_object --enable-rule property_cardinality

# Disable specific rules
owl2jsonschema input.owl -o output.json --disable-rule annotations_to_metadata

# Specify output format
owl2jsonschema input.owl -o output.yaml --format yaml

# Set language for labels/descriptions
owl2jsonschema input.owl -o output.json --language fr
```

### Python API

```python
from owl2jsonschema import TransformationEngine, TransformationConfig, OntologyParser
import json

# Parse the ontology
parser = OntologyParser()
ontology = parser.parse("input.owl")

# Configure the transformation
config = TransformationConfig({
    "rules": {
        "class_to_object": {"enabled": True},
        "property_cardinality": {"enabled": True},
        "annotations_to_metadata": {"enabled": False}
    },
    "options": {
        "language": "en",
        "indent": 2
    }
})

# Run the transformation
engine = TransformationEngine(config)
json_schema = engine.transform(ontology)

# Save the result
with open("output.json", "w") as f:
    json.dump(json_schema, f, indent=2)
```

## ⚙️ Configuration

Create a `config.yaml` file to customize the transformation:

```yaml
# Transformation configuration
rules:
  # Class transformation rules
  class_to_object:
    enabled: true
  class_hierarchy:
    enabled: true
  
  # Property transformation rules
  property_cardinality:
    enabled: true
    options:
      use_arrays: true
  property_domain_range:
    enabled: true
  
  # Annotation rules
  labels_to_titles:
    enabled: true
    options:
      language: "en"
  comments_to_descriptions:
    enabled: true
    options:
      language: "en"
  
  # Advanced rules
  union_to_anyof:
    enabled: true
  intersection_to_allof:
    enabled: true

# Output configuration
output:
  format: "json-schema-draft-07"
  indent: 2
  include_metadata: true
  language: "en"
```

## 🏗️ Build System

OntoJSON includes a comprehensive build system for creating standalone applications:

### Building Standalone Applications

```bash
# Navigate to build system
cd build_system

# Interactive build menu
python build_app.py

# Direct platform builds
python scripts/build_macos.py     # macOS: Creates .app and .dmg
python scripts/build_windows.py   # Windows: Creates .exe and installer
python scripts/build_linux.py     # Linux: Coming soon
```

### Build Features

- **macOS**: 
  - Native `.app` bundle
  - DMG installer with drag-to-Applications
  - Code signing support
  - Universal binary (Intel + Apple Silicon)

- **Windows**:
  - Standalone `.exe` file
  - NSIS installer with Start Menu integration
  - Portable ZIP package
  - Version information embedding

- **Linux** (Coming Soon):
  - AppImage for universal compatibility
  - DEB/RPM packages
  - Flatpak support

For detailed build instructions, see [build_system/README.md](build_system/README.md).

## 📚 Documentation

- **[Transformation Rules](transformation_rules.md)**: Complete list of available transformation rules
- **[Architecture](architecture.md)**: System architecture and design patterns
- **[Build System](build_system/README.md)**: Instructions for building standalone applications
- **[API Reference](docs/api.md)**: Detailed API documentation (coming soon)

## 🧪 Development

### Project Structure

```
OWLtoJSONschema/
├── src/
│   ├── owl2jsonschema/        # Core transformation engine
│   │   ├── rules/             # Transformation rules
│   │   ├── model.py           # Data models
│   │   ├── engine.py          # Main engine
│   │   └── visitor.py         # Visitor pattern implementation
│   └── owl2jsonschema_gui/    # GUI application
│       ├── app.py             # Application entry point
│       └── main_window.py     # Main window implementation
├── build_system/              # Standalone app builder
│   ├── scripts/               # Platform-specific builders
│   └── configs/               # Build configurations
├── tests/                     # Test suite
├── examples/                  # Example ontologies
└── docs/                      # Documentation
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=owl2jsonschema

# Run specific test file
pytest tests/test_engine.py

# Run GUI tests
pytest tests/test_gui.py
```

### Code Quality

```bash
# Format code
black src tests

# Check linting
flake8 src tests

# Type checking
mypy src

# Run all checks
make lint
```

### Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

Licensed under the European Union Public Licence (EUPL) v1.2. See [LICENSE](LICENSE) file for details.

## 👥 Credits

See [credits.txt](credits.txt) for acknowledgments and third-party licenses.

## 🐛 Support

- **Issues**: Report bugs via [GitHub Issues](https://github.com/username/OWLtoJSONschema/issues)
- **Discussions**: Ask questions in [GitHub Discussions](https://github.com/username/OWLtoJSONschema/discussions)
- **Email**: Contact the maintainer at [email](mailto:maintainer@example.com)

## 🚦 Project Status

- ✅ Core transformation engine: **Stable**
- ✅ GUI application: **Stable**
- ✅ macOS build system: **Stable**
- ✅ Windows build system: **Ready** (requires Windows to build)
- 🚧 Linux build system: **In Development**
- 🚧 Web version: **Planned**
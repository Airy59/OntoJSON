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
  - Build locally using `./create_app_bundle.sh` (creates app in project root)
  - Location after build: `[project-root]/OntoJSON.app`
  
- **Windows**: `OntoJSON.exe` - Windows executable
  - Download from /build_system/dist
  - Or build locally: See [Build System Documentation](#build-system)
  
- **Linux**: Coming soon

### Option 2: Python Package Installation

#### Basic Installation

```bash
# Clone the repository
git clone <repository-url>
cd OntoJSON

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
  - Support for multiple file formats (.owl, .rdf, .ttl, .jsonld)

- **Rule Configuration**:
  - Enable/disable individual transformation rules via checkboxes
      note: not all combinations were tested or even make sense; preferrably use default settings
  - Rules are organized into categories: Classes, Properties, Annotations, Advanced, Structural
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

OntoJSON includes a comprehensive build system for creating standalone applications for macOS, Windows, or Linux (Ubuntu):

### Building Standalone Applications

#### macOS App Bundle (Simple Method)
```bash
# Build the app bundle in project root
./create_app_bundle.sh

# App will be created at: ./OntoJSON.app
# Launch with: open OntoJSON.app
```

#### Advanced Build System (Self-Contained Apps)
```bash
# For self-contained app with all dependencies (no Python required)
# Non-interactive command-line mode (recommended for automation)
python build_system/build_app.py --macos

# Or interactive mode with options
python build_system/build_app.py

# Output location: build_system/dist/OntoJSON.app (112MB self-contained)
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

- **Linux** (coming Soon):
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
OntoJSON/
├── src/
│   ├── owl2jsonschema/           # Core transformation engine
│   │   ├── rules/                # Transformation rules
│   │   │   ├── __init__.py
│   │   │   ├── advanced_rules.py
│   │   │   ├── annotation_rules.py
│   │   │   ├── class_rules.py
│   │   │   ├── property_rules.py
│   │   │   └── structural_rules.py
│   │   ├── __init__.py
│   │   ├── abox_generator.py     # ABox generation utilities
│   │   ├── abox_to_json.py       # ABox to JSON conversion
│   │   ├── builder.py             # Schema builder
│   │   ├── cli.py                 # Command-line interface
│   │   ├── config.py              # Configuration management
│   │   ├── engine.py              # Main transformation engine
│   │   ├── model.py               # Data models
│   │   ├── parser.py              # Ontology parser
│   │   ├── reasoner.py            # OWL reasoning utilities
│   │   └── visitor.py             # Visitor pattern implementation
│   └── owl2jsonschema_gui/       # GUI application
│       ├── __init__.py
│       ├── app.py                 # Application entry point
│       └── main_window.py         # Main window implementation
├── build_system/                  # Standalone app builder
│   ├── configs/                   # Build configurations
│   │   └── build_config.py
│   ├── scripts/                   # Platform-specific builders
│   │   ├── build_macos.py
│   │   └── build_windows.py
│   ├── build_app.py               # Main build script
│   ├── README.md                  # Build system documentation
│   └── requirements.txt           # Build dependencies
├── Documentation/                 # Project documentation
│   ├── for_testing.graphol
│   ├── readme.md
│   └── test ontology files...
├── examples/                      # Example ontologies
│   └── person_ontology.owl
├── OntoJSON.app/                  # macOS application bundle
│   └── Contents/
│       ├── Info.plist
│       ├── MacOS/
│       │   └── OntoJSON
│       └── Resources/
│           └── ORW_big.png
├── Resources/                     # Application resources
│   ├── ORW_48.png
│   └── ORW_big.png
├── test_output/                   # Test output directory
│   └── various test schemas...
├── tests/                         # Test suite
│   ├── __init__.py
│   ├── test_abox_to_json.py
│   ├── test_all_variants.py
│   ├── test_check_required.py
│   ├── test_circular_reference.py
│   ├── test_debug_abox_conversion.py
│   ├── test_debug_partof.py
│   ├── test_debug_variants.py
│   ├── test_default_config.py
│   ├── test_disjoint_classes.py
│   ├── test_engine_order.py
│   ├── test_engine.py
│   ├── test_final_verification.py
│   ├── test_gui_config.py
│   ├── test_gui_defaults.py
│   ├── test_optional_properties.py
│   ├── test_properties_assignment.py
│   └── test_thing_inheritance.py
├── .gitignore                     # Git ignore file
├── .vscode/                       # VS Code settings
├── .idea/                         # PyCharm/IntelliJ settings
├── architecture.md                # Architecture documentation
├── create_app_bundle.sh           # macOS app bundle creator
├── credits.txt                    # Credits and acknowledgments
├── Info.plist                     # macOS app metadata
├── launch_from_pycharm.py         # PyCharm launcher
├── launch_ontojson.py             # Main launcher script
├── LAUNCHING_ONTOJSON.md          # Launch instructions
├── OntoJSON.command               # macOS command launcher
├── owl2jsonschema_gui.py          # GUI launcher
├── owlrl_issue_diagnosis.md      # OWL-RL issue documentation
├── PROPERTY_REQUIREMENTS_*.md    # Property requirement docs
├── pyproject.toml                 # Python project configuration
├── QUICK_START.md                 # Quick start guide
├── README.md                      # This file
├── run_ontojson_gui.py            # Alternative GUI launcher
├── sample_config.json             # Sample configuration
├── SOLUTION_GUIDE.md              # Solution documentation
└── transformation_rules.md        # Transformation rules docs
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

- **Issues**: Report bugs via [GitHub Issues](https://github.com/username/OntoJSON/issues)
- **Discussions**: Ask questions in [GitHub Discussions](https://github.com/username/OntoJSON/discussions)
- **Email**: Contact the maintainer at [email](mailto:airy-services@hotmail.com)

## 🚦 Project Status

- ✅ Core transformation engine: **Stable**
- ✅ GUI application: **Stable**
- ✅ macOS build system: **Stable**
- ✅ Windows build system: **Ready** (requires Windows to build)
- 🚧 Linux build system: **In Development**
- 🚧 Web version: **Planned**

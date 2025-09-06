# OntoJSON - OWL to JSON Schema Transformation Engine

A powerful, configurable transformation engine for converting RDF/OWL ontologies to JSON Schema with support for rule-based transformations using the visitor pattern. Includes both command-line tools and a user-friendly GUI application.

## 🚀 Features

### Core Capabilities
- **Configurable Transformation Rules**: Enable or disable specific transformation rules based on your needs
- **Visitor Pattern Architecture**: Clean separation of concerns with extensible rule-based transformations
- **Comprehensive Rule Set**: Supports a wide range of OWL constructs and their JSON Schema equivalents
- **Full Inheritance Support**: Correctly handles complex class hierarchies including multiple inheritance
- **RDF/Turtle Support**: Import and transform RDF Turtle files (.ttl) with proper namespace handling
- **Import Resolution**: Automatic resolution and loading of imported ontologies
- **Ontology Partitioning**: Split large ontologies into semantically coherent modules
  - Efficient chunking for files exceeding memory/token limits
  - Multiple partitioning strategies (community detection, domain-based, hierarchical)
  - Preserves semantic completeness (annotations, restrictions, domains/ranges)
  - Quality metrics and visualizations

### Smart Multi-Ontology Support
- **Intelligent Workflow Detection**:
  - Single ontology: Direct transformation without modification
  - Multiple ontologies: Automatic composite creation with import statements
- **Flexible Input Methods**:
  - Text editor with mixed local/remote sources
  - Drag-and-drop file selection
  - URI input dialog for remote ontologies
- **Composite Ontology Builder**:
  - Automatic generation of `owl:imports` statements
  - Custom metadata support (title, version, author, description)
  - Temporary file management for processing
  - Support for heterogeneous sources (mix local files and remote URIs)

### Complete T-box/A-box Workflow
- **Step 1 - T-box Transformation**: Convert OWL ontologies to JSON Schema
- **Step 2 - A-box Generation**: Create random individuals conforming to T-box constraints
- **Step 3 - JSON Instance Generation**: Transform A-box to JSON/JSON-LD instances with validation

### Application Features
- **Multi-Platform Support**:
  - Desktop GUI Application (PyQt6) with three-step workflow
  - Web Interface (Flask) for browser-based access
  - Command-line Interface (CLI) for automation
  - REST API for programmatic integration
- **Standalone Distributions**: Pre-built applications for macOS, Windows, and Linux (no Python required)
- **Extensible Design**: Easy to add custom transformation rules and extend functionality
- **Multiple Output Formats**: Support for JSON Schema, YAML, JSON-LD, and more
- **Async Processing**: Background task processing for large transformations (web interface)

## 📦 Installation

### Option 1: Use Pre-built Applications (Recommended for End Users)

Download the standalone application for your platform:

- **macOS**: `OntoJSON.app` - Native macOS application
  - Build locally using `./create_app_bundle.sh` (creates app in project root)
  - Location after build: `[project-root]/OntoJSON.app`
  
- **Windows**: `OntoJSON.exe` - Windows executable
  - Download from /build_system/dist or releases page
  - Or build locally: See [Build System Documentation](build_system/README.md)
  
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

#### Installation with Web Interface Support

```bash
# Install with Flask web interface
pip install -e ".[web]"

# Or install all interfaces
pip install -e ".[gui,web]"
```

#### Development Installation

```bash
# Install with all development dependencies
pip install -e ".[dev,gui,web]"
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

##### Ontology Input Management
- **Flexible Text Editor Interface**:
  - One source per line format
  - Mix local paths and remote URIs freely
  - Real-time source counter
  - Line-by-line editing with cursor control
- **Interactive Controls**:
  - 📁 Select Files - Browse local ontologies
  - 🌐 Add URI - Input remote ontologies
  - ➖ Remove Line - Delete at cursor
  - 🗑️ Clear All - Reset the list
- **Smart Workflow Detection**:
  - Single source → Direct transformation
  - Multiple sources → Composite creation dialog

##### Composite Ontology Features (Auto-triggered for 2+ sources)
- **Metadata Dialog**:
  - Title, version, author fields
  - Description and comments
  - All fields are optional
- **Automatic Processing**:
  - Generates `owl:imports` statements
  - Creates composite ontology with metadata
  - Resolves dependencies automatically
- **Persistence Options**:
  - Save composite ontology to file (File → Save Ontology to...)
  - Export in multiple formats (Turtle, RDF/XML, JSON-LD, N3)
  - Reuse saved composite as input for future transformations
  - Preserves all metadata and import statements

##### Three-Step Workflow Tabs

**Tab 1: T-box Transformation**
- Configure transformation rules
- Select language for labels
- Include/exclude URI metadata
- View original and JSON-LD formats
- Statistics and metrics panel

**Tab 2: A-box Generation**
- Set base URI for individuals
- Configure min/max instances per class
- Generate random compliant data
- Validate with OWL reasoner
- Export as Turtle/RDF/N-Triples

**Tab 3: JSON Instance Generation**
- Choose reference style (inline vs URI)
- Transform A-box to JSON
- Side-by-side JSON/JSON-LD view
- Validate against generated schema
- Export in multiple formats

##### Additional Features
- **Rule Configuration**:
  - 20 configurable transformation rules
  - Organized by category
  - Save/load configurations
- **Real-time Features**:
  - Live preview and statistics
  - Progress indicators
  - Status bar with workflow state
- **Export Options**:
  - Multiple format support
  - Save at any workflow step

### Web Interface

OntoJSON now includes a web interface for browser-based access:

```bash
# Start the web server
python src/owl2jsonschema_web/app.py

# Navigate to http://localhost:5000 in your browser
```

#### Web Interface Features
- Drag-and-drop file upload
- Real-time transformation progress
- REST API endpoints for integration
- Async task processing for large files
- Configuration profiles management

For detailed web interface documentation, see [WEB_APP_GUIDE.md](WEB_APP_GUIDE.md).

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

#### Single Ontology Transformation

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

#### Multiple Ontology Transformation (Composite Creation)

When transforming multiple ontologies, OntoJSON automatically creates a composite ontology that can be persisted:

```python
from owl2jsonschema import TransformationEngine, TransformationConfig, OntologyParser
from owl2jsonschema.composite_builder import CompositeOntologyBuilder
import json

# Multiple ontology sources (local files and/or URIs)
ontology_sources = [
    "/path/to/ontology1.owl",
    "https://example.org/ontology2.rdf",
    "/path/to/ontology3.ttl"
]

# Only needed for multiple sources - single sources are processed directly
if len(ontology_sources) > 1:
    # Add metadata for the composite
    metadata = {
        "title": "Unified Domain Model",
        "version": "1.0.0",
        "author": "Your Organization",
        "description": "A composite ontology combining multiple domain models"
    }
    
    # Build the composite ontology with imports
    builder = CompositeOntologyBuilder.create_composite(
        ontology_sources,
        metadata=metadata
    )
    
    # Save composite to file (both temporary and persistent options)
    temp_file = builder.save_to_temp_file(format="turtle")
    
    # Optionally save permanently for reuse
    builder.save_to_file("composite_ontology.ttl", format="turtle")
    
    # Parse the composite (imports are resolved automatically)
    parser = OntologyParser()
    ontology = parser.parse(temp_file)
    
    # Clean up temporary file (persistent file remains)
    import os
    os.remove(temp_file)
else:
    # Single ontology - process directly
    parser = OntologyParser()
    ontology = parser.parse(ontology_sources[0])

# Transform to JSON Schema (same for single or composite)
config = TransformationConfig()
engine = TransformationEngine(config)
json_schema = engine.transform(ontology)

# Save the schema
with open("output_schema.json", "w") as f:
    json.dump(json_schema, f, indent=2)
```

**Key Differences:**
- **Single ontology**: Parsed and transformed directly, preserving original structure
- **Multiple ontologies**: Composite wrapper created with `owl:imports` statements
- **Import resolution**: Automatic in both cases via the parser

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

- **[Web Application Guide](WEB_APP_GUIDE.md)**: Complete guide for using the web interface
- **[Transformation Rules](transformation_rules.md)**: Complete list of available transformation rules
- **[Architecture](architecture.md)**: System architecture and design patterns
- **[Build System](build_system/README.md)**: Instructions for building standalone applications
- **[Ontology Partitioning](OntologyPartitioning/README.md)**: Documentation for the ontology partitioning system
- **[API Reference](docs/api.md)**: Detailed API documentation (coming soon)

## 🧪 Development

### Project Structure

```plaintext
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
│   │   ├── services/             # Platform-agnostic services
│   │   │   ├── __init__.py
│   │   │   ├── transformation_service.py
│   │   │   ├── file_service.py
│   │   │   └── configuration_service.py
│   │   ├── __init__.py
│   │   ├── abox_generator.py     # ABox generation utilities
│   │   ├── abox_to_json.py       # ABox to JSON conversion
│   │   ├── builder.py             # Schema builder
│   │   ├── cli.py                 # Command-line interface
│   │   ├── composite_builder.py   # Composite ontology builder
│   │   ├── config.py              # Configuration management
│   │   ├── engine.py              # Main transformation engine
│   │   ├── model.py               # Data models
│   │   ├── parser.py              # Ontology parser with import resolution
│   │   ├── reasoner.py            # OWL reasoning utilities
│   │   └── visitor.py             # Visitor pattern implementation
│   ├── owl2jsonschema_gui/       # GUI application
│   │   ├── __init__.py
│   │   ├── app.py                 # Application entry point
│   │   ├── editor_selector.py     # External editor selection dialog
│   │   └── main_window.py         # Main window implementation
│   └── owl2jsonschema_web/       # Web application
│       ├── api/                   # REST API endpoints
│       │   ├── __init__.py
│       │   ├── routes.py
│       │   ├── transformation.py
│       │   ├── configuration.py
│       │   └── tasks.py
│       ├── templates/             # HTML templates
│       │   ├── base.html
│       │   ├── index.html
│       │   └── transform.html
│       ├── __init__.py
│       ├── app.py                 # Flask application
│       ├── config.py              # Web app configuration
│       ├── tasks.py               # Celery async tasks
│       └── views.py               # Web views
├── OntologyPartitioning/          # Ontology partitioning system
│   ├── ontology_chunker.py       # Efficient chunker for large files
│   ├── semantic_partitioner.py   # Semantic partitioning engine
│   ├── domain_classifier.py      # Domain-based classification
│   ├── community_namer.py        # Community naming utilities
│   ├── partitioning_strategy.md  # Strategy documentation
│   └── README.md                  # Partitioning documentation
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
- ✅ Web interface: **Stable** (Flask-based)
- 🚧 Linux build system: **In Development**

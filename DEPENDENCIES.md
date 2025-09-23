# OntoJSON Dependencies Documentation

## Overview
This document describes all dependencies required for the OntoJSON application, including core functionality, GUI, web interface, and ontology partitioning features.

## Installation

### Quick Install
To install all required dependencies in a virtual environment:

```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install all dependencies
pip install -e ".[gui]"
pip install python-louvain  # For community detection
```

### Alternative: Using requirements.txt
```bash
source .venv/bin/activate
pip install -r requirements.txt
```

## Core Dependencies

### Essential Libraries
- **rdflib** (>=6.0.0): RDF parsing and manipulation
- **pyyaml** (>=6.0): YAML configuration file support
- **jsonschema** (>=4.0.0): JSON Schema validation
- **click** (>=8.0.0): Command-line interface creation
- **faker** (>=19.0.0): Test data generation
- **owlrl** (>=7.1.4): OWL reasoning capabilities

### Ontology Partitioning
These dependencies enable advanced ontology analysis and modularization:
- **networkx** (>=3.0): Graph-based ontology representation and analysis
- **python-louvain** (>=0.16): Community detection algorithms for ontology partitioning
- **matplotlib** (>=3.5.0): Visualization of ontology structures
- **scipy** (>=1.9.0): Scientific computing for advanced algorithms
- **scikit-learn** (>=1.0.0): Machine learning algorithms for clustering

### GUI Dependencies
- **PyQt6** (>=6.0.0): Cross-platform GUI framework
- **requests** (>=2.25.0): HTTP library for URL handling
- **certifi** (>=2021.0.0): SSL certificate validation

## Optional Dependencies

### Web Interface
```bash
pip install Flask flask-cors flask-session celery redis
```

### Development Tools
```bash
pip install pytest pytest-cov black flake8 mypy pre-commit
```

### Build System
For creating standalone applications:
```bash
pip install pyinstaller dmgbuild Pillow py2app
```

### macOS-specific
For proper app naming on macOS:
```bash
pip install setproctitle pyobjc-framework-Cocoa
```

## Dependency Management

### Using pyproject.toml
The project uses `pyproject.toml` for dependency specification. Dependencies are organized into groups:
- Core dependencies (always installed)
- `[gui]` - GUI-specific dependencies
- `[web]` - Web interface dependencies
- `[dev]` - Development tools

### Virtual Environment
Always use a virtual environment to avoid conflicts:
```bash
# Activate environment before any operations
source .venv/bin/activate

# Verify activation
which python  # Should show .venv/bin/python
```

## Troubleshooting

### Missing Module Errors
If you encounter import errors:
1. Ensure virtual environment is activated
2. Reinstall dependencies: `pip install -e ".[gui]"`
3. For community module: `pip install python-louvain`

### GUI Not Starting
1. Verify PyQt6 installation: `python -c "import PyQt6"`
2. Check display settings (X11 forwarding for remote connections)
3. Run with debug: `python run_ontojson_gui.py`

### Ontology Partitioning Issues
If partitioning features fail:
1. Verify networkx: `python -c "import networkx; print(networkx.__version__)"`
2. Check community module: `python -c "import community"`
3. Ensure all scientific libraries are installed: `pip install scipy scikit-learn matplotlib`

## Version Compatibility

- Python: 3.8 or higher required
- macOS: 10.14+ for PyQt6
- Windows: Windows 10+ recommended
- Linux: Most distributions supported with X11

## Updates and Maintenance

To update all dependencies:
```bash
source .venv/bin/activate
pip install --upgrade -r requirements.txt
```

To check for outdated packages:
```bash
pip list --outdated
```

## Support

For dependency-related issues:
1. Check this documentation first
2. Ensure all dependencies are installed in .venv
3. Review error messages for specific missing modules
4. Consider reinstalling the virtual environment if issues persist
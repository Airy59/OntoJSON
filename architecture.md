# OWL to JSON Schema Transformation Architecture

This document outlines the architecture for the OWL to JSON Schema transformation engine. The architecture is designed to support configurable, rule-based transformations using the visitor pattern.

## Overview

The transformation engine converts RDF/OWL ontologies into JSON Schema documents. It uses a visitor pattern to traverse the ontology structure and apply transformation rules. Rules can be enabled or disabled through configuration.

The system supports two primary workflows:
1. **Single Ontology**: Direct transformation of a single OWL/RDF file
2. **Multiple Ontologies**: Automatic creation of a composite ontology that imports multiple sources

```
Single Ontology Flow:
┌─────────────┐     ┌─────────────────┐     ┌────────────────┐
│  OWL/RDF    │────▶│  Transformation │────▶│  JSON Schema   │
│  Ontology   │     │     Engine      │     │    Document    │
└─────────────┘     └─────────────────┘     └────────────────┘
                            │
                            ▼
                    ┌─────────────────┐
                    │  Transformation │
                    │      Rules      │
                    └─────────────────┘

Multiple Ontologies Flow:
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│ Ontology 1  │────▶│  Composite   │────▶│  Composite  │
├─────────────┤     │   Builder    │     │  Ontology   │
│ Ontology 2  │────▶│              │     │ (persisted) │
├─────────────┤     └──────────────┘     └─────────────┘
│ Ontology N  │────────────┘                     │
└─────────────┘                                  │
                                                  ├──► Save to file
                                                  │    (Turtle, RDF/XML,
                                                  │     JSON-LD, etc.)
                                                  ▼
                                         ┌─────────────────┐
                                         │  Transformation │
                                         │     Engine      │
                                         └─────────────────┘
                                                  │
                                                  ▼
                                         ┌────────────────┐
                                         │  JSON Schema   │
                                         └────────────────┘
```

## Core Components

### 1. Ontology Model

Represents the OWL ontology in memory. This model will be traversed by the visitors.

- **OntologyModel**: Main class representing the entire ontology
- **OntologyElement**: Base interface for all ontology elements
  - **OntologyClass**: Represents an OWL class
  - **OntologyProperty**: Base for properties
    - **ObjectProperty**: Represents owl:ObjectProperty
    - **DatatypeProperty**: Represents owl:DatatypeProperty
  - **OntologyIndividual**: Represents named individuals
  - **OntologyRestriction**: Represents restrictions on classes or properties

### 2. Visitor Pattern Implementation

The visitor pattern allows for separation of algorithms from the object structure they operate on.

- **OntologyVisitor**: Base visitor interface
  ```python
  class OntologyVisitor:
      def visit_ontology(self, ontology):
          pass
          
      def visit_class(self, owl_class):
          pass
          
      def visit_object_property(self, property):
          pass
          
      def visit_datatype_property(self, property):
          pass
          
      def visit_individual(self, individual):
          pass
          
      def visit_restriction(self, restriction):
          pass
  ```

- **OntologyElement**: Base element interface with accept method
  ```python
  class OntologyElement:
      def accept(self, visitor):
          pass
  ```

- **Concrete Elements**: Implement accept method
  ```python
  class OntologyClass(OntologyElement):
      def accept(self, visitor):
          return visitor.visit_class(self)
  ```

### 3. Transformation Rules

Each transformation rule is implemented as a separate visitor that focuses on a specific aspect of the transformation.

- **TransformationRule**: Base class for all transformation rules
  ```python
  class TransformationRule(OntologyVisitor):
      def __init__(self, config=None):
          self.config = config or {}
          self.enabled = True
          
      def is_enabled(self):
          return self.enabled
          
      def enable(self):
          self.enabled = True
          
      def disable(self):
          self.enabled = False
  ```

- **Concrete Rules**: Implement specific transformation logic
  ```python
  class ClassToObjectRule(TransformationRule):
      def visit_class(self, owl_class):
          if not self.is_enabled():
              return None
              
          # Transform OWL class to JSON Schema object
          schema = {
              "type": "object",
              "title": owl_class.get_label(),
              "description": owl_class.get_comment(),
              "properties": {}
          }
          
          return schema
  ```

### 4. Transformation Engine

Coordinates the transformation process by applying rules to the ontology model.

- **TransformationEngine**: Main engine class
  ```python
  class TransformationEngine:
      def __init__(self, config=None):
          self.config = config or {}
          self.rules = []
          
      def add_rule(self, rule):
          self.rules.append(rule)
          
      def transform(self, ontology_model):
          schema = {"$schema": "http://json-schema.org/draft-07/schema#"}
          
          # Apply each rule
          for rule in self.rules:
              if rule.is_enabled():
                  result = ontology_model.accept(rule)
                  # Merge result into schema
                  
          return schema
  ```

### 5. Configuration System

Manages the configuration of the transformation engine and rules.

- **TransformationConfig**: Configuration class
  ```python
  class TransformationConfig:
      def __init__(self, config_dict=None):
          self.config = config_dict or {}
          
      def get_rule_config(self, rule_id):
          return self.config.get("rules", {}).get(rule_id, {})
          
      def is_rule_enabled(self, rule_id):
          rule_config = self.get_rule_config(rule_id)
          return rule_config.get("enabled", True)
  ```

### 6. Result Builder

Constructs the final JSON Schema document by combining the results of individual rules.

- **SchemaBuilder**: Builds the final schema
  ```python
  class SchemaBuilder:
      def __init__(self):
          self.schema = {"$schema": "http://json-schema.org/draft-07/schema#"}
          self.definitions = {}
          
      def add_definition(self, name, schema):
          self.definitions[name] = schema
          
      def add_to_schema(self, path, value):
          # Add value to schema at specified path
          
      def build(self):
          if self.definitions:
              self.schema["definitions"] = self.definitions
          return self.schema
  ```

### 7. Composite Ontology Builder

Creates composite ontologies that aggregate multiple source ontologies through OWL import statements.

- **CompositeOntologyBuilder**: Main builder class
  ```python
  class CompositeOntologyBuilder:
      def __init__(self, base_uri=None):
          self.base_uri = base_uri or generate_uuid_uri()
          self.graph = Graph()
          self.ontology_uri = URIRef(self.base_uri)
          
      def add_metadata(self, metadata):
          # Add title, description, version, author, etc.
          
      def add_imports(self, ontology_paths):
          # Add owl:imports statements for each ontology
          
      def serialize(self, format="turtle"):
          # Serialize the composite ontology
          
      @classmethod
      def create_composite(cls, ontology_paths, metadata=None):
          # Convenience method to create composite in one step
  ```

- **Features**:
  - Automatic URI generation if not provided
  - Support for custom metadata (title, version, author, description, comments)
  - Handles both local file paths and remote URIs
  - Converts local paths to file:// URIs for proper importing
  - Serialization to various RDF formats (Turtle, RDF/XML, N3, JSON-LD)
  - **Persistent saving**: Composite ontology can be saved with all metadata
  - **Reusability**: Saved composite can be used as input for future transformations

## Data Flow

### Single Ontology Processing

1. **Parsing**: The ontology file is parsed into the ontology model
2. **Configuration**: The transformation engine is configured with rules and settings
3. **Transformation**: The engine applies enabled rules to the ontology model
4. **Result Building**: The results from individual rules are combined into a complete JSON Schema
5. **Output**: The JSON Schema is serialized to a file

```
┌─────────────┐     ┌─────────────┐     ┌─────────────────┐     ┌────────────────┐
│  Ontology   │────▶│  Ontology   │────▶│  Transformation │────▶│  JSON Schema   │
│    File     │     │    Model    │     │     Engine      │     │    Document    │
└─────────────┘     └─────────────┘     └─────────────────┘     └────────────────┘
                                                │
                    ┌─────────────┐             │
                    │Configuration│─────────────┘
                    └─────────────┘
```

### Multiple Ontologies Processing

1. **Collection**: Multiple ontology sources (files/URIs) are collected
2. **Composite Creation**: A composite ontology is created with `owl:imports` statements
3. **Metadata Addition**: Optional metadata is added to the composite
4. **Persistence Options**:
   - Temporary file for immediate processing
   - **Save to persistent file** (Turtle, RDF/XML, JSON-LD, etc.)
   - Reuse saved composite as input for future transformations
5. **Parsing**: The composite ontology is parsed (imports are resolved automatically)
6. **Transformation**: Standard transformation process applies
7. **File Management**: Temporary files are cleaned up; persistent files are retained

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ Sources List │────▶│  Composite   │────▶│  Composite   │
│              │     │   Builder    │     │   Ontology   │
└──────────────┘     └──────────────┘     └──────────────┘
       │                    │                      │
   Metadata ────────────────┘                      ├── Save to file
                                                   │   (persisted)
                                                   ▼
                                          ┌──────────────┐
                                          │   Parser     │
                                          │   (imports   │
                                          │   resolved)  │
                                          └──────────────┘
                                                   │
                                                   ▼
                                          ┌──────────────┐
                                          │Transformation│
                                          │   Engine     │
                                          └──────────────┘
```

## GUI Application Workflow

The OntoJSON GUI provides an intuitive interface for managing single and multiple ontology transformations:

### Input Management

The GUI features a flexible text editor for ontology sources:
- **Mixed Input Types**: Supports local file paths and remote URIs in a single list
- **Line-Based Entry**: One ontology source per line
- **Interactive Controls**:
  - "Select Files" - Browse and add local ontology files
  - "Add URI" - Input remote ontology URLs
  - "Remove Line" - Delete entry at cursor position
  - "Clear All" - Reset the entire list

### Automatic Workflow Detection

The system automatically determines the appropriate workflow:
1. **Single Source** (1 entry):
   - Direct transformation without modification
   - No composite creation dialog
   - Preserves original ontology structure
   
2. **Multiple Sources** (2+ entries):
   - Triggers composite metadata dialog
   - Creates temporary composite ontology
   - Adds `owl:imports` for all sources
   - Resolves dependencies automatically

### Three-Step Transformation Process

The GUI implements a complete T-box/A-box workflow:

```
┌───────────────┐     ┌──────────────┐     ┌────────────────┐
│   T-box       │────▶│   A-box      │────▶│     JSON       │
│ Transformation│     │  Generation  │     │   Instances    │
└───────────────┘     └──────────────┘     └────────────────┘
      Step 1               Step 2               Step 3
```

1. **T-box Transformation**: Convert OWL ontology to JSON Schema
2. **A-box Generation**: Create random individuals conforming to T-box
3. **JSON Instance Generation**: Convert A-box to JSON/JSON-LD instances

## Rule Execution Strategy

The transformation engine can use different strategies for applying rules:

1. **Sequential**: Rules are applied in sequence, with each rule operating on the original ontology model
2. **Cascading**: Rules are applied in sequence, with each rule operating on the result of the previous rule
3. **Parallel**: Rules are applied in parallel, then results are merged

The default strategy is Sequential, which allows each rule to focus on a specific aspect of the transformation without being affected by other rules.

## Extension Points

The architecture provides several extension points:

1. **Custom Rules**: New rules can be added by implementing the TransformationRule interface
2. **Custom Visitors**: Additional visitors can be implemented for specialized processing
3. **Custom Builders**: The SchemaBuilder can be extended or replaced for custom output formats
4. **Pre/Post Processors**: Hooks for pre-processing the ontology or post-processing the schema

## Implementation Considerations

1. **Performance**: For large ontologies, consider lazy loading and streaming processing
2. **Memory Usage**: Use references instead of deep copies where possible
3. **Validation**: Validate the output schema against JSON Schema specifications
4. **Error Handling**: Provide clear error messages and fallback mechanisms
5. **Logging**: Implement comprehensive logging for debugging and auditing
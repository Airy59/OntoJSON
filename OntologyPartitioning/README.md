# Ontology Partitioning System

A comprehensive solution for partitioning large ontologies into semantically coherent modules while preserving complete semantic information.

## Overview

The Ontology Partitioning System addresses the challenge of processing large ontology files that exceed memory or token limits. It provides:

- **Efficient chunking** for files too large to load in memory
- **Multiple partitioning strategies** for creating coherent modules
- **Semantic completeness** preservation during partitioning
- **Quality metrics** for evaluating partition quality
- **Full UI integration** with the OntoJSON application

## Key Components

### 1. Ontology Chunker (`ontology_chunker.py`)

Efficiently splits large ontology files using streaming and shell commands to avoid memory issues.

**Features:**
- Streaming-based processing using grep/sed
- Preserves namespace prefixes in each chunk
- Groups entities by type (classes, properties)
- Creates manageable 30-entity chunks

**Usage:**
```python
from OntologyPartitioning.ontology_chunker import OntologyChunker

chunker = OntologyChunker("large_ontology.ttl")
chunker.chunk_ontology()
```

### 2. Semantic Partitioner (`semantic_partitioner.py`)

Creates semantically coherent module partitions from ontologies.

**Features:**
- Three partitioning strategies:
  - **Community Detection**: Graph-based clustering using Louvain algorithm
  - **Domain-based**: Groups entities by semantic domains
  - **Hierarchical**: Based on class taxonomy
- Preserves semantic completeness (annotations, restrictions, domains/ranges)
- Generates quality metrics (cohesion, coupling, modularity)
- Creates visualizations and reports

**Usage:**
```python
from OntologyPartitioning.semantic_partitioner import SemanticPartitioner

partitioner = SemanticPartitioner("ontology.ttl")
partitioner.partition(strategy="community", use_chunks=True)
```

### 3. Domain Classifier (`domain_classifier.py`)

Classifies ontology entities into semantic domains using multiple sources.

**Features:**
- Integrates with DBpedia SPARQL endpoint
- Uses RailML, IFOPT, and OTL Spoor domain knowledge
- Falls back to keyword matching
- Caches results for performance

### 4. Community Namer (`community_namer.py`)

Generates meaningful names for detected communities based on their content.

**Features:**
- Analyzes entity labels and URIs
- Extracts common terms and patterns
- Handles small communities specially
- Creates human-readable names

## Partitioning Strategies

### Community Detection
Uses graph-based clustering to identify tightly connected groups of entities.
- **Pros**: Discovers natural clusters in the data
- **Cons**: May produce many singleton partitions
- **Best for**: Ontologies with clear modular structure

### Domain-based
Groups entities by their semantic domain (infrastructure, safety, operations, etc.).
- **Pros**: Creates intuitive, domain-specific modules
- **Cons**: Requires domain knowledge or online resources
- **Best for**: Well-documented ontologies with clear domains

### Hierarchical
Partitions based on the class hierarchy.
- **Pros**: Preserves taxonomic relationships
- **Cons**: May not capture all relationships
- **Best for**: Ontologies with rich class hierarchies

## Quality Metrics

The system evaluates partition quality using several metrics:

- **Cohesion**: Measures how well-connected entities within partitions are (0-1, higher is better)
- **Coupling**: Measures dependencies between partitions (0-1, lower is better)
- **Modularity**: Overall quality score for community detection (-1 to 1, higher is better)
- **Size Distribution**: Analysis of partition sizes to identify imbalances

## Semantic Completeness

The latest version ensures complete semantic preservation by:

1. **Including all triples where an entity is the subject**
2. **Recursively collecting blank node triples** for OWL restrictions
3. **Preserving all rdfs:domain and rdfs:range declarations**
4. **Keeping all annotation properties** (labels, comments, dates, etc.)
5. **Maintaining complex class definitions** and equivalent classes

This ensures that partitioned modules are self-contained and semantically complete.

## GUI Integration

The system is fully integrated into the OntoJSON GUI application:

1. **Menu Access**: Tools → Ontology Partitioning
2. **Side-by-side Configuration**: Strategy selection and parameters
3. **Tree View Results**: Browse partitions and their contents
4. **File Viewers**: View complete partition files in dialogs or external editors
5. **Reports**: Access markdown reports and visualizations

## Output Files

The system generates comprehensive output in the `{ontology}_modules/` directory:

```
ontology_modules/
├── community/                    # Community detection results
│   ├── *.ttl                    # Individual partition files
│   ├── index.json               # Partition metadata
│   └── named_index.json         # Human-readable names mapping
├── domain/                      # Domain-based results
├── hierarchical/                # Hierarchical results
├── PARTITIONING_REPORT.md       # Human-readable report
├── COMMUNITY_NAMES.md           # Community naming details
├── partitioning_summary.json    # Machine-readable summary
└── *_visualization.png          # Graph visualizations
```

## Command Line Usage

### Basic partitioning:
```bash
python OntologyPartitioning/semantic_partitioner.py ontology.ttl
```

### With specific strategy:
```bash
python OntologyPartitioning/semantic_partitioner.py ontology.ttl -s community
```

### Using chunks for large files:
```bash
python OntologyPartitioning/semantic_partitioner.py ontology.ttl --use-chunks
```

### All strategies:
```bash
python OntologyPartitioning/semantic_partitioner.py ontology.ttl -s all
```

## Performance Considerations

- **Large Files**: Use chunking (`--use-chunks`) for files over 100MB
- **Memory Usage**: Chunking keeps memory usage under 1GB even for gigabyte-sized files
- **Processing Time**: Expect 1-5 minutes for large ontologies with chunking
- **Cache**: Domain classification results are cached to speed up repeated runs

## Requirements

- Python 3.8+
- rdflib
- networkx
- matplotlib
- PyQt6 (for GUI)
- requests (for online domain classification)
- Unix-like system with grep/sed (for chunking)

## Future Enhancements

Potential improvements for future versions:

1. **Tunable parameters** for community merging thresholds
2. **Custom domain mappings** via configuration files
3. **Incremental partitioning** for ontology updates
4. **Export to standard formats** (OWL modules, SKOS concept schemes)
5. **Partition validation** against competency questions
6. **Cross-partition dependency analysis** tools

## License

Part of the OntoJSON project. See main LICENSE file for details.
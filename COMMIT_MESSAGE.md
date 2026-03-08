# Fix: Class Name Collision Handling for Referenced Ontologies

## Problem
The class name disambiguation logic was only checking explicit `owl:imports` statements to determine secondary imports. However, ontologies can also be **referenced** (without explicit imports) when classes from other namespaces are used in property ranges, restrictions, etc. This caused referenced ontologies (like SOSA referenced by POP) to be incorrectly treated as primary imports, resulting in both classes being disambiguated when only the secondary one should be.

## Solution
Enhanced the parser to detect both:
1. **Explicit imports** (`owl:imports` statements)
2. **References** (namespace URIs appearing in class URIs, property ranges, and restrictions)

The logic now correctly identifies secondary references by:
- Collecting all namespace URIs that appear in the merged graph
- Identifying primary import namespaces (from primary import file URIs)
- Marking all other referenced namespaces as secondary

## Changes

### `src/owl2jsonschema/parser.py`
- **Enhanced `_parse_ontology_metadata()`**: Added detection of referenced namespaces by scanning:
  - Class URIs (`rdf:type owl:Class`)
  - Property ranges (`rdfs:range`)
  - Restrictions (`owl:allValuesFrom`)
- **Secondary detection logic**: Now marks any referenced namespace as secondary if it:
  - Is NOT the main ontology namespace
  - Is NOT a primary import namespace
  - Appears in the graph (has classes/properties)

### `src/owl2jsonschema/engine.py`
- **Enhanced primary imports building**: Added mapping from primary import file URIs to their namespace URIs
- **Added debug output**: To help trace which namespaces are marked as primary vs secondary

## Result
- **Primary imports** (e.g., POP): Keep original class names unless colliding with other primary imports
- **Secondary references** (e.g., SOSA referenced by POP): Always get disambiguated with namespace suffix when colliding

## Example
Before: `Observation_pop` and `Observation_sosa` (both disambiguated incorrectly)
After: `Observation` (POP, primary) and `Observation_sosa` (SOSA, secondary reference)

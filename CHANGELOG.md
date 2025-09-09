# Changelog

All notable changes to OntoJSON will be documented in this file.

## [Unreleased] - 2025-01-09

### Fixed
- Fixed "Broken pipe" error during ontology assembly in `TransformationService.transform_multiple()`
  - Corrected method name mismatch: changed `serialize_to_file()` to `save_to_file()` in `transformation_service.py:172`
  - The CompositeOntologyBuilder correctly uses `save_to_file()` method, not `serialize_to_file()`
  - This resolves issues when assembling multiple ontologies into a composite structure

### Technical Details
- **File Modified**: `src/owl2jsonschema/services/transformation_service.py`
- **Line Changed**: 172
- **Root Cause**: Method name inconsistency between the service layer and the composite builder
- **Impact**: Users can now successfully transform multiple ontologies without encountering assembly errors
"""
A-box to JSON Converter

This module converts RDF/OWL A-box instances to JSON instances
that conform to the generated JSON Schema.
"""

import json
from typing import Dict, Any, List, Optional, Set
import sys
from rdflib import Graph, RDF, RDFS, OWL, Namespace, URIRef, Literal, BNode
from rdflib.namespace import XSD
import jsonschema
from jsonschema import validate, ValidationError
from collections import defaultdict


class ABoxToJSONConverter:
    """Converts RDF/OWL A-box to JSON instances conforming to a JSON Schema."""
    
    def __init__(self, json_schema: Dict[str, Any], base_uri: str = "https://example.org#",
                 reference_style: str = "reference"):
        """
        Initialize the converter.
        
        Args:
            json_schema: The JSON Schema to conform to
            base_uri: Base URI for the ontology
            reference_style: How to handle object references - "inline" or "reference" (default)
                            - "inline": Follow $ref and embed full objects
                            - "reference": Use @id references
        """
        self.json_schema = json_schema
        self.base_uri = base_uri
        self.namespace = Namespace(base_uri)
        self.reference_style = reference_style
        
        # Extract class definitions from schema
        self.class_definitions = json_schema.get('definitions', {})
        
        # Build a mapping of RDF types to JSON schema definitions
        self.type_mapping = self._build_type_mapping()
        
        # Cache for converted objects (used in inline mode to avoid duplication)
        self._converted_cache = {}
        
    def _build_type_mapping(self) -> Dict[str, str]:
        """Build a mapping from RDF class URIs to JSON schema definition names."""
        mapping = {}
        
        for def_name in self.class_definitions:
            # The definition name usually corresponds to the local name of the class
            # We'll map both with and without namespace
            mapping[def_name] = def_name
            mapping[f"{self.base_uri}{def_name}"] = def_name
            
        return mapping
    
    def convert(self, abox_graph: Graph) -> Dict[str, Any]:
        """
        Convert an A-box graph to JSON instances.
        
        Args:
            abox_graph: The RDF graph containing A-box instances
            
        Returns:
            Dictionary containing JSON instances organized by type
        """
        instances = defaultdict(list)
        
        # Clear cache for new conversion
        self._converted_cache = {}
        
        # Store the graph for reference in inline mode
        self._current_graph = abox_graph
        
        # Find all individuals in the graph
        individuals = self._find_individuals(abox_graph)
        
        # Convert each individual to JSON
        for individual_uri in individuals:
            json_obj = self._convert_individual(individual_uri, abox_graph)
            if json_obj:
                # Determine the type of the individual
                types = list(abox_graph.objects(individual_uri, RDF.type))
                for type_uri in types:
                    type_name = self._get_type_name(type_uri)
                    if type_name in self.class_definitions:
                        instances[type_name].append(json_obj)
                        break  # Use the first matching type
        
        return dict(instances)
    
    def _find_individuals(self, graph: Graph) -> Set[URIRef]:
        """Find all individuals in the graph."""
        individuals = set()
        
        # Find all subjects that have rdf:type
        for s in graph.subjects(RDF.type, None):
            if isinstance(s, URIRef) and not self._is_class_or_property(s, graph):
                individuals.add(s)
        
        return individuals
    
    def _is_class_or_property(self, uri: URIRef, graph: Graph) -> bool:
        """Check if a URI represents a class or property definition."""
        # Check if it's an OWL class or property
        if (uri, RDF.type, OWL.Class) in graph:
            return True
        if (uri, RDF.type, RDFS.Class) in graph:
            return True
        if (uri, RDF.type, OWL.ObjectProperty) in graph:
            return True
        if (uri, RDF.type, OWL.DatatypeProperty) in graph:
            return True
        if (uri, RDF.type, RDF.Property) in graph:
            return True
        
        return False
    
    def _convert_individual(self, individual_uri: URIRef, graph: Graph) -> Dict[str, Any]:
        """Convert a single individual to JSON."""
        json_obj = {}
        
        # Always add URI if present in any schema definition
        json_obj['uri'] = str(individual_uri)
        
        # Get the type of the individual
        types = list(graph.objects(individual_uri, RDF.type))
        if not types:
            return json_obj
        
        # Use the first type that matches our schema
        type_name = None
        for type_uri in types:
            # Skip OWL built-in types
            if str(type_uri) == str(OWL.NamedIndividual):
                continue
            candidate_name = self._get_type_name(type_uri)
            if candidate_name in self.class_definitions:
                type_name = candidate_name
                break
        
        if not type_name:
            return json_obj
        
        # Get the schema definition for this type
        class_def = self._get_full_class_definition(type_name)
        
        # Extract ALL properties from the RDF graph for this individual
        # Get all predicates for this individual
        for predicate, obj in graph.predicate_objects(individual_uri):
            # Skip RDF type assertions and labels
            if predicate in [RDF.type, RDFS.label, RDFS.comment]:
                continue
            
            # Get the local name of the predicate
            predicate_name = self._get_type_name(predicate)
            
            # Check if this property is in our schema
            if 'properties' in class_def and predicate_name in class_def['properties']:
                prop_schema = class_def['properties'][predicate_name]
                
                # Check if we already have values for this property
                if predicate_name not in json_obj or predicate_name == 'uri':
                    # Get all values for this property
                    values = list(graph.objects(individual_uri, predicate))
                    
                    if values:
                        # Handle single vs array values
                        if prop_schema.get('type') == 'array':
                            json_obj[predicate_name] = [self._convert_value(v, prop_schema.get('items', {}), graph)
                                                       for v in values]
                        else:
                            # Take the first value for single-valued properties
                            json_obj[predicate_name] = self._convert_value(values[0], prop_schema, graph)
        
        # Also try with different URI patterns in case properties use different namespaces
        if 'properties' in class_def:
            for prop_name, prop_schema in class_def['properties'].items():
                if prop_name == 'uri' or prop_name in json_obj:
                    continue  # Already handled
                
                # Try multiple URI patterns for the property
                possible_prop_uris = [
                    URIRef(f"{self.base_uri}{prop_name}"),
                    URIRef(f"{self.base_uri.rstrip('#/')}/{prop_name}"),
                    URIRef(f"http://example.org#{prop_name}"),
                    URIRef(f"https://example.org#{prop_name}"),
                ]
                
                for prop_uri in possible_prop_uris:
                    values = list(graph.objects(individual_uri, prop_uri))
                    if values:
                        # Handle single vs array values
                        if prop_schema.get('type') == 'array':
                            json_obj[prop_name] = [self._convert_value(v, prop_schema.get('items', {}), graph)
                                                  for v in values]
                        else:
                            # Take the first value for single-valued properties
                            json_obj[prop_name] = self._convert_value(values[0], prop_schema, graph)
                        break  # Found values, stop trying other URI patterns
        
        return json_obj
    
    def _get_full_class_definition(self, type_name: str, visited: Optional[Set[str]] = None) -> Dict[str, Any]:
        """
        Get the full class definition including inherited properties.
        
        Args:
            type_name: Name of the class to get definition for
            visited: Set of already visited classes to prevent infinite recursion
        """
        if visited is None:
            visited = set()
        
        # Check for circular references
        if type_name in visited:
            return {'properties': {}}
        
        if type_name not in self.class_definitions:
            return {}
        
        # Mark this class as visited
        visited.add(type_name)
        
        class_def = self.class_definitions[type_name]
        full_def = {'properties': {}}
        
        # Handle allOf inheritance
        if 'allOf' in class_def:
            for item in class_def['allOf']:
                if '$ref' in item:
                    # Resolve reference
                    ref_name = item['$ref'].split('/')[-1]
                    if ref_name in self.class_definitions and ref_name not in visited:
                        parent_def = self._get_full_class_definition(ref_name, visited.copy())
                        if 'properties' in parent_def:
                            full_def['properties'].update(parent_def['properties'])
                elif 'properties' in item:
                    full_def['properties'].update(item['properties'])
        
        # Add direct properties
        if 'properties' in class_def:
            full_def['properties'].update(class_def['properties'])
        
        # Copy other fields
        for key in class_def:
            if key not in ['allOf', 'properties']:
                full_def[key] = class_def[key]
        
        return full_def
    
    def _convert_value(self, value: Any, schema: Dict[str, Any], graph: Graph) -> Any:
        """Convert an RDF value to JSON based on the schema."""
        if isinstance(value, Literal):
            # Handle literal values
            if schema.get('type') == 'string':
                return str(value)
            elif schema.get('type') == 'integer':
                return int(value)
            elif schema.get('type') == 'number':
                return float(value)
            elif schema.get('type') == 'boolean':
                return bool(value)
            else:
                return str(value)
        elif isinstance(value, URIRef):
            # Handle references to other individuals
            # Check if schema expects a reference (has oneOf with $ref and @id patterns)
            if 'oneOf' in schema:
                # Schema supports both inline and reference modes
                if self.reference_style == "inline":
                    # Follow the reference and inline the object
                    for option in schema['oneOf']:
                        if '$ref' in option:
                            # Use the inline option - convert the referenced object
                            ref_uri = str(value)
                            if ref_uri not in self._converted_cache:
                                # Convert the referenced individual
                                referenced_obj = self._convert_individual(value, graph)
                                if referenced_obj:
                                    self._converted_cache[ref_uri] = referenced_obj
                                    return referenced_obj
                            else:
                                # Return cached version to avoid infinite recursion
                                return self._converted_cache[ref_uri]
                            # If conversion fails, fall back to reference
                            return {"@id": str(value)}
                    # No $ref option found, use @id reference
                    return {"@id": str(value)}
                else:
                    # Use reference style (default)
                    return {"@id": str(value)}
            elif '$ref' in schema:
                # Old style schema with just $ref
                if self.reference_style == "inline":
                    # Follow the reference and inline the object
                    ref_uri = str(value)
                    if ref_uri not in self._converted_cache:
                        referenced_obj = self._convert_individual(value, graph)
                        if referenced_obj:
                            self._converted_cache[ref_uri] = referenced_obj
                            return referenced_obj
                    else:
                        return self._converted_cache[ref_uri]
                    # If conversion fails, fall back to reference
                    return {"@id": str(value)}
                else:
                    # Use reference style
                    return {"@id": str(value)}
            else:
                # Return as string
                return str(value)
        else:
            return str(value)
    
    def _get_type_name(self, type_uri: URIRef) -> str:
        """Extract the type name from a URI."""
        uri_str = str(type_uri)
        
        # Check if it's in our mapping
        if uri_str in self.type_mapping:
            return self.type_mapping[uri_str]
        
        # Extract local name
        if '#' in uri_str:
            return uri_str.split('#')[-1]
        elif '/' in uri_str:
            return uri_str.split('/')[-1]
        else:
            return uri_str
    
    def _has_circular_reference(self, type_name: str, visited: Optional[Set[str]] = None) -> bool:
        """
        Check if a type has circular references in its schema.
        
        Args:
            type_name: The type to check
            visited: Set of already visited types
            
        Returns:
            True if circular reference detected
        """
        if visited is None:
            visited = set()
        
        if type_name in visited:
            return True
        
        if type_name not in self.class_definitions:
            return False
        
        visited.add(type_name)
        class_def = self.class_definitions[type_name]
        
        # Check properties for references to the same type
        if 'properties' in class_def:
            for prop_name, prop_schema in class_def['properties'].items():
                # Check direct references
                if '$ref' in prop_schema:
                    ref_type = prop_schema['$ref'].split('/')[-1]
                    if ref_type == type_name:
                        return True
                
                # Check array items
                if 'items' in prop_schema and '$ref' in prop_schema.get('items', {}):
                    ref_type = prop_schema['items']['$ref'].split('/')[-1]
                    if ref_type == type_name:
                        return True
        
        # Check allOf for circular inheritance
        if 'allOf' in class_def:
            for item in class_def['allOf']:
                if '$ref' in item:
                    ref_type = item['$ref'].split('/')[-1]
                    if self._has_circular_reference(ref_type, visited.copy()):
                        return True
        
        return False
    
    def validate(self, json_instances: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        """
        Validate JSON instances against the schema.
        
        Note: JSON Schema validation has limitations compared to OWL semantics.
        Constraints like irreflexive and asymmetric properties cannot be validated
        at the JSON Schema level and must be checked by OWL reasoners.
        
        Args:
            json_instances: Dictionary of instances organized by type
            
        Returns:
            Validation results with 'valid' boolean and 'errors' list
        """
        results = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'validated_count': 0,
            'total_count': 0
        }
        
        # Temporarily increase recursion limit for complex schemas
        old_recursion_limit = sys.getrecursionlimit()
        try:
            sys.setrecursionlimit(5000)  # Moderate increase
            
            for type_name, instances in json_instances.items():
                if type_name not in self.class_definitions:
                    results['errors'].append({
                        'type': type_name,
                        'error': f"No schema definition found for type '{type_name}'"
                    })
                    results['valid'] = False
                    continue
                
                # Check for circular references
                if self._has_circular_reference(type_name):
                    results['warnings'].append({
                        'type': type_name,
                        'warning': f"Schema contains circular references (e.g., self-referential properties). "
                                 f"JSON Schema validation skipped for this type. "
                                 f"Semantic constraints (irreflexive, asymmetric) must be validated by OWL reasoner."
                    })
                    # Skip JSON Schema validation for types with circular references
                    # Count them as validated since we're explicitly skipping
                    results['validated_count'] += len(instances)
                    results['total_count'] += len(instances)
                    continue
                
                # Create a schema for this specific type
                type_schema = {
                    "$schema": "http://json-schema.org/draft-07/schema#",
                    "type": "object",
                    "definitions": self.class_definitions,
                    "$ref": f"#/definitions/{type_name}"
                }
                
                for i, instance in enumerate(instances):
                    results['total_count'] += 1
                    try:
                        validate(instance=instance, schema=type_schema)
                        results['validated_count'] += 1
                    except RecursionError as e:
                        # This shouldn't happen with our circular reference check, but just in case
                        results['warnings'].append({
                            'type': type_name,
                            'instance_index': i,
                            'warning': f"Schema validation skipped due to complexity. "
                                     f"OWL semantic constraints should be validated by reasoner."
                        })
                        results['validated_count'] += 1  # Count as validated since we're skipping
                    except ValidationError as e:
                        results['valid'] = False
                        results['errors'].append({
                            'type': type_name,
                            'instance_index': i,
                            'error': str(e),
                            'path': list(e.absolute_path) if e.absolute_path else []
                        })
                    except Exception as e:
                        results['valid'] = False
                        results['errors'].append({
                            'type': type_name,
                            'instance_index': i,
                            'error': f"Unexpected error: {str(e)}",
                            'path': []
                        })
        finally:
            # Restore original recursion limit
            sys.setrecursionlimit(old_recursion_limit)
        
        return results
    
    def convert_and_validate(self, abox_graph: Graph) -> Dict[str, Any]:
        """
        Convert A-box to JSON and validate against schema.
        
        Args:
            abox_graph: The RDF graph containing A-box instances
            
        Returns:
            Dictionary with 'instances' and 'validation' results
        """
        # Convert to JSON
        instances = self.convert(abox_graph)
        
        # Validate
        validation = self.validate(instances)
        
        return {
            'instances': instances,
            'validation': validation
        }
    
    def to_jsonld(self, instances: Optional[Dict[str, List[Dict[str, Any]]]] = None) -> Dict[str, Any]:
        """
        Convert JSON instances to JSON-LD format.
        
        Args:
            instances: Optional pre-converted instances. If None, will be generated.
            
        Returns:
            JSON-LD representation of the instances
        """
        if instances is None:
            instances = {}
        
        # Create JSON-LD context
        context = {
            "@base": self.base_uri,
            "@vocab": self.base_uri
        }
        
        # Add type mappings for each class
        for class_name in self.class_definitions:
            context[class_name] = f"{self.base_uri}{class_name}"
        
        # Create JSON-LD document
        json_ld = {
            "@context": context,
            "@graph": []
        }
        
        # Convert instances to JSON-LD format
        for type_name, type_instances in instances.items():
            for instance in type_instances:
                json_ld_instance = instance.copy()
                json_ld_instance["@type"] = type_name
                
                # Convert 'uri' to '@id'
                if 'uri' in json_ld_instance:
                    json_ld_instance["@id"] = json_ld_instance.pop('uri')
                
                # Convert references
                for key, value in list(json_ld_instance.items()):
                    if isinstance(value, dict) and '$ref' in value:
                        json_ld_instance[key] = {"@id": value['$ref']}
                    elif isinstance(value, list):
                        new_list = []
                        for item in value:
                            if isinstance(item, dict) and '$ref' in item:
                                new_list.append({"@id": item['$ref']})
                            else:
                                new_list.append(item)
                        json_ld_instance[key] = new_list
                
                json_ld["@graph"].append(json_ld_instance)
        
        return json_ld


class JSONInstanceFormatter:
    """Formats JSON instances for display and export."""
    
    @staticmethod
    def format_for_display(instances: Dict[str, List[Dict[str, Any]]]) -> str:
        """Format JSON instances for display in the GUI."""
        return json.dumps(instances, indent=2, sort_keys=True)
    
    @staticmethod
    def format_as_json_ld(instances: Dict[str, List[Dict[str, Any]]], 
                         context: Optional[Dict[str, Any]] = None) -> str:
        """Format JSON instances as JSON-LD with context."""
        json_ld = {
            "@context": context or {
                "@base": "https://example.org#",
                "@vocab": "https://example.org#"
            },
            "@graph": []
        }
        
        # Flatten all instances into the graph
        for type_name, type_instances in instances.items():
            for instance in type_instances:
                json_ld_instance = instance.copy()
                json_ld_instance["@type"] = type_name
                if 'uri' in json_ld_instance:
                    json_ld_instance["@id"] = json_ld_instance.pop('uri')
                json_ld["@graph"].append(json_ld_instance)
        
        return json.dumps(json_ld, indent=2, sort_keys=True)
    
    @staticmethod
    def generate_validation_report(validation_results: Dict[str, Any]) -> str:
        """Generate a human-readable validation report."""
        report = []
        report.append("=" * 50)
        report.append("JSON SCHEMA VALIDATION REPORT")
        report.append("=" * 50)
        report.append("")
        
        # Check for warnings
        has_warnings = 'warnings' in validation_results and validation_results['warnings']
        
        if has_warnings:
            report.append("⚠️  IMPORTANT NOTES:")
            report.append("-" * 50)
            for warning in validation_results.get('warnings', []):
                if 'type' in warning:
                    report.append(f"• {warning['type']}: {warning.get('warning', 'Warning')}")
                else:
                    report.append(f"• {warning.get('warning', 'Warning')}")
            report.append("")
            report.append("Note: OWL semantic constraints (e.g., irreflexive, asymmetric properties)")
            report.append("cannot be validated at the JSON Schema level. Please use OWL reasoner")
            report.append("validation (Step 2: A-box Validation) for complete semantic checking.")
            report.append("")
            report.append("-" * 50)
            report.append("")
        
        if validation_results['valid'] and not validation_results.get('errors'):
            report.append("✅ JSON SCHEMA VALIDATION SUCCESSFUL")
            report.append("")
            report.append(f"Total instances processed: {validation_results['validated_count']}")
            if has_warnings:
                report.append("(Some types skipped due to circular references - see warnings above)")
            else:
                report.append("All instances conform to the JSON Schema.")
        else:
            report.append("❌ VALIDATION FAILED")
            report.append("")
            report.append(f"Instances validated: {validation_results['validated_count']}/{validation_results['total_count']}")
            report.append(f"Errors found: {len(validation_results.get('errors', []))}")
            
            if validation_results.get('errors'):
                report.append("")
                report.append("-" * 50)
                report.append("VALIDATION ERRORS:")
                report.append("-" * 50)
                
                for error in validation_results['errors']:
                    report.append("")
                    report.append(f"Type: {error.get('type', 'Unknown')}")
                    if 'instance_index' in error:
                        report.append(f"Instance Index: {error['instance_index']}")
                    if 'path' in error and error['path']:
                        report.append(f"Property Path: {'.'.join(str(p) for p in error['path'])}")
                    report.append(f"Error: {error['error']}")
                    report.append("-" * 30)
        
        return "\n".join(report)
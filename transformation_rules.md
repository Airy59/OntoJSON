# OWL to JSON Schema Transformation Rules

This document outlines the rules for transforming RDF/OWL ontologies into JSON Schema. Each rule can be enabled or disabled in the transformation configuration.

## Core Transformation Rules

### Class Transformations

1. **OWL Class to JSON Object** (Rule ID: `class_to_object`)
   - An OWL class is transformed into a JSON Schema object type
   - The class URI becomes the `$id` or is stored in `owl:Class` property
   - Class hierarchy is preserved through the `allOf` construct

2. **Class Hierarchy to JSON Schema Inheritance** (Rule ID: `class_hierarchy`)
   - OWL subclass relationships (`rdfs:subClassOf`) are transformed into JSON Schema inheritance using `allOf`
   - A subclass schema includes its parent schema via `allOf`

3. **Class Restrictions to JSON Schema Constraints** (Rule ID: `class_restrictions`)
   - OWL class restrictions are transformed into appropriate JSON Schema constraints
   - `owl:Restriction` on properties become property constraints

### Property Transformations

4. **OWL Object Property to JSON Object Property** (Rule ID: `object_property`)
   - `owl:ObjectProperty` becomes a JSON Schema property with `type: object` or a reference to another schema
   - Domain and range information is preserved

5. **OWL Datatype Property to JSON Schema Property** (Rule ID: `datatype_property`)
   - `owl:DatatypeProperty` becomes a JSON Schema property with appropriate type
   - XSD datatypes are mapped to JSON Schema types

6. **Property Cardinality to JSON Schema Constraints** (Rule ID: `property_cardinality`)
   - `owl:minCardinality` becomes `minItems` for arrays or `required` for single properties
   - `owl:maxCardinality` becomes `maxItems` for arrays
   - `owl:cardinality` sets both `minItems` and `maxItems` to the same value

7. **Property Restrictions to JSON Schema Validation** (Rule ID: `property_restrictions`)
   - `owl:allValuesFrom` becomes `items` or `additionalProperties` constraints
   - `owl:someValuesFrom` becomes validation rules

### Annotation Transformations

8. **RDFS Labels to JSON Schema Titles** (Rule ID: `labels_to_titles`)
   - `rdfs:label` becomes JSON Schema `title`
   - Language tags can be preserved or a specific language can be selected

9. **RDFS Comments to JSON Schema Descriptions** (Rule ID: `comments_to_descriptions`)
   - `rdfs:comment` becomes JSON Schema `description`
   - Language tags can be preserved or a specific language can be selected

10. **Other Annotations to JSON Schema Metadata** (Rule ID: `annotations_to_metadata`)
    - Other annotation properties become custom metadata in the JSON Schema
    - Stored under a custom namespace or in `$comment`

### Advanced Transformations

11. **OWL Enumeration to JSON Schema Enum** (Rule ID: `enumeration_to_enum`)
    - `owl:oneOf` with individuals becomes JSON Schema `enum`
    - Individual URIs or labels can be used as enum values

12. **OWL Union to JSON Schema anyOf** (Rule ID: `union_to_anyOf`)
    - `owl:unionOf` becomes JSON Schema `anyOf`
    - Each class in the union becomes an option in `anyOf`

13. **OWL Intersection to JSON Schema allOf** (Rule ID: `intersection_to_allOf`)
    - `owl:intersectionOf` becomes JSON Schema `allOf`
    - Each class in the intersection becomes a requirement in `allOf`

14. **OWL Complement to JSON Schema not** (Rule ID: `complement_to_not`)
    - `owl:complementOf` becomes JSON Schema `not`
    - The complemented class becomes the schema in `not`

15. **OWL Equivalent Classes to JSON Schema Definitions** (Rule ID: `equivalent_classes`)
    - `owl:equivalentClass` relationships are represented using shared schema definitions
    - Both classes reference the same schema definition

16. **OWL Disjoint Classes to JSON Schema Validation** (Rule ID: `disjoint_classes`)
    - `owl:disjointWith` relationships are enforced through validation rules
    - Custom validators may be required for full enforcement

### Structural Transformations

17. **Ontology to JSON Schema Document** (Rule ID: `ontology_to_document`)
    - The ontology becomes a JSON Schema document with appropriate metadata
    - Ontology imports become schema references

18. **Named Individuals to JSON Schema Examples** (Rule ID: `individuals_to_examples`)
    - Named individuals become examples in the JSON Schema
    - Property values of individuals are preserved in the examples

19. **Ontology Metadata to JSON Schema Metadata** (Rule ID: `ontology_metadata`)
    - Ontology metadata (version, creator, etc.) becomes JSON Schema metadata
    - Stored in appropriate JSON Schema fields or custom fields

## Configuration Options

The transformation engine should support:

1. **Rule Selection**: Enable/disable specific transformation rules
2. **Rule Customization**: Configure parameters for specific rules
3. **Namespace Handling**: Options for handling namespaces and URIs
4. **Output Format**: Control the structure and formatting of the output JSON Schema
5. **Reference Handling**: Options for handling references between schemas

## Extension Points

The transformation engine should be extensible to allow:

1. **Custom Rules**: Adding new transformation rules
2. **Custom Mappings**: Defining custom mappings for specific ontology patterns
3. **Pre/Post Processing**: Hooks for pre-processing the ontology or post-processing the JSON Schema
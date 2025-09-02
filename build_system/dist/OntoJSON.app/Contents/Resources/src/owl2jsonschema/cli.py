"""
Command Line Interface for OWL to JSON Schema transformation.
"""

import click
import json
import yaml
from pathlib import Path
from .engine import TransformationEngine
from .config import TransformationConfig
from .parser import OntologyParser


@click.command()
@click.argument('input_file', type=click.Path(exists=True))
@click.option('-o', '--output', 'output_file', type=click.Path(), 
              help='Output file path (default: stdout)')
@click.option('-c', '--config', 'config_file', type=click.Path(exists=True),
              help='Configuration file (YAML or JSON)')
@click.option('--enable-rule', 'enable_rules', multiple=True,
              help='Enable specific transformation rules')
@click.option('--disable-rule', 'disable_rules', multiple=True,
              help='Disable specific transformation rules')
@click.option('--format', type=click.Choice(['json', 'yaml']), default='json',
              help='Output format (default: json)')
@click.option('--indent', type=int, default=2,
              help='Indentation for output (default: 2)')
@click.option('--rdf-format', type=click.Choice(['xml', 'turtle', 'n3', 'auto']), 
              default='auto', help='RDF format of input file (default: auto-detect)')
@click.option('--language', type=str, default='en',
              help='Language for labels and comments (default: en)')
@click.option('--verbose', is_flag=True, help='Enable verbose output')
def main(input_file, output_file, config_file, enable_rules, disable_rules,
         format, indent, rdf_format, language, verbose):
    """
    Transform OWL/RDF ontology to JSON Schema.
    
    INPUT_FILE: Path to the OWL/RDF ontology file
    """
    
    try:
        # Load configuration
        if config_file:
            if verbose:
                click.echo(f"Loading configuration from {config_file}")
            config = TransformationConfig.from_file(config_file)
        else:
            config = TransformationConfig()
        
        # Apply command-line rule overrides
        for rule_id in enable_rules:
            if verbose:
                click.echo(f"Enabling rule: {rule_id}")
            config.enable_rule(rule_id)
        
        for rule_id in disable_rules:
            if verbose:
                click.echo(f"Disabling rule: {rule_id}")
            config.disable_rule(rule_id)
        
        # Set language option
        config.set_rule_option("labels_to_titles", "language", language)
        config.set_rule_option("comments_to_descriptions", "language", language)
        
        # Parse the ontology
        if verbose:
            click.echo(f"Parsing ontology from {input_file}")
        
        parser = OntologyParser()
        if rdf_format == 'auto':
            # Let rdflib auto-detect the format
            ontology = parser.parse(input_file)
        else:
            ontology = parser.parse(input_file, format=rdf_format)
        
        if verbose:
            click.echo(f"Parsed ontology: {ontology.uri}")
            click.echo(f"  Classes: {len(ontology.classes)}")
            click.echo(f"  Object Properties: {len(ontology.object_properties)}")
            click.echo(f"  Datatype Properties: {len(ontology.datatype_properties)}")
            click.echo(f"  Individuals: {len(ontology.individuals)}")
        
        # Create and run the transformation engine
        if verbose:
            click.echo("Running transformation...")
        
        engine = TransformationEngine(config)
        json_schema = engine.transform(ontology)
        
        if verbose:
            enabled_rules = engine.get_enabled_rules()
            click.echo(f"Applied {len(enabled_rules)} transformation rules")
        
        # Format the output
        if format == 'yaml':
            output_str = yaml.dump(json_schema, default_flow_style=False, sort_keys=False)
        else:
            output_str = json.dumps(json_schema, indent=indent)
        
        # Write output
        if output_file:
            Path(output_file).write_text(output_str)
            if verbose:
                click.echo(f"Output written to {output_file}")
        else:
            click.echo(output_str)
        
        if verbose:
            click.echo("Transformation completed successfully")
        
    except FileNotFoundError as e:
        click.echo(f"Error: File not found - {e}", err=True)
        raise click.Abort()
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        if verbose:
            import traceback
            traceback.print_exc()
        raise click.Abort()


@click.command()
@click.option('--output', 'output_file', type=click.Path(),
              default='config.yaml', help='Output configuration file')
@click.option('--format', type=click.Choice(['yaml', 'json']), default='yaml',
              help='Configuration format (default: yaml)')
def generate_config(output_file, format):
    """Generate a default configuration file."""
    
    config = TransformationConfig()
    
    if format == 'json':
        Path(output_file).write_text(json.dumps(config.config, indent=2))
    else:
        Path(output_file).write_text(yaml.dump(config.config, default_flow_style=False))
    
    click.echo(f"Default configuration written to {output_file}")


@click.command()
def list_rules():
    """List all available transformation rules."""
    
    # Import all rules to get the complete list
    from .rules import (
        ClassToObjectRule,
        ClassHierarchyRule,
        ClassRestrictionsRule,
        ObjectPropertyRule,
        DatatypePropertyRule,
        PropertyCardinalityRule,
        PropertyRestrictionsRule,
        LabelsToTitlesRule,
        CommentsToDescriptionsRule,
        AnnotationsToMetadataRule,
        EnumerationToEnumRule,
        UnionToAnyOfRule,
        IntersectionToAllOfRule,
        ComplementToNotRule,
        EquivalentClassesRule,
        DisjointClassesRule,
        OntologyToDocumentRule,
        IndividualsToExamplesRule,
        OntologyMetadataRule
    )
    
    rules = [
        ("class_to_object", "Transform OWL classes to JSON Schema objects"),
        ("class_hierarchy", "Transform class hierarchy to JSON Schema inheritance"),
        ("class_restrictions", "Transform class restrictions to JSON Schema constraints"),
        ("object_property", "Transform object properties to JSON Schema properties"),
        ("datatype_property", "Transform datatype properties to JSON Schema properties"),
        ("property_cardinality", "Transform property cardinality to JSON Schema constraints"),
        ("property_restrictions", "Transform property restrictions to JSON Schema validation"),
        ("labels_to_titles", "Transform RDFS labels to JSON Schema titles"),
        ("comments_to_descriptions", "Transform RDFS comments to JSON Schema descriptions"),
        ("annotations_to_metadata", "Transform annotations to JSON Schema metadata"),
        ("enumeration_to_enum", "Transform OWL enumerations to JSON Schema enum"),
        ("union_to_anyOf", "Transform OWL unions to JSON Schema anyOf"),
        ("intersection_to_allOf", "Transform OWL intersections to JSON Schema allOf"),
        ("complement_to_not", "Transform OWL complement to JSON Schema not"),
        ("equivalent_classes", "Handle OWL equivalent classes"),
        ("disjoint_classes", "Handle OWL disjoint classes"),
        ("ontology_to_document", "Transform ontology structure to JSON Schema document"),
        ("individuals_to_examples", "Transform named individuals to JSON Schema examples"),
        ("ontology_metadata", "Transform ontology metadata to JSON Schema metadata"),
    ]
    
    click.echo("Available transformation rules:\n")
    for rule_id, description in rules:
        click.echo(f"  {rule_id:30} - {description}")
    
    click.echo("\nUse --enable-rule or --disable-rule to control specific rules.")


@click.group()
def cli():
    """OWL to JSON Schema Transformation Tool"""
    pass


# Add subcommands to the main group
cli.add_command(main, name='transform')
cli.add_command(generate_config)
cli.add_command(list_rules)


if __name__ == '__main__':
    cli()
"""
Command-line interface for JSON Schema to OWL transformation.
"""

import click
from pathlib import Path

from .parser import SchemaParser
from .transformer import JsonSchema2OwlTransformer
from .config import JsonSchema2OwlConfig


@click.command()
@click.argument("input_file", type=click.Path(exists=True))
@click.option("-o", "--output", "output_file", type=click.Path(), help="Output file path (default: stdout)")
@click.option(
    "--base-uri",
    default="http://example.org/ns#",
    help="Base URI for the ontology (default: http://example.org/ns#)",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["turtle", "xml", "n3", "nt"]),
    default="turtle",
    help="RDF output format (default: turtle)",
)
@click.option(
    "--title",
    default=None,
    help="Ontology title",
)
@click.option(
    "--comment",
    default=None,
    help="Ontology comment/description",
)
@click.option("--verbose", is_flag=True, help="Enable verbose output")
def main(input_file, output_file, base_uri, output_format, title, comment, verbose):
    """Transform a JSON Schema file to an OWL ontology."""
    try:
        config = JsonSchema2OwlConfig(
            base_uri=base_uri,
            ontology_title=title,
            ontology_comment=comment,
        )
        transformer = JsonSchema2OwlTransformer(
            base_uri=base_uri,
            ontology_title=title,
            ontology_comment=comment or "Generated from JSON Schema",
            config=config,
        )
        if verbose:
            click.echo(f"Parsing {input_file}...")
        result = transformer.transform_file(input_file, output_format=output_format)
        if verbose:
            click.echo(f"Transformation complete. Serializing as {output_format}.")
        if output_file:
            Path(output_file).write_text(result, encoding="utf-8")
            if verbose:
                click.echo(f"Written to {output_file}")
        else:
            click.echo(result)
    except Exception as e:
        if verbose:
            raise
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


if __name__ == "__main__":
    main()

"""
Test script for generating separate JSON schemas for composite and component ontologies.

This test demonstrates the new functionality where:
1. A composite ontology is created from multiple source ontologies
2. The composite ontology is transformed to JSON Schema
3. Each individual component ontology is also transformed to JSON Schema
4. All schemas are saved to separate files
"""

import json
from pathlib import Path
from src.owl2jsonschema.services.transformation_service import TransformationService
from src.owl2jsonschema.config import TransformationConfig


def test_component_schema_generation():
    """Test generation of schemas for both composite and component ontologies."""
    
    print("=" * 80)
    print("Testing Component Schema Generation")
    print("=" * 80)
    
    # Initialize the transformation service
    service = TransformationService()
    
    # Define test ontology sources
    # Using existing test ontologies in the project
    test_sources = [
        "test_ontology1.ttl",
        "test_ontology2.ttl"
    ]
    
    # Check if test files exist, otherwise use the main test ontology
    existing_sources = []
    for source in test_sources:
        if Path(source).exists():
            existing_sources.append(source)
    
    # Fallback to single test ontology if individual test files don't exist
    if not existing_sources:
        print("Individual test ontologies not found, using main test ontology")
        existing_sources = ["test_ontology.ttl"]
    
    print(f"\nSource ontologies: {existing_sources}")
    print(f"Number of sources: {len(existing_sources)}")
    
    # Create output directory
    output_dir = Path("test_output/component_schemas")
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"\nOutput directory: {output_dir}")
    
    # Create transformation configuration
    config = TransformationConfig()
    
    # Perform transformation
    print("\nPerforming transformation...")
    print("-" * 80)
    
    result = service.transform_multiple(
        sources=existing_sources,
        config=config,
        composite_metadata={
            "title": "Test Composite Ontology",
            "description": "Composite ontology for testing component schema generation",
            "version": "1.0.0"
        },
        transform_components=True  # Enable component transformation
    )
    
    # Check result
    if not result.success:
        print(f"❌ Transformation failed: {result.error}")
        return False
    
    print("✅ Transformation successful!")
    
    # Display metadata
    print("\nTransformation Metadata:")
    print("-" * 80)
    for key, value in result.metadata.items():
        print(f"  {key}: {value}")
    
    # Display warnings if any
    if result.warnings:
        print("\n⚠️  Warnings:")
        for warning in result.warnings:
            print(f"  - {warning}")
    
    # Save results to files
    print("\nSaving schemas to files...")
    print("-" * 80)
    
    saved_files = service.save_transformation_results(
        result=result,
        output_dir=output_dir,
        composite_filename="composite_schema.json",
        component_suffix="_component_schema.json"
    )
    
    # Display saved files
    print("\n📁 Saved Files:")
    for schema_name, file_path in saved_files.items():
        file_size = Path(file_path).stat().st_size
        print(f"  {schema_name:20} -> {file_path} ({file_size} bytes)")
    
    # Analyze schemas
    print("\n📊 Schema Analysis:")
    print("-" * 80)
    
    # Analyze composite schema
    if result.schema:
        composite_defs = result.schema.get("$defs", {})
        print(f"  Composite schema definitions: {len(composite_defs)}")
        if composite_defs:
            print(f"    Classes: {', '.join(list(composite_defs.keys())[:5])}...")
    
    # Analyze component schemas
    if result.component_schemas:
        print(f"\n  Component schemas: {len(result.component_schemas)}")
        for component_name, component_schema in result.component_schemas.items():
            component_defs = component_schema.get("$defs", {})
            print(f"    {component_name}: {len(component_defs)} definitions")
    
    print("\n" + "=" * 80)
    print("✅ Test completed successfully!")
    print("=" * 80)
    
    return True


def verify_schema_files():
    """Verify that the generated schema files are valid JSON."""
    
    print("\n\n" + "=" * 80)
    print("Verifying Generated Schema Files")
    print("=" * 80)
    
    output_dir = Path("test_output/component_schemas")
    
    if not output_dir.exists():
        print("❌ Output directory does not exist")
        return False
    
    schema_files = list(output_dir.glob("*.json"))
    
    if not schema_files:
        print("❌ No schema files found")
        return False
    
    print(f"\nFound {len(schema_files)} schema files:")
    
    all_valid = True
    for schema_file in schema_files:
        try:
            with open(schema_file, 'r') as f:
                schema = json.load(f)
            
            # Check for required JSON Schema fields
            has_schema = "$schema" in schema
            has_defs = "$defs" in schema or "definitions" in schema
            
            status = "✅" if (has_schema or has_defs) else "⚠️ "
            print(f"  {status} {schema_file.name}")
            
            if has_schema:
                print(f"      $schema: {schema.get('$schema')}")
            if "$defs" in schema:
                print(f"      $defs: {len(schema['$defs'])} definitions")
            elif "definitions" in schema:
                print(f"      definitions: {len(schema['definitions'])} definitions")
            
        except json.JSONDecodeError as e:
            print(f"  ❌ {schema_file.name}: Invalid JSON - {e}")
            all_valid = False
        except Exception as e:
            print(f"  ❌ {schema_file.name}: Error - {e}")
            all_valid = False
    
    print("\n" + "=" * 80)
    if all_valid:
        print("✅ All schema files are valid!")
    else:
        print("❌ Some schema files have issues")
    print("=" * 80)
    
    return all_valid


if __name__ == "__main__":
    try:
        # Run the test
        success = test_component_schema_generation()
        
        # Verify the generated files
        if success:
            verify_schema_files()
        
    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
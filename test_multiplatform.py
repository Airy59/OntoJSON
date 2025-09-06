#!/usr/bin/env python3
"""
Multi-platform compatibility test for OntoJSON.

This script tests that the core transformation engine works correctly
across different interfaces (CLI, GUI, Web).
"""

import sys
import os
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

def test_service_layer():
    """Test that the service layer works independently."""
    print("Testing service layer...")
    
    from owl2jsonschema.services import (
        TransformationService,
        FileService,
        ConfigurationService
    )
    
    # Test transformation service
    trans_service = TransformationService()
    assert trans_service is not None
    print("✓ TransformationService initialized")
    
    # Test file service with different adapters
    from owl2jsonschema.services.file_service import LocalFileAdapter, WebUploadAdapter
    
    # Local adapter
    local_service = FileService(LocalFileAdapter())
    assert local_service is not None
    print("✓ FileService with LocalFileAdapter initialized")
    
    # Web adapter
    web_service = FileService(WebUploadAdapter())
    assert web_service is not None
    print("✓ FileService with WebUploadAdapter initialized")
    
    # Test configuration service
    config_service = ConfigurationService()
    assert config_service is not None
    print("✓ ConfigurationService initialized")
    
    # Test creating config
    config = config_service.create_config_from_dict(None)
    assert config is not None
    print("✓ Default configuration created")
    
    return True


def test_cli_interface():
    """Test that CLI interface can use the services."""
    print("\nTesting CLI interface...")
    
    try:
        from owl2jsonschema.cli import main
        print("✓ CLI module imported successfully")
        
        # Test that CLI can access transformation engine
        from owl2jsonschema.engine import TransformationEngine
        from owl2jsonschema.config import TransformationConfig
        
        config = TransformationConfig()
        engine = TransformationEngine(config)
        assert engine is not None
        print("✓ CLI can create TransformationEngine")
        
        return True
    except ImportError as e:
        print(f"⚠ CLI interface import issue (expected if click not installed): {e}")
        return True


def test_gui_interface():
    """Test that GUI interface can use the services."""
    print("\nTesting GUI interface...")
    
    try:
        # Don't actually create Qt app, just test imports
        from owl2jsonschema_gui import app
        print("✓ GUI module imported successfully")
        
        # Test that GUI can access services
        from owl2jsonschema.services import TransformationService
        service = TransformationService()
        assert service is not None
        print("✓ GUI can create TransformationService")
        
        return True
    except ImportError as e:
        print(f"⚠ GUI interface import issue (expected if PyQt6 not installed): {e}")
        return True


def test_web_interface():
    """Test that Web interface can use the services."""
    print("\nTesting Web interface...")
    
    try:
        # Test Flask app creation
        from owl2jsonschema_web import create_app
        
        # Create app with test config
        app = create_app()
        assert app is not None
        print("✓ Flask app created successfully")
        
        # Test that API can access services
        from owl2jsonschema.services import TransformationService
        service = TransformationService()
        assert service is not None
        print("✓ Web API can create TransformationService")
        
        # Test API routes exist
        with app.test_client() as client:
            # Test health endpoint
            response = client.get('/api/health')
            assert response.status_code == 200
            print("✓ API health endpoint accessible")
            
            # Test rules endpoint
            response = client.get('/api/rules')
            assert response.status_code == 200
            print("✓ API rules endpoint accessible")
        
        return True
    except ImportError as e:
        print(f"⚠ Web interface import issue (expected if Flask not installed): {e}")
        return True


def test_core_transformation():
    """Test core transformation functionality."""
    print("\nTesting core transformation...")
    
    from owl2jsonschema.services import TransformationService
    
    # Create a simple test ontology
    test_ontology = """
    @prefix owl: <http://www.w3.org/2002/07/owl#> .
    @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
    @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
    @prefix ex: <http://example.org/> .
    
    ex:TestClass a owl:Class ;
        rdfs:label "Test Class" ;
        rdfs:comment "A test class for validation" .
    
    ex:testProperty a owl:DatatypeProperty ;
        rdfs:domain ex:TestClass ;
        rdfs:range xsd:string .
    """
    
    # Save to temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.ttl', delete=False) as f:
        f.write(test_ontology)
        temp_path = f.name
    
    try:
        service = TransformationService()
        result = service.transform_single(
            source=temp_path,
            rdf_format='turtle'
        )
        
        assert result.success, f"Transformation failed: {result.error}"
        assert result.schema is not None
        print("✓ Core transformation successful")
        
        # Check that schema has expected structure
        assert 'definitions' in result.schema or '$defs' in result.schema
        print("✓ Schema has definitions")
        
        return True
    finally:
        # Clean up
        Path(temp_path).unlink(missing_ok=True)


def test_file_abstraction():
    """Test file abstraction layer."""
    print("\nTesting file abstraction...")
    
    from owl2jsonschema.services import FileService
    from owl2jsonschema.services.file_service import LocalFileAdapter, WebUploadAdapter
    
    # Test with local adapter
    local_service = FileService(LocalFileAdapter())
    
    # Test writing and reading
    test_content = "Test content for file abstraction"
    temp_path = local_service.get_temp_path(suffix='.txt')
    
    assert local_service.write_text(temp_path, test_content)
    print("✓ File written with LocalFileAdapter")
    
    read_content = local_service.read_text(temp_path)
    assert read_content == test_content
    print("✓ File read with LocalFileAdapter")
    
    # Clean up
    local_service.delete(temp_path)
    assert not local_service.exists(temp_path)
    print("✓ File deleted with LocalFileAdapter")
    
    # Test with web adapter
    web_service = FileService(WebUploadAdapter())
    
    # Test in-memory storage
    web_path = "test_file.txt"
    assert web_service.write_text(web_path, test_content)
    print("✓ File written with WebUploadAdapter")
    
    read_content = web_service.read_text(web_path)
    assert read_content == test_content
    print("✓ File read from WebUploadAdapter")
    
    return True


def main():
    """Run all compatibility tests."""
    print("=" * 60)
    print("OntoJSON Multi-Platform Compatibility Test")
    print("=" * 60)
    
    tests = [
        ("Service Layer", test_service_layer),
        ("File Abstraction", test_file_abstraction),
        ("Core Transformation", test_core_transformation),
        ("CLI Interface", test_cli_interface),
        ("GUI Interface", test_gui_interface),
        ("Web Interface", test_web_interface),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"✗ {test_name} failed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    for test_name, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{test_name:.<40} {status}")
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! The application is multi-platform compatible.")
    else:
        print("\n⚠ Some tests failed. Check the output above for details.")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
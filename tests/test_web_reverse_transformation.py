"""
Tests for web reverse transformation API endpoints.
"""

import pytest
import json
import tempfile
from pathlib import Path


@pytest.fixture
def app():
    """Create test Flask application."""
    from src.owl2jsonschema_web import create_app
    app = create_app({'TESTING': True})
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture
def sample_schema():
    """Sample JSON Schema for testing."""
    return {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "definitions": {
            "Person": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "age": {"type": "number"},
                    "email": {"type": "string", "format": "email"}
                },
                "required": ["name"]
            },
            "Address": {
                "type": "object",
                "properties": {
                    "street": {"type": "string"},
                    "city": {"type": "string"},
                    "country": {"type": "string"}
                }
            }
        }
    }


class TestReverseTransformAPI:
    """Tests for reverse transformation API endpoints."""
    
    def test_reverse_transform_with_dict(self, client, sample_schema):
        """Test transformation with JSON Schema as dict."""
        response = client.post(
            '/api/reverse/transform',
            json={
                'schema': sample_schema,
                'base_namespace': 'http://example.org/test#',
                'language': 'en',
                'format': 'turtle'
            }
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert 'ontology' in data
        assert data['format'] == 'turtle'
        assert 'statistics' in data
        
        # Check statistics
        stats = data['statistics']
        assert 'classes' in stats
        assert 'datatype_properties' in stats
        assert 'object_properties' in stats
    
    def test_reverse_transform_different_formats(self, client, sample_schema):
        """Test transformation with different output formats."""
        formats = ['turtle', 'xml', 'json-ld']
        
        for fmt in formats:
            response = client.post(
                '/api/reverse/transform',
                json={
                    'schema': sample_schema,
                    'format': fmt
                }
            )
            
            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True
            assert data['format'] == fmt
    
    def test_reverse_transform_with_file(self, client, sample_schema):
        """Test transformation with file upload."""
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(sample_schema, f)
            temp_path = f.name
        
        try:
            with open(temp_path, 'rb') as f:
                response = client.post(
                    '/api/reverse/transform',
                    data={'file': (f, 'schema.json')},
                    content_type='multipart/form-data'
                )
            
            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True
            
        finally:
            Path(temp_path).unlink()
    
    def test_reverse_transform_invalid_schema(self, client):
        """Test transformation with invalid JSON Schema."""
        invalid_schema = "not a valid json"
        
        response = client.post(
            '/api/reverse/transform',
            data={'schema': invalid_schema},
            content_type='multipart/form-data'
        )
        
        # Should handle error gracefully
        assert response.status_code in [400, 500]
    
    def test_reverse_transform_no_schema(self, client):
        """Test transformation without schema."""
        response = client.post(
            '/api/reverse/transform',
            json={}
        )
        
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data


class TestValidationAPI:
    """Tests for JSON Schema validation API."""
    
    def test_validate_valid_schema(self, client, sample_schema):
        """Test validation with valid schema."""
        response = client.post(
            '/api/reverse/validate',
            json={'schema': sample_schema}
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['valid'] is True
        assert 'warnings' in data
        assert 'schema_version' in data
    
    def test_validate_schema_with_warnings(self, client):
        """Test validation that produces warnings."""
        schema_without_version = {
            "definitions": {
                "Test": {
                    "type": "object"
                }
            }
        }
        
        response = client.post(
            '/api/reverse/validate',
            json={'schema': schema_without_version}
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['valid'] is True
        assert len(data['warnings']) > 0
    
    def test_validate_invalid_schema(self, client):
        """Test validation with invalid schema."""
        response = client.post(
            '/api/reverse/validate',
            json={'schema': 'not a dict'}
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['valid'] is False
        assert 'error' in data


class TestPreviewAPI:
    """Tests for transformation preview API."""
    
    def test_preview_patterns(self, client):
        """Test getting transformation patterns."""
        response = client.get('/api/reverse/preview')
        
        assert response.status_code == 200
        data = response.get_json()
        assert 'patterns' in data
        assert len(data['patterns']) > 0
        
        # Check pattern structure
        pattern = data['patterns'][0]
        assert 'json_schema' in pattern
        assert 'owl' in pattern
        assert 'description' in pattern
    
    def test_preview_formats(self, client):
        """Test getting available formats."""
        response = client.get('/api/reverse/formats')
        
        assert response.status_code == 200
        data = response.get_json()
        assert 'formats' in data
        assert len(data['formats']) > 0
        
        # Check format structure
        fmt = data['formats'][0]
        assert 'name' in fmt
        assert 'extension' in fmt
        assert 'mime_type' in fmt


class TestIntegration:
    """Integration tests for reverse transformation workflow."""
    
    def test_full_workflow(self, client, sample_schema):
        """Test complete workflow: validate -> transform -> download."""
        # Step 1: Validate
        validation_response = client.post(
            '/api/reverse/validate',
            json={'schema': sample_schema}
        )
        assert validation_response.status_code == 200
        assert validation_response.get_json()['valid'] is True
        
        # Step 2: Transform
        transform_response = client.post(
            '/api/reverse/transform',
            json={
                'schema': sample_schema,
                'base_namespace': 'http://example.org/test#',
                'format': 'turtle'
            }
        )
        assert transform_response.status_code == 200
        transform_data = transform_response.get_json()
        assert transform_data['success'] is True
        
        # Step 3: Verify ontology content
        ontology = transform_data['ontology']
        assert 'Person' in ontology
        assert 'Address' in ontology
        assert len(ontology) > 0


class TestErrorHandling:
    """Tests for error handling."""
    
    def test_missing_schema_error(self, client):
        """Test error when schema is missing."""
        response = client.post('/api/reverse/transform', json={})
        assert response.status_code == 400
        assert 'error' in response.get_json()
    
    def test_invalid_format_handled(self, client, sample_schema):
        """Test that invalid format is handled gracefully."""
        response = client.post(
            '/api/reverse/transform',
            json={
                'schema': sample_schema,
                'format': 'invalid_format'
            }
        )
        
        # Should either succeed with default format or return error
        assert response.status_code in [200, 400]
    
    def test_invalid_namespace_handled(self, client, sample_schema):
        """Test that invalid namespace is handled."""
        response = client.post(
            '/api/reverse/transform',
            json={
                'schema': sample_schema,
                'base_namespace': 'not-a-valid-uri'
            }
        )
        
        # Should still work or return appropriate error
        assert response.status_code in [200, 400]


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
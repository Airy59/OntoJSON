"""
File Service

Service for handling JSON Schema file operations.
"""

import json
import tempfile
from pathlib import Path
from typing import Union, Optional, Tuple


class ReverseFileService:
    """
    Service for handling JSON Schema file operations.
    
    Provides utilities for reading, writing, and managing JSON Schema files.
    """
    
    def __init__(self):
        """Initialize the file service."""
        pass
    
    def read_schema(self, file_path: Union[str, Path]) -> dict:
        """
        Read a JSON Schema from a file.
        
        Args:
            file_path: Path to the JSON Schema file
            
        Returns:
            Schema as dictionary
            
        Raises:
            FileNotFoundError: If file doesn't exist
            json.JSONDecodeError: If file contains invalid JSON
        """
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"Schema file not found: {file_path}")
        
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def write_ontology(
        self,
        ontology_content: str,
        output_path: Union[str, Path],
        format: str = "turtle"
    ) -> str:
        """
        Write an OWL ontology to a file.
        
        Args:
            ontology_content: Serialized ontology content
            output_path: Path where to save the file
            format: Output format (affects file extension if not provided)
            
        Returns:
            Path to the saved file
        """
        path = Path(output_path)
        
        # Ensure parent directory exists
        path.parent.mkdir(parents=True, exist_ok=True)
        
        # Add appropriate extension if not present
        if not path.suffix:
            ext_map = {
                'turtle': '.ttl',
                'xml': '.owl',
                'json-ld': '.jsonld'
            }
            path = path.with_suffix(ext_map.get(format, '.ttl'))
        
        # Write the file
        with open(path, 'w', encoding='utf-8') as f:
            f.write(ontology_content)
        
        return str(path)
    
    def save_to_temp(
        self,
        content: str,
        suffix: str = '.ttl'
    ) -> str:
        """
        Save content to a temporary file.
        
        Args:
            content: Content to save
            suffix: File suffix/extension
            
        Returns:
            Path to temporary file
        """
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix=suffix,
            delete=False,
            encoding='utf-8'
        ) as temp_file:
            temp_file.write(content)
            return temp_file.name
    
    def get_temp_path(self, suffix: str = '.ttl') -> str:
        """
        Get a temporary file path without creating the file.
        
        Args:
            suffix: File suffix/extension
            
        Returns:
            Path to temporary file location
        """
        temp_file = tempfile.NamedTemporaryFile(
            mode='w',
            suffix=suffix,
            delete=False
        )
        path = temp_file.name
        temp_file.close()
        Path(path).unlink()  # Remove the created file
        return path
    
    def validate_json_file(self, file_path: Union[str, Path]) -> Tuple[bool, Optional[str]]:
        """
        Validate that a file contains valid JSON.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                json.load(f)
            return True, None
        except FileNotFoundError:
            return False, f"File not found: {file_path}"
        except json.JSONDecodeError as e:
            return False, f"Invalid JSON: {e}"
        except Exception as e:
            return False, str(e)
    
    def get_format_extension(self, format: str) -> str:
        """
        Get the file extension for a given output format.
        
        Args:
            format: Output format name
            
        Returns:
            File extension (with dot)
        """
        ext_map = {
            'turtle': '.ttl',
            'ttl': '.ttl',
            'xml': '.owl',
            'rdfxml': '.owl',
            'json-ld': '.jsonld',
            'jsonld': '.jsonld',
            'nt': '.nt',
            'n3': '.n3'
        }
        return ext_map.get(format.lower(), '.ttl')


# Export main class
__all__ = ['ReverseFileService']
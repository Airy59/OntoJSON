"""
Utility functions for OWL to JSON Schema transformation.
"""

import re
from typing import Any, Optional, Dict, Union, List


def clean_string(text: Union[str, None]) -> Union[str, None]:
    """
    Clean a string by replacing sequences of tabs and newlines with a single space.
    Also handles other common whitespace issues.
    
    Args:
        text: The string to clean (can be None)
    
    Returns:
        The cleaned string or None if input was None
    """
    if text is None:
        return None
    
    if not isinstance(text, str):
        return text
    
    # Replace one or more tabs with a single space
    cleaned = re.sub(r'\t+', ' ', text)
    
    # Replace newlines (and carriage returns) with spaces
    # First, replace \r\n or \n\r combinations with a single space
    cleaned = re.sub(r'\r\n|\n\r', ' ', cleaned)
    # Then replace any remaining \n or \r with a space
    cleaned = re.sub(r'[\r\n]', ' ', cleaned)
    
    # Clean up multiple spaces that might result from replacements
    cleaned = re.sub(r' {2,}', ' ', cleaned)
    
    # Remove leading/trailing whitespace
    cleaned = cleaned.strip()
    
    return cleaned


def clean_dict_values(data: Dict[str, Any], keys_to_clean: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Clean string values in a dictionary.
    
    Args:
        data: Dictionary to clean
        keys_to_clean: Optional list of specific keys to clean. If None, cleans common annotation keys.
    
    Returns:
        Dictionary with cleaned string values
    """
    if keys_to_clean is None:
        # Default keys that typically contain text from ontologies
        keys_to_clean = ['comment', 'description', 'definition', 'label', 'title', 
                        'rdfs:comment', 'rdfs:label', 'skos:definition', 'dc:description']
    
    cleaned_data = data.copy()
    
    for key, value in data.items():
        if key in keys_to_clean:
            if isinstance(value, str):
                cleaned_data[key] = clean_string(value)
            elif isinstance(value, dict):
                # Handle language-tagged values
                cleaned_data[key] = {
                    lang: clean_string(text) if isinstance(text, str) else text
                    for lang, text in value.items()
                }
            elif isinstance(value, list):
                # Handle lists of strings
                cleaned_data[key] = [
                    clean_string(item) if isinstance(item, str) else item
                    for item in value
                ]
    
    return cleaned_data


def clean_annotation_text(annotations: Dict[str, Any]) -> Dict[str, Any]:
    """
    Clean text in annotation dictionaries specifically.
    
    Args:
        annotations: Dictionary of annotations
    
    Returns:
        Dictionary with cleaned annotation values
    """
    cleaned = {}
    
    # Keys that commonly contain text content that needs cleaning
    text_annotation_keys = {
        'comment', 'description', 'definition', 'label', 'title',
        'rdfs:comment', 'rdfs:label', 'skos:definition', 'dc:description',
        'dc:title', 'skos:prefLabel', 'skos:altLabel', 'skos:hiddenLabel',
        'obo:IAO_0000115',  # Common OBO definition annotation
        'obo:definition'
    }
    
    for key, value in annotations.items():
        # Check if this key likely contains text content
        if any(text_key in key.lower() for text_key in ['comment', 'definition', 'description', 'label', 'title']):
            if isinstance(value, str):
                cleaned[key] = clean_string(value)
            elif isinstance(value, dict):
                # Handle nested dictionaries (e.g., language-tagged values)
                cleaned[key] = {
                    k: clean_string(v) if isinstance(v, str) else v
                    for k, v in value.items()
                }
            elif isinstance(value, list):
                # Handle lists
                cleaned[key] = [
                    clean_string(item) if isinstance(item, str) else item
                    for item in value
                ]
            else:
                cleaned[key] = value
        else:
            # For non-text annotations, keep as is
            cleaned[key] = value
    
    return cleaned


def clean_language_tagged_value(value: Union[str, Dict[str, str], None]) -> Union[str, Dict[str, str], None]:
    """
    Clean a value that might be a simple string or a language-tagged dictionary.
    
    Args:
        value: String, dictionary of language-tagged strings, or None
    
    Returns:
        Cleaned value in the same format as input
    """
    if value is None:
        return None
    
    if isinstance(value, str):
        return clean_string(value)
    
    if isinstance(value, dict):
        return {
            lang: clean_string(text) if isinstance(text, str) else text
            for lang, text in value.items()
        }
    
    return value
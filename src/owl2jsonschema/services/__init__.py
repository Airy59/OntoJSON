"""
Service layer for OWL to JSON Schema transformation.

This module provides platform-agnostic services that can be used by
different presentation layers (CLI, GUI, Web).
"""

from .transformation_service import TransformationService
from .file_service import FileService, FileServiceAdapter
from .configuration_service import ConfigurationService

__all__ = [
    'TransformationService',
    'FileService',
    'FileServiceAdapter',
    'ConfigurationService'
]
"""
File Service

Abstract file handling service to support different storage backends.
"""

import os
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Union, BinaryIO, Optional, List, Tuple
from urllib.parse import urlparse
import requests


class FileServiceAdapter(ABC):
    """
    Abstract base class for file service adapters.
    
    Different adapters can be implemented for local filesystem,
    cloud storage (S3, Azure), or in-memory operations.
    """
    
    @abstractmethod
    def read(self, path: str) -> bytes:
        """Read file content as bytes."""
        pass
    
    @abstractmethod
    def write(self, path: str, content: Union[str, bytes]) -> bool:
        """Write content to a file."""
        pass
    
    @abstractmethod
    def exists(self, path: str) -> bool:
        """Check if a file exists."""
        pass
    
    @abstractmethod
    def delete(self, path: str) -> bool:
        """Delete a file."""
        pass
    
    @abstractmethod
    def list_files(self, directory: str, pattern: str = "*") -> List[str]:
        """List files in a directory."""
        pass
    
    @abstractmethod
    def get_temp_path(self, suffix: str = "") -> str:
        """Get a temporary file path."""
        pass


class LocalFileAdapter(FileServiceAdapter):
    """
    File service adapter for local filesystem operations.
    """
    
    def __init__(self, base_path: Optional[Path] = None):
        """
        Initialize local file adapter.
        
        Args:
            base_path: Base directory for file operations
        """
        self.base_path = Path(base_path) if base_path else Path.cwd()
    
    def _resolve_path(self, path: str) -> Path:
        """Resolve a path relative to base path."""
        p = Path(path)
        if p.is_absolute():
            return p
        return self.base_path / p
    
    def read(self, path: str) -> bytes:
        """Read file content as bytes."""
        resolved_path = self._resolve_path(path)
        if not resolved_path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        return resolved_path.read_bytes()
    
    def write(self, path: str, content: Union[str, bytes]) -> bool:
        """Write content to a file."""
        try:
            resolved_path = self._resolve_path(path)
            resolved_path.parent.mkdir(parents=True, exist_ok=True)
            
            if isinstance(content, str):
                resolved_path.write_text(content, encoding='utf-8')
            else:
                resolved_path.write_bytes(content)
            return True
        except Exception:
            return False
    
    def exists(self, path: str) -> bool:
        """Check if a file exists."""
        return self._resolve_path(path).exists()
    
    def delete(self, path: str) -> bool:
        """Delete a file."""
        try:
            resolved_path = self._resolve_path(path)
            if resolved_path.exists():
                resolved_path.unlink()
            return True
        except Exception:
            return False
    
    def list_files(self, directory: str, pattern: str = "*") -> List[str]:
        """List files in a directory."""
        dir_path = self._resolve_path(directory)
        if not dir_path.exists() or not dir_path.is_dir():
            return []
        
        files = []
        for file_path in dir_path.glob(pattern):
            if file_path.is_file():
                files.append(str(file_path.relative_to(self.base_path)))
        return files
    
    def get_temp_path(self, suffix: str = "") -> str:
        """Get a temporary file path."""
        temp_file = tempfile.NamedTemporaryFile(
            suffix=suffix,
            delete=False,
            dir=tempfile.gettempdir()
        )
        temp_file.close()
        return temp_file.name


class WebUploadAdapter(FileServiceAdapter):
    """
    File service adapter for web uploads and temporary storage.
    """
    
    def __init__(self, upload_dir: Optional[Path] = None):
        """
        Initialize web upload adapter.
        
        Args:
            upload_dir: Directory for storing uploaded files
        """
        if upload_dir:
            self.upload_dir = Path(upload_dir)
            self.upload_dir.mkdir(parents=True, exist_ok=True)
        else:
            self.upload_dir = Path(tempfile.gettempdir()) / "ontojson_uploads"
            self.upload_dir.mkdir(parents=True, exist_ok=True)
        
        # In-memory storage for session-based files
        self.memory_storage = {}
    
    def read(self, path: str) -> bytes:
        """Read file content as bytes."""
        # Check memory storage first
        if path in self.memory_storage:
            return self.memory_storage[path]
        
        # Check disk storage
        file_path = self.upload_dir / path
        if file_path.exists():
            return file_path.read_bytes()
        
        raise FileNotFoundError(f"File not found: {path}")
    
    def write(self, path: str, content: Union[str, bytes]) -> bool:
        """Write content to a file."""
        try:
            # Store in both memory and disk for redundancy
            if isinstance(content, str):
                content = content.encode('utf-8')
            
            self.memory_storage[path] = content
            
            file_path = self.upload_dir / path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_bytes(content)
            
            return True
        except Exception:
            return False
    
    def exists(self, path: str) -> bool:
        """Check if a file exists."""
        return path in self.memory_storage or (self.upload_dir / path).exists()
    
    def delete(self, path: str) -> bool:
        """Delete a file."""
        try:
            # Remove from memory storage
            if path in self.memory_storage:
                del self.memory_storage[path]
            
            # Remove from disk
            file_path = self.upload_dir / path
            if file_path.exists():
                file_path.unlink()
            
            return True
        except Exception:
            return False
    
    def list_files(self, directory: str, pattern: str = "*") -> List[str]:
        """List files in a directory."""
        # List from memory storage
        memory_files = [
            path for path in self.memory_storage.keys()
            if path.startswith(directory)
        ]
        
        # List from disk storage
        dir_path = self.upload_dir / directory
        disk_files = []
        if dir_path.exists() and dir_path.is_dir():
            for file_path in dir_path.glob(pattern):
                if file_path.is_file():
                    rel_path = file_path.relative_to(self.upload_dir)
                    disk_files.append(str(rel_path))
        
        # Combine and deduplicate
        all_files = list(set(memory_files + disk_files))
        return all_files
    
    def get_temp_path(self, suffix: str = "") -> str:
        """Get a temporary file path."""
        import uuid
        filename = f"{uuid.uuid4().hex}{suffix}"
        return str(self.upload_dir / filename)
    
    def save_upload(self, file_obj: BinaryIO, filename: str) -> str:
        """
        Save an uploaded file.
        
        Args:
            file_obj: File-like object from web upload
            filename: Original filename
            
        Returns:
            Path where the file was saved
        """
        import uuid
        
        # Generate unique filename to avoid collisions
        unique_filename = f"{uuid.uuid4().hex}_{filename}"
        file_path = self.upload_dir / unique_filename
        
        # Read and save content
        content = file_obj.read()
        file_path.write_bytes(content)
        
        # Store in memory as well for quick access
        self.memory_storage[unique_filename] = content
        
        return str(file_path)


class FileService:
    """
    Main file service that uses adapters for actual operations.
    """
    
    def __init__(self, adapter: Optional[FileServiceAdapter] = None):
        """
        Initialize file service.
        
        Args:
            adapter: File service adapter to use (defaults to LocalFileAdapter)
        """
        self.adapter = adapter or LocalFileAdapter()
    
    def set_adapter(self, adapter: FileServiceAdapter):
        """Change the file service adapter."""
        self.adapter = adapter
    
    def read_text(self, path: str, encoding: str = 'utf-8') -> str:
        """Read file content as text."""
        content = self.adapter.read(path)
        return content.decode(encoding)
    
    def read_bytes(self, path: str) -> bytes:
        """Read file content as bytes."""
        return self.adapter.read(path)
    
    def write_text(self, path: str, content: str) -> bool:
        """Write text content to a file."""
        return self.adapter.write(path, content)
    
    def write_bytes(self, path: str, content: bytes) -> bool:
        """Write binary content to a file."""
        return self.adapter.write(path, content)
    
    def exists(self, path: str) -> bool:
        """Check if a file exists."""
        return self.adapter.exists(path)
    
    def delete(self, path: str) -> bool:
        """Delete a file."""
        return self.adapter.delete(path)
    
    def list_files(self, directory: str, pattern: str = "*") -> List[str]:
        """List files in a directory."""
        return self.adapter.list_files(directory, pattern)
    
    def get_temp_path(self, suffix: str = "") -> str:
        """Get a temporary file path."""
        return self.adapter.get_temp_path(suffix)
    
    def resolve_source(self, source: str) -> Tuple[str, bool]:
        """
        Resolve a source path or URI.
        
        Args:
            source: File path or URI
            
        Returns:
            Tuple of (resolved_path, is_remote)
        """
        # Check if it's a URI
        parsed = urlparse(source)
        
        if parsed.scheme in ('http', 'https'):
            # Download remote file to temporary location
            temp_path = self.get_temp_path(suffix='.ttl')
            try:
                response = requests.get(source, timeout=30)
                response.raise_for_status()
                self.write_bytes(temp_path, response.content)
                return temp_path, True
            except Exception as e:
                raise RuntimeError(f"Failed to download {source}: {e}")
        
        elif parsed.scheme == 'file' or not parsed.scheme:
            # Local file
            path = parsed.path if parsed.scheme == 'file' else source
            
            # If using web adapter, might need to handle differently
            if isinstance(self.adapter, WebUploadAdapter):
                # For web uploads, the path should already be in the upload directory
                if not self.exists(path):
                    raise FileNotFoundError(f"File not found: {path}")
                return path, False
            else:
                # For local adapter, resolve the path
                if not Path(path).exists():
                    raise FileNotFoundError(f"File not found: {path}")
                return str(Path(path).resolve()), False
        
        else:
            raise ValueError(f"Unsupported scheme: {parsed.scheme}")
    
    def cleanup_temp_files(self, paths: List[str]):
        """Clean up temporary files."""
        for path in paths:
            try:
                self.delete(path)
            except Exception:
                pass  # Ignore errors during cleanup
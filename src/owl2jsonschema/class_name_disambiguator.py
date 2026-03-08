"""
Class Name Disambiguator

This module handles disambiguation of class names when there are naming collisions
between classes from different ontologies (e.g., sosa:Observation vs pop:Observation).
"""

from typing import Dict, Set, Optional, List
from urllib.parse import urlparse
import re


class ClassNameDisambiguator:
    """
    Handles disambiguation of class names to avoid collisions between classes
    from different ontologies.
    """
    
    def __init__(self, main_ontology_uri: str, imported_ontology_uris: List[str] = None, 
                 primary_imports: List[str] = None, maximalist: bool = False):
        """
        Initialize the disambiguator.
        
        Args:
            main_ontology_uri: URI of the main ontology
            imported_ontology_uris: List of URIs of ALL imported ontologies (primary + secondary)
            primary_imports: List of URIs of PRIMARY imported ontologies (directly imported by main)
            maximalist: If True, add suffixes to ALL imported classes. If False, only when collision.
        """
        self.main_ontology_uri = main_ontology_uri
        self.imported_ontology_uris = imported_ontology_uris or []
        self.primary_imports = set(primary_imports or [])
        self.maximalist = maximalist
        
        # Track class names and their origins
        self.class_name_to_uris: Dict[str, List[str]] = {}
        self.uri_to_class_name: Dict[str, str] = {}
        self.uri_to_namespace_prefix: Dict[str, str] = {}
        
        # Build namespace prefix mappings
        self._build_namespace_mappings()
    
    def _build_namespace_mappings(self):
        """Build mappings from ontology URIs to namespace prefixes."""
        # Extract namespace prefix for main ontology
        main_prefix = self._extract_namespace_prefix(self.main_ontology_uri)
        self.uri_to_namespace_prefix[self.main_ontology_uri] = main_prefix
        
        # Extract namespace prefixes for imported ontologies
        for imported_uri in self.imported_ontology_uris:
            prefix = self._extract_namespace_prefix(imported_uri)
            self.uri_to_namespace_prefix[imported_uri] = prefix
    
    def _extract_namespace_prefix(self, ontology_uri: str) -> str:
        """
        Extract a namespace prefix from an ontology URI.
        
        Examples:
            http://www.w3.org/ns/sosa# -> sosa
            http://www.w3.org/ns/sosa -> sosa
            https://cdm.ovh/rsm/pop# -> pop
            https://cdm.ovh/rsm/pop -> pop
        
        Args:
            ontology_uri: The ontology URI
            
        Returns:
            A namespace prefix (lowercase)
        """
        # Remove trailing # or /
        uri = ontology_uri.rstrip('#/')
        
        # Try to extract from common patterns
        # Pattern 1: http://example.org/ns/prefix# or http://example.org/ns/prefix
        match = re.search(r'/([^/#]+?)(?:#|/)?$', uri)
        if match:
            prefix = match.group(1).lower()
            # Remove common suffixes
            prefix = re.sub(r'\.(owl|ttl|rdf|xml)$', '', prefix)
            return prefix
        
        # Pattern 2: Extract from domain/path
        parsed = urlparse(uri)
        path_parts = [p for p in parsed.path.split('/') if p]
        if path_parts:
            prefix = path_parts[-1].lower()
            prefix = re.sub(r'\.(owl|ttl|rdf|xml)$', '', prefix)
            return prefix
        
        # Fallback: use domain name
        if parsed.netloc:
            domain_parts = parsed.netloc.split('.')
            if len(domain_parts) >= 2:
                return domain_parts[-2].lower()
        
        # Last resort: use a hash of the URI
        return f"ns{abs(hash(uri)) % 10000}"
    
    def _get_ontology_uri_for_class(self, class_uri: str) -> Optional[str]:
        """
        Determine which ontology (main or imported) a class URI belongs to.
        
        Args:
            class_uri: The class URI
            
        Returns:
            The ontology URI, or None if not found
        """
        # Check if it belongs to main ontology
        if self._uri_belongs_to_ontology(class_uri, self.main_ontology_uri):
            return self.main_ontology_uri
        
        # Check imported ontologies
        for imported_uri in self.imported_ontology_uris:
            if self._uri_belongs_to_ontology(class_uri, imported_uri):
                return imported_uri
        
        return None
    
    def _is_primary_import(self, ontology_uri: str) -> bool:
        """
        Check if an ontology URI is a primary import.
        
        This handles the case where primary imports might be stored as file URIs
        (like file:///path/to/pop.ttl) but class URIs use namespace URIs 
        (like http://example.org/pop#). 
        
        We check if the ontology URI matches any primary import by:
        1. Direct match
        2. Checking if the ontology URI's namespace matches a primary import's namespace
        3. For file URIs in primary imports, we check if any class from that namespace
           would belong to that file's ontology
        
        Args:
            ontology_uri: The ontology URI to check (typically a namespace URI like http://example.org/pop#)
            
        Returns:
            True if this is a primary import
        """
        # Direct match (handles case where primary_imports contains namespace URIs)
        if ontology_uri in self.primary_imports:
            return True
        
        # Check if this ontology URI matches any primary import file URI
        # Primary imports might be file URIs, but we're checking against namespace URIs
        # So we need to see if classes from this namespace would belong to a primary import file
        for primary_import_uri in self.primary_imports:
            # If primary import is a file URI, we can't directly match it to a namespace URI
            # Instead, we check if a class from this namespace would be considered as
            # belonging to the primary import file's ontology
            # Since we can't know the mapping without parsing, we use a heuristic:
            # If the primary import URI is a file URI and this ontology URI is a namespace URI,
            # we can't match them directly. We need to rely on the fact that namespace bases
            # extracted from classes should correspond to primary imports.
            
            # For file URIs, check if they end with a filename that might match
            # For now, if primary import is a file URI, we'll assume namespace URIs
            # that are in imported_ontology_uris but NOT in secondary imports are primary
            # Actually, a simpler approach: if it's a file URI, skip direct matching
            # and rely on the fact that we should have namespace URIs in primary_imports too
            
            # Check reverse: if primary import URI (might be namespace) belongs to this ontology
            if self._uri_belongs_to_ontology(primary_import_uri, ontology_uri):
                return True
            
            # Check forward: if this ontology URI belongs to primary import URI
            # (handles case where primary import is a broader namespace)
            if self._uri_belongs_to_ontology(ontology_uri, primary_import_uri):
                return True
        
        return False
    
    def _uri_belongs_to_ontology(self, class_uri: str, ontology_uri: str) -> bool:
        """
        Check if a class URI belongs to a given ontology URI.
        
        Args:
            class_uri: The class URI
            ontology_uri: The ontology URI to check against
            
        Returns:
            True if the class belongs to the ontology
        """
        # Normalize both URIs
        ontology_base = ontology_uri.rstrip('#/')
        class_uri_str = str(class_uri)
        
        # Check if class URI starts with ontology base
        if class_uri_str.startswith(ontology_base):
            return True
        
        # Also check with # separator
        if '#' in ontology_base:
            ontology_ns = ontology_base + '#'
            if class_uri_str.startswith(ontology_ns):
                return True
        
        # Check if ontology_base ends with # and class uses that namespace
        if ontology_base.endswith('#'):
            if class_uri_str.startswith(ontology_base):
                return True
        elif '#' not in ontology_base:
            # If ontology URI doesn't have #, check if class URI is in same namespace
            # by checking if it starts with the base and has # or / separator
            if class_uri_str.startswith(ontology_base + '#') or class_uri_str.startswith(ontology_base + '/'):
                return True
        
        return False
    
    def register_class(self, class_uri: str, local_name: str):
        """
        Register a class and track its name.
        
        Args:
            class_uri: The full URI of the class
            local_name: The local name (extracted from URI)
        """
        if local_name not in self.class_name_to_uris:
            self.class_name_to_uris[local_name] = []
        self.class_name_to_uris[local_name].append(class_uri)
        self.uri_to_class_name[class_uri] = local_name
    
    def get_disambiguated_name(
        self,
        class_uri: str,
        local_name: str,
        maximalist: Optional[bool] = None
    ) -> str:
        """
        Get the disambiguated name for a class.
        
        Args:
            class_uri: The full URI of the class
            local_name: The local name (extracted from URI)
            maximalist: If True, add suffixes to ALL imported classes (regardless of collision).
                       If False, only add suffixes to imported classes when there's a collision.
                       If None, uses the instance's maximalist setting.
        
        Returns:
            The disambiguated class name
        """
        # Use instance setting if not provided
        if maximalist is None:
            maximalist = self.maximalist
        
        # Determine which ontology this class belongs to
        ontology_uri = self._get_ontology_uri_for_class(class_uri)
        if not ontology_uri:
            # Can't determine origin, return as-is
            return local_name
        
        # Check if this is the main ontology
        is_main_ontology = (ontology_uri == self.main_ontology_uri)
        
        # Main ontology classes always keep their original name
        if is_main_ontology:
            return local_name
        
        # Check if this is a primary import (using improved matching)
        is_primary_import = self._is_primary_import(ontology_uri)
        
        # For imported classes:
        if maximalist:
            # Maximalist: add suffix to ALL imported classes, regardless of collision
            prefix = self.uri_to_namespace_prefix.get(ontology_uri, "unknown")
            return f"{local_name}_{prefix}"
        else:
            # Default: only add suffix if there's a collision
            # Check if there's a collision by checking if multiple classes with same name
            # exist from different ontologies
            if local_name not in self.class_name_to_uris:
                # This shouldn't happen if class was registered, but handle gracefully
                return local_name
            
            # Get all URIs with this local name
            uris_with_same_name = self.class_name_to_uris[local_name]
            
            # Check if there are multiple classes with this name from different ontologies
            ontology_uris_seen = set()
            primary_ontology_uris_seen = set()
            for uri in uris_with_same_name:
                uri_ontology = self._get_ontology_uri_for_class(uri)
                if uri_ontology:
                    ontology_uris_seen.add(uri_ontology)
                    if self._is_primary_import(uri_ontology):
                        primary_ontology_uris_seen.add(uri_ontology)
            
            # If only one ontology has classes with this name, no collision
            if len(ontology_uris_seen) <= 1:
                return local_name
            
            # Multiple ontologies have classes with this name - collision detected
            if is_primary_import:
                # Primary import: only disambiguate if colliding with OTHER primary imports
                # (not with secondary imports or main ontology)
                if len(primary_ontology_uris_seen) > 1:
                    # Multiple primary imports have this name - disambiguate
                    prefix = self.uri_to_namespace_prefix.get(ontology_uri, "unknown")
                    return f"{local_name}_{prefix}"
                else:
                    # Only this primary import has this name (collision is with secondary imports)
                    # Primary imports keep original name when colliding only with secondary imports
                    return local_name
            else:
                # Secondary import: always disambiguate when there's any collision
                prefix = self.uri_to_namespace_prefix.get(ontology_uri, "unknown")
                return f"{local_name}_{prefix}"
    
    def extract_local_name(self, uri: str) -> str:
        """
        Extract the local name from a URI.
        
        Args:
            uri: The class URI
            
        Returns:
            The local name
        """
        if '#' in uri:
            return uri.split('#')[-1]
        elif '/' in uri:
            return uri.split('/')[-1]
        return uri

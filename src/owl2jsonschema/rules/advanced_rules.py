"""
Advanced Transformation Rules

This module contains advanced transformation rules for OWL constructs.
"""

from typing import Any, Dict, List, Optional
from ..visitor import TransformationRule
from ..model import OntologyModel, OntologyClass
from ..builder import ReferenceResolver


class EnumerationToEnumRule(TransformationRule):
    """Transform OWL enumerations (oneOf) to JSON Schema enum."""
    
    def visit_class(self, owl_class: OntologyClass) -> Dict[str, Any]:
        """Check if a class is defined as an enumeration."""
        if not self.is_enabled():
            return None
        
        # This would need to be detected during parsing
        # For now, we'll check annotations for a special marker
        if "enumeration" in owl_class.annotations:
            values = owl_class.annotations.get("enumeration", [])
            if values:
                use_labels = self.get_option("use_labels", True)
                
                if use_labels:
                    # Try to use labels if available
                    enum_values = []
                    for value in values:
                        # In a real implementation, we'd look up the label for each individual
                        enum_values.append(value)
                    return {"enum": enum_values}
                else:
                    # Use URIs directly
                    return {"enum": values}
        
        return None


class UnionToAnyOfRule(TransformationRule):
    """Transform OWL unionOf to JSON Schema anyOf."""
    
    def visit_class(self, owl_class: OntologyClass) -> Dict[str, Any]:
        """Check if a class is defined as a union."""
        if not self.is_enabled():
            return None
        
        # Check if the class has union information in annotations
        # In a real implementation, this would be parsed from the OWL
        if "unionOf" in owl_class.annotations:
            union_classes = owl_class.annotations.get("unionOf", [])
            if union_classes:
                resolver = ReferenceResolver()
                any_of = []
                
                for class_uri in union_classes:
                    class_name = self._get_class_name(class_uri)
                    any_of.append(resolver.create_ref(class_name))
                
                if any_of:
                    return {"anyOf": any_of}
        
        return None
    
    def _get_class_name(self, uri: str) -> str:
        """Extract class name from URI."""
        if '#' in uri:
            return uri.split('#')[-1]
        elif '/' in uri:
            return uri.split('/')[-1]
        return uri


class IntersectionToAllOfRule(TransformationRule):
    """Transform OWL intersectionOf to JSON Schema allOf."""
    
    def visit_class(self, owl_class: OntologyClass) -> Dict[str, Any]:
        """Check if a class is defined as an intersection."""
        if not self.is_enabled():
            return None
        
        # Check if the class has intersection information in annotations
        # In a real implementation, this would be parsed from the OWL
        if "intersectionOf" in owl_class.annotations:
            intersection_classes = owl_class.annotations.get("intersectionOf", [])
            if intersection_classes:
                resolver = ReferenceResolver()
                all_of = []
                
                for class_uri in intersection_classes:
                    class_name = self._get_class_name(class_uri)
                    all_of.append(resolver.create_ref(class_name))
                
                if all_of:
                    return {"allOf": all_of}
        
        return None
    
    def _get_class_name(self, uri: str) -> str:
        """Extract class name from URI."""
        if '#' in uri:
            return uri.split('#')[-1]
        elif '/' in uri:
            return uri.split('/')[-1]
        return uri


class ComplementToNotRule(TransformationRule):
    """Transform OWL complementOf to JSON Schema not."""
    
    def visit_class(self, owl_class: OntologyClass) -> Dict[str, Any]:
        """Check if a class is defined as a complement."""
        if not self.is_enabled():
            return None
        
        # Check if the class has complement information in annotations
        # In a real implementation, this would be parsed from the OWL
        if "complementOf" in owl_class.annotations:
            complement_class = owl_class.annotations.get("complementOf")
            if complement_class:
                resolver = ReferenceResolver()
                class_name = self._get_class_name(complement_class)
                
                return {"not": resolver.create_ref(class_name)}
        
        return None
    
    def _get_class_name(self, uri: str) -> str:
        """Extract class name from URI."""
        if '#' in uri:
            return uri.split('#')[-1]
        elif '/' in uri:
            return uri.split('/')[-1]
        return uri


class EquivalentClassesRule(TransformationRule):
    """Handle OWL equivalent classes."""
    
    def visit_ontology(self, ontology: OntologyModel) -> Dict[str, Any]:
        """Process equivalent class relationships."""
        if not self.is_enabled():
            return None
        
        equivalences = {}
        
        for owl_class in ontology.classes:
            if owl_class.equivalent_classes:
                class_name = self._get_class_name(owl_class.uri)
                
                # Create a shared definition for equivalent classes
                for equiv_uri in owl_class.equivalent_classes:
                    equiv_name = self._get_class_name(equiv_uri)
                    
                    # Store the equivalence relationship
                    if class_name not in equivalences:
                        equivalences[class_name] = []
                    equivalences[class_name].append(equiv_name)
        
        if equivalences:
            # Create shared definitions
            shared_definitions = {}
            processed = set()
            
            for class_name, equiv_classes in equivalences.items():
                if class_name not in processed:
                    # Create a group of equivalent classes
                    group = [class_name] + equiv_classes
                    group_name = f"_shared_{class_name}"
                    
                    # Mark all as processed
                    for name in group:
                        processed.add(name)
                    
                    # Create references for all equivalent classes
                    for name in group:
                        shared_definitions[name] = {"$ref": f"#/definitions/{group_name}"}
            
            return {"equivalent_definitions": shared_definitions} if shared_definitions else None
        
        return None
    
    def _get_class_name(self, uri: str) -> str:
        """Extract class name from URI."""
        if '#' in uri:
            return uri.split('#')[-1]
        elif '/' in uri:
            return uri.split('/')[-1]
        return uri


class DisjointClassesRule(TransformationRule):
    """Handle OWL disjoint classes."""
    
    def visit_ontology(self, ontology: OntologyModel) -> Dict[str, Any]:
        """Process disjoint class relationships."""
        if not self.is_enabled():
            return None
        
        disjoint_groups = []
        
        for owl_class in ontology.classes:
            if owl_class.disjoint_with:
                class_name = self._get_class_name(owl_class.uri)
                
                for disjoint_uri in owl_class.disjoint_with:
                    disjoint_name = self._get_class_name(disjoint_uri)
                    
                    # Create a disjoint group
                    group = sorted([class_name, disjoint_name])
                    if group not in disjoint_groups:
                        disjoint_groups.append(group)
        
        if disjoint_groups:
            # In JSON Schema, we can't directly express disjointness
            # We can add it as metadata or use custom validation
            enforcement = self.get_option("enforcement", "metadata")
            
            if enforcement == "metadata":
                # Add as metadata comment
                return {
                    "disjoint_metadata": {
                        "$comment": f"Disjoint class groups: {disjoint_groups}"
                    }
                }
            elif enforcement == "oneOf":
                # Create oneOf constraints where applicable
                # This is complex and would need more sophisticated logic
                return {
                    "disjoint_constraints": {
                        "type": "oneOf_constraints",
                        "groups": disjoint_groups
                    }
                }
        
        return None
    
    def _get_class_name(self, uri: str) -> str:
        """Extract class name from URI."""
        if '#' in uri:
            return uri.split('#')[-1]
        elif '/' in uri:
            return uri.split('/')[-1]
        return uri
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
    
    def visit_ontology(self, ontology: OntologyModel) -> Dict[str, Any]:
        """Process all classes in the ontology for enumerations."""
        if not self.is_enabled():
            return None
        
        enum_updates = {}
        
        for owl_class in ontology.classes:
            if "enumeration" in owl_class.annotations:
                class_name = self._get_class_name(owl_class.uri)
                enum_schema = self._create_enum_schema(owl_class)
                if enum_schema:
                    enum_updates[class_name] = enum_schema
        
        return {"enum_updates": enum_updates} if enum_updates else None
    
    def visit_class(self, owl_class: OntologyClass) -> Dict[str, Any]:
        """Check if a class is defined as an enumeration."""
        if not self.is_enabled():
            return None
        
        # Check if the class has enumeration values in its annotations
        if "enumeration" in owl_class.annotations:
            return self._create_enum_schema(owl_class)
        
        return None
    
    def _create_enum_schema(self, owl_class: OntologyClass) -> Dict[str, Any]:
        """Create an enum schema for a class."""
        values = owl_class.annotations.get("enumeration", [])
        if not values:
            return None
        
        # Create the enum schema
        schema = {
            "type": "string",
            "enum": values
        }
        
        # Add title from label if available
        label = owl_class.get_label(self.get_option("language", "en"))
        if label:
            schema["title"] = label
        
        # Add description from comment if available
        comment = owl_class.get_comment(self.get_option("language", "en"))
        if comment:
            schema["description"] = comment
        
        return schema
    
    def _get_class_name(self, uri: str) -> str:
        """Extract class name from URI."""
        if '#' in uri:
            return uri.split('#')[-1]
        elif '/' in uri:
            return uri.split('/')[-1]
        return uri


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
        
        # Build a map of disjoint groups
        disjoint_groups = {}  # class -> set of disjoint classes
        
        for owl_class in ontology.classes:
            if owl_class.disjoint_with:
                class_name = self._get_class_name(owl_class.uri)
                
                if class_name not in disjoint_groups:
                    disjoint_groups[class_name] = set()
                
                for disjoint_uri in owl_class.disjoint_with:
                    disjoint_name = self._get_class_name(disjoint_uri)
                    disjoint_groups[class_name].add(disjoint_name)
                    
                    # Make relationship bidirectional
                    if disjoint_name not in disjoint_groups:
                        disjoint_groups[disjoint_name] = set()
                    disjoint_groups[disjoint_name].add(class_name)
        
        if not disjoint_groups:
            return None
        
        # Find disjoint classes that share a common superclass
        # These should be transformed into oneOf in the superclass
        disjoint_unions = {}
        
        for owl_class in ontology.classes:
            class_name = self._get_class_name(owl_class.uri)
            
            # Check if this class has subclasses that are disjoint with each other
            subclasses = []
            for sub_class in ontology.classes:
                if class_name != self._get_class_name(sub_class.uri) and \
                   any(self._get_class_name(sc) == class_name for sc in sub_class.super_classes):
                    subclasses.append(self._get_class_name(sub_class.uri))
            
            if len(subclasses) >= 2:
                # Check if the subclasses are disjoint
                all_disjoint = True
                for i, sub1 in enumerate(subclasses):
                    for sub2 in subclasses[i+1:]:
                        if sub1 not in disjoint_groups.get(sub2, set()):
                            all_disjoint = False
                            break
                    if not all_disjoint:
                        break
                
                if all_disjoint:
                    # Create a oneOf schema for this superclass
                    resolver = ReferenceResolver()
                    one_of = []
                    for subclass in subclasses:
                        one_of.append(resolver.create_ref(subclass))
                    
                    disjoint_unions[class_name] = {
                        "oneOf": one_of,
                        "title": class_name,
                        "description": f"Disjoint union of: {', '.join(subclasses)}"
                    }
        
        if disjoint_unions:
            return {"disjoint_unions": disjoint_unions}
        
        # Fallback to metadata if no disjoint unions found
        groups_list = []
        processed = set()
        for class_name, disjoints in disjoint_groups.items():
            if class_name not in processed:
                group = sorted([class_name] + list(disjoints))
                groups_list.append(group)
                for c in group:
                    processed.add(c)
        
        if groups_list:
            return {
                "disjoint_metadata": {
                    "$comment": f"Disjoint class groups: {groups_list}"
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
"""
Annotation Transformation Rules

This module contains transformation rules for OWL annotations.
"""

from typing import Any, Dict, Optional
from ..visitor import TransformationRule
from ..model import (
    OntologyModel,
    OntologyClass,
    ObjectProperty,
    DatatypeProperty
)


class LabelsToTitlesRule(TransformationRule):
    """Transform RDFS labels to JSON Schema titles."""
    
    def visit_ontology(self, ontology: OntologyModel) -> Dict[str, Any]:
        """Process labels for all elements in the ontology."""
        if not self.is_enabled():
            return None
        
        updates = {}
        language = self.get_option("language", "en")
        
        # Process classes
        for owl_class in ontology.classes:
            label = owl_class.get_label(language)
            if label:
                class_name = self._get_name(owl_class.uri)
                updates[f"class:{class_name}"] = {"title": label}
        
        # Process object properties
        for property in ontology.object_properties:
            label = property.get_label(language)
            if label:
                prop_name = self._get_name(property.uri)
                updates[f"property:{prop_name}"] = {"title": label}
        
        # Process datatype properties
        for property in ontology.datatype_properties:
            label = property.get_label(language)
            if label:
                prop_name = self._get_name(property.uri)
                updates[f"property:{prop_name}"] = {"title": label}
        
        return {"title_updates": updates} if updates else None
    
    def visit_class(self, owl_class: OntologyClass) -> Dict[str, Any]:
        """Add title to a class schema from its label."""
        if not self.is_enabled():
            return None
        
        language = self.get_option("language", "en")
        label = owl_class.get_label(language)
        
        if label:
            return {"title": label}
        
        return None
    
    def visit_object_property(self, property: ObjectProperty) -> Dict[str, Any]:
        """Add title to a property schema from its label."""
        if not self.is_enabled():
            return None
        
        language = self.get_option("language", "en")
        label = property.get_label(language)
        
        if label:
            return {"title": label}
        
        return None
    
    def visit_datatype_property(self, property: DatatypeProperty) -> Dict[str, Any]:
        """Add title to a property schema from its label."""
        if not self.is_enabled():
            return None
        
        language = self.get_option("language", "en")
        label = property.get_label(language)
        
        if label:
            return {"title": label}
        
        return None
    
    def _get_name(self, uri: str) -> str:
        """Extract name from URI."""
        if '#' in uri:
            return uri.split('#')[-1]
        elif '/' in uri:
            return uri.split('/')[-1]
        return uri


class CommentsToDescriptionsRule(TransformationRule):
    """Transform RDFS comments to JSON Schema descriptions."""
    
    def visit_ontology(self, ontology: OntologyModel) -> Dict[str, Any]:
        """Process comments for all elements in the ontology."""
        if not self.is_enabled():
            return None
        
        updates = {}
        language = self.get_option("language", "en")
        
        # Process classes
        for owl_class in ontology.classes:
            comment = owl_class.get_comment(language)
            if comment:
                class_name = self._get_name(owl_class.uri)
                updates[f"class:{class_name}"] = {"description": comment}
        
        # Process object properties
        for property in ontology.object_properties:
            comment = property.get_comment(language)
            if comment:
                prop_name = self._get_name(property.uri)
                updates[f"property:{prop_name}"] = {"description": comment}
        
        # Process datatype properties
        for property in ontology.datatype_properties:
            comment = property.get_comment(language)
            if comment:
                prop_name = self._get_name(property.uri)
                updates[f"property:{prop_name}"] = {"description": comment}
        
        return {"description_updates": updates} if updates else None
    
    def visit_class(self, owl_class: OntologyClass) -> Dict[str, Any]:
        """Add description to a class schema from its comment."""
        if not self.is_enabled():
            return None
        
        language = self.get_option("language", "en")
        comment = owl_class.get_comment(language)
        
        if comment:
            return {"description": comment}
        
        return None
    
    def visit_object_property(self, property: ObjectProperty) -> Dict[str, Any]:
        """Add description to a property schema from its comment."""
        if not self.is_enabled():
            return None
        
        language = self.get_option("language", "en")
        comment = property.get_comment(language)
        
        if comment:
            return {"description": comment}
        
        return None
    
    def visit_datatype_property(self, property: DatatypeProperty) -> Dict[str, Any]:
        """Add description to a property schema from its comment."""
        if not self.is_enabled():
            return None
        
        language = self.get_option("language", "en")
        comment = property.get_comment(language)
        
        if comment:
            return {"description": comment}
        
        return None
    
    def _get_name(self, uri: str) -> str:
        """Extract name from URI."""
        if '#' in uri:
            return uri.split('#')[-1]
        elif '/' in uri:
            return uri.split('/')[-1]
        return uri


class AnnotationsToMetadataRule(TransformationRule):
    """Transform other OWL annotations to JSON Schema metadata."""
    
    def visit_ontology(self, ontology: OntologyModel) -> Dict[str, Any]:
        """Process annotations for all elements in the ontology."""
        if not self.is_enabled():
            return None
        
        updates = {}
        include_in_comment = self.get_option("include_in_comment", True)
        custom_field = self.get_option("custom_field", None)
        
        # Process classes
        for owl_class in ontology.classes:
            if owl_class.annotations:
                class_name = self._get_name(owl_class.uri)
                metadata = self._format_annotations(owl_class.annotations)
                
                if metadata:
                    if include_in_comment:
                        updates[f"class:{class_name}"] = {
                            "$comment": f"Annotations: {metadata}"
                        }
                    elif custom_field:
                        updates[f"class:{class_name}"] = {
                            custom_field: metadata
                        }
                    else:
                        updates[f"class:{class_name}"] = metadata
        
        # Process object properties
        for property in ontology.object_properties:
            if property.annotations:
                prop_name = self._get_name(property.uri)
                metadata = self._format_annotations(property.annotations)
                
                if metadata:
                    if include_in_comment:
                        updates[f"property:{prop_name}"] = {
                            "$comment": f"Annotations: {metadata}"
                        }
                    elif custom_field:
                        updates[f"property:{prop_name}"] = {
                            custom_field: metadata
                        }
                    else:
                        updates[f"property:{prop_name}"] = metadata
        
        # Process datatype properties
        for property in ontology.datatype_properties:
            if property.annotations:
                prop_name = self._get_name(property.uri)
                metadata = self._format_annotations(property.annotations)
                
                if metadata:
                    if include_in_comment:
                        updates[f"property:{prop_name}"] = {
                            "$comment": f"Annotations: {metadata}"
                        }
                    elif custom_field:
                        updates[f"property:{prop_name}"] = {
                            custom_field: metadata
                        }
                    else:
                        updates[f"property:{prop_name}"] = metadata
        
        return {"metadata_updates": updates} if updates else None
    
    def visit_class(self, owl_class: OntologyClass) -> Dict[str, Any]:
        """Add metadata to a class schema from its annotations."""
        if not self.is_enabled():
            return None
        
        if not owl_class.annotations:
            return None
        
        include_in_comment = self.get_option("include_in_comment", True)
        custom_field = self.get_option("custom_field", None)
        
        metadata = self._format_annotations(owl_class.annotations)
        
        if metadata:
            if include_in_comment:
                return {"$comment": f"Annotations: {metadata}"}
            elif custom_field:
                return {custom_field: metadata}
            else:
                return metadata
        
        return None
    
    def visit_object_property(self, property: ObjectProperty) -> Dict[str, Any]:
        """Add metadata to a property schema from its annotations."""
        if not self.is_enabled():
            return None
        
        if not property.annotations:
            return None
        
        include_in_comment = self.get_option("include_in_comment", True)
        custom_field = self.get_option("custom_field", None)
        
        metadata = self._format_annotations(property.annotations)
        
        if metadata:
            if include_in_comment:
                return {"$comment": f"Annotations: {metadata}"}
            elif custom_field:
                return {custom_field: metadata}
            else:
                return metadata
        
        return None
    
    def visit_datatype_property(self, property: DatatypeProperty) -> Dict[str, Any]:
        """Add metadata to a property schema from its annotations."""
        if not self.is_enabled():
            return None
        
        if not property.annotations:
            return None
        
        include_in_comment = self.get_option("include_in_comment", True)
        custom_field = self.get_option("custom_field", None)
        
        metadata = self._format_annotations(property.annotations)
        
        if metadata:
            if include_in_comment:
                return {"$comment": f"Annotations: {metadata}"}
            elif custom_field:
                return {custom_field: metadata}
            else:
                return metadata
        
        return None
    
    def _format_annotations(self, annotations: Dict[str, Any]) -> Any:
        """Format annotations for inclusion in JSON Schema."""
        format_style = self.get_option("format_style", "dict")
        
        if format_style == "string":
            # Format as a string
            items = []
            for key, value in annotations.items():
                items.append(f"{key}: {value}")
            return "; ".join(items)
        elif format_style == "dict":
            # Return as dictionary
            return annotations
        else:
            # Default to dictionary
            return annotations
    
    def _get_name(self, uri: str) -> str:
        """Extract name from URI."""
        if '#' in uri:
            return uri.split('#')[-1]
        elif '/' in uri:
            return uri.split('/')[-1]
        return uri
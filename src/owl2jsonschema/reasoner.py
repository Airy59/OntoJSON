"""
A-box validation using OWL-RL reasoner for consistency checking.
"""

from typing import List, Dict, Any, Optional, Tuple
from rdflib import Graph, Namespace, URIRef, Literal, RDF, RDFS, OWL
import owlrl


class ABoxValidator:
    """Validator for checking A-box consistency against T-box using OWL-RL."""
    
    def __init__(self, tbox_path: Optional[str] = None, tbox_graph: Optional[Graph] = None):
        """
        Initialize the validator with T-box.
        
        Args:
            tbox_path: Path to T-box ontology file
            tbox_graph: Pre-loaded T-box graph (alternative to path)
        """
        self.tbox_graph = Graph()
        
        if tbox_graph:
            self.tbox_graph = tbox_graph
        elif tbox_path:
            self.tbox_graph.parse(tbox_path)
        
        self.combined_graph = Graph()
        self.inconsistencies = []
        self.is_consistent = True
    
    def validate(self, abox_graph: Graph) -> Tuple[bool, List[Dict[str, Any]]]:
        """
        Validate A-box against T-box for consistency.
        
        Args:
            abox_graph: The A-box graph to validate
            
        Returns:
            Tuple of (is_consistent, list_of_issues)
        """
        # Reset state
        self.inconsistencies = []
        self.is_consistent = True
        
        # Combine T-box and A-box
        self.combined_graph = Graph()
        for triple in self.tbox_graph:
            self.combined_graph.add(triple)
        for triple in abox_graph:
            self.combined_graph.add(triple)
        
        # Apply OWL-RL reasoning
        try:
            # Create OWL-RL closure
            owlrl.DeductiveClosure(
                owlrl.OWLRL_Semantics,
                rdfs_closure=True,
                axiomatic_triples=True,
                datatype_axioms=True
            ).expand(self.combined_graph)
            
            # Check for inconsistencies
            self._check_inconsistencies()
            
        except Exception as e:
            self.is_consistent = False
            self.inconsistencies.append({
                'type': 'reasoning_error',
                'message': f'Reasoner error: {str(e)}'
            })
        
        return self.is_consistent, self.inconsistencies
    
    def _check_inconsistencies(self):
        """Check for various types of inconsistencies in the combined graph."""
        
        # Check for owl:Nothing instances (indicates inconsistency)
        self._check_nothing_instances()
        
        # Check for disjoint class violations
        self._check_disjoint_violations()
        
        # Check for functional property violations
        self._check_functional_property_violations()
        
        # Check for cardinality violations
        self._check_cardinality_violations()
        
        # Check for domain/range violations
        self._check_domain_range_violations()
    
    def _check_nothing_instances(self):
        """Check if any individual is typed as owl:Nothing (contradiction)."""
        for subj in self.combined_graph.subjects(RDF.type, OWL.Nothing):
            if isinstance(subj, URIRef):
                self.is_consistent = False
                self.inconsistencies.append({
                    'type': 'nothing_instance',
                    'individual': str(subj),
                    'message': f'Individual {self._get_local_name(str(subj))} is typed as owl:Nothing (contradiction)'
                })
    
    def _check_disjoint_violations(self):
        """Check for violations of disjoint class constraints."""
        # Get all individuals
        individuals = set()
        for s in self.combined_graph.subjects(RDF.type, OWL.NamedIndividual):
            individuals.add(s)
        
        # For each individual, check if it belongs to disjoint classes
        for ind in individuals:
            types = list(self.combined_graph.objects(ind, RDF.type))
            class_types = [t for t in types if t != OWL.NamedIndividual and t != OWL.Thing]
            
            # Check each pair of types for disjointness
            for i, class1 in enumerate(class_types):
                for class2 in class_types[i+1:]:
                    if self._are_disjoint(class1, class2):
                        self.is_consistent = False
                        self.inconsistencies.append({
                            'type': 'disjoint_violation',
                            'individual': str(ind),
                            'classes': [str(class1), str(class2)],
                            'message': f'Individual {self._get_local_name(str(ind))} belongs to disjoint classes: {self._get_local_name(str(class1))} and {self._get_local_name(str(class2))}'
                        })
    
    def _check_functional_property_violations(self):
        """Check for functional property violations (more than one value)."""
        # Get all functional properties
        func_props = set()
        for prop in self.combined_graph.subjects(RDF.type, OWL.FunctionalProperty):
            func_props.add(prop)
        
        # Check each functional property
        for prop in func_props:
            # Group by subject
            subjects_values = {}
            for s, p, o in self.combined_graph.triples((None, prop, None)):
                if s not in subjects_values:
                    subjects_values[s] = []
                subjects_values[s].append(o)
            
            # Check for multiple values
            for subj, values in subjects_values.items():
                if len(values) > 1:
                    self.is_consistent = False
                    self.inconsistencies.append({
                        'type': 'functional_violation',
                        'subject': str(subj),
                        'property': str(prop),
                        'values': [str(v) for v in values],
                        'message': f'Functional property {self._get_local_name(str(prop))} has {len(values)} values for {self._get_local_name(str(subj))}'
                    })
    
    def _check_cardinality_violations(self):
        """Check for cardinality restriction violations."""
        # This would require parsing OWL restrictions which is complex
        # For now, we'll rely on OWL-RL's built-in checking
        # OWL-RL will add owl:Nothing if cardinality is violated
        pass
    
    def _check_domain_range_violations(self):
        """Check for domain and range violations."""
        # OWL-RL should infer the correct types based on domain/range
        # If there's a contradiction, it will result in owl:Nothing
        # So this is handled by _check_nothing_instances
        pass
    
    def _are_disjoint(self, class1: URIRef, class2: URIRef) -> bool:
        """Check if two classes are disjoint."""
        # Direct disjointness
        if (class1, OWL.disjointWith, class2) in self.combined_graph:
            return True
        if (class2, OWL.disjointWith, class1) in self.combined_graph:
            return True
        
        # Check AllDisjointClasses
        for disjoint_node in self.combined_graph.subjects(RDF.type, OWL.AllDisjointClasses):
            members = list(self.combined_graph.objects(disjoint_node, OWL.members))
            for member_list in members:
                class_list = self._parse_rdf_list(member_list)
                if class1 in class_list and class2 in class_list:
                    return True
        
        return False
    
    def _parse_rdf_list(self, list_node) -> List[URIRef]:
        """Parse an RDF list into a Python list."""
        result = []
        current = list_node
        while current and current != RDF.nil:
            # Get first element
            first = self.combined_graph.value(current, RDF.first)
            if first:
                result.append(first)
            # Move to rest
            current = self.combined_graph.value(current, RDF.rest)
        return result
    
    def _get_local_name(self, uri: str) -> str:
        """Extract local name from URI for better readability."""
        if '#' in uri:
            return uri.split('#')[-1]
        elif '/' in uri:
            return uri.split('/')[-1]
        return uri
    
    def get_validation_report(self) -> str:
        """
        Get a human-readable validation report.
        
        Returns:
            String report of validation results
        """
        report = []
        report.append("=" * 50)
        report.append("A-BOX VALIDATION REPORT")
        report.append("=" * 50)
        report.append("")
        
        if self.is_consistent:
            report.append("✅ CONSISTENT: The A-box is consistent with the T-box")
        else:
            report.append("❌ INCONSISTENT: The A-box violates T-box constraints")
            report.append("")
            report.append("Issues found:")
            report.append("-" * 30)
            
            # Group issues by type
            issues_by_type = {}
            for issue in self.inconsistencies:
                issue_type = issue['type']
                if issue_type not in issues_by_type:
                    issues_by_type[issue_type] = []
                issues_by_type[issue_type].append(issue)
            
            # Report each type
            type_names = {
                'nothing_instance': 'Contradiction (owl:Nothing)',
                'disjoint_violation': 'Disjoint Class Violation',
                'functional_violation': 'Functional Property Violation',
                'reasoning_error': 'Reasoning Error'
            }
            
            for issue_type, issues in issues_by_type.items():
                report.append("")
                report.append(f"📍 {type_names.get(issue_type, issue_type)}:")
                for issue in issues:
                    report.append(f"   • {issue['message']}")
        
        report.append("")
        report.append("=" * 50)
        
        return "\n".join(report)
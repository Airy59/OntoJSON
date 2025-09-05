#!/usr/bin/env python3
"""
Community Namer - Derives meaningful names for community partitions
based on their contents.
"""

import json
import re
from pathlib import Path
from collections import Counter
from typing import Dict, List, Tuple
from rdflib import Graph, URIRef, RDFS, RDF, OWL


class CommunityNamer:
    """Analyzes community partitions and derives meaningful names."""
    
    def __init__(self, modules_dir: str):
        self.modules_dir = Path(modules_dir)
        self.community_dir = self.modules_dir / "community"
        self.index_file = self.community_dir / "index.json"
        self.community_names = {}
        
    def extract_keywords_from_uri(self, uri: str) -> List[str]:
        """Extract meaningful keywords from a URI."""
        # Get the local part of the URI
        if '#' in uri:
            local = uri.split('#')[-1]
        elif '/' in uri:
            local = uri.split('/')[-1]
        else:
            local = uri
        
        # Split camelCase and snake_case
        words = re.findall(r'[A-Z][a-z]+|[a-z]+|[A-Z]+(?=[A-Z][a-z]|\b)', local)
        return [w.lower() for w in words if len(w) > 2]
    
    def analyze_community(self, community_file: Path) -> Tuple[List[str], int]:
        """Analyze a community file and extract key concepts."""
        g = Graph()
        g.parse(community_file, format='turtle')
        
        # Collect all keywords from entities
        keywords = []
        entity_count = 0
        
        # Get classes
        for s in g.subjects(RDF.type, OWL.Class):
            if isinstance(s, URIRef):
                keywords.extend(self.extract_keywords_from_uri(str(s)))
                entity_count += 1
                
                # Also check labels
                for label in g.objects(s, RDFS.label):
                    words = str(label).lower().split()
                    keywords.extend([w for w in words if len(w) > 2])
        
        # Get properties
        for prop_type in [OWL.ObjectProperty, OWL.DatatypeProperty]:
            for s in g.subjects(RDF.type, prop_type):
                if isinstance(s, URIRef):
                    keywords.extend(self.extract_keywords_from_uri(str(s)))
                    entity_count += 1
        
        return keywords, entity_count
    
    def derive_name_from_keywords(self, keywords: List[str], entity_count: int) -> str:
        """Derive a meaningful name from keyword frequency."""
        if not keywords:
            return f"small_entities_{entity_count}"
        
        # Count keyword frequency
        keyword_freq = Counter(keywords)
        
        # Domain-specific keyword groupings
        domain_mappings = {
            'infrastructure': ['track', 'station', 'signal', 'infrastructure', 'tunnel', 
                             'bridge', 'platform', 'route', 'line', 'network'],
            'vehicle': ['vehicle', 'train', 'wagon', 'locomotive', 'car', 'rolling', 
                       'axle', 'wheel', 'brake', 'engine', 'motor'],
            'electrical': ['electrical', 'voltage', 'power', 'energy', 'contact', 
                          'pantograph', 'current', 'phase', 'wire', 'catenary'],
            'safety': ['safety', 'hazard', 'risk', 'accident', 'emergency', 'protection',
                      'detection', 'warning', 'alarm'],
            'signaling': ['signal', 'etcs', 'ertms', 'control', 'communication', 
                         'radio', 'balise', 'message'],
            'operational': ['operation', 'timetable', 'schedule', 'movement', 'journey',
                           'speed', 'departure', 'arrival', 'delay'],
            'technical': ['technical', 'specification', 'parameter', 'limit', 'maximum',
                         'minimum', 'capability', 'performance', 'requirement'],
            'geographic': ['country', 'border', 'location', 'position', 'coordinate',
                          'point', 'area', 'zone', 'region'],
            'administrative': ['organization', 'document', 'certificate', 'authority',
                              'regulation', 'compliance', 'approval', 'license'],
            'measurement': ['load', 'weight', 'length', 'width', 'height', 'distance',
                           'radius', 'gauge', 'dimension', 'impedance']
        }
        
        # Check which domain has the most matches
        domain_scores = {}
        for domain, domain_keywords in domain_mappings.items():
            score = sum(keyword_freq.get(kw, 0) for kw in domain_keywords)
            if score > 0:
                domain_scores[domain] = score
        
        # Get top 3 most frequent keywords
        top_keywords = [kw for kw, _ in keyword_freq.most_common(3)]
        
        # Generate name based on domain and top keywords
        if domain_scores:
            # Get the best matching domain
            best_domain = max(domain_scores, key=domain_scores.get)
            
            # Find the most specific keyword from that domain
            domain_kws = domain_mappings[best_domain]
            specific_kw = next((kw for kw in top_keywords if kw in domain_kws), None)
            
            if specific_kw and specific_kw != best_domain:
                return f"{best_domain}_{specific_kw}"
            else:
                # Add a distinguishing keyword if available
                other_kw = next((kw for kw in top_keywords if kw not in domain_kws), None)
                if other_kw:
                    return f"{best_domain}_{other_kw}"
                else:
                    return best_domain
        else:
            # No clear domain, use top keywords
            if len(top_keywords) >= 2:
                return f"{top_keywords[0]}_{top_keywords[1]}"
            elif top_keywords:
                return top_keywords[0]
            else:
                return f"entities_{entity_count}"
    
    def name_all_communities(self) -> Dict[str, str]:
        """Analyze all communities and generate meaningful names."""
        print("Analyzing community partitions to derive names...")
        
        # Get all community files
        community_files = sorted(self.community_dir.glob("community_*.ttl"))
        
        for comm_file in community_files:
            comm_id = comm_file.stem  # e.g., "community_2"
            
            print(f"  Analyzing {comm_id}...")
            keywords, entity_count = self.analyze_community(comm_file)
            
            # Derive a meaningful name
            meaningful_name = self.derive_name_from_keywords(keywords, entity_count)
            
            # For very small communities (1-2 entities), try to be more specific
            if entity_count <= 2 and keywords:
                # Use the most specific keyword
                meaningful_name = '_'.join(keywords[:2]) if len(keywords) > 1 else keywords[0]
            
            self.community_names[comm_id] = meaningful_name
            print(f"    -> {meaningful_name} ({entity_count} entities)")
        
        return self.community_names
    
    def save_named_index(self) -> None:
        """Save an index with meaningful names."""
        # Load original index
        with open(self.index_file, 'r') as f:
            index = json.load(f)
        
        # Add meaningful names
        index['named_partitions'] = self.community_names
        
        # Save enhanced index
        enhanced_index_file = self.community_dir / "named_index.json"
        with open(enhanced_index_file, 'w') as f:
            json.dump(index, f, indent=2)
        
        print(f"\nSaved enhanced index to {enhanced_index_file}")
    
    def create_name_mapping_report(self) -> None:
        """Create a markdown report with the name mappings."""
        report_file = self.modules_dir / "COMMUNITY_NAMES.md"
        
        # Load the partition summary to get entity counts
        summary_file = self.modules_dir / "partitioning_summary.json"
        with open(summary_file, 'r') as f:
            summary = json.load(f)
        
        community_sizes = summary['strategies']['community']['partitions']
        
        # Group communities by size
        large = {k: v for k, v in community_sizes.items() if v > 50}
        medium = {k: v for k, v in community_sizes.items() if 10 <= v <= 50}
        small = {k: v for k, v in community_sizes.items() if v < 10}
        
        with open(report_file, 'w') as f:
            f.write("# Community Partition Names\n\n")
            f.write("## Name Mappings\n\n")
            
            f.write("### Large Communities (>50 entities)\n\n")
            f.write("| Original ID | Entities | Derived Name | Description |\n")
            f.write("|------------|----------|--------------|-------------|\n")
            for comm_id in sorted(large.keys(), key=lambda x: large[x], reverse=True):
                name = self.community_names.get(comm_id, "unknown")
                count = large[comm_id]
                f.write(f"| {comm_id} | {count} | {name} | ")
                f.write(self.get_description(name))
                f.write(" |\n")
            
            f.write("\n### Medium Communities (10-50 entities)\n\n")
            f.write("| Original ID | Entities | Derived Name | Description |\n")
            f.write("|------------|----------|--------------|-------------|\n")
            for comm_id in sorted(medium.keys(), key=lambda x: medium[x], reverse=True):
                name = self.community_names.get(comm_id, "unknown")
                count = medium[comm_id]
                f.write(f"| {comm_id} | {count} | {name} | ")
                f.write(self.get_description(name))
                f.write(" |\n")
            
            f.write("\n### Small Communities (<10 entities)\n\n")
            f.write("*Note: Small communities often represent specific technical concepts or edge cases*\n\n")
            f.write("| Original ID | Entities | Derived Name |\n")
            f.write("|------------|----------|--------------|")
            for comm_id in sorted(small.keys()):
                name = self.community_names.get(comm_id, "unknown")
                count = small[comm_id]
                f.write(f"\n| {comm_id} | {count} | {name} |")
            
            f.write("\n\n## Naming Methodology\n\n")
            f.write("Names are derived by:\n")
            f.write("1. Analyzing all entities in each community\n")
            f.write("2. Extracting keywords from URIs and labels\n")
            f.write("3. Identifying dominant domain themes\n")
            f.write("4. Combining domain and specific terms for uniqueness\n\n")
            f.write("*Generated by Community Namer*\n")
        
        print(f"Created naming report at {report_file}")
    
    def get_description(self, name: str) -> str:
        """Get a description based on the derived name."""
        descriptions = {
            'infrastructure': 'Core railway infrastructure components',
            'vehicle': 'Vehicle and rolling stock specifications',
            'electrical': 'Electrical systems and power supply',
            'safety': 'Safety systems and protocols',
            'signaling': 'Signaling and control systems',
            'operational': 'Operational procedures and management',
            'technical': 'Technical specifications and parameters',
            'geographic': 'Geographic and location information',
            'administrative': 'Administrative and regulatory aspects',
            'measurement': 'Measurement and dimension specifications'
        }
        
        # Check if the name starts with a known domain
        for domain, desc in descriptions.items():
            if name.startswith(domain):
                return desc
        
        # Generic description
        if '_' in name:
            parts = name.split('_')
            return f"Concepts related to {' and '.join(parts)}"
        else:
            return f"Concepts related to {name}"


def main():
    # Path to the ERA ontology modules
    modules_dir = Path("../Ontologies/ERA_ontology_312_modules")
    
    if not modules_dir.exists():
        print(f"Error: Modules directory not found: {modules_dir}")
        return 1
    
    namer = CommunityNamer(modules_dir)
    
    # Generate names for all communities
    community_names = namer.name_all_communities()
    
    # Save enhanced index
    namer.save_named_index()
    
    # Create name mapping report
    namer.create_name_mapping_report()
    
    print(f"\nSuccessfully named {len(community_names)} communities")
    return 0


if __name__ == "__main__":
    exit(main())
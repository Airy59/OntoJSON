#!/usr/bin/env python3
"""
Semantic Partitioner for Ontologies

This script analyzes ontologies and partitions them into semantically coherent modules
based on various strategies including domain-based, hierarchical, and dependency-based approaches.
"""

import os
import json
import argparse
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from collections import defaultdict, deque
from datetime import datetime
import networkx as nx
from rdflib import Graph, Namespace, URIRef, RDF, RDFS, OWL
import community.community_louvain as community_louvain
import matplotlib.pyplot as plt


class SemanticPartitioner:
    """Analyzes and partitions ontologies into semantically coherent modules."""
    
    def __init__(self, input_file: str, output_dir: str = None, use_chunks: bool = False):
        self.input_file = Path(input_file)
        self.output_dir = Path(output_dir) if output_dir else self.input_file.parent / f"{self.input_file.stem}_modules"
        self.output_dir.mkdir(exist_ok=True)
        self.use_chunks = use_chunks
        
        # Initialize RDF graph
        self.graph = Graph()
        
        # Namespaces
        self.namespaces = {}
        
        # Analysis results
        self.classes = set()
        self.object_properties = set()
        self.datatype_properties = set()
        self.annotation_properties = set()
        self.individuals = set()
        
        # Relationships
        self.class_hierarchy = defaultdict(set)  # parent -> children
        self.property_domains = defaultdict(set)  # property -> domains
        self.property_ranges = defaultdict(set)   # property -> ranges
        self.class_properties = defaultdict(set)  # class -> properties
        
        # Dependency graph
        self.dependency_graph = nx.DiGraph()
        
        # Partitioning results
        self.partitions = {}
        self.partition_metrics = {}
        
    def load_ontology(self) -> None:
        """Load the ontology, using chunks if specified."""
        print(f"Loading ontology from {self.input_file}...")
        
        if self.use_chunks:
            # Check if chunks exist
            chunk_dir = self.input_file.parent / f"{self.input_file.stem}_chunks"
            if chunk_dir.exists():
                self._load_from_chunks(chunk_dir)
            else:
                print(f"No chunks found. Loading full file...")
                self._parse_with_format_detection()
        else:
            self._parse_with_format_detection()
        
        # Extract namespaces
        for prefix, namespace in self.graph.namespaces():
            self.namespaces[prefix] = namespace
        
        print(f"  - Loaded {len(self.graph)} triples")
        print(f"  - Found {len(self.namespaces)} namespaces")
    
    def _parse_with_format_detection(self) -> None:
        """Parse the ontology file with automatic format detection."""
        # Try different formats based on file extension
        if self.input_file.suffix.lower() == '.ttl':
            fmt = 'turtle'
        elif self.input_file.suffix.lower() == '.owl':
            fmt = 'xml'  # OWL files are typically in RDF/XML format
        elif self.input_file.suffix.lower() == '.rdf':
            fmt = 'xml'
        elif self.input_file.suffix.lower() == '.n3':
            fmt = 'n3'
        elif self.input_file.suffix.lower() == '.nt':
            fmt = 'nt'
        elif self.input_file.suffix.lower() == '.jsonld':
            fmt = 'json-ld'
        else:
            # Try to detect format from content
            with open(self.input_file, 'r', encoding='utf-8') as f:
                first_line = f.readline().strip()
                if first_line.startswith('<?xml'):
                    fmt = 'xml'
                elif first_line.startswith('@prefix') or first_line.startswith('@base'):
                    fmt = 'turtle'
                elif first_line.startswith('{'):
                    fmt = 'json-ld'
                else:
                    fmt = 'xml'  # Default to XML for OWL files
        
        print(f"  - Detected format: {fmt}")
        
        try:
            self.graph.parse(self.input_file, format=fmt)
        except Exception as e:
            print(f"  - Failed with {fmt} format, trying alternative formats...")
            # Try other formats
            for alt_fmt in ['xml', 'turtle', 'n3', 'nt']:
                if alt_fmt != fmt:
                    try:
                        self.graph = Graph()  # Reset graph
                        self.graph.parse(self.input_file, format=alt_fmt)
                        print(f"  - Successfully loaded with {alt_fmt} format")
                        break
                    except:
                        continue
            else:
                raise Exception(f"Could not parse {self.input_file} in any supported format")
    
    def _load_from_chunks(self, chunk_dir: Path) -> None:
        """Load ontology from pre-chunked files."""
        print(f"Loading from chunks in {chunk_dir}...")
        
        # Load header first
        header_file = chunk_dir / "00_header.ttl"
        if header_file.exists():
            self.graph.parse(header_file, format="turtle")
        
        # Load combined chunks
        combined_files = sorted(chunk_dir.glob("combined_*.ttl"))
        for i, chunk_file in enumerate(combined_files, 1):
            print(f"  - Loading chunk {i}/{len(combined_files)}: {chunk_file.name}")
            try:
                self.graph.parse(chunk_file, format="turtle")
            except Exception as e:
                print(f"    Warning: Error loading {chunk_file.name}: {e}")
    
    def analyze_structure(self) -> None:
        """Analyze the ontology structure."""
        print("Analyzing ontology structure...")
        
        # Extract classes
        for s in self.graph.subjects(RDF.type, OWL.Class):
            if not isinstance(s, URIRef):
                continue
            self.classes.add(s)
            self.dependency_graph.add_node(s, type='class')
        
        # Extract properties
        for s in self.graph.subjects(RDF.type, OWL.ObjectProperty):
            self.object_properties.add(s)
            self.dependency_graph.add_node(s, type='object_property')
        
        for s in self.graph.subjects(RDF.type, OWL.DatatypeProperty):
            self.datatype_properties.add(s)
            self.dependency_graph.add_node(s, type='datatype_property')
        
        for s in self.graph.subjects(RDF.type, OWL.AnnotationProperty):
            self.annotation_properties.add(s)
            self.dependency_graph.add_node(s, type='annotation_property')
        
        # Extract individuals
        for s in self.graph.subjects(RDF.type, OWL.NamedIndividual):
            self.individuals.add(s)
            self.dependency_graph.add_node(s, type='individual')
        
        # Analyze class hierarchy
        for s, o in self.graph.subject_objects(RDFS.subClassOf):
            if isinstance(s, URIRef) and isinstance(o, URIRef):
                self.class_hierarchy[o].add(s)
                self.dependency_graph.add_edge(s, o, type='subclass')
        
        # Analyze property domains and ranges
        for prop, domain in self.graph.subject_objects(RDFS.domain):
            if isinstance(prop, URIRef) and isinstance(domain, URIRef):
                self.property_domains[prop].add(domain)
                self.class_properties[domain].add(prop)
                self.dependency_graph.add_edge(prop, domain, type='domain')
        
        for prop, range_ in self.graph.subject_objects(RDFS.range):
            if isinstance(prop, URIRef) and isinstance(range_, URIRef):
                self.property_ranges[prop].add(range_)
                self.dependency_graph.add_edge(prop, range_, type='range')
        
        print(f"  - Classes: {len(self.classes)}")
        print(f"  - Object Properties: {len(self.object_properties)}")
        print(f"  - Datatype Properties: {len(self.datatype_properties)}")
        print(f"  - Annotation Properties: {len(self.annotation_properties)}")
        print(f"  - Individuals: {len(self.individuals)}")
        print(f"  - Dependency graph: {self.dependency_graph.number_of_nodes()} nodes, "
              f"{self.dependency_graph.number_of_edges()} edges")
    
    def partition_hierarchical(self, max_depth: int = 2) -> Dict[str, Set[URIRef]]:
        """Partition based on class hierarchy."""
        print(f"Applying hierarchical partitioning (max_depth={max_depth})...")
        
        partitions = {}
        visited = set()
        
        # Find top-level classes (no parents or only owl:Thing as parent)
        top_level = set()
        for cls in self.classes:
            parents = set(self.graph.objects(cls, RDFS.subClassOf))
            if not parents or parents == {OWL.Thing}:
                top_level.add(cls)
        
        print(f"  - Found {len(top_level)} top-level classes")
        
        # Create partitions based on top-level classes
        for root in top_level:
            if root in visited:
                continue
            
            partition_name = self._get_local_name(root)
            partition = {root}
            visited.add(root)
            
            # Add descendants up to max_depth
            queue = deque([(root, 0)])
            while queue:
                node, depth = queue.popleft()
                if depth < max_depth:
                    for child in self.class_hierarchy.get(node, []):
                        if child not in visited:
                            partition.add(child)
                            visited.add(child)
                            queue.append((child, depth + 1))
            
            # Add associated properties (iterate over a copy to avoid modification during iteration)
            for cls in list(partition):
                partition.update(self.class_properties.get(cls, []))
            
            partitions[partition_name] = partition
        
        # Handle unvisited nodes
        unvisited = (self.classes | self.object_properties | self.datatype_properties) - visited
        if unvisited:
            partitions['misc'] = unvisited
        
        print(f"  - Created {len(partitions)} hierarchical partitions")
        return partitions
    
    def partition_community(self, min_size: int = 3) -> Dict[str, Set[URIRef]]:
        """Partition using community detection on the dependency graph.
        
        Args:
            min_size: Minimum size for a community. Smaller communities are merged.
        """
        print("Applying community detection partitioning...")
        
        # Convert to undirected graph for community detection
        undirected = self.dependency_graph.to_undirected()
        
        # Apply Louvain community detection with resolution parameter
        # Higher resolution = more communities, lower = fewer but larger communities
        resolution = 1.0  # Start with default
        communities = community_louvain.best_partition(undirected, resolution=resolution)
        
        # Group nodes by community
        initial_partitions = defaultdict(set)
        for node, community_id in communities.items():
            initial_partitions[community_id].add(node)
        
        print(f"  - Initially detected {len(initial_partitions)} communities")
        
        # Merge small communities
        merged_partitions = self._merge_small_communities(initial_partitions, min_size)
        
        # Rename communities with meaningful names
        final_partitions = {}
        for idx, (comm_id, entities) in enumerate(merged_partitions.items()):
            # Try to derive a meaningful name from the community content
            community_name = self._derive_community_name(entities, idx)
            final_partitions[community_name] = entities
        
        print(f"  - After merging: {len(final_partitions)} communities")
        
        # Calculate modularity
        modularity = community_louvain.modularity(communities, undirected)
        print(f"  - Modularity score: {modularity:.3f}")
        
        # Report community sizes
        sizes = sorted([len(entities) for entities in final_partitions.values()], reverse=True)
        print(f"  - Community sizes: {sizes[:10]}{'...' if len(sizes) > 10 else ''}")
        
        return final_partitions
    
    def _merge_small_communities(self, partitions: Dict[int, Set[URIRef]], min_size: int) -> Dict[int, Set[URIRef]]:
        """Merge communities smaller than min_size with their most connected neighbors."""
        # Sort communities by size
        sorted_communities = sorted(partitions.items(), key=lambda x: len(x[1]))
        
        # Track merged communities
        merged = {}
        processed = set()
        
        for comm_id, entities in sorted_communities:
            if comm_id in processed:
                continue
                
            current_community = entities.copy()
            processed.add(comm_id)
            
            # If community is too small, try to merge with neighbors
            while len(current_community) < min_size:
                # Find the best neighbor to merge with
                best_neighbor = None
                best_connection_count = 0
                
                for other_id, other_entities in sorted_communities:
                    if other_id == comm_id or other_id in processed:
                        continue
                    
                    # Count connections between communities
                    connection_count = 0
                    for entity in current_community:
                        for neighbor in self.dependency_graph.neighbors(entity):
                            if neighbor in other_entities:
                                connection_count += 1
                    
                    if connection_count > best_connection_count:
                        best_neighbor = other_id
                        best_connection_count = connection_count
                
                # Merge with best neighbor if found
                if best_neighbor and best_connection_count > 0:
                    current_community.update(partitions[best_neighbor])
                    processed.add(best_neighbor)
                else:
                    # No suitable neighbor found, stop trying to merge
                    break
            
            merged[comm_id] = current_community
        
        return merged
    
    def _derive_community_name(self, entities: Set[URIRef], fallback_idx: int) -> str:
        """Derive a meaningful name for a community based on its entities."""
        # Collect keywords from entity names and labels
        keywords = []
        
        for entity in entities:
            # Get local name
            local_name = self._get_local_name(entity)
            if local_name:
                # Split camelCase or snake_case
                import re
                words = re.findall(r'[A-Z][a-z]+|[a-z]+|[A-Z]+(?=[A-Z][a-z]|\b)', local_name)
                keywords.extend(w.lower() for w in words)
            
            # Get labels
            for label in self.graph.objects(entity, RDFS.label):
                label_words = str(label).lower().split()
                keywords.extend(label_words)
        
        # Find most common meaningful keywords (excluding common words)
        stop_words = {'the', 'a', 'an', 'and', 'or', 'of', 'to', 'for', 'in', 'on', 'at', 'with', 'by', 'is', 'has', 'have'}
        keyword_counts = defaultdict(int)
        for kw in keywords:
            if kw not in stop_words and len(kw) > 2:
                keyword_counts[kw] += 1
        
        if keyword_counts:
            # Get top 2 keywords
            top_keywords = sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)[:2]
            name_parts = [kw for kw, _ in top_keywords]
            return '_'.join(name_parts)
        else:
            # Fallback to generic name
            return f"community_{fallback_idx}"
    
    def partition_domain(self, use_online_ontologies: bool = False) -> Dict[str, Set[URIRef]]:
        """Partition based on domain classification using online ontologies if enabled.
        
        Args:
            use_online_ontologies: If True, uses DBpedia and railway ontologies for classification
        """
        print("Applying domain-based partitioning...")
        
        if use_online_ontologies:
            try:
                # Use the enhanced domain classifier
                from .domain_classifier import OntologyDomainClassifier
                
                print("  - Using online ontologies (DBpedia, RailML, IFOPT, OTL Spoor) for classification...")
                classifier = OntologyDomainClassifier()
                
                # Collect all entities to classify
                entities = self.classes | self.object_properties | self.datatype_properties
                
                # Classify batch
                partitions = classifier.classify_batch(entities, self.graph)
                
                # Print statistics
                stats = classifier.get_domain_statistics(partitions)
                print(f"  - Created {len(partitions)} domain partitions")
                for domain, info in stats['domains'].items():
                    print(f"    - {domain}: {info['count']} entities ({info['percentage']:.1f}%)")
                
                return partitions
                
            except ImportError:
                print("  - Warning: domain_classifier not available, falling back to keyword-based classification")
            except Exception as e:
                print(f"  - Warning: Online classification failed ({e}), falling back to keyword-based classification")
        
        # Fallback to keyword-based classification
        print("  - Using keyword-based domain classification...")
        
        keywords = {
            'infrastructure': ['track', 'station', 'signal', 'infrastructure', 'tunnel', 'bridge',
                             'platform', 'route', 'line', 'network', 'switch', 'crossing'],
            'rolling_stock': ['vehicle', 'train', 'wagon', 'locomotive', 'car', 'rolling',
                            'axle', 'wheel', 'bogie', 'engine', 'motor', 'coach'],
            'signaling': ['signal', 'etcs', 'ertms', 'control', 'communication', 'radio',
                         'balise', 'message', 'interlocking', 'aspect'],
            'electrical': ['electrical', 'voltage', 'power', 'energy', 'contact', 'pantograph',
                          'current', 'phase', 'wire', 'catenary', 'substation'],
            'operations': ['operation', 'timetable', 'schedule', 'movement', 'journey',
                          'departure', 'arrival', 'delay', 'service', 'traffic'],
            'safety': ['safety', 'hazard', 'risk', 'accident', 'emergency', 'protection',
                      'detection', 'warning', 'alarm', 'incident'],
            'geographic': ['location', 'position', 'coordinate', 'point', 'area', 'zone',
                          'region', 'country', 'border', 'kilometer', 'mileage'],
            'administrative': ['organization', 'authority', 'operator', 'certificate',
                             'document', 'license', 'regulation', 'compliance'],
            'technical': ['specification', 'parameter', 'limit', 'capability', 'performance',
                         'requirement', 'standard', 'dimension', 'measurement']
        }
        
        partitions = defaultdict(set)
        unassigned = set()
        
        # Check each entity
        for entity in self.classes | self.object_properties | self.datatype_properties:
            assigned = False
            entity_str = str(entity).lower()
            
            # Check labels
            labels = list(self.graph.objects(entity, RDFS.label))
            label_str = ' '.join(str(l).lower() for l in labels)
            
            # Try to assign to a domain
            best_domain = None
            best_score = 0
            
            for domain, domain_keywords in keywords.items():
                score = 0
                for keyword in domain_keywords:
                    if keyword in entity_str:
                        score += 2  # Higher weight for entity name match
                    if keyword in label_str:
                        score += 1  # Lower weight for label match
                
                if score > best_score:
                    best_score = score
                    best_domain = domain
            
            if best_domain and best_score > 0:
                partitions[best_domain].add(entity)
            else:
                unassigned.add(entity)
        
        # Add unassigned to a general partition
        if unassigned:
            partitions['general'] = unassigned
        
        print(f"  - Created {len(partitions)} domain partitions")
        for domain, entities in partitions.items():
            print(f"    - {domain}: {len(entities)} entities")
        
        return dict(partitions)
    
    def calculate_metrics(self, partitions: Dict[str, Set[URIRef]]) -> Dict[str, float]:
        """Calculate quality metrics for partitions."""
        metrics = {}
        
        # Count inter-partition edges
        inter_edges = 0
        intra_edges = 0
        
        # Create partition lookup
        node_to_partition = {}
        for partition_name, nodes in partitions.items():
            for node in nodes:
                node_to_partition[node] = partition_name
        
        # Count edges
        for u, v in self.dependency_graph.edges():
            if u in node_to_partition and v in node_to_partition:
                if node_to_partition[u] == node_to_partition[v]:
                    intra_edges += 1
                else:
                    inter_edges += 1
        
        total_edges = inter_edges + intra_edges
        
        # Calculate metrics
        metrics['partitions'] = len(partitions)
        metrics['inter_edges'] = inter_edges
        metrics['intra_edges'] = intra_edges
        metrics['coupling'] = inter_edges / total_edges if total_edges > 0 else 0
        metrics['cohesion'] = intra_edges / total_edges if total_edges > 0 else 1
        
        # Size distribution
        sizes = [len(nodes) for nodes in partitions.values()]
        metrics['min_size'] = min(sizes) if sizes else 0
        metrics['max_size'] = max(sizes) if sizes else 0
        metrics['avg_size'] = sum(sizes) / len(sizes) if sizes else 0
        
        return metrics
    
    def _get_local_name(self, uri: URIRef) -> str:
        """Extract local name from URI."""
        uri_str = str(uri)
        if '#' in uri_str:
            return uri_str.split('#')[-1]
        elif '/' in uri_str:
            return uri_str.split('/')[-1]
        return uri_str
    
    def generate_modules(self, partitions: Dict[str, Set[URIRef]], strategy_name: str) -> None:
        """Generate module files for the partitions with complete semantic information."""
        print(f"Generating module files for {strategy_name} strategy...")
        
        strategy_dir = self.output_dir / strategy_name
        strategy_dir.mkdir(exist_ok=True)
        
        # Save partition index
        index = {
            'strategy': strategy_name,
            'source_file': str(self.input_file),
            'partitions': {}
        }
        
        for partition_name, entities in partitions.items():
            module_file = strategy_dir / f"{partition_name}.ttl"
            
            # Create a subgraph for this partition
            subgraph = Graph()
            
            # Copy namespaces
            for prefix, namespace in self.namespaces.items():
                subgraph.bind(prefix, namespace)
            
            # Track all triples and additional entities to include
            triples_to_add = set()
            additional_entities = set()
            
            # For each entity in this partition
            for entity in entities:
                # 1. Add ALL triples where entity is the subject
                # This includes all annotations, properties, restrictions about this entity
                for triple in self.graph.triples((entity, None, None)):
                    triples_to_add.add(triple)
                    
                    # If the object is a blank node (e.g., restriction), include all its triples
                    obj = triple[2]
                    if not isinstance(obj, URIRef):
                        self._collect_blank_node_triples(obj, triples_to_add)
                
                # 2. For properties, include domain and range declarations
                if entity in self.object_properties or entity in self.datatype_properties:
                    # Include all domain declarations
                    for triple in self.graph.triples((entity, RDFS.domain, None)):
                        triples_to_add.add(triple)
                    # Include all range declarations
                    for triple in self.graph.triples((entity, RDFS.range, None)):
                        triples_to_add.add(triple)
                    # Include property characteristics (functional, inverse, etc.)
                    for pred in [RDF.type, OWL.inverseOf, OWL.equivalentProperty,
                                RDFS.subPropertyOf, OWL.propertyChainAxiom]:
                        for triple in self.graph.triples((entity, pred, None)):
                            triples_to_add.add(triple)
                
                # 3. For classes, include hierarchy and restrictions
                if entity in self.classes:
                    # Include subclass relationships
                    for triple in self.graph.triples((entity, RDFS.subClassOf, None)):
                        triples_to_add.add(triple)
                        # If subClassOf points to a restriction (blank node), include it
                        obj = triple[2]
                        if not isinstance(obj, URIRef):
                            self._collect_blank_node_triples(obj, triples_to_add)
                    
                    # Include equivalent class definitions
                    for triple in self.graph.triples((entity, OWL.equivalentClass, None)):
                        triples_to_add.add(triple)
                        obj = triple[2]
                        if not isinstance(obj, URIRef):
                            self._collect_blank_node_triples(obj, triples_to_add)
                    
                    # Include disjoint unions
                    for triple in self.graph.triples((entity, OWL.disjointUnionOf, None)):
                        triples_to_add.add(triple)
                        obj = triple[2]
                        if not isinstance(obj, URIRef):
                            self._collect_blank_node_triples(obj, triples_to_add)
                
                # 4. Include type declarations
                for triple in self.graph.triples((entity, RDF.type, None)):
                    triples_to_add.add(triple)
                
                # 5. Include all annotations (labels, comments, etc.)
                for annotation_prop in self.annotation_properties:
                    for triple in self.graph.triples((entity, annotation_prop, None)):
                        triples_to_add.add(triple)
                
                # Also include standard annotations even if not declared
                for annotation_prop in [RDFS.label, RDFS.comment, RDFS.seeAlso,
                                       RDFS.isDefinedBy, OWL.versionInfo]:
                    for triple in self.graph.triples((entity, annotation_prop, None)):
                        triples_to_add.add(triple)
            
            # Add all collected triples to the subgraph
            for triple in triples_to_add:
                subgraph.add(triple)
            
            # Also include ontology-level metadata if this is the first partition
            if partition_name == list(partitions.keys())[0]:
                # Include ontology declarations and imports
                for triple in self.graph.triples((None, RDF.type, OWL.Ontology)):
                    subgraph.add(triple)
                    ont_uri = triple[0]
                    # Add all properties of the ontology
                    for ont_triple in self.graph.triples((ont_uri, None, None)):
                        subgraph.add(ont_triple)
            
            # Save module
            subgraph.serialize(module_file, format='turtle')
            
            index['partitions'][partition_name] = {
                'file': str(module_file),
                'entities': len(entities),
                'triples': len(subgraph)
            }
            
            print(f"  - Generated {partition_name}.ttl ({len(entities)} entities, {len(subgraph)} triples)")
        
        # Save index
        index_file = strategy_dir / 'index.json'
        with open(index_file, 'w') as f:
            json.dump(index, f, indent=2)
    
    def _collect_blank_node_triples(self, blank_node, triples_set: set) -> None:
        """Recursively collect all triples related to a blank node."""
        # Add all triples where the blank node is the subject
        for triple in self.graph.triples((blank_node, None, None)):
            if triple not in triples_set:
                triples_set.add(triple)
                # If the object is also a blank node, recurse
                if not isinstance(triple[2], URIRef):
                    self._collect_blank_node_triples(triple[2], triples_set)
        
        # For RDF lists (used in unions, intersections, etc.)
        for triple in self.graph.triples((blank_node, RDF.first, None)):
            triples_set.add(triple)
        for triple in self.graph.triples((blank_node, RDF.rest, None)):
            triples_set.add(triple)
            # Continue following the list
            if triple[2] != RDF.nil and not isinstance(triple[2], URIRef):
                self._collect_blank_node_triples(triple[2], triples_set)
    
    def visualize_partitions(self, partitions: Dict[str, Set[URIRef]], strategy_name: str) -> None:
        """Create a visualization of the partitions."""
        print(f"Creating visualization for {strategy_name} strategy...")
        
        # Create color map for partitions
        partition_names = list(partitions.keys())
        colors = plt.cm.get_cmap('tab20', len(partition_names))
        color_map = {name: colors(i) for i, name in enumerate(partition_names)}
        
        # Create node colors
        node_colors = []
        node_to_partition = {}
        for partition_name, nodes in partitions.items():
            for node in nodes:
                node_to_partition[node] = partition_name
        
        for node in self.dependency_graph.nodes():
            if node in node_to_partition:
                node_colors.append(color_map[node_to_partition[node]])
            else:
                node_colors.append('gray')
        
        # Create layout
        pos = nx.spring_layout(self.dependency_graph, k=2, iterations=50)
        
        # Draw graph
        plt.figure(figsize=(15, 10))
        nx.draw_networkx_nodes(self.dependency_graph, pos, node_size=30, 
                              node_color=node_colors, alpha=0.7)
        nx.draw_networkx_edges(self.dependency_graph, pos, alpha=0.2, 
                              arrows=False, edge_color='gray')
        
        # Add legend
        legend_elements = [plt.Line2D([0], [0], marker='o', color='w', 
                                     markerfacecolor=color_map[name], 
                                     markersize=10, label=f"{name} ({len(partitions[name])})")
                          for name in partition_names]
        plt.legend(handles=legend_elements, loc='upper right', bbox_to_anchor=(1.15, 1))
        
        plt.title(f"Ontology Partitioning - {strategy_name}")
        plt.axis('off')
        plt.tight_layout()
        
        # Save figure
        fig_file = self.output_dir / f"{strategy_name}_visualization.png"
        plt.savefig(fig_file, dpi=150, bbox_inches='tight')
        plt.close()
        
        print(f"  - Saved visualization to {fig_file}")
    
    def partition(self, strategies: List[str] = None) -> None:
        """Run the complete partitioning process."""
        print(f"\nSemantic Partitioning of {self.input_file.name}")
        print("=" * 60)
        
        # Load and analyze
        self.load_ontology()
        self.analyze_structure()
        
        # Default strategies
        if strategies is None:
            strategies = ['hierarchical', 'community', 'domain']
        
        # Apply each strategy
        results = {}
        for strategy in strategies:
            print(f"\n{strategy.upper()} PARTITIONING")
            print("-" * 40)
            
            if strategy == 'hierarchical':
                partitions = self.partition_hierarchical()
            elif strategy == 'community':
                partitions = self.partition_community()
            elif strategy == 'domain':
                # Check if we should use online ontologies (can be configured)
                use_online = True  # Enable by default for better classification
                partitions = self.partition_domain(use_online_ontologies=use_online)
            else:
                print(f"Unknown strategy: {strategy}")
                continue
            
            # Calculate metrics
            metrics = self.calculate_metrics(partitions)
            
            print(f"\nMetrics for {strategy}:")
            print(f"  - Partitions: {metrics['partitions']}")
            print(f"  - Coupling: {metrics['coupling']:.3f}")
            print(f"  - Cohesion: {metrics['cohesion']:.3f}")
            print(f"  - Size range: {metrics['min_size']}-{metrics['max_size']} (avg: {metrics['avg_size']:.1f})")
            
            # Generate modules
            self.generate_modules(partitions, strategy)
            
            # Visualize
            try:
                self.visualize_partitions(partitions, strategy)
            except Exception as e:
                print(f"  - Could not create visualization: {e}")
            
            results[strategy] = {
                'partitions': partitions,
                'metrics': metrics
            }
        
        # Save summary
        self.save_summary(results)
        
        print(f"\nPartitioning complete!")
        print(f"Output directory: {self.output_dir}")
    
    def save_summary(self, results: Dict) -> None:
        """Save a summary of all partitioning results."""
        summary_file = self.output_dir / "partitioning_summary.json"
        
        summary = {
            'source_file': str(self.input_file),
            'total_classes': len(self.classes),
            'total_properties': len(self.object_properties) + len(self.datatype_properties),
            'total_individuals': len(self.individuals),
            'strategies': {}
        }
        
        for strategy, data in results.items():
            summary['strategies'][strategy] = {
                'metrics': data['metrics'],
                'partitions': {name: len(entities)
                             for name, entities in data['partitions'].items()}
            }
        
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        print(f"\nSummary saved to {summary_file}")
        
        # Generate markdown report
        self.generate_markdown_report(results)
    
    def generate_markdown_report(self, results: Dict) -> None:
        """Generate a comprehensive markdown report of partitioning results."""
        report_file = self.output_dir / "PARTITIONING_REPORT.md"
        
        with open(report_file, 'w') as f:
            f.write(f"# Ontology Partitioning Report\n\n")
            f.write(f"**Source Ontology:** {self.input_file.name}\n")
            f.write(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            # Overall statistics
            f.write("## Ontology Statistics\n\n")
            f.write(f"- **Classes:** {len(self.classes)}\n")
            f.write(f"- **Object Properties:** {len(self.object_properties)}\n")
            f.write(f"- **Datatype Properties:** {len(self.datatype_properties)}\n")
            f.write(f"- **Annotation Properties:** {len(self.annotation_properties)}\n")
            f.write(f"- **Individuals:** {len(self.individuals)}\n")
            f.write(f"- **Total Entities:** {len(self.classes) + len(self.object_properties) + len(self.datatype_properties)}\n")
            f.write(f"- **Total Triples:** {len(self.graph)}\n\n")
            
            # Dependency graph statistics
            f.write("## Dependency Analysis\n\n")
            f.write(f"- **Graph Nodes:** {self.dependency_graph.number_of_nodes()}\n")
            f.write(f"- **Graph Edges:** {self.dependency_graph.number_of_edges()}\n")
            if self.dependency_graph.number_of_nodes() > 0:
                avg_degree = sum(dict(self.dependency_graph.degree()).values()) / self.dependency_graph.number_of_nodes()
                f.write(f"- **Average Degree:** {avg_degree:.2f}\n")
                
                # Find components
                import networkx as nx
                components = list(nx.connected_components(self.dependency_graph.to_undirected()))
                f.write(f"- **Connected Components:** {len(components)}\n")
                if len(components) > 1:
                    f.write(f"  - Largest component: {max(len(c) for c in components)} nodes\n")
                    f.write(f"  - Smallest component: {min(len(c) for c in components)} nodes\n")
            f.write("\n")
            
            # Results for each strategy
            f.write("## Partitioning Results\n\n")
            
            for strategy, data in results.items():
                f.write(f"### {strategy.title()} Strategy\n\n")
                
                metrics = data['metrics']
                partitions = data['partitions']
                
                # Metrics table
                f.write("#### Metrics\n\n")
                f.write("| Metric | Value |\n")
                f.write("|--------|-------|\n")
                f.write(f"| Number of Partitions | {metrics['partitions']} |\n")
                f.write(f"| Cohesion | {metrics['cohesion']:.3f} |\n")
                f.write(f"| Coupling | {metrics['coupling']:.3f} |\n")
                f.write(f"| Min Partition Size | {metrics['min_size']} |\n")
                f.write(f"| Max Partition Size | {metrics['max_size']} |\n")
                f.write(f"| Avg Partition Size | {metrics['avg_size']:.1f} |\n")
                f.write(f"| Inter-partition Edges | {metrics['inter_edges']} |\n")
                f.write(f"| Intra-partition Edges | {metrics['intra_edges']} |\n\n")
                
                # Partition distribution
                f.write("#### Partition Size Distribution\n\n")
                sizes = sorted([len(entities) for entities in partitions.values()], reverse=True)
                
                # Size categories
                large = [s for s in sizes if s > 50]
                medium = [s for s in sizes if 10 <= s <= 50]
                small = [s for s in sizes if 3 <= s < 10]
                singleton = [s for s in sizes if s == 1]
                tiny = [s for s in sizes if s == 2]
                
                f.write("| Category | Count | Sizes |\n")
                f.write("|----------|-------|-------|\n")
                f.write(f"| Large (>50) | {len(large)} | {large[:5]}{'...' if len(large) > 5 else ''} |\n")
                f.write(f"| Medium (10-50) | {len(medium)} | {medium[:10]}{'...' if len(medium) > 10 else ''} |\n")
                f.write(f"| Small (3-9) | {len(small)} | {small[:10]}{'...' if len(small) > 10 else ''} |\n")
                f.write(f"| Tiny (2) | {len(tiny)} | - |\n")
                f.write(f"| Singleton (1) | {len(singleton)} | - |\n\n")
                
                # Top partitions
                f.write("#### Top 10 Largest Partitions\n\n")
                f.write("| Partition Name | Entity Count |\n")
                f.write("|----------------|-------------|\n")
                
                sorted_partitions = sorted(partitions.items(),
                                         key=lambda x: len(x[1]), reverse=True)[:10]
                for name, entities in sorted_partitions:
                    f.write(f"| {name} | {len(entities)} |\n")
                f.write("\n")
            
            # Quality assessment
            f.write("## Quality Assessment\n\n")
            
            for strategy, data in results.items():
                metrics = data['metrics']
                cohesion = metrics['cohesion']
                coupling = metrics['coupling']
                
                f.write(f"### {strategy.title()} Strategy\n\n")
                
                # Interpret metrics
                if cohesion > 0.7:
                    cohesion_assessment = "✅ **Excellent** - Highly cohesive partitions"
                elif cohesion > 0.5:
                    cohesion_assessment = "✓ **Good** - Reasonably cohesive partitions"
                else:
                    cohesion_assessment = "⚠️ **Fair** - Could benefit from refinement"
                
                if coupling < 0.3:
                    coupling_assessment = "✅ **Excellent** - Low inter-partition dependencies"
                elif coupling < 0.5:
                    coupling_assessment = "✓ **Good** - Moderate inter-partition dependencies"
                else:
                    coupling_assessment = "⚠️ **Fair** - High inter-partition dependencies"
                
                f.write(f"- **Cohesion ({cohesion:.3f}):** {cohesion_assessment}\n")
                f.write(f"- **Coupling ({coupling:.3f}):** {coupling_assessment}\n\n")
                
                # Recommendations
                singleton_count = sum(1 for p in data['partitions'].values() if len(p) == 1)
                if singleton_count > len(data['partitions']) * 0.3:
                    f.write("⚠️ **Note:** High number of singleton partitions. Consider adjusting parameters or merging strategy.\n\n")
            
            f.write("## Output Files\n\n")
            f.write("The following files have been generated:\n\n")
            f.write("- `partitioning_summary.json` - Machine-readable summary\n")
            f.write("- `PARTITIONING_REPORT.md` - This human-readable report\n")
            
            for strategy in results.keys():
                f.write(f"- `{strategy}/` - Directory containing partition modules\n")
                f.write(f"  - `*.ttl` - Individual partition files in Turtle format\n")
                f.write(f"  - `index.json` - Index of partitions with metadata\n")
                f.write(f"- `{strategy}_visualization.png` - Graph visualization\n")
            
            f.write("\n---\n")
            f.write("*Generated by Semantic Partitioner*\n")
        
        print(f"Report saved to {report_file}")


def main():
    parser = argparse.ArgumentParser(description="Semantically partition ontologies into coherent modules")
    parser.add_argument("input_file", help="Input ontology file")
    parser.add_argument("-o", "--output-dir", help="Output directory for modules")
    parser.add_argument("-s", "--strategies", nargs='+', 
                       choices=['hierarchical', 'community', 'domain'],
                       help="Partitioning strategies to apply")
    parser.add_argument("--use-chunks", action="store_true",
                       help="Load from pre-chunked files if available")
    
    args = parser.parse_args()
    
    # Check if input file exists
    if not os.path.exists(args.input_file):
        print(f"Error: Input file '{args.input_file}' not found")
        return 1
    
    # Create partitioner and run
    partitioner = SemanticPartitioner(args.input_file, args.output_dir, args.use_chunks)
    partitioner.partition(args.strategies)
    
    return 0


if __name__ == "__main__":
    exit(main())
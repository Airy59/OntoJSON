#!/usr/bin/env python3
"""
Enhanced Domain Classifier using Online Ontologies
Combines DBpedia, RailML, IFOPT, and OTL Spoor for semantic domain classification
"""

import re
import json
import logging
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple
from collections import defaultdict
from urllib.parse import quote
import requests
from rdflib import URIRef, RDFS

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OntologyDomainClassifier:
    """Classifies ontology entities into domains using online semantic resources."""
    
    def __init__(self, cache_dir: str = ".ontology_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        
        # DBpedia SPARQL endpoint
        self.dbpedia_endpoint = "http://dbpedia.org/sparql"
        
        # Railway domain mappings based on RailML, IFOPT, OTL Spoor
        self.railway_domains = self._initialize_railway_domains()
        
        # Cache for online lookups
        self.concept_cache = self._load_cache()
        
    def _initialize_railway_domains(self) -> Dict[str, Dict]:
        """Initialize railway-specific domain mappings from RailML, IFOPT, and OTL Spoor."""
        return {
            'infrastructure': {
                'keywords': ['track', 'rail', 'station', 'platform', 'signal', 
                            'tunnel', 'bridge', 'switch', 'crossing', 'junction',
                            'infrastructure', 'route', 'line', 'network', 'section'],
                'railml_types': ['infrastructure', 'track', 'operationalPoint'],
                'ifopt_types': ['StopPlace', 'Quay', 'AccessSpace'],
                'otl_spoor_types': ['Spoor', 'Wissel', 'Sein', 'Perron'],
                'dbpedia_categories': ['Railway_infrastructure', 'Railway_stations', 'Rail_transport']
            },
            'rolling_stock': {
                'keywords': ['vehicle', 'train', 'wagon', 'locomotive', 'car', 
                            'coach', 'freight', 'passenger', 'rolling', 'stock',
                            'axle', 'wheel', 'bogie', 'engine', 'motor'],
                'railml_types': ['vehicle', 'formation', 'trainPart'],
                'ifopt_types': ['Vehicle', 'VehicleType'],
                'otl_spoor_types': ['Trein', 'Locomotief', 'Wagon'],
                'dbpedia_categories': ['Rolling_stock', 'Locomotives', 'Railroad_cars']
            },
            'signaling': {
                'keywords': ['signal', 'etcs', 'ertms', 'control', 'communication',
                            'radio', 'balise', 'message', 'interlocking', 'block',
                            'aspect', 'indication', 'protection', 'warning'],
                'railml_types': ['signalling', 'controller', 'interlocking'],
                'ifopt_types': ['SignallingSystem'],
                'otl_spoor_types': ['Seinwezen', 'ETCS', 'ATB'],
                'dbpedia_categories': ['Railway_signalling', 'Train_protection_systems']
            },
            'electrical': {
                'keywords': ['electrical', 'voltage', 'power', 'energy', 'contact',
                            'pantograph', 'current', 'phase', 'wire', 'catenary',
                            'substation', 'transformer', 'feeder'],
                'railml_types': ['electrification', 'powerSupply'],
                'ifopt_types': ['PowerSupply', 'ElectricalSystem'],
                'otl_spoor_types': ['Bovenleiding', 'Onderspanningsstation'],
                'dbpedia_categories': ['Railway_electrification', 'Electric_railways']
            },
            'operations': {
                'keywords': ['operation', 'timetable', 'schedule', 'movement', 'journey',
                            'departure', 'arrival', 'delay', 'service', 'traffic',
                            'dispatcher', 'planning', 'coordination'],
                'railml_types': ['timetable', 'roster', 'operatingPeriod'],
                'ifopt_types': ['ServiceJourney', 'ServicePattern'],
                'otl_spoor_types': ['Dienstregeling', 'Rit'],
                'dbpedia_categories': ['Rail_transport_operations', 'Public_transport_timetables']
            },
            'safety': {
                'keywords': ['safety', 'hazard', 'risk', 'accident', 'emergency',
                            'protection', 'detection', 'warning', 'alarm', 'security',
                            'incident', 'failure', 'maintenance'],
                'railml_types': ['safetySystem'],
                'ifopt_types': ['SafetyEquipment', 'EmergencyEquipment'],
                'otl_spoor_types': ['Veiligheid', 'Noodstop'],
                'dbpedia_categories': ['Railway_safety', 'Rail_accidents']
            },
            'geographic': {
                'keywords': ['location', 'position', 'coordinate', 'point', 'area',
                            'zone', 'region', 'country', 'border', 'kilometer',
                            'mileage', 'chainage', 'geocode'],
                'railml_types': ['geoCoord', 'mileage'],
                'ifopt_types': ['Location', 'Place', 'Zone'],
                'otl_spoor_types': ['Locatie', 'Kilometrering'],
                'dbpedia_categories': ['Geography', 'Railway_lines']
            },
            'administrative': {
                'keywords': ['organization', 'authority', 'operator', 'owner', 'manager',
                            'certificate', 'license', 'regulation', 'compliance',
                            'document', 'contract', 'agreement'],
                'railml_types': ['organisationalUnit'],
                'ifopt_types': ['Organisation', 'Authority', 'Operator'],
                'otl_spoor_types': ['Beheerder', 'Eigenaar'],
                'dbpedia_categories': ['Railway_companies', 'Transport_operators']
            },
            'technical': {
                'keywords': ['specification', 'parameter', 'limit', 'capability',
                            'performance', 'requirement', 'standard', 'dimension',
                            'measurement', 'gauge', 'load', 'weight', 'speed'],
                'railml_types': ['technicalSpecification'],
                'ifopt_types': ['TechnicalSpecification'],
                'otl_spoor_types': ['Specificatie', 'Norm'],
                'dbpedia_categories': ['Railway_technology', 'Technical_specifications']
            }
        }
    
    def _load_cache(self) -> Dict[str, str]:
        """Load cached concept mappings."""
        cache_file = self.cache_dir / "concept_mappings.json"
        if cache_file.exists():
            with open(cache_file, 'r') as f:
                return json.load(f)
        return {}
    
    def _save_cache(self):
        """Save concept mappings to cache."""
        cache_file = self.cache_dir / "concept_mappings.json"
        with open(cache_file, 'w') as f:
            json.dump(self.concept_cache, f, indent=2)
    
    def query_dbpedia(self, concept: str) -> Optional[List[str]]:
        """Query DBpedia for concept categories."""
        # Check cache first
        if concept in self.concept_cache:
            return self.concept_cache.get(concept)
        
        try:
            # Construct SPARQL query
            query = f"""
            PREFIX dbo: <http://dbpedia.org/ontology/>
            PREFIX dcterms: <http://purl.org/dc/terms/>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            
            SELECT DISTINCT ?category WHERE {{
                {{
                    ?resource rdfs:label "{concept}"@en .
                    ?resource dcterms:subject ?category .
                }}
                UNION
                {{
                    ?resource dbo:wikiPageRedirects ?redirect .
                    ?redirect rdfs:label "{concept}"@en .
                    ?redirect dcterms:subject ?category .
                }}
            }}
            LIMIT 10
            """
            
            # Send request
            response = requests.get(
                self.dbpedia_endpoint,
                params={'query': query, 'format': 'json'},
                timeout=5
            )
            
            if response.status_code == 200:
                results = response.json()
                categories = []
                for binding in results.get('results', {}).get('bindings', []):
                    if 'category' in binding:
                        cat_uri = binding['category']['value']
                        # Extract category name from URI
                        cat_name = cat_uri.split('/')[-1].replace('_', ' ')
                        categories.append(cat_name)
                
                # Cache the result
                self.concept_cache[concept] = categories
                self._save_cache()
                return categories
                
        except Exception as e:
            logger.warning(f"DBpedia query failed for '{concept}': {e}")
        
        return None
    
    def classify_by_dbpedia_categories(self, entity_name: str) -> Optional[str]:
        """Classify entity using DBpedia categories."""
        # Extract meaningful words from entity name
        words = re.findall(r'[A-Z][a-z]+|[a-z]+|[A-Z]+(?=[A-Z][a-z]|\b)', entity_name)
        meaningful_words = [w for w in words if len(w) > 2]
        
        # Query DBpedia for each meaningful word
        domain_scores = defaultdict(float)
        
        for word in meaningful_words[:3]:  # Limit to first 3 words
            categories = self.query_dbpedia(word)
            if categories:
                # Match categories against railway domains
                for category in categories:
                    cat_lower = category.lower()
                    for domain, config in self.railway_domains.items():
                        # Check if category matches DBpedia categories for this domain
                        for dbpedia_cat in config['dbpedia_categories']:
                            if dbpedia_cat.lower() in cat_lower or cat_lower in dbpedia_cat.lower():
                                domain_scores[domain] += 2.0  # High weight for DBpedia match
                        
                        # Check if category contains domain keywords
                        for keyword in config['keywords']:
                            if keyword in cat_lower:
                                domain_scores[domain] += 0.5
        
        if domain_scores:
            # Return the domain with highest score
            return max(domain_scores, key=domain_scores.get)
        
        return None
    
    def classify_by_railway_ontologies(self, entity_name: str, entity_uri: str = None) -> Optional[str]:
        """Classify entity using railway-specific ontology patterns."""
        entity_lower = entity_name.lower()
        domain_scores = defaultdict(float)
        
        for domain, config in self.railway_domains.items():
            # Check RailML types
            for railml_type in config.get('railml_types', []):
                if railml_type.lower() in entity_lower:
                    domain_scores[domain] += 1.5
            
            # Check IFOPT types
            for ifopt_type in config.get('ifopt_types', []):
                if ifopt_type.lower() in entity_lower:
                    domain_scores[domain] += 1.5
            
            # Check OTL Spoor types
            for otl_type in config.get('otl_spoor_types', []):
                if otl_type.lower() in entity_lower:
                    domain_scores[domain] += 1.5
        
        if domain_scores:
            return max(domain_scores, key=domain_scores.get)
        
        return None
    
    def classify_by_keywords(self, entity_name: str, labels: List[str] = None) -> Optional[str]:
        """Fallback classification using keyword matching."""
        entity_lower = entity_name.lower()
        label_text = ' '.join(labels).lower() if labels else ''
        
        domain_scores = defaultdict(float)
        
        for domain, config in self.railway_domains.items():
            for keyword in config['keywords']:
                # Check entity name
                if keyword in entity_lower:
                    domain_scores[domain] += 1.0
                # Check labels
                if keyword in label_text:
                    domain_scores[domain] += 0.5
        
        if domain_scores:
            return max(domain_scores, key=domain_scores.get)
        
        return None
    
    def classify_entity(self, entity: URIRef, graph=None) -> str:
        """
        Classify an entity into a domain using multiple strategies.
        
        Args:
            entity: The entity URI to classify
            graph: Optional RDF graph for extracting labels
            
        Returns:
            Domain name or 'general' if no match found
        """
        # Extract entity name from URI
        entity_str = str(entity)
        if '#' in entity_str:
            entity_name = entity_str.split('#')[-1]
        elif '/' in entity_str:
            entity_name = entity_str.split('/')[-1]
        else:
            entity_name = entity_str
        
        # Extract labels if graph provided
        labels = []
        if graph:
            for label in graph.objects(entity, RDFS.label):
                labels.append(str(label))
        
        # Try classification strategies in order of preference
        
        # 1. Try DBpedia classification (most comprehensive)
        domain = self.classify_by_dbpedia_categories(entity_name)
        if domain:
            logger.debug(f"DBpedia classified '{entity_name}' as '{domain}'")
            return domain
        
        # 2. Try railway-specific ontologies
        domain = self.classify_by_railway_ontologies(entity_name, entity_str)
        if domain:
            logger.debug(f"Railway ontology classified '{entity_name}' as '{domain}'")
            return domain
        
        # 3. Fallback to keyword matching
        domain = self.classify_by_keywords(entity_name, labels)
        if domain:
            logger.debug(f"Keyword matching classified '{entity_name}' as '{domain}'")
            return domain
        
        # 4. Default to 'general' domain
        logger.debug(f"No classification found for '{entity_name}', using 'general'")
        return 'general'
    
    def classify_batch(self, entities: Set[URIRef], graph=None) -> Dict[str, Set[URIRef]]:
        """
        Classify a batch of entities into domains.
        
        Args:
            entities: Set of entity URIs to classify
            graph: Optional RDF graph for extracting labels
            
        Returns:
            Dictionary mapping domain names to sets of entities
        """
        domains = defaultdict(set)
        
        total = len(entities)
        for i, entity in enumerate(entities, 1):
            if i % 10 == 0:
                logger.info(f"Classifying entity {i}/{total}")
            
            domain = self.classify_entity(entity, graph)
            domains[domain].add(entity)
        
        return dict(domains)
    
    def get_domain_statistics(self, domains: Dict[str, Set[URIRef]]) -> Dict:
        """Generate statistics about domain classification."""
        stats = {
            'total_entities': sum(len(entities) for entities in domains.values()),
            'domains': {}
        }
        
        for domain, entities in sorted(domains.items(), key=lambda x: len(x[1]), reverse=True):
            stats['domains'][domain] = {
                'count': len(entities),
                'percentage': len(entities) / stats['total_entities'] * 100
            }
        
        return stats


def main():
    """Test the domain classifier."""
    import sys
    from rdflib import Graph
    
    if len(sys.argv) < 2:
        print("Usage: python domain_classifier.py <ontology_file>")
        return
    
    # Load ontology
    g = Graph()
    g.parse(sys.argv[1])
    
    # Extract all classes and properties
    from rdflib import OWL, RDF
    entities = set()
    
    for s in g.subjects(RDF.type, OWL.Class):
        if isinstance(s, URIRef):
            entities.add(s)
    
    for prop_type in [OWL.ObjectProperty, OWL.DatatypeProperty]:
        for s in g.subjects(RDF.type, prop_type):
            if isinstance(s, URIRef):
                entities.add(s)
    
    print(f"Found {len(entities)} entities to classify")
    
    # Initialize classifier
    classifier = OntologyDomainClassifier()
    
    # Classify entities
    domains = classifier.classify_batch(entities, g)
    
    # Print results
    print("\nDomain Classification Results:")
    print("-" * 40)
    
    stats = classifier.get_domain_statistics(domains)
    for domain, info in stats['domains'].items():
        print(f"{domain}: {info['count']} entities ({info['percentage']:.1f}%)")
    
    # Save results
    output = {
        'statistics': stats,
        'domains': {
            domain: [str(e) for e in entities]
            for domain, entities in domains.items()
        }
    }
    
    with open('domain_classification_results.json', 'w') as f:
        json.dump(output, f, indent=2)
    
    print("\nResults saved to domain_classification_results.json")


if __name__ == "__main__":
    main()
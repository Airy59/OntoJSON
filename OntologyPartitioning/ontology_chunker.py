#!/usr/bin/env python3
"""
Efficient Ontology Chunker

This script chunks large OWL/Turtle ontology files into smaller, manageable pieces
without loading the entire file into memory. It uses line-based streaming to process
files of any size and avoid token limit issues.

Note: This is for temporary chunking to handle token limits, not semantic partitioning.
"""

import os
import sys
import json
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from collections import defaultdict
import subprocess
import re


class OntologyChunker:
    """Chunks large ontology files efficiently using streaming."""
    
    def __init__(self, input_file: str, output_dir: str = None):
        self.input_file = Path(input_file)
        self.output_dir = Path(output_dir) if output_dir else self.input_file.parent / f"{self.input_file.stem}_chunks"
        self.output_dir.mkdir(exist_ok=True)
        
        # File paths for outputs
        self.index_file = self.output_dir / "chunk_index.json"
        self.header_file = self.output_dir / "00_header.ttl"
        
        # Index structure
        self.index = {
            "source_file": str(self.input_file),
            "header_lines": 0,
            "total_lines": 0,
            "entities": {},
            "chunks": {}
        }
        
    def scan_file(self) -> None:
        """Scan the file to build an index of all entities and their locations."""
        print(f"Scanning {self.input_file}...")
        
        current_entity = None
        current_start = 0
        entity_count = 0
        line_number = 0
        header_end = 0
        in_header = True
        
        # Regular expression patterns
        entity_pattern = re.compile(r'^###\s+(.+)$')
        class_pattern = re.compile(r'^(\S+)\s+(?:a|rdf:type)\s+owl:Class')
        property_pattern = re.compile(r'^(\S+)\s+(?:a|rdf:type)\s+owl:(Object|Datatype|Annotation)Property')
        
        with open(self.input_file, 'r', encoding='utf-8') as f:
            for line_number, line in enumerate(f, 1):
                line = line.strip()
                
                # Check for entity markers
                entity_match = entity_pattern.match(line)
                if entity_match:
                    # Save previous entity if exists
                    if current_entity and not in_header:
                        self.index["entities"][current_entity] = {
                            "start_line": current_start,
                            "end_line": line_number - 1,
                            "type": self._determine_entity_type(current_entity)
                        }
                        entity_count += 1
                    
                    # Start new entity
                    current_entity = entity_match.group(1).strip()
                    current_start = line_number
                    in_header = False
                    
                    if header_end == 0:
                        header_end = line_number - 1
                        self.index["header_lines"] = header_end
                
                # Also check for inline definitions (without ### markers)
                elif not in_header:
                    class_match = class_pattern.match(line)
                    prop_match = property_pattern.match(line)
                    
                    if class_match or prop_match:
                        uri = class_match.group(1) if class_match else prop_match.group(1)
                        # Only track if it's a new entity
                        if uri not in self.index["entities"] and uri != current_entity:
                            if current_entity:
                                self.index["entities"][current_entity] = {
                                    "start_line": current_start,
                                    "end_line": line_number - 1,
                                    "type": self._determine_entity_type(current_entity)
                                }
                            current_entity = uri
                            current_start = line_number
                            entity_count += 1
        
        # Save the last entity
        if current_entity:
            self.index["entities"][current_entity] = {
                "start_line": current_start,
                "end_line": line_number,
                "type": self._determine_entity_type(current_entity)
            }
            entity_count += 1
        
        self.index["total_lines"] = line_number
        
        print(f"Scan complete:")
        print(f"  - Total lines: {line_number}")
        print(f"  - Header lines: {header_end}")
        print(f"  - Entities found: {entity_count}")
        
    def _determine_entity_type(self, entity_uri: str) -> str:
        """Determine the type of entity based on its URI or content."""
        # This is a simple heuristic - could be improved
        if "Property" in entity_uri:
            return "property"
        elif "Class" in entity_uri or entity_uri.startswith(":"):
            return "class"
        else:
            return "unknown"
    
    def extract_header(self) -> None:
        """Extract the header (prefixes and ontology metadata) to a separate file."""
        print(f"Extracting header to {self.header_file}...")
        
        if self.index["header_lines"] > 0:
            cmd = f"head -n {self.index['header_lines']} '{self.input_file}' > '{self.header_file}'"
            subprocess.run(cmd, shell=True, check=True)
            print(f"  - Header extracted ({self.index['header_lines']} lines)")
    
    def create_chunks(self, entities_per_chunk: int = 50) -> None:
        """Create chunks by grouping entities."""
        print(f"Creating chunks (max {entities_per_chunk} entities per chunk)...")
        
        # Group entities by type
        entities_by_type = defaultdict(list)
        for uri, info in self.index["entities"].items():
            entities_by_type[info["type"]].append((uri, info))
        
        chunk_id = 1
        
        # Create chunks for each type
        for entity_type, entities in entities_by_type.items():
            # Sort entities by start line for sequential access
            entities.sort(key=lambda x: x[1]["start_line"])
            
            # Group into chunks
            for i in range(0, len(entities), entities_per_chunk):
                chunk_entities = entities[i:i+entities_per_chunk]
                
                chunk_name = f"{chunk_id:02d}_{entity_type}_{i//entities_per_chunk + 1}"
                chunk_file = self.output_dir / f"{chunk_name}.ttl"
                
                # Calculate line range for this chunk
                start_line = chunk_entities[0][1]["start_line"]
                end_line = chunk_entities[-1][1]["end_line"]
                
                self.index["chunks"][chunk_name] = {
                    "file": str(chunk_file),
                    "type": entity_type,
                    "entities": [uri for uri, _ in chunk_entities],
                    "start_line": start_line,
                    "end_line": end_line,
                    "entity_count": len(chunk_entities)
                }
                
                chunk_id += 1
        
        print(f"  - Created {len(self.index['chunks'])} chunk definitions")
    
    def extract_chunks(self) -> None:
        """Extract chunk files using sed for efficiency."""
        print("Extracting chunk files...")
        
        for chunk_name, chunk_info in self.index["chunks"].items():
            start = chunk_info["start_line"]
            end = chunk_info["end_line"]
            output_file = chunk_info["file"]
            
            # Use sed to extract lines
            cmd = f"sed -n '{start},{end}p' '{self.input_file}' > '{output_file}'"
            subprocess.run(cmd, shell=True, check=True)
            
            print(f"  - Extracted {chunk_name}: lines {start}-{end} ({chunk_info['entity_count']} entities)")
    
    def create_combined_chunks(self) -> None:
        """Create combined chunk files that include the header."""
        print("Creating combined chunks with headers...")
        
        for chunk_name, chunk_info in self.index["chunks"].items():
            combined_file = self.output_dir / f"combined_{chunk_name}.ttl"
            chunk_file = chunk_info["file"]
            
            # Combine header and chunk
            cmd = f"cat '{self.header_file}' '{chunk_file}' > '{combined_file}'"
            subprocess.run(cmd, shell=True, check=True)
            
            chunk_info["combined_file"] = str(combined_file)
            print(f"  - Created combined_{chunk_name}.ttl")
    
    def save_index(self) -> None:
        """Save the chunk index to a JSON file."""
        print(f"Saving index to {self.index_file}...")
        
        with open(self.index_file, 'w', encoding='utf-8') as f:
            json.dump(self.index, f, indent=2)
        
        print("  - Index saved")
    
    def create_summary(self) -> None:
        """Create a summary report of the chunking."""
        summary_file = self.output_dir / "summary.txt"
        
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write("Ontology Chunking Summary\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"Source file: {self.input_file}\n")
            f.write(f"Total lines: {self.index['total_lines']}\n")
            f.write(f"Header lines: {self.index['header_lines']}\n")
            f.write(f"Total entities: {len(self.index['entities'])}\n")
            f.write(f"Total chunks: {len(self.index['chunks'])}\n\n")
            
            # Entity type breakdown
            entity_types = defaultdict(int)
            for info in self.index["entities"].values():
                entity_types[info["type"]] += 1
            
            f.write("Entity Types:\n")
            for entity_type, count in entity_types.items():
                f.write(f"  - {entity_type}: {count}\n")
            f.write("\n")
            
            # Chunk details
            f.write("Chunks:\n")
            for name, info in sorted(self.index["chunks"].items()):
                f.write(f"  {name}:\n")
                f.write(f"    - Type: {info['type']}\n")
                f.write(f"    - Entities: {info['entity_count']}\n")
                f.write(f"    - Lines: {info['start_line']}-{info['end_line']}\n")
                f.write(f"    - File: {Path(info['file']).name}\n")
                if "combined_file" in info:
                    f.write(f"    - Combined: {Path(info['combined_file']).name}\n")
                f.write("\n")
        
        print(f"Summary written to {summary_file}")
    
    def chunk(self, entities_per_chunk: int = 50, create_combined: bool = True) -> None:
        """Run the complete chunking process."""
        print(f"\nChunking {self.input_file.name} for token limit handling...")
        print("=" * 50)
        
        # Step 1: Scan the file
        self.scan_file()
        
        # Step 2: Extract header
        self.extract_header()
        
        # Step 3: Create chunk definitions
        self.create_chunks(entities_per_chunk)
        
        # Step 4: Extract chunks
        self.extract_chunks()
        
        # Step 5: Create combined files if requested
        if create_combined:
            self.create_combined_chunks()
        
        # Step 6: Save index
        self.save_index()
        
        # Step 7: Create summary
        self.create_summary()
        
        print("\nChunking complete!")
        print(f"Output directory: {self.output_dir}")


def main():
    parser = argparse.ArgumentParser(description="Efficiently chunk large ontology files to handle token limits")
    parser.add_argument("input_file", help="Input ontology file (TTL format)")
    parser.add_argument("-o", "--output-dir", help="Output directory for chunks")
    parser.add_argument("-n", "--entities-per-chunk", type=int, default=50,
                        help="Maximum entities per chunk (default: 50)")
    parser.add_argument("--no-combined", action="store_true",
                        help="Don't create combined files with headers")
    
    args = parser.parse_args()
    
    # Check if input file exists
    if not os.path.exists(args.input_file):
        print(f"Error: Input file '{args.input_file}' not found")
        sys.exit(1)
    
    # Create chunker and run
    chunker = OntologyChunker(args.input_file, args.output_dir)
    chunker.chunk(
        entities_per_chunk=args.entities_per_chunk,
        create_combined=not args.no_combined
    )


if __name__ == "__main__":
    main()
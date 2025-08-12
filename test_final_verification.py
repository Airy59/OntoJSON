#!/usr/bin/env python3
"""Final verification that all issues are resolved."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from owl2jsonschema import TransformationEngine, TransformationConfig, OntologyParser
import json

def verify_fix():
    """Verify that the fix resolves all issues."""
    
    test_file = Path("Documentation/test ontology for OWL to JSON schema transformation.ttl")
    
    print("=" * 80)
    print("FINAL VERIFICATION OF FIX")
    print("=" * 80)
    print()
    
    # Parse ontology
    parser = OntologyParser()
    ontology = parser.parse(str(test_file))
    
    # Use GUI default configuration
    config_dict = {
        "rules": {
            "class_to_object": {"enabled": True},
            "object_property": {"enabled": True},
            "disjoint_classes": {"enabled": True, "options": {"enforcement": "oneOf"}},
            "thing_with_uri": {"enabled": True}
        },
        "output": {
            "include_uri": False,
            "use_arrays": True
        }
    }
    
    config = TransformationConfig(config_dict)
    engine = TransformationEngine(config)
    result = engine.transform(ontology)
    
    # Verification checklist
    print("VERIFICATION CHECKLIST:")
    print("-" * 40)
    
    checks_passed = []
    
    # 1. Check partOf exists in RollingStock
    if "definitions" in result and "RollingStock" in result["definitions"]:
        rs = result["definitions"]["RollingStock"]
        partof_found = False
        
        # Check in direct properties
        if "properties" in rs and "partOf" in rs["properties"]:
            partof_found = True
        
        # Check in allOf
        if "allOf" in rs:
            for item in rs["allOf"]:
                if "properties" in item and "partOf" in item["properties"]:
                    partof_found = True
        
        if partof_found:
            print("✓ 1. partOf property exists in RollingStock")
            checks_passed.append(True)
        else:
            print("✗ 1. partOf property missing in RollingStock")
            checks_passed.append(False)
        
        # 2. Check partOf is optional (not required)
        required_fields = []
        if "required" in rs:
            required_fields.extend(rs["required"])
        if "allOf" in rs:
            for item in rs["allOf"]:
                if "required" in item:
                    required_fields.extend(item["required"])
        
        if "partOf" not in required_fields:
            print("✓ 2. partOf is optional (not in required fields)")
            checks_passed.append(True)
        else:
            print("✗ 2. partOf is incorrectly marked as required")
            checks_passed.append(False)
        
        # 3. Check RollingStock has disjoint union structure
        has_oneof = False
        if "oneOf" in rs:
            has_oneof = True
        elif "allOf" in rs:
            for item in rs["allOf"]:
                if "oneOf" in item:
                    has_oneof = True
        
        if has_oneof:
            print("✓ 3. RollingStock has disjoint union (oneOf) structure")
            checks_passed.append(True)
        else:
            print("✗ 3. RollingStock missing disjoint union structure")
            checks_passed.append(False)
        
        # 4. Check other properties are preserved
        other_checks = [
            ("Formation", "composedOf"),
            ("Vehicle", "ofType"),
            ("LegalEntity", "creationDate")
        ]
        
        for class_name, prop_name in other_checks:
            if class_name in result["definitions"]:
                class_def = result["definitions"][class_name]
                prop_found = False
                
                if "properties" in class_def and prop_name in class_def["properties"]:
                    prop_found = True
                elif "allOf" in class_def:
                    for item in class_def["allOf"]:
                        if "properties" in item and prop_name in item["properties"]:
                            prop_found = True
                
                if prop_found:
                    print(f"✓ 4. {prop_name} exists in {class_name}")
                    checks_passed.append(True)
                else:
                    print(f"✗ 4. {prop_name} missing in {class_name}")
                    checks_passed.append(False)
    
    print()
    print("=" * 80)
    if all(checks_passed):
        print("✅ ALL CHECKS PASSED - FIX IS COMPLETE AND WORKING!")
    else:
        print(f"❌ Some checks failed ({checks_passed.count(False)} of {len(checks_passed)})")
    print("=" * 80)
    
    return all(checks_passed)

if __name__ == "__main__":
    success = verify_fix()
    sys.exit(0 if success else 1)
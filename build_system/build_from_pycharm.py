#!/usr/bin/env python3
"""
PyCharm-compatible build script that uses the project's virtual environment.
Run this script directly from PyCharm to build the application.
"""

import sys
import os
import subprocess
from pathlib import Path

def main():
    """Main build function for PyCharm."""
    # Get the project root
    project_root = Path(__file__).parent.parent
    build_dir = Path(__file__).parent
    
    # Use the virtual environment's Python
    venv_python = project_root / '.venv' / 'bin' / 'python'
    if not venv_python.exists():
        # Try Windows path
        venv_python = project_root / '.venv' / 'Scripts' / 'python.exe'
    
    if not venv_python.exists():
        print("❌ Virtual environment not found!")
        print("Please ensure .venv exists in the project root.")
        return 1
    
    print(f"Using Python: {venv_python}")
    
    # Build script path
    macos_script = build_dir / 'scripts' / 'build_macos.py'
    
    # Run the build
    print("\n" + "="*60)
    print("    Building OntoJSON for macOS")
    print("="*60)
    
    # Ask user for options
    create_dmg = input("\nCreate DMG installer? (y/n): ").lower() == 'y'
    
    # Build command
    cmd = [str(venv_python), str(macos_script)]
    if not create_dmg:
        cmd.append('--no-dmg')
    
    # Execute
    result = subprocess.run(cmd, cwd=str(project_root))
    
    if result.returncode == 0:
        print("\n✅ Build completed successfully!")
        print(f"📦 App location: {build_dir}/dist/OntoJSON.app")
        if create_dmg:
            print(f"💿 DMG location: {build_dir}/dist/OntoJSON-1.0.0-macOS.dmg")
    else:
        print("\n❌ Build failed!")
        return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
#!/usr/bin/env python
"""
Main build script for OntoJSON application.
Supports building for macOS, Windows, and Linux platforms.
Works with virtual environments automatically.
"""

import sys
import os
import platform
import subprocess
from pathlib import Path

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent / 'scripts'))

class AppBuilder:
    def __init__(self):
        self.current_platform = platform.system()
        self.platforms = {
            '1': ('macOS', 'Darwin', self.build_macos),
            '2': ('Windows', 'Windows', self.build_windows),
            '3': ('Linux', 'Linux', self.build_linux),
        }
        self.project_root = Path(__file__).parent.parent
        self.python_cmd = self.detect_python()
    
    def detect_python(self):
        """Detect the best Python interpreter to use."""
        # First check if we're already in a virtual environment
        if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
            print(f"🐍 Using current virtual environment: {sys.prefix}")
            return sys.executable
        
        # Check for common virtual environment locations
        venv_paths = [
            self.project_root / '.venv' / 'bin' / 'python3',
            self.project_root / 'venv' / 'bin' / 'python3',
            self.project_root / '.venv' / 'Scripts' / 'python.exe',  # Windows
            self.project_root / 'venv' / 'Scripts' / 'python.exe',  # Windows
        ]
        
        for venv_python in venv_paths:
            if venv_python.exists():
                print(f"🐍 Found virtual environment: {venv_python}")
                return str(venv_python)
        
        # Fall back to current Python
        print(f"🐍 Using system Python: {sys.executable}")
        return sys.executable
    
    def check_dependencies(self):
        """Check if required packages are installed."""
        print("📦 Checking dependencies...")
        
        required = ['pyinstaller', 'Pillow']
        missing = []
        
        # Use subprocess to check with the detected Python
        for package in required:
            try:
                result = subprocess.run(
                    [self.python_cmd, '-c', f'import {package.lower()}'],
                    capture_output=True,
                    text=True
                )
                if result.returncode != 0:
                    missing.append(package)
            except:
                missing.append(package)
        
        if missing:
            print(f"\n⚠️  Missing packages: {', '.join(missing)}")
            response = input("\nInstall missing packages? (y/n): ").lower()
            if response == 'y':
                self.install_dependencies()
            else:
                print("❌ Cannot proceed without required packages")
                return False
        
        print("✅ All dependencies satisfied")
        return True
    
    def install_dependencies(self):
        """Install required packages."""
        print("\n📥 Installing dependencies...")
        
        requirements_file = Path(__file__).parent / 'requirements.txt'
        cmd = [self.python_cmd, '-m', 'pip', 'install', '-r', str(requirements_file)]
        
        result = subprocess.run(cmd)
        if result.returncode != 0:
            print("❌ Failed to install dependencies")
            return False
        
        print("✅ Dependencies installed successfully")
        return True
    
    def show_menu(self):
        """Display the platform selection menu."""
        print("\n" + "="*60)
        print("       OntoJSON Application Builder")
        print("="*60)
        print(f"\nCurrent platform: {self.current_platform}")
        print("\nSelect target platform:")
        print("\n  1. macOS   - Create .app bundle and .dmg installer")
        print("  2. Windows - Create .exe installer (Coming soon)")
        print("  3. Linux   - Create AppImage/deb package (Coming soon)")
        print("  4. All     - Build for all platforms (Coming soon)")
        print("\n  0. Exit")
        print("\n" + "-"*60)
    
    def build_macos(self, interactive=True):
        """Build for macOS."""
        if self.current_platform != 'Darwin':
            print("\n⚠️  Warning: Cross-platform builds may not work perfectly")
            print("   Best results are achieved when building on the target platform")
            if interactive:
                response = input("\nContinue anyway? (y/n): ").lower()
                if response != 'y':
                    return
        
        print("\n🍎 Building for macOS...")
        
        # Run the macOS build script
        script_path = Path(__file__).parent / 'scripts' / 'build_macos.py'
        
        # Ask about DMG creation or use defaults
        if interactive:
            create_dmg = input("\nCreate DMG installer? (y/n): ").lower() == 'y'
            # Ask about code signing
            sign_app = False
            if self.current_platform == 'Darwin':
                sign_app = input("Sign the application? (requires Developer ID) (y/n): ").lower() == 'y'
        else:
            # Non-interactive defaults
            print("Using default options: No DMG, No signing")
            create_dmg = False
            sign_app = False
        
        cmd = [self.python_cmd, str(script_path)]
        if not create_dmg:
            cmd.append('--no-dmg')
        if sign_app:
            cmd.append('--sign')
        
        result = subprocess.run(cmd, cwd=str(self.project_root))
        
        if result.returncode == 0:
            print("\n✅ Build completed successfully!")
            print(f"📦 App location: {Path(__file__).parent}/dist/OntoJSON.app")
            if create_dmg:
                print(f"💿 DMG location: {Path(__file__).parent}/dist/OntoJSON-1.0.0-macOS.dmg")
    
    def build_windows(self):
        """Build for Windows."""
        if self.current_platform != 'Windows' and self.current_platform != 'Darwin':
            print("\n⚠️  Warning: Building Windows executables works best on Windows")
            print("   You are currently on:", self.current_platform)
            response = input("\nContinue anyway? (y/n): ").lower()
            if response != 'y':
                return
        
        print("\n🪟 Building for Windows...")
        
        # Run the Windows build script
        script_path = Path(__file__).parent / 'scripts' / 'build_windows.py'
        
        if not script_path.exists():
            print("❌ Windows build script not found!")
            return
        
        # Ask about installer creation
        create_installer = False
        if self.current_platform == 'Windows':
            create_installer = input("\nCreate NSIS installer? (requires NSIS) (y/n): ").lower() == 'y'
        
        # Ask about portable ZIP
        create_zip = input("Create portable ZIP package? (y/n): ").lower() == 'y'
        
        cmd = [self.python_cmd, str(script_path)]
        if not create_installer:
            cmd.append('--no-installer')
        if not create_zip:
            cmd.append('--no-zip')
        
        subprocess.run(cmd, cwd=str(self.project_root))
    
    def build_linux(self):
        """Build for Linux."""
        print("\n🐧 Linux build support coming soon!")
        print("\nPlanned features:")
        print("  • Create AppImage for universal Linux support")
        print("  • Generate .deb package for Debian/Ubuntu")
        print("  • Generate .rpm package for Fedora/RHEL")
        print("  • Create Flatpak for modern distributions")
    
    def run(self):
        """Main execution loop."""
        # Check dependencies first
        if not self.check_dependencies():
            return
        
        while True:
            self.show_menu()
            
            choice = input("\nSelect option: ").strip()
            
            if choice == '0':
                print("\n👋 Goodbye!")
                break
            elif choice in self.platforms:
                name, required_platform, build_func = self.platforms[choice]
                build_func()
                input("\nPress Enter to continue...")
            elif choice == '4':
                print("\n🌍 Multi-platform build support coming soon!")
                input("\nPress Enter to continue...")
            else:
                print("\n❌ Invalid option, please try again")
                input("\nPress Enter to continue...")


def main():
    """Main entry point."""
    builder = AppBuilder()
    
    # Check if running with command line arguments
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        if arg in ['--macos', '-m', 'macos']:
            # Non-interactive when called from command line
            builder.build_macos(interactive=False)
        elif arg in ['--windows', '-w', 'windows']:
            builder.build_windows()
        elif arg in ['--linux', '-l', 'linux']:
            builder.build_linux()
        elif arg in ['--help', '-h']:
            print("Usage: python build_app.py [OPTIONS]")
            print("\nOptions:")
            print("  --macos, -m     Build for macOS (non-interactive)")
            print("  --windows, -w   Build for Windows (coming soon)")
            print("  --linux, -l     Build for Linux (coming soon)")
            print("  --help, -h      Show this help message")
            print("\nNote: Command line mode uses default options (no DMG, no signing)")
        else:
            print(f"Unknown option: {arg}")
            print("Use --help for available options")
    else:
        # Run interactive mode
        try:
            builder.run()
        except KeyboardInterrupt:
            print("\n\n⚠️  Build cancelled by user")
            sys.exit(1)


if __name__ == '__main__':
    main()
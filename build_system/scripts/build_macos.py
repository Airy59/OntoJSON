#!/usr/bin/env python
"""
macOS build script for OntoJSON application.
Creates a self-contained .app bundle and optionally a DMG installer.
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from configs.build_config import *

class MacOSBuilder:
    def __init__(self):
        self.app_path = None
        self.dmg_path = None
        
    def clean_build(self):
        """Clean previous build artifacts."""
        print("🧹 Cleaning previous builds...")
        
        # Clean PyInstaller directories
        for dir_name in ['build', 'dist', '__pycache__']:
            dir_path = PROJECT_ROOT / dir_name
            if dir_path.exists():
                shutil.rmtree(dir_path)
                
        # Clean temp directory
        if TEMP_DIR.exists():
            shutil.rmtree(TEMP_DIR)
        TEMP_DIR.mkdir(parents=True, exist_ok=True)
        
        # Clean dist directory but keep it
        if DIST_DIR.exists():
            shutil.rmtree(DIST_DIR)
        DIST_DIR.mkdir(parents=True, exist_ok=True)
        
    def create_icns_icon(self):
        """Convert PNG icon to macOS ICNS format."""
        print("🎨 Creating macOS icon...")
        
        iconset_path = TEMP_DIR / f"{APP_NAME}.iconset"
        iconset_path.mkdir(exist_ok=True)
        
        # Create different sized icons (macOS requires specific sizes)
        sizes = [16, 32, 64, 128, 256, 512, 1024]
        
        try:
            from PIL import Image
            
            # Open the source image
            img = Image.open(ICON_MAC)
            
            for size in sizes:
                # Standard resolution
                img_resized = img.resize((size, size), Image.Resampling.LANCZOS)
                img_resized.save(iconset_path / f"icon_{size}x{size}.png")
                
                # Retina resolution (2x)
                if size <= 512:
                    img_resized_2x = img.resize((size * 2, size * 2), Image.Resampling.LANCZOS)
                    img_resized_2x.save(iconset_path / f"icon_{size}x{size}@2x.png")
            
            # Convert iconset to icns
            icns_path = TEMP_DIR / f"{APP_NAME}.icns"
            subprocess.run([
                'iconutil', '-c', 'icns', 
                '-o', str(icns_path), 
                str(iconset_path)
            ], check=True)
            
            return str(icns_path)
            
        except Exception as e:
            print(f"⚠️  Warning: Could not create ICNS icon: {e}")
            return None
    
    def build_app_bundle(self):
        """Build the macOS application bundle using PyInstaller."""
        print("🔨 Building macOS application bundle...")
        
        # Create ICNS icon
        icns_path = self.create_icns_icon()
        
        # Detect current architecture
        import platform
        arch = platform.machine()
        if arch == 'arm64':
            target_arch = 'arm64'
            print("  Building for Apple Silicon (ARM64)")
        elif arch == 'x86_64':
            target_arch = 'x86_64'
            print("  Building for Intel (x86_64)")
        else:
            target_arch = None
            print(f"  Building for current architecture: {arch}")
        
        # Prepare PyInstaller command
        cmd = [
            sys.executable, '-m', 'PyInstaller',
            '--clean',
            '--noconfirm',
            '--name', APP_NAME,
            '--windowed',  # No console window
            '--onedir',  # Create app bundle, not single file
        ]
        
        # Add icon if created
        if icns_path:
            cmd.extend(['--icon', icns_path])
        
        # Add data files
        for data_spec in PYINSTALLER_OPTIONS['add_data']:
            if isinstance(data_spec, tuple):
                src, dest = data_spec
                cmd.extend(['--add-data', f'{src}:{dest}'])
            else:
                cmd.extend(['--add-data', data_spec])
        
        # Add paths for module searching
        if 'paths' in PYINSTALLER_OPTIONS:
            for path in PYINSTALLER_OPTIONS['paths']:
                cmd.extend(['--paths', path])
        
        # Add hidden imports
        for import_name in PYINSTALLER_OPTIONS['hidden_imports']:
            cmd.extend(['--hidden-import', import_name])
        
        # Exclude unnecessary modules
        for module in PYINSTALLER_OPTIONS['exclude_module']:
            cmd.extend(['--exclude-module', module])
        
        # macOS specific options
        cmd.extend([
            '--osx-bundle-identifier', APP_IDENTIFIER,
        ])
        
        # Only add target-arch if we have a valid one
        if target_arch:
            cmd.extend(['--target-arch', target_arch])
        
        # Add the main script
        cmd.append(MAIN_SCRIPT)
        
        # Run PyInstaller
        print(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, cwd=PROJECT_ROOT)
        
        if result.returncode != 0:
            print("❌ PyInstaller build failed!")
            return False
        
        # Move the app to dist directory
        built_app = PROJECT_ROOT / 'dist' / f'{APP_NAME}.app'
        if built_app.exists():
            self.app_path = DIST_DIR / f'{APP_NAME}.app'
            if self.app_path.exists():
                shutil.rmtree(self.app_path)
            shutil.move(str(built_app), str(self.app_path))
            
            # Update Info.plist with our custom values
            self.update_info_plist()
            
            print(f"✅ App bundle created: {self.app_path}")
            return True
        else:
            print("❌ App bundle not found after build!")
            return False
    
    def update_info_plist(self):
        """Update the Info.plist file in the app bundle."""
        if not self.app_path:
            return
            
        plist_path = self.app_path / 'Contents' / 'Info.plist'
        if not plist_path.exists():
            return
        
        print("📝 Updating Info.plist...")
        
        # Use plistlib to update the plist
        import plistlib
        
        with open(plist_path, 'rb') as f:
            plist = plistlib.load(f)
        
        # Update with our values
        plist.update({
            'CFBundleName': APP_NAME,
            'CFBundleDisplayName': APP_NAME,
            'CFBundleIdentifier': APP_IDENTIFIER,
            'CFBundleVersion': APP_VERSION,
            'CFBundleShortVersionString': APP_VERSION,
            'NSHumanReadableCopyright': APP_COPYRIGHT,
            'LSApplicationCategoryType': MACOS_CONFIG['category'],
            'LSMinimumSystemVersion': MACOS_CONFIG['minimum_system_version'],
            'NSHighResolutionCapable': True,
        })
        
        with open(plist_path, 'wb') as f:
            plistlib.dump(plist, f)
    
    def create_dmg(self):
        """Create a DMG installer for distribution."""
        if not self.app_path or not self.app_path.exists():
            print("❌ App bundle not found, skipping DMG creation")
            return False
        
        print("💿 Creating DMG installer...")
        
        dmg_name = f"{APP_NAME}-{APP_VERSION}-macOS"
        self.dmg_path = DIST_DIR / f"{dmg_name}.dmg"
        
        # Remove existing DMG if it exists
        if self.dmg_path.exists():
            self.dmg_path.unlink()
        
        # Create a temporary directory for DMG contents
        dmg_temp = TEMP_DIR / 'dmg_contents'
        if dmg_temp.exists():
            shutil.rmtree(dmg_temp)
        dmg_temp.mkdir(parents=True)
        
        # Copy app to temp directory
        shutil.copytree(self.app_path, dmg_temp / f'{APP_NAME}.app')
        
        # Create symbolic link to Applications
        os.symlink('/Applications', str(dmg_temp / 'Applications'))
        
        # Try using dmgbuild if available
        try:
            import dmgbuild
            
            # Create dmgbuild settings
            settings = {
                'title': APP_NAME,
                'background': None,
                'icon_size': 128,
                'window_rect': ((100, 100), (640, 480)),
                'icon_locations': {
                    f'{APP_NAME}.app': (140, 120),
                    'Applications': (500, 120),
                },
                'format': 'UDZO',
            }
            
            # Write settings to temp file
            settings_file = TEMP_DIR / 'dmg_settings.py'
            with open(settings_file, 'w') as f:
                f.write(f"settings = {settings}")
            
            dmgbuild.build_dmg(
                str(self.dmg_path),
                APP_NAME,
                str(settings_file)
            )
            
        except ImportError:
            # Fallback to hdiutil
            print("  Using hdiutil (dmgbuild not available)...")
            
            cmd = [
                'hdiutil', 'create',
                '-volname', APP_NAME,
                '-srcfolder', str(dmg_temp),
                '-ov',
                '-format', 'UDZO',
                str(self.dmg_path)
            ]
            
            result = subprocess.run(cmd)
            if result.returncode != 0:
                print("❌ DMG creation failed!")
                return False
        
        print(f"✅ DMG created: {self.dmg_path}")
        print(f"   Size: {self.dmg_path.stat().st_size / 1024 / 1024:.1f} MB")
        return True
    
    def sign_app(self):
        """Code sign the application (requires Apple Developer certificate)."""
        if not self.app_path:
            return
        
        print("🔐 Attempting to sign the application...")
        
        # Check if we have a signing identity
        result = subprocess.run(
            ['security', 'find-identity', '-v', '-p', 'codesigning'],
            capture_output=True, text=True
        )
        
        if 'Developer ID Application' not in result.stdout:
            print("  ⚠️  No Developer ID certificate found, skipping signing")
            print("  (The app will still work locally but may show security warnings)")
            return
        
        # Sign the app
        cmd = [
            'codesign',
            '--deep',
            '--force',
            '--verify',
            '--verbose',
            '--sign', 'Developer ID Application',
            '--options', 'runtime',
            str(self.app_path)
        ]
        
        result = subprocess.run(cmd)
        if result.returncode == 0:
            print("  ✅ Application signed successfully")
        else:
            print("  ⚠️  Signing failed, app will work but may show warnings")
    
    def build(self, create_dmg=True, sign=False):
        """Run the complete build process."""
        print(f"\n🚀 Building {APP_NAME} for macOS\n")
        
        # Clean previous builds
        self.clean_build()
        
        # Build the app bundle
        if not self.build_app_bundle():
            return False
        
        # Optionally sign the app
        if sign:
            self.sign_app()
        
        # Create DMG if requested
        if create_dmg:
            self.create_dmg()
        
        print("\n✨ Build complete!")
        print(f"\n📦 Output files:")
        print(f"  App Bundle: {self.app_path}")
        if self.dmg_path and self.dmg_path.exists():
            print(f"  DMG Installer: {self.dmg_path}")
        
        return True


def main():
    """Main entry point for the script."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Build OntoJSON for macOS')
    parser.add_argument('--no-dmg', action='store_true', 
                       help='Skip DMG creation')
    parser.add_argument('--sign', action='store_true',
                       help='Sign the application (requires Developer ID)')
    
    args = parser.parse_args()
    
    builder = MacOSBuilder()
    success = builder.build(
        create_dmg=not args.no_dmg,
        sign=args.sign
    )
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
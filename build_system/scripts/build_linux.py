#!/usr/bin/env python
"""
Linux build script for OntoJSON application.
Creates AppImage, .deb package, and optional .rpm package.
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path
import platform
import tempfile

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from configs.build_config import *

class LinuxBuilder:
    def __init__(self):
        self.appimage_path = None
        self.deb_path = None
        self.rpm_path = None
        self.app_dir = None
        
    def check_platform(self):
        """Check if we're on Linux or warn about cross-compilation."""
        current_os = platform.system()
        if current_os != 'Linux':
            print(f"⚠️  Warning: Building Linux executable on {current_os}")
            print("   Cross-platform builds are not recommended.")
            print("   For best results, build on Linux.")
            return False
        return True
    
    def check_dependencies(self):
        """Check for Linux-specific build dependencies."""
        print("🔍 Checking Linux build dependencies...")
        
        missing = []
        
        # Check for required tools
        tools = {
            'appimagetool': 'AppImage creation',
            'dpkg-deb': '.deb package creation',
            'rpmbuild': '.rpm package creation (optional)',
            'desktop-file-validate': 'Desktop file validation',
        }
        
        for tool, description in tools.items():
            if not shutil.which(tool):
                if tool != 'rpmbuild':  # RPM is optional
                    missing.append(f"{tool} ({description})")
                elif tool == 'rpmbuild':
                    print(f"  ⚠️  {tool} not found - RPM creation will be skipped")
        
        if missing:
            print("\n❌ Missing required tools:")
            for item in missing:
                print(f"   • {item}")
            print("\nInstall on Ubuntu/Debian:")
            print("  sudo apt-get install appimagetool dpkg-dev desktop-file-utils")
            print("\nInstall on Fedora/RHEL:")
            print("  sudo dnf install appimagetool dpkg rpm-build desktop-file-utils")
            return False
        
        return True
    
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
    
    def create_desktop_entry(self):
        """Create .desktop file for Linux desktop integration."""
        print("📝 Creating desktop entry...")
        
        desktop_content = f"""[Desktop Entry]
Name={LINUX_CONFIG['desktop_file']['Name']}
Comment={LINUX_CONFIG['desktop_file']['Comment']}
Exec={LINUX_CONFIG['desktop_file']['Exec']}
Icon={LINUX_CONFIG['desktop_file']['Icon']}
Terminal={LINUX_CONFIG['desktop_file']['Terminal']}
Type={LINUX_CONFIG['desktop_file']['Type']}
Categories={LINUX_CONFIG['desktop_file']['Categories']}
StartupNotify=true
"""
        
        desktop_file = TEMP_DIR / f"{APP_NAME}.desktop"
        with open(desktop_file, 'w') as f:
            f.write(desktop_content)
        
        # Validate desktop file
        result = subprocess.run(
            ['desktop-file-validate', str(desktop_file)],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            print(f"  ⚠️  Desktop file validation warnings: {result.stderr}")
        
        return desktop_file
    
    def build_executable(self):
        """Build the Linux executable using PyInstaller."""
        print("🔨 Building Linux executable...")
        
        # Prepare PyInstaller command
        cmd = [
            sys.executable, '-m', 'PyInstaller',
            '--clean',
            '--noconfirm',
            '--name', APP_NAME,
            '--windowed',  # No console window
            '--onefile',   # Single executable for Linux
        ]
        
        # Add icon (PNG format for Linux)
        if Path(ICON_LINUX).exists():
            cmd.extend(['--icon', ICON_LINUX])
        
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
        
        # Add the main script
        cmd.append(MAIN_SCRIPT)
        
        # Run PyInstaller
        print(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, cwd=PROJECT_ROOT)
        
        if result.returncode != 0:
            print("❌ PyInstaller build failed!")
            return None
        
        # Return the path to the built executable
        built_exe = PROJECT_ROOT / 'dist' / APP_NAME
        if built_exe.exists():
            return built_exe
        else:
            print("❌ Executable not found after build!")
            return None
    
    def create_appimage(self, exe_path):
        """Create AppImage for universal Linux distribution."""
        print("📦 Creating AppImage...")
        
        # Create AppDir structure
        appdir = TEMP_DIR / f"{APP_NAME}.AppDir"
        if appdir.exists():
            shutil.rmtree(appdir)
        appdir.mkdir(parents=True)
        
        # Create directory structure
        (appdir / "usr" / "bin").mkdir(parents=True)
        (appdir / "usr" / "share" / "applications").mkdir(parents=True)
        (appdir / "usr" / "share" / "icons" / "hicolor" / "256x256" / "apps").mkdir(parents=True)
        
        # Copy executable
        shutil.copy2(exe_path, appdir / "usr" / "bin" / APP_NAME)
        os.chmod(appdir / "usr" / "bin" / APP_NAME, 0o755)
        
        # Copy icon
        if Path(ICON_LINUX).exists():
            shutil.copy2(ICON_LINUX, appdir / "usr" / "share" / "icons" / "hicolor" / "256x256" / "apps" / f"{APP_NAME}.png")
            # Also copy to root for AppImage
            shutil.copy2(ICON_LINUX, appdir / f"{APP_NAME}.png")
        
        # Create desktop entry
        desktop_file = self.create_desktop_entry()
        shutil.copy2(desktop_file, appdir / "usr" / "share" / "applications" / f"{APP_NAME}.desktop")
        # Also copy to root for AppImage
        shutil.copy2(desktop_file, appdir / f"{APP_NAME}.desktop")
        
        # Create AppRun script
        apprun_content = f"""#!/bin/bash
HERE="$(dirname "$(readlink -f "${{0}}")")"
export PATH="${{HERE}}/usr/bin:${{PATH}}"
export LD_LIBRARY_PATH="${{HERE}}/usr/lib:${{LD_LIBRARY_PATH}}"
exec "${{HERE}}/usr/bin/{APP_NAME}" "$@"
"""
        apprun_file = appdir / "AppRun"
        with open(apprun_file, 'w') as f:
            f.write(apprun_content)
        os.chmod(apprun_file, 0o755)
        
        # Build AppImage
        self.appimage_path = DIST_DIR / f"{APP_NAME}-{APP_VERSION}-x86_64.AppImage"
        
        # Check if appimagetool is available
        if shutil.which('appimagetool'):
            cmd = ['appimagetool', str(appdir), str(self.appimage_path)]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"✅ AppImage created: {self.appimage_path}")
                print(f"   Size: {self.appimage_path.stat().st_size / 1024 / 1024:.1f} MB")
                return True
            else:
                print(f"❌ AppImage creation failed: {result.stderr}")
        else:
            print("⚠️  appimagetool not found. AppImage creation skipped.")
            print("   Install with: wget https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage")
        
        return False
    
    def create_deb_package(self, exe_path):
        """Create .deb package for Debian/Ubuntu."""
        print("📦 Creating .deb package...")
        
        # Create package directory structure
        pkg_name = f"{APP_NAME.lower()}_{APP_VERSION}_amd64"
        pkg_dir = TEMP_DIR / pkg_name
        if pkg_dir.exists():
            shutil.rmtree(pkg_dir)
        
        # Create directory structure
        (pkg_dir / "DEBIAN").mkdir(parents=True)
        (pkg_dir / "usr" / "bin").mkdir(parents=True)
        (pkg_dir / "usr" / "share" / "applications").mkdir(parents=True)
        (pkg_dir / "usr" / "share" / "icons" / "hicolor" / "256x256" / "apps").mkdir(parents=True)
        (pkg_dir / "usr" / "share" / "doc" / APP_NAME.lower()).mkdir(parents=True)
        
        # Copy executable
        shutil.copy2(exe_path, pkg_dir / "usr" / "bin" / APP_NAME)
        os.chmod(pkg_dir / "usr" / "bin" / APP_NAME, 0o755)
        
        # Copy icon
        if Path(ICON_LINUX).exists():
            shutil.copy2(ICON_LINUX, pkg_dir / "usr" / "share" / "icons" / "hicolor" / "256x256" / "apps" / f"{APP_NAME}.png")
        
        # Copy desktop file
        desktop_file = self.create_desktop_entry()
        shutil.copy2(desktop_file, pkg_dir / "usr" / "share" / "applications" / f"{APP_NAME}.desktop")
        
        # Create control file
        control_content = f"""Package: {APP_NAME.lower()}
Version: {APP_VERSION}
Section: misc
Priority: optional
Architecture: amd64
Depends: python3, python3-pyqt6
Maintainer: {APP_AUTHOR}
Description: {APP_DESCRIPTION}
 OntoJSON is a tool for converting OWL ontologies to JSON Schema.
 It provides both a graphical interface and command-line tools
 for transforming ontological models into JSON Schema format.
"""
        
        with open(pkg_dir / "DEBIAN" / "control", 'w') as f:
            f.write(control_content)
        
        # Create copyright file
        copyright_content = f"""{APP_COPYRIGHT}

This software is licensed under the European Union Public License (EUPL) v1.2.
"""
        
        with open(pkg_dir / "usr" / "share" / "doc" / APP_NAME.lower() / "copyright", 'w') as f:
            f.write(copyright_content)
        
        # Build the .deb package
        self.deb_path = DIST_DIR / f"{pkg_name}.deb"
        
        cmd = ['dpkg-deb', '--build', str(pkg_dir), str(self.deb_path)]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ .deb package created: {self.deb_path}")
            print(f"   Size: {self.deb_path.stat().st_size / 1024 / 1024:.1f} MB")
            return True
        else:
            print(f"❌ .deb package creation failed: {result.stderr}")
            return False
    
    def create_rpm_package(self, exe_path):
        """Create .rpm package for Fedora/RHEL."""
        print("📦 Creating .rpm package...")
        
        # Check if rpmbuild is available
        if not shutil.which('rpmbuild'):
            print("⚠️  rpmbuild not found. RPM creation skipped.")
            print("   Install on Fedora/RHEL: sudo dnf install rpm-build")
            return False
        
        # Create RPM build directories
        rpm_dir = TEMP_DIR / "rpmbuild"
        for subdir in ['BUILD', 'RPMS', 'SOURCES', 'SPECS', 'SRPMS']:
            (rpm_dir / subdir).mkdir(parents=True, exist_ok=True)
        
        # Create tarball of the application
        tar_name = f"{APP_NAME}-{APP_VERSION}"
        tar_dir = TEMP_DIR / tar_name
        tar_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy files to tar directory
        shutil.copy2(exe_path, tar_dir / APP_NAME)
        if Path(ICON_LINUX).exists():
            shutil.copy2(ICON_LINUX, tar_dir / f"{APP_NAME}.png")
        desktop_file = self.create_desktop_entry()
        shutil.copy2(desktop_file, tar_dir / f"{APP_NAME}.desktop")
        
        # Create tarball
        tarball = rpm_dir / "SOURCES" / f"{tar_name}.tar.gz"
        subprocess.run(
            ['tar', '-czf', str(tarball), '-C', str(TEMP_DIR), tar_name],
            check=True
        )
        
        # Create spec file
        spec_content = f"""Name:           {APP_NAME.lower()}
Version:        {APP_VERSION}
Release:        1%{{?dist}}
Summary:        {APP_DESCRIPTION}
License:        EUPL-1.2
URL:            https://github.com/yourusername/{APP_NAME.lower()}
Source0:        {tar_name}.tar.gz

Requires:       python3
Requires:       python3-qt6

%description
OntoJSON is a tool for converting OWL ontologies to JSON Schema.
It provides both a graphical interface and command-line tools
for transforming ontological models into JSON Schema format.

%prep
%setup -q

%install
mkdir -p %{{buildroot}}/usr/bin
mkdir -p %{{buildroot}}/usr/share/applications
mkdir -p %{{buildroot}}/usr/share/icons/hicolor/256x256/apps

install -m 755 {APP_NAME} %{{buildroot}}/usr/bin/
install -m 644 {APP_NAME}.desktop %{{buildroot}}/usr/share/applications/
install -m 644 {APP_NAME}.png %{{buildroot}}/usr/share/icons/hicolor/256x256/apps/

%files
/usr/bin/{APP_NAME}
/usr/share/applications/{APP_NAME}.desktop
/usr/share/icons/hicolor/256x256/apps/{APP_NAME}.png

%changelog
* $(date +"%a %b %d %Y") {APP_AUTHOR} - {APP_VERSION}-1
- Initial RPM release
"""
        
        spec_file = rpm_dir / "SPECS" / f"{APP_NAME.lower()}.spec"
        with open(spec_file, 'w') as f:
            f.write(spec_content)
        
        # Build RPM
        cmd = ['rpmbuild', '-bb', '--define', f'_topdir {rpm_dir}', str(spec_file)]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            # Find the built RPM
            rpm_arch = 'x86_64' if platform.machine() == 'x86_64' else platform.machine()
            built_rpm = rpm_dir / "RPMS" / rpm_arch / f"{APP_NAME.lower()}-{APP_VERSION}-1.{rpm_arch}.rpm"
            
            if built_rpm.exists():
                self.rpm_path = DIST_DIR / f"{APP_NAME.lower()}-{APP_VERSION}-1.{rpm_arch}.rpm"
                shutil.move(str(built_rpm), str(self.rpm_path))
                print(f"✅ .rpm package created: {self.rpm_path}")
                print(f"   Size: {self.rpm_path.stat().st_size / 1024 / 1024:.1f} MB")
                return True
        
        print(f"❌ .rpm package creation failed: {result.stderr if result else 'Unknown error'}")
        return False
    
    def build(self, create_appimage=True, create_deb=True, create_rpm=True):
        """Run the complete build process."""
        print(f"\n🚀 Building {APP_NAME} for Linux\n")
        
        # Check platform
        is_linux = self.check_platform()
        
        if is_linux:
            # Check dependencies only on Linux
            if not self.check_dependencies():
                print("\n❌ Please install required dependencies and try again.")
                return False
        
        # Clean previous builds
        self.clean_build()
        
        # Build the executable
        exe_path = self.build_executable()
        if not exe_path:
            return False
        
        # Move executable to dist directory
        final_exe = DIST_DIR / APP_NAME
        if final_exe.exists():
            final_exe.unlink()
        shutil.move(str(exe_path), str(final_exe))
        
        print(f"\n✅ Executable created: {final_exe}")
        print(f"   Size: {final_exe.stat().st_size / 1024 / 1024:.1f} MB")
        
        # Create packages only on Linux
        if is_linux:
            # Create AppImage
            if create_appimage:
                self.create_appimage(final_exe)
            
            # Create .deb package
            if create_deb:
                self.create_deb_package(final_exe)
            
            # Create .rpm package
            if create_rpm:
                self.create_rpm_package(final_exe)
        else:
            print("\n⚠️  Package creation skipped (not on Linux)")
            print("   The standalone executable has been created.")
        
        print("\n✨ Build complete!")
        print(f"\n📦 Output files:")
        print(f"  Executable: {final_exe}")
        if self.appimage_path and self.appimage_path.exists():
            print(f"  AppImage: {self.appimage_path}")
        if self.deb_path and self.deb_path.exists():
            print(f"  .deb Package: {self.deb_path}")
        if self.rpm_path and self.rpm_path.exists():
            print(f"  .rpm Package: {self.rpm_path}")
        
        return True


def main():
    """Main entry point for the script."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Build OntoJSON for Linux')
    parser.add_argument('--no-appimage', action='store_true', 
                       help='Skip AppImage creation')
    parser.add_argument('--no-deb', action='store_true',
                       help='Skip .deb package creation')
    parser.add_argument('--no-rpm', action='store_true',
                       help='Skip .rpm package creation')
    
    args = parser.parse_args()
    
    builder = LinuxBuilder()
    success = builder.build(
        create_appimage=not args.no_appimage,
        create_deb=not args.no_deb,
        create_rpm=not args.no_rpm
    )
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
#!/usr/bin/env python
"""
Windows build script for OntoJSON application.
Creates a self-contained .exe and optionally an installer.
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path
import platform

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from configs.build_config import *

class WindowsBuilder:
    def __init__(self):
        self.exe_path = None
        self.installer_path = None
        
    def check_platform(self):
        """Check if we're on Windows or warn about cross-compilation."""
        current_os = platform.system()
        if current_os != 'Windows':
            print(f"⚠️  Warning: Building Windows executable on {current_os}")
            print("   Cross-platform builds may have limitations.")
            print("   For best results, build on Windows.")
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
    
    def create_ico_icon(self):
        """Convert PNG icon to Windows ICO format."""
        print("🎨 Creating Windows icon...")
        
        ico_path = TEMP_DIR / f"{APP_NAME}.ico"
        
        try:
            from PIL import Image
            
            # Open the source image
            img = Image.open(ICON_WIN)
            
            # Create multiple sizes for ICO (Windows requires specific sizes)
            sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
            
            # Create ICO with multiple resolutions
            img.save(
                ico_path,
                format='ICO',
                sizes=sizes,
                append_images=[img.resize(size, Image.Resampling.LANCZOS) for size in sizes[1:]]
            )
            
            return str(ico_path)
            
        except Exception as e:
            print(f"⚠️  Warning: Could not create ICO icon: {e}")
            # Try to use the PNG directly (PyInstaller can handle it)
            return str(ICON_WIN)
    
    def build_executable(self):
        """Build the Windows executable using PyInstaller."""
        print("🔨 Building Windows executable...")
        
        # Create ICO icon
        icon_path = self.create_ico_icon()
        
        # Prepare PyInstaller command
        cmd = [
            sys.executable, '-m', 'PyInstaller',
            '--clean',
            '--noconfirm',
            '--name', APP_NAME,
            '--windowed',  # No console window
            '--onefile',   # Single executable file for Windows
        ]
        
        # Add icon
        if icon_path:
            cmd.extend(['--icon', icon_path])
        
        # Add version information for Windows
        version_file = self.create_version_file()
        if version_file:
            cmd.extend(['--version-file', version_file])
        
        # Add data files
        for data_spec in PYINSTALLER_OPTIONS['add_data']:
            if isinstance(data_spec, tuple):
                src, dest = data_spec
                # Use appropriate separator based on current platform
                separator = ';' if platform.system() == 'Windows' else ':'
                cmd.extend(['--add-data', f'{src}{separator}{dest}'])
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
        
        # Windows-specific: Add UAC manifest for proper permissions (only on Windows)
        if platform.system() == 'Windows':
            cmd.extend(['--uac-admin'])
        
        # Add the main script
        cmd.append(MAIN_SCRIPT)
        
        # Run PyInstaller
        print(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, cwd=PROJECT_ROOT, shell=(platform.system() == 'Windows'))
        
        if result.returncode != 0:
            print("❌ PyInstaller build failed!")
            return False
        
        # Move the executable to dist directory
        built_exe = PROJECT_ROOT / 'dist' / f'{APP_NAME}.exe'
        if built_exe.exists():
            self.exe_path = DIST_DIR / f'{APP_NAME}.exe'
            if self.exe_path.exists():
                self.exe_path.unlink()
            shutil.move(str(built_exe), str(self.exe_path))
            
            print(f"✅ Executable created: {self.exe_path}")
            print(f"   Size: {self.exe_path.stat().st_size / 1024 / 1024:.1f} MB")
            return True
        else:
            print("❌ Executable not found after build!")
            return False
    
    def create_version_file(self):
        """Create version file for Windows executable metadata."""
        print("📝 Creating version information...")
        
        version_file = TEMP_DIR / 'version.txt'
        
        # Parse version numbers
        version_parts = APP_VERSION.split('.')
        while len(version_parts) < 4:
            version_parts.append('0')
        
        version_content = f"""
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=({','.join(version_parts)}),
    prodvers=({','.join(version_parts)}),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo(
      [
        StringTable(
          u'040904B0',
          [
            StringStruct(u'CompanyName', u'{WINDOWS_CONFIG["company_name"]}'),
            StringStruct(u'FileDescription', u'{WINDOWS_CONFIG["file_description"]}'),
            StringStruct(u'FileVersion', u'{APP_VERSION}'),
            StringStruct(u'InternalName', u'{WINDOWS_CONFIG["internal_name"]}'),
            StringStruct(u'LegalCopyright', u'{WINDOWS_CONFIG["legal_copyright"]}'),
            StringStruct(u'OriginalFilename', u'{WINDOWS_CONFIG["original_filename"]}'),
            StringStruct(u'ProductName', u'{WINDOWS_CONFIG["product_name"]}'),
            StringStruct(u'ProductVersion', u'{WINDOWS_CONFIG["product_version"]}')
          ]
        )
      ]
    ),
    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)
"""
        
        # Write with UTF-8 encoding and BOM to ensure proper reading by PyInstaller
        with open(version_file, 'w', encoding='utf-8-sig') as f:
            f.write(version_content)
        
        return str(version_file)
    
    def create_installer_nsis(self):
        """Create NSIS installer for Windows."""
        print("📦 Creating NSIS installer...")
        
        if not self.exe_path or not self.exe_path.exists():
            print("❌ Executable not found, skipping installer creation")
            return False
        
        # Create NSIS script
        nsis_script = TEMP_DIR / f'{APP_NAME}.nsi'
        
        nsis_content = f'''
; OntoJSON NSIS Installer Script

!include "MUI2.nsh"

; General Settings
Name "{APP_NAME}"
OutFile "{DIST_DIR}\\{APP_NAME}-{APP_VERSION}-Setup.exe"
InstallDir "$PROGRAMFILES64\\{APP_NAME}"
InstallDirRegKey HKLM "Software\\{APP_NAME}" "Install_Dir"
RequestExecutionLevel admin

; UI Settings
!define MUI_ABORTWARNING
!define MUI_ICON "{ICON_WIN}"

; Pages
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "${{NSISDIR}}\\Docs\\Modern UI\\License.txt"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_WELCOME
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH

; Languages
!insertmacro MUI_LANGUAGE "English"

; Installer Section
Section "MainSection" SEC01
  SetOutPath "$INSTDIR"
  
  ; Copy files
  File "{self.exe_path}"
  
  ; Create shortcuts
  CreateDirectory "$SMPROGRAMS\\{APP_NAME}"
  CreateShortcut "$SMPROGRAMS\\{APP_NAME}\\{APP_NAME}.lnk" "$INSTDIR\\{APP_NAME}.exe"
  CreateShortcut "$SMPROGRAMS\\{APP_NAME}\\Uninstall.lnk" "$INSTDIR\\Uninstall.exe"
  CreateShortcut "$DESKTOP\\{APP_NAME}.lnk" "$INSTDIR\\{APP_NAME}.exe"
  
  ; Write registry keys
  WriteRegStr HKLM "Software\\{APP_NAME}" "Install_Dir" "$INSTDIR"
  WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{APP_NAME}" "DisplayName" "{APP_NAME}"
  WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{APP_NAME}" "UninstallString" '"$INSTDIR\\Uninstall.exe"'
  WriteRegDWORD HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{APP_NAME}" "NoModify" 1
  WriteRegDWORD HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{APP_NAME}" "NoRepair" 1
  WriteUninstaller "$INSTDIR\\Uninstall.exe"
SectionEnd

; Uninstaller Section
Section "Uninstall"
  Delete "$INSTDIR\\{APP_NAME}.exe"
  Delete "$INSTDIR\\Uninstall.exe"
  Delete "$DESKTOP\\{APP_NAME}.lnk"
  
  RMDir /r "$SMPROGRAMS\\{APP_NAME}"
  RMDir "$INSTDIR"
  
  DeleteRegKey HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{APP_NAME}"
  DeleteRegKey HKLM "Software\\{APP_NAME}"
SectionEnd
'''
        
        with open(nsis_script, 'w') as f:
            f.write(nsis_content)
        
        # Check if NSIS is available
        nsis_path = shutil.which('makensis')
        if not nsis_path:
            print("⚠️  NSIS not found. Please install NSIS to create installer.")
            print("   Download from: https://nsis.sourceforge.io/Download")
            return False
        
        # Compile the installer
        cmd = ['makensis', str(nsis_script)]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            self.installer_path = DIST_DIR / f'{APP_NAME}-{APP_VERSION}-Setup.exe'
            if self.installer_path.exists():
                print(f"✅ Installer created: {self.installer_path}")
                print(f"   Size: {self.installer_path.stat().st_size / 1024 / 1024:.1f} MB")
                return True
        
        print(f"❌ Installer creation failed: {result.stderr}")
        return False
    
    def create_portable_zip(self):
        """Create a portable ZIP package."""
        print("📦 Creating portable ZIP package...")
        
        if not self.exe_path or not self.exe_path.exists():
            print("❌ Executable not found, skipping ZIP creation")
            return False
        
        # Create ZIP file
        import zipfile
        
        zip_path = DIST_DIR / f'{APP_NAME}-{APP_VERSION}-Windows-Portable.zip'
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Add the executable
            zipf.write(self.exe_path, f'{APP_NAME}/{APP_NAME}.exe')
            
            # Add a README
            readme_content = f"""
{APP_NAME} - Portable Version
Version: {APP_VERSION}

This is a portable version of {APP_NAME} for Windows.
No installation required - just extract and run {APP_NAME}.exe

{APP_COPYRIGHT}
"""
            zipf.writestr(f'{APP_NAME}/README.txt', readme_content)
        
        print(f"✅ Portable ZIP created: {zip_path}")
        print(f"   Size: {zip_path.stat().st_size / 1024 / 1024:.1f} MB")
        return True
    
    def build(self, create_installer=True, create_zip=True):
        """Run the complete build process."""
        print(f"\n🚀 Building {APP_NAME} for Windows\n")
        
        # Check platform
        is_windows = self.check_platform()
        
        # Clean previous builds
        self.clean_build()
        
        # Build the executable
        if not self.build_executable():
            return False
        
        # Create installer if requested and on Windows
        if create_installer and is_windows:
            self.create_installer_nsis()
        elif create_installer:
            print("⚠️  Installer creation skipped (not on Windows)")
        
        # Create portable ZIP
        if create_zip:
            self.create_portable_zip()
        
        print("\n✨ Build complete!")
        print(f"\n📦 Output files:")
        print(f"  Executable: {self.exe_path}")
        if self.installer_path and self.installer_path.exists():
            print(f"  Installer: {self.installer_path}")
        
        return True


def main():
    """Main entry point for the script."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Build OntoJSON for Windows')
    parser.add_argument('--no-installer', action='store_true', 
                       help='Skip installer creation')
    parser.add_argument('--no-zip', action='store_true',
                       help='Skip portable ZIP creation')
    
    args = parser.parse_args()
    
    builder = WindowsBuilder()
    success = builder.build(
        create_installer=not args.no_installer,
        create_zip=not args.no_zip
    )
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
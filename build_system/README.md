# OntoJSON Build System

This build system creates self-contained applications for OntoJSON across different platforms.

## 📋 Prerequisites

- Python 3.8 or higher
- PyQt6 installed in your environment
- Platform-specific tools:
  - **macOS**: Xcode Command Line Tools
  - **Windows**: Visual Studio Build Tools (coming soon)
  - **Linux**: build-essential package (coming soon)

## 🚀 Quick Start

### Simple macOS App Bundle (Recommended)
```bash
# From project root - creates OntoJSON.app
./create_app_bundle.sh
# Output: ./OntoJSON.app (in project root)
```

### Advanced Build System
```bash
cd build_system
python build_app.py  # Interactive mode
```

### Command Line Mode
```bash
# Build for macOS (non-interactive, uses defaults: no DMG, no signing)
python build_app.py --macos

# Build for Windows (coming soon)
python build_app.py --windows

# Build for Linux (coming soon)
python build_app.py --linux
```

**Note:**
- `build_app.py` automatically detects and uses virtual environments (.venv or venv) if present
- Command-line mode (`--macos`) runs non-interactively with default options
- Interactive mode is available by running without arguments: `python build_app.py`

## 📦 Installation

1. **Install required packages:**
```bash
pip install -r requirements.txt
```

2. **Run the build script:**
```bash
python build_app.py
```

## 🍎 macOS Build

The macOS builder creates:
- **`.app` bundle**: A standard macOS application
- **`.dmg` installer**: A distributable disk image

### Building from PyCharm or any IDE:

The `build_app.py` script automatically detects and uses virtual environments:

1. **Ensure packages are installed in your venv:**
```bash
# From project root (after activating venv)
pip install pyinstaller pillow
```

2. **Run the build script (non-interactive):**
```bash
# From project root
python build_system/build_app.py --macos
```

3. **Or configure IDE Run Configuration:**
   - Go to Run → Edit Configurations
   - Create new Python configuration
   - Script path: `build_system/build_app.py`
   - Working directory: Project root
   - Script parameters: `--macos` (for non-interactive build)
   - Python interpreter: Project virtual environment

### Features:
- ✅ Universal binary (Intel + Apple Silicon)
- ✅ Custom app icon (ICNS format)
- ✅ Proper app naming in dock and menus
- ✅ Optional code signing (requires Developer ID)
- ✅ Compressed DMG with drag-to-install interface

### Build Options:
```bash
# Non-interactive build from project root (recommended)
python build_system/build_app.py --macos

# Interactive build with options
cd build_system
python build_app.py
# Then select option 1 for macOS
```

### Output:
- **Simple method** (`create_app_bundle.sh`):
  - Location: `./OntoJSON.app` (in project root)
  - Size: ~4.2MB (launcher, requires .venv)
- **Advanced build system** (`build_app.py`):
  - Location: `build_system/dist/OntoJSON.app`
  - Size: ~112MB (self-contained with Python & all dependencies)
  - DMG (if created): `build_system/dist/OntoJSON-1.0.0-macOS.dmg`

## 🪟 Windows Build

The Windows builder creates:
- **`.exe` file**: A standalone executable
- **NSIS installer**: Optional installer with Start Menu shortcuts
- **Portable ZIP**: No-installation-required package

### Features:
- ✅ Single executable file
- ✅ Custom Windows icon (ICO format)
- ✅ Version information embedded
- ✅ NSIS installer creation (optional)
- ✅ Portable ZIP package
- ✅ UAC manifest for proper permissions

### Build Options:
```bash
# Basic build (exe + ZIP)
python scripts/build_windows.py

# Executable only (no installer or ZIP)
python scripts/build_windows.py --no-installer --no-zip

# With NSIS installer (requires NSIS installed)
python scripts/build_windows.py
```

### Requirements:
- **PyInstaller**: Automatically installed
- **NSIS** (optional): For creating installer
  - Download from: https://nsis.sourceforge.io/Download
  - Required only if you want to create an installer

### Cross-Platform Building Limitations:
**IMPORTANT:** PyInstaller can only create executables for the platform it's running on:
- On macOS → Creates .app bundles (not .exe)
- On Windows → Creates .exe files (not .app)
- On Linux → Creates Linux executables

To build for Windows, you need:
1. A Windows machine or VM
2. Or use GitHub Actions/CI for cross-platform builds
3. Or use Wine (complex, not recommended)

### Output:
- Executable: `dist/OntoJSON.exe`
- Installer: `dist/OntoJSON-1.0.0-Setup.exe` (if NSIS available)
- Portable: `dist/OntoJSON-1.0.0-Windows-Portable.zip`

## 🐧 Linux Build (Coming Soon)

Planned features:
- AppImage for universal Linux support
- `.deb` package for Debian/Ubuntu
- `.rpm` package for Fedora/RHEL
- Flatpak for modern distributions

## 📁 Directory Structure

### Project Root
```
OntoJSON/
├── create_app_bundle.sh  # Simple macOS app builder (creates app in root)
├── OntoJSON.app/         # Created by create_app_bundle.sh
└── build_system/         # Advanced build system (below)
```

### Build System Directory
```
build_system/
├── build_app.py          # Main build script with platform selection
├── requirements.txt      # Build dependencies
├── README.md            # This file
├── configs/
│   └── build_config.py  # Build configuration and metadata
├── scripts/
│   ├── build_macos.py   # macOS-specific builder
│   ├── build_windows.py # Windows builder (coming soon)
│   └── build_linux.py   # Linux builder (coming soon)
├── dist/                # Output directory for built applications (when using advanced build)
└── temp/                # Temporary build files
```

## ⚙️ Configuration

Edit `configs/build_config.py` to customize:
- Application metadata (name, version, author)
- Icons and resources
- PyInstaller options
- Platform-specific settings

## 🐛 Troubleshooting

### macOS Issues

**"App can't be opened because it is from an unidentified developer"**
- Right-click the app and select "Open"
- Or go to System Preferences → Security & Privacy → General
- Click "Open Anyway"

**Icon not showing correctly**
- Ensure the source PNG is at least 1024x1024 pixels
- The script automatically generates all required icon sizes

**DMG creation fails**
- Install dmgbuild: `pip install dmgbuild`
- Or the script will fall back to using hdiutil

### General Issues

**PyInstaller not found**
- Run: `pip install pyinstaller`

**Hidden import errors**
- Add missing modules to `hidden_imports` in `build_config.py`

**Large file size**
- Add unnecessary modules to `exclude_module` in `build_config.py`

## 📄 License

The build system is part of the OntoJSON project and follows the same EUPL v1.2 license.

## 🤝 Contributing

To add support for a new platform:
1. Create a new builder script in `scripts/`
2. Add platform configuration to `configs/build_config.py`
3. Update `build_app.py` to include the new platform

## 📞 Support

For issues or questions, please open an issue in the main OntoJSON repository.
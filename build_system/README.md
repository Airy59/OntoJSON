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

### Interactive Mode
```bash
cd build_system
python build_app.py
```

### Command Line Mode
```bash
# Build for macOS
python build_app.py --macos

# Build for Windows (coming soon)
python build_app.py --windows

# Build for Linux (coming soon)
python build_app.py --linux
```

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

### Features:
- ✅ Universal binary (Intel + Apple Silicon)
- ✅ Custom app icon (ICNS format)
- ✅ Proper app naming in dock and menus
- ✅ Optional code signing (requires Developer ID)
- ✅ Compressed DMG with drag-to-install interface

### Build Options:
```bash
# Basic build (app + DMG)
python scripts/build_macos.py

# App bundle only (no DMG)
python scripts/build_macos.py --no-dmg

# With code signing
python scripts/build_macos.py --sign
```

### Output:
- App Bundle: `dist/OntoJSON.app`
- DMG Installer: `dist/OntoJSON-1.0.0-macOS.dmg`

## 🪟 Windows Build (Coming Soon)

Planned features:
- Standalone `.exe` file
- MSI installer with Start Menu integration
- Digital signature support
- Auto-update functionality

## 🐧 Linux Build (Coming Soon)

Planned features:
- AppImage for universal Linux support
- `.deb` package for Debian/Ubuntu
- `.rpm` package for Fedora/RHEL
- Flatpak for modern distributions

## 📁 Directory Structure

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
├── dist/                # Output directory for built applications
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
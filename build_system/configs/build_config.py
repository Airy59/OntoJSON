"""
Build configuration for OntoJSON application packaging.
"""

import os
from pathlib import Path

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
BUILD_DIR = PROJECT_ROOT / "build_system"
DIST_DIR = BUILD_DIR / "dist"
TEMP_DIR = BUILD_DIR / "temp"
SRC_DIR = PROJECT_ROOT / "src"
RESOURCES_DIR = PROJECT_ROOT / "Resources"

# Application metadata
APP_NAME = "OntoJSON"
APP_VERSION = "1.0.0"
APP_IDENTIFIER = "com.owl2jsonschema.ontojson"
APP_DESCRIPTION = "OWL to JSON Schema Converter"
APP_AUTHOR = "Airy Magnien"
APP_COPYRIGHT = "© 2024 Airy Magnien. Licensed under EUPL v1.2"

# Entry points
MAIN_SCRIPT = str(PROJECT_ROOT / "owl2jsonschema_gui.py")
CLI_SCRIPT = str(SRC_DIR / "owl2jsonschema" / "cli.py")

# Icons
ICON_MAC = str(RESOURCES_DIR / "ORW_big.png")
ICON_WIN = str(RESOURCES_DIR / "ORW_big.png")  # Will be converted to .ico
ICON_LINUX = str(RESOURCES_DIR / "ORW_big.png")

# PyInstaller configuration
PYINSTALLER_OPTIONS = {
    'name': APP_NAME,
    'onefile': False,  # Create a folder bundle instead of single file
    'windowed': True,  # No console window for GUI
    'icon': None,  # Set per platform
    'add_data': [
        (str(RESOURCES_DIR), 'Resources'),
        (str(PROJECT_ROOT / 'Info.plist'), '.'),
    ],
    'hidden_imports': [
        'PyQt6',
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'owlready2',
        'rdflib',
        'jsonschema',
    ],
    'exclude_module': [
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'tkinter',
    ],
}

# Platform-specific configurations
MACOS_CONFIG = {
    'bundle_identifier': APP_IDENTIFIER,
    'bundle_name': APP_NAME,
    'bundle_version': APP_VERSION,
    'copyright': APP_COPYRIGHT,
    'category': 'public.app-category.developer-tools',
    'minimum_system_version': '10.15',
}

WINDOWS_CONFIG = {
    'company_name': APP_AUTHOR,
    'file_description': APP_DESCRIPTION,
    'internal_name': APP_NAME,
    'legal_copyright': APP_COPYRIGHT,
    'original_filename': f'{APP_NAME}.exe',
    'product_name': APP_NAME,
    'product_version': APP_VERSION,
}

LINUX_CONFIG = {
    'desktop_file': {
        'Name': APP_NAME,
        'Comment': APP_DESCRIPTION,
        'Exec': APP_NAME,
        'Icon': APP_NAME,
        'Terminal': 'false',
        'Type': 'Application',
        'Categories': 'Development;',
    }
}

# DMG configuration for macOS
DMG_CONFIG = {
    'title': APP_NAME,
    'icon': ICON_MAC,
    'background': None,  # Can add a background image
    'window_rect': ((100, 100), (640, 480)),
    'icon_size': 128,
    'icon_positions': {
        APP_NAME + '.app': (140, 120),
        'Applications': (500, 120),
    },
    'format': 'UDZO',  # Compressed
}
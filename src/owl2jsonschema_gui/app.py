"""
Main application entry point for the OWL to JSON Schema GUI.

This module initializes and launches the GUI application for converting
OWL ontologies to JSON Schema.
"""
import sys
import os
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon

# Make the parent directory available for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the main window class - using an absolute import path
from owl2jsonschema_gui.main_window import MainWindow

# Application configuration constants
APP_NAME = "OntoJSON"
APP_DISPLAY_NAME = "OntoJSON - OWL to JSON Schema Converter"
ORG_NAME = "OWL2JSONSchema"
APP_STYLE = "Fusion"


def set_macos_app_name():
    """
    Set the application name for macOS dock and menus.
    This should be called before creating the QApplication.
    """
    if sys.platform == 'darwin':
        # Method 1: Set process title using setproctitle
        try:
            import setproctitle
            setproctitle.setproctitle(APP_NAME)
        except ImportError:
            pass
        
        # Method 2: Set environment variables for macOS
        os.environ['__CFBundleName'] = APP_NAME
        os.environ['__CFBundleDisplayName'] = APP_NAME
        os.environ['__CFBundleIdentifier'] = 'com.owl2jsonschema.ontojson'
        
        # Method 3: Use AppKit to set the app name
        try:
            from AppKit import NSBundle, NSProcessInfo
            # Set the process name
            NSProcessInfo.processInfo().setProcessName_(APP_NAME)
            
            # Set bundle name
            bundle = NSBundle.mainBundle()
            if bundle:
                info = bundle.localizedInfoDictionary() or bundle.infoDictionary()
                if info:
                    info['CFBundleName'] = APP_NAME
                    info['CFBundleDisplayName'] = APP_NAME
        except ImportError:
            pass


def configure_application(app):
    """
    Configure the application settings.
    
    Args:
        app: The QApplication instance to configure
    """
    # Set application metadata
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_NAME)  # Important for macOS dock
    app.setOrganizationName(ORG_NAME)
    app.setStyle(APP_STYLE)
    
    # Set application icon
    try:
        # Try to load the high-resolution icon
        icon_path = Path("Resources/ORW_big.png")
        if not icon_path.exists():
            # Try alternative path (in case we're running from a different directory)
            icon_path = Path(__file__).parent.parent.parent / "Resources" / "ORW_big.png"
        
        if icon_path.exists():
            app.setWindowIcon(QIcon(str(icon_path)))
        else:
            # Fallback to low-res icon
            icon_path = Path("Resources/ORW_48.png")
            if not icon_path.exists():
                icon_path = Path(__file__).parent.parent.parent / "Resources" / "ORW_48.png"
            if icon_path.exists():
                app.setWindowIcon(QIcon(str(icon_path)))
    except Exception as e:
        print(f"Could not set application icon: {e}")


def main():
    """
    Main entry point for the GUI application.
    
    Initializes the Qt application, configures it, creates the main window,
    and starts the application event loop.
    """
    # Set macOS app name BEFORE creating QApplication
    set_macos_app_name()
    
    # Enable high DPI scaling - must be called BEFORE creating QApplication
    try:
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )
    except AttributeError:
        # Method might not be available in all Qt versions
        pass
    
    # Create application
    app = QApplication(sys.argv)

    # Configure application
    configure_application(app)

    # Create and show main window
    window = MainWindow()
    window.setWindowTitle(APP_NAME)  # Ensure window title is set
    window.show()

    # Run application
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

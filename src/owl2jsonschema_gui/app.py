"""
Main application entry point for the OWL to JSON Schema GUI.

This module initializes and launches the GUI application for converting
OWL ontologies to JSON Schema.
"""
import sys
import os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

# Make the parent directory available for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the main window class - using an absolute import path
from owl2jsonschema_gui.main_window import MainWindow

# Application configuration constants
APP_NAME = "OWL to JSON Schema Converter"
ORG_NAME = "OWL2JSONSchema"
APP_STYLE = "Fusion"


def configure_application(app):
    """
    Configure the application settings.
    
    Args:
        app: The QApplication instance to configure
    """
    # Set application metadata
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(ORG_NAME)
    app.setStyle(APP_STYLE)


def main():
    """
    Main entry point for the GUI application.
    
    Initializes the Qt application, configures it, creates the main window,
    and starts the application event loop.
    """
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
    window.show()

    # Run application
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

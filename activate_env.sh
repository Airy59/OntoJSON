#!/bin/bash
# Activation script for OntoJSON virtual environment

echo "Activating OntoJSON virtual environment..."
source .venv/bin/activate

echo "Virtual environment activated!"
echo "Python version: $(python --version)"
echo ""
echo "To run the GUI application: python src/owl2jsonschema_gui/app.py"
echo "To run the web application: python src/owl2jsonschema_web/app.py"
echo "To deactivate the environment: deactivate"
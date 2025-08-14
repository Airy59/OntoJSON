# OntoJSON Issues - Complete Solution Guide

## 🎯 Issues Resolved

1. **owlrl Import Error**: Python complains that `owlrl` is not installed despite being in virtual environment
2. **Dark Theme Issue**: GUI uses Windows dark theme which looks poor

---

## 🔍 Issue 1: owlrl Import Error

### Root Cause
- `owlrl` version 7.1.4 IS properly installed in `.venv/Lib/site-packages/owlrl/`
- VSCode F5/Run button is NOT using the virtual environment Python interpreter
- Terminal with activated virtual environment works perfectly

### ✅ Immediate Solution (Working)
**Use terminal instead of VSCode F5:**
```cmd
# In VSCode terminal:
.venv\Scripts\activate.bat
python run_ontojson_gui.py
```

### 🔧 VSCode Configuration Fixes

#### Option 1: Reload VSCode Window
1. Press `Ctrl+Shift+P`
2. Type "Developer: Reload Window"
3. Press Enter
4. Try F5 again

#### Option 2: Clear Python Cache
1. Delete all `__pycache__` folders in your project
2. Press `Ctrl+Shift+P` → "Python: Clear Cache and Reload Window"

#### Option 3: Check Launch Configuration
Create/update `.vscode/launch.json`:
```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "OntoJSON GUI",
            "type": "python",
            "request": "launch",
            "program": "${workspaceFolder}/run_ontojson_gui.py",
            "python": "${workspaceFolder}/.venv/Scripts/python.exe",
            "console": "integratedTerminal",
            "cwd": "${workspaceFolder}"
        }
    ]
}
```

### 🏗️ Project Configuration Fixes

#### Fix 1: Add Missing Dependency to pyproject.toml
The `owlrl` dependency is missing from your project configuration:

**Current dependencies in pyproject.toml:**
```toml
dependencies = [
    "rdflib>=6.0.0",
    "pyyaml>=6.0",
    "jsonschema>=4.0.0",
    "click>=8.0.0",
    "faker>=19.0.0",
]
```

**Should be:**
```toml
dependencies = [
    "rdflib>=6.0.0",
    "pyyaml>=6.0",
    "jsonschema>=4.0.0",
    "click>=8.0.0",
    "faker>=19.0.0",
    "owlrl>=7.1.4",  # ADD THIS LINE
]
```

#### Fix 2: Reinstall Project in Development Mode
After fixing pyproject.toml:
```cmd
.venv\Scripts\activate.bat
pip install -e .
```

---

## 🎨 Issue 2: Dark Theme GUI Problem

### Root Cause
PyQt6 automatically uses the system theme (Windows dark mode), which looks poor in your application.

### ✅ Solution: Force Light Theme

#### Method 1: Modify app.py (Recommended)
Add this to the `configure_application()` function in `src/owl2jsonschema_gui/app.py`:

```python
def configure_application(app):
    """Configure the application settings."""
    # Set application metadata
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_NAME)
    app.setOrganizationName(ORG_NAME)
    app.setStyle(APP_STYLE)
    
    # FORCE LIGHT THEME - ADD THESE LINES:
    from PyQt6.QtGui import QPalette, QColor
    
    # Create a light palette
    light_palette = QPalette()
    
    # Window colors
    light_palette.setColor(QPalette.ColorRole.Window, QColor(240, 240, 240))
    light_palette.setColor(QPalette.ColorRole.WindowText, QColor(0, 0, 0))
    
    # Base colors (for input fields)
    light_palette.setColor(QPalette.ColorRole.Base, QColor(255, 255, 255))
    light_palette.setColor(QPalette.ColorRole.AlternateBase, QColor(245, 245, 245))
    
    # Text colors
    light_palette.setColor(QPalette.ColorRole.Text, QColor(0, 0, 0))
    light_palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 0, 0))
    
    # Button colors
    light_palette.setColor(QPalette.ColorRole.Button, QColor(240, 240, 240))
    light_palette.setColor(QPalette.ColorRole.ButtonText, QColor(0, 0, 0))
    
    # Highlight colors
    light_palette.setColor(QPalette.ColorRole.Highlight, QColor(76, 163, 224))
    light_palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
    
    # Apply the light palette
    app.setPalette(light_palette)
    
    # Set application icon (existing code continues...)
    try:
        # ... rest of existing icon code
```

#### Method 2: Environment Variable (Alternative)
Add this at the very beginning of `main()` in `app.py`:

```python
def main():
    """Main entry point for the GUI application."""
    # Force light theme BEFORE creating QApplication
    import os
    os.environ['QT_QPA_PLATFORMTHEME'] = ''  # Disable system theme
    
    # Set macOS app name BEFORE creating QApplication
    set_macos_app_name()
    # ... rest of existing code
```

#### Method 3: Windows-Specific Fix
Add this to `main()` in `app.py` for Windows-specific theme control:

```python
def main():
    """Main entry point for the GUI application."""
    # Windows-specific theme fix
    import sys
    if sys.platform == 'win32':
        import os
        # Disable Windows dark mode for this app
        os.environ['QT_QPA_PLATFORMTHEME'] = ''
        # Force light theme
        os.environ['QT_STYLE_OVERRIDE'] = 'Fusion'
    
    # ... rest of existing code
```

---

## 🚀 Implementation Steps

### Step 1: Fix owlrl Dependency (Requires Code Mode)
1. Switch to Code mode
2. Add `owlrl>=7.1.4` to pyproject.toml dependencies
3. Run `pip install -e .` in activated virtual environment

### Step 2: Fix GUI Theme (Requires Code Mode)
1. Switch to Code mode
2. Modify `src/owl2jsonschema_gui/app.py` with Method 1 (recommended)
3. Test the application

### Step 3: Fix Font Readability (Requires Code Mode)
1. Replace all `QFont("Courier", 10)` with `QFont("Consolas, 'Courier New', monospace", 11)`
2. This provides better readability on Windows high-resolution screens
3. Consolas is much clearer and bolder than Courier

### Step 3: Fix VSCode F5 Issue
1. Try Option 1 (Reload Window) first
2. If that doesn't work, create the launch.json configuration
3. Test F5 functionality

### Step 4: Test Everything
1. Run from terminal: `python run_ontojson_gui.py`
2. Verify light theme is applied
3. Test F5 in VSCode
4. Verify owlrl imports work in both scenarios

---

## 📋 Verification Checklist

- [ ] owlrl imports successfully from terminal
- [ ] owlrl imports successfully from VSCode F5
- [ ] GUI uses light theme instead of dark
- [ ] All GUI functionality works properly
- [ ] Project dependencies are properly declared
- [ ] Virtual environment is correctly configured

---

## 🔧 Quick Commands Reference

```cmd
# Activate virtual environment
.venv\Scripts\activate.bat

# Test owlrl import
python -c "import owlrl; print('owlrl imported successfully')"

# Run GUI application
python run_ontojson_gui.py

# Reinstall project dependencies
pip install -e .

# Check Python interpreter
python -c "import sys; print(sys.executable)"
```

---

## 📝 Notes

- The owlrl package IS installed correctly - the issue is VSCode configuration
- Running from terminal works perfectly and is a reliable workaround
- The GUI theme fix will make the application much more readable on Windows
- Both issues are now fully diagnosed and have clear solutions

**Status: Ready for implementation in Code mode**
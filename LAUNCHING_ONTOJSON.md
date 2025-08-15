# Launching OntoJSON with Proper App Name on macOS

## The Challenge
When launching Python GUI applications on macOS, the dock and menu bar often show "Python" instead of your app name. This is because macOS identifies the process by the executable name (python3).

## Solutions for Different Launch Methods

### 1. **Best Option: Use the App Bundle**
```bash
# First, create the app bundle (only needed once)
./create_app_bundle.sh

# The app bundle is created at: /Users/airymagnien/PycharmProjects/OntoJSON/OntoJSON.app
# (or in your project root directory)

# Then launch by double-clicking OntoJSON.app
# Or from terminal:
open OntoJSON.app
# Or with full path:
open /Users/airymagnien/PycharmProjects/OntoJSON/OntoJSON.app
```
This provides the most native macOS experience with proper app naming.

### 2. **From Terminal**
Use one of these launcher scripts:
```bash
# Option A: Using the .command file
./OntoJSON.command

# Option B: Using the Python launcher
python3 launch_ontojson.py

# Option C: Using the GUI launcher directly
python3 owl2jsonschema_gui.py
```

### 3. **From PyCharm**

#### Option A: Configure PyCharm to use the launcher script
1. Go to Run → Edit Configurations
2. Create a new Python configuration
3. Set **Script path** to: `run_ontojson_gui.py`
4. Set **Working directory** to your project root
5. Run the configuration

#### Option B: Use External Tool (Recommended for PyCharm)
1. Go to PyCharm → Preferences → Tools → External Tools
2. Click + to add a new tool
3. Configure as follows:
   - **Name**: OntoJSON GUI
   - **Program**: `/usr/bin/open`
   - **Arguments**: `OntoJSON.app`
   - **Working directory**: `$ProjectFileDir$`
4. Run via Tools → External Tools → OntoJSON GUI

#### Option C: Create a Shell Script Configuration
1. Go to Run → Edit Configurations
2. Click + → Shell Script
3. Configure:
   - **Script text**: `./OntoJSON.command`
   - **Working directory**: Use project root
4. Run this configuration

### 4. **Adding to macOS Dock**
1. First create the app bundle: `./create_app_bundle.sh`
2. Drag OntoJSON.app to your Applications folder
3. Right-click on the app in Applications and select "Keep in Dock"
4. Now you can launch from the dock with proper naming

## Technical Details

The app uses multiple methods to ensure proper naming:
- **setproctitle**: Changes the process title
- **PyObjC/AppKit**: Uses native macOS APIs to set the app name
- **CFBundle environment variables**: Sets bundle identifiers
- **Info.plist**: Provides metadata for the app bundle

## Troubleshooting

If you still see "Python" in the dock:
1. Make sure you've installed the required packages:
   ```bash
   pip3 install setproctitle pyobjc-core pyobjc-framework-Cocoa
   ```
2. Use the app bundle (OntoJSON.app) for the most reliable results
3. On macOS, GUI apps work best when launched from an app bundle rather than directly from Python

## File Reference
- `OntoJSON.app/` - macOS app bundle (created by create_app_bundle.sh in project root)
- `create_app_bundle.sh` - Script that builds OntoJSON.app in the project root directory
- `launch_ontojson.py` - Main launcher script with app naming support
- `run_ontojson_gui.py` - PyCharm-compatible launcher
- `OntoJSON.command` - Shell script launcher for Terminal
- `owl2jsonschema_gui.py` - Basic GUI launcher
- `src/owl2jsonschema_gui/app.py` - Main application with naming configuration
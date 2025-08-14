#!/bin/bash
# Script to create a macOS app bundle for OntoJSON

echo "Creating OntoJSON.app bundle..."

# Create the app bundle structure
APP_DIR="OntoJSON.app"
CONTENTS_DIR="$APP_DIR/Contents"
MACOS_DIR="$CONTENTS_DIR/MacOS"
RESOURCES_DIR="$CONTENTS_DIR/Resources"

# Remove existing app bundle if it exists
if [ -d "$APP_DIR" ]; then
    echo "Removing existing app bundle..."
    rm -rf "$APP_DIR"
fi

# Create directories
mkdir -p "$MACOS_DIR"
mkdir -p "$RESOURCES_DIR"

# Copy the Info.plist
cp Info.plist "$CONTENTS_DIR/"

# Copy the icon
if [ -f "Resources/ORW_big.png" ]; then
    cp "Resources/ORW_big.png" "$RESOURCES_DIR/"
fi

# Create the launcher script
cat > "$MACOS_DIR/OntoJSON" << 'EOF'
#!/bin/bash
# OntoJSON launcher for macOS app bundle

# Get the directory of this script
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
# Go up to the app bundle's parent directory
APP_ROOT="$( cd "$DIR/../../.." && pwd )"

# Change to the project directory
cd "$APP_ROOT"

# Set the app name for the dock
export __CFBundleName="OntoJSON"
export __CFBundleDisplayName="OntoJSON"
export __CFBundleIdentifier="com.owl2jsonschema.ontojson"

# Launch the application
exec python3 launch_ontojson.py "$@"
EOF

# Make the launcher executable
chmod +x "$MACOS_DIR/OntoJSON"

echo "OntoJSON.app bundle created successfully!"
echo ""
echo "You can now:"
echo "1. Double-click OntoJSON.app to launch the application"
echo "2. Drag OntoJSON.app to your Applications folder"
echo "3. Add OntoJSON.app to your dock for easy access"
#!/bin/bash
# build.sh – Build executables for various platforms

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

# ----------------------------------------------------------------------
# Activate virtual environment if available and not active
# ----------------------------------------------------------------------
if [[ -z "$VIRTUAL_ENV" ]] && [[ -d ".venv" ]]; then
    source .venv/bin/activate
fi

# ----------------------------------------------------------------------
# Check Requirements
# ----------------------------------------------------------------------
check_nuitka() {
    if ! command -v nuitka &> /dev/null; then
        echo "Nuitka not found. Install with: pip install nuitka"
        exit 1
    fi
}

check_appimagetool() {
    if ! command -v appimagetool &> /dev/null; then
        echo "appimagetool not found."
        echo "Download it from: https://github.com/AppImage/AppImageKit/releases"
        exit 1
    fi
}

# ----------------------------------------------------------------------
# Build functions
# ----------------------------------------------------------------------
build_linux() {
    check_nuitka
    echo "Building Linux standalone executable..."
    nuitka --standalone --assume-yes-for-downloads \
            --output-dir=./build \
            --static-libpython=yes \
            --include-data-dir=bitrot/data.rot=data.rot \
            bitrot/bitrot.py
    
    echo "Linux builds ready in ./build/"
}

build_appimage() {
    # --- CACHE LOGIC ---
    if [[ "$USE_CACHE" == true ]]; then
        echo "Using cached Nuitka build..."
        if [[ ! -d "build/bitrot.dist" ]]; then
            echo "Error: No cached build found in build/bitrot.dist. Run without --cache first."
            exit 1
        fi
    else
        build_linux
    fi
    # -------------------
    
    check_appimagetool
    echo "Packaging into AppImage..."

    APPDIR="bitrot.AppDir"
    rm -rf "$APPDIR"
    mkdir -p "$APPDIR/usr/bin"
    
    if [ -d "build/bitrot.dist" ]; then
        cp -a build/bitrot.dist/* "$APPDIR/usr/bin/"
    else
        echo "Error: build/bitrot.dist not found."
        exit 1
    fi

    # ----------------------------------------------------------------------
    # SMART BINARY DETECTION
    # ----------------------------------------------------------------------
    # We look for a file in usr/bin that is NOT a directory and NOT a .so file
    # and is likely our executable.
    BINARY_NAME=$(find "$APPDIR/usr/bin" -maxdepth 1 -type f ! -name "*.so*" ! -name "*.pyc*" | head -n 1 | xargs basename)

    if [[ -z "$BINARY_NAME" ]]; then
        echo "Error: Could not find the compiled binary inside build/bitrot.dist"
        exit 1
    fi

    echo "Detected binary name: $BINARY_NAME"
    
    # Ensure the detected binary is executable
    chmod +x "$APPDIR/usr/bin/$BINARY_NAME"
    # ----------------------------------------------------------------------

    # Create the AppRun script using the DETECTED binary name
    cat << EOF > "$APPDIR/AppRun"
#!/bin/sh
HERE="\$(dirname "\$(readlink -f "\${0}")")"
export LD_LIBRARY_PATH="\$HERE/usr/bin:\$LD_LIBRARY_PATH"
if [ -f "\$HERE/usr/bin/$BINARY_NAME" ]; then
    exec "\$HERE/usr/bin/$BINARY_NAME" "\$@"
else
    echo "Error: Binary $BINARY_NAME not found inside AppImage"
    exit 1
fi
EOF
    chmod +x "$APPDIR/AppRun"

    cat << EOF > "$APPDIR/bitrot.desktop"
[Desktop Entry]
Name=Bitrot
Exec=$BINARY_NAME
Icon=bitrot
Type=Application
Categories=Utility;
EOF

    if [ -f "bitrot/data.rot/icons/favicon.png" ]; then
        cp "bitrot/data.rot/icons/favicon.png" "$APPDIR/bitrot.png"
    else
        touch "$APPDIR/bitrot.png" 
    fi

    appimagetool "$APPDIR"
    echo "AppImage generated successfully using binary: $BINARY_NAME"
}
build_macos() {
    check_nuitka
    echo "Building macOS executable..."
    nuitka --standalone --macos-create-app-bundle --macos-app-icon=./bitrot/data.rot/icons/favicon.icns --assume-yes-for-downloads --output-dir=./build --static-libpython=yes bitrot/bitrot.py
    echo "macOS builds ready in ./build/"
}

# ----------------------------------------------------------------------
# Parse target and options
# ----------------------------------------------------------------------
TARGET=""
USE_CACHE=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --linux) TARGET="linux"; shift ;;
        --appimage) TARGET="appimage"; shift ;;
        --macos) TARGET="macos"; shift ;;
        --cache) USE_CACHE=true; shift ;;
        --help)
            cat << EOF
Usage: $(basename "$0") [TARGET] [OPTIONS]

Targets:
  --linux      Build for Linux (standalone folder)
  --appimage   Build for Linux (packaged .AppImage)
  --macos      Build for macOS (app bundle)

Options:
  --cache      Skip Nuitka compilation and use existing build/bitrot.dist (AppImage only)

Example:
  ./build.sh --appimage --cache
EOF
            exit 0
            ;;
        *)
            echo "Unknown argument: $1"
            echo "Use --help for usage."
            exit 1
            ;;
    esac
done

if [[ -z "$TARGET" ]]; then
    echo "Please specify a target (--linux, --appimage, --macos)."
    exit 1
fi

# ----------------------------------------------------------------------
# Execute build
# ----------------------------------------------------------------------
case "$TARGET" in
    linux) build_linux ;;
    appimage) build_appimage ;;
    macos) build_macos ;;
esac

echo "Build completed."
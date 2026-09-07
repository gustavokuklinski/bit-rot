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
        echo "Example: wget https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage -O appimagetool && chmod +x appimagetool && sudo mv appimagetool /usr/local/bin/"
        exit 1
    fi
}

# ----------------------------------------------------------------------
# Build functions
# ----------------------------------------------------------------------
build_linux() {
    check_nuitka
    echo "Building Linux standalone executable..."
    # We build to a specific folder to make AppImage packaging easier
    nuitka --standalone --assume-yes-for-downloads \
            --output-dir=./build \
            --static-libpython=yes \
            --include-data-dir=bitrot/data.rot=data.rot \
            bitrot/bitrot.py
    
    # If you need the editor as well, build it, but AppImage usually has one entry point
    nuitka --standalone --assume-yes-for-downloads \
            --output-dir=./build \
            --static-libpython=yes \
            --include-data-dir=bitrot/data.rot=data.rot \
            bitrot/editor.py
    
    echo "Linux builds ready in ./build/"
}

build_appimage() {
    # 1. First, generate the Nuitka standalone binaries
    build_linux
    
    check_appimagetool
    echo "Packaging into AppImage..."

    # Define AppDir structure
    APPDIR="bitrot.AppDir"
    rm -rf "$APPDIR"
    mkdir -p "$APPDIR/usr/bin"
    
    # 2. Copy the Nuitka build output into AppDir
    # Nuitka creates a folder like 'bitrot.dist'
    cp -r build/bitrot.dist/* "$APPDIR/usr/bin/"
    
    # 3. Create the AppRun script (The entry point for AppImage)
    cat << EOF > "$APPDIR/AppRun"
#!/bin/sh
HERE="\$(dirname "\$(readlink -f "\${0}")")"
export LD_LIBRARY_PATH="\$HERE/usr/bin:\$LD_LIBRARY_PATH"
exec "\$HERE/usr/bin/bitrot" "\$@"
EOF
    chmod +x "$APPDIR/AppRun"

    # 4. Create the .desktop file
    cat << EOF > "$APPDIR/bitrot.desktop"
[Desktop Entry]
Name=Bitrot
Exec=bitrot
Icon=bitrot
Type=Application
Categories=Utility;
EOF

    # 5. Copy an icon (Ensure you have a .png version for Linux)
    # Using the favicon path from your macos build as a reference, but Linux needs PNG
    if [ -f "bitrot/data.rot/icons/favicon.png" ]; then
        cp "bitrot/data.rot/icons/favicon.png" "$APPDIR/bitrot.png"
    else
        echo "Warning: favicon.png not found, AppImage will have no icon."
        touch "$APPDIR/bitrot.png" # Create dummy file to prevent appimagetool error
    fi

    # 6. Run appimagetool
    appimagetool "$APPDIR"
    
    echo "AppImage generated successfully!"
}

build_macos() {
    check_nuitka
    echo "Building macOS executable..."
    nuitka --standalone --macos-create-app-bundle --macos-app-icon=./bitrot/data.rot/icons/favicon.icns --assume-yes-for-downloads --output-dir=./build --static-libpython=yes bitrot/bitrot.py
    nuitka --standalone --macos-create-app-bundle --macos-app-icon=./bitrot/data.rot/icons/favicon.icns --assume-yes-for-downloads --output-dir=./build --static-libpython=yes bitrot/editor.py
    echo "macOS builds ready in ./build/"
    echo "After build, run: xattr -cr bitrot.app"
}

# ----------------------------------------------------------------------
# Parse target
# ----------------------------------------------------------------------
TARGET=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --linux) TARGET="linux"; shift ;;
        --appimage) TARGET="appimage"; shift ;;
        --macos) TARGET="macos"; shift ;;
        --help)
            cat << EOF
Usage: $(basename "$0") [TARGET]

Targets:
  --linux      Build for Linux (standalone folder)
  --appimage   Build for Linux (packaged .AppImage)
  --macos      Build for macOS (app bundle)

EOF
            exit 0
            ;;
        *)
            echo "Unknown target: $1"
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
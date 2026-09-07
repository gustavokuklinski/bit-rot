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
# Check Nuitka (required for all except Android)
# ----------------------------------------------------------------------
check_nuitka() {
    if ! command -v nuitka &> /dev/null; then
        echo "Nuitka not found. Install with: pip install nuitka"
        exit 1
    fi
}

# ----------------------------------------------------------------------
# Build functions
# ----------------------------------------------------------------------
build_linux() {
    check_nuitka
    echo "Building Linux executable..."
    nuitka --standalone --assume-yes-for-downloads --output-dir=./build --static-libpython=yes --include-data-dir=bitrot/data.rot=data.rot bitrot/bitrot.py
    nuitka --standalone --assume-yes-for-downloads --output-dir=./build --static-libpython=yes --include-data-dir=bitrot/data.rot=data.rot bitrot/editor.py
    echo "Linux builds ready in ./build/"
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
        --macos) TARGET="macos"; shift ;;
        --help)
            cat << EOF
Usage: $(basename "$0") [TARGET]

Targets:
  --linux      Build for Linux (onefile)
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
    echo "Please specify a target (--linux, --macos)."
    exit 1
fi

# ----------------------------------------------------------------------
# Execute build
# ----------------------------------------------------------------------
case "$TARGET" in
    linux) build_linux ;;
    macos) build_macos ;;
    all)
        build_linux
        build_macos
        ;;
esac

echo "Build completed."
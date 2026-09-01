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
    nuitka --onefile --include-data-dir=./bitrot/game=game --output-dir=./build ./bitrot/bitrot.py
    nuitka --onefile --include-data-dir=./bitrot/game=game --output-dir=./build ./bitrot/editor.py
    echo "Linux builds ready in ./build/"
}

build_windows() {
    check_nuitka
    echo "Building Windows executable..."
    nuitka --onefile --windows-console-mode=disable --windows-icon-from-ico=./bitrot/game/icons/favicon.ico --output-dir=./build ./bitrot/bitrot.py
    nuitka --onefile --windows-console-mode=disable --windows-icon-from-ico=./bitrot/game/icons/favicon.ico --output-dir=./build ./bitrot/editor.py
    echo "Windows builds ready in ./build/"
}

build_macos() {
    check_nuitka
    echo "Building macOS executable..."
    nuitka --onefile --macos-create-app-bundle --macos-app-icon=./bitrot/game/icons/favicon.icns --output-dir=./build ./bitrot/bitrot.py
    nuitka --onefile --macos-create-app-bundle --macos-app-icon=./bitrot/game/icons/favicon.icns --output-dir=./build ./bitrot/editor.py
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
        --windows) TARGET="windows"; shift ;;
        --macos) TARGET="macos"; shift ;;
        --android) TARGET="android"; shift ;;
        --all) TARGET="all"; shift ;;
        --help)
            cat << EOF
Usage: $(basename "$0") [TARGET]

Targets:
  --linux      Build for Linux (onefile)
  --windows    Build for Windows (onefile, console disabled)
  --macos      Build for macOS (app bundle)
  --all        Build all of the above

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
    echo "Please specify a target (--linux, --windows, --macos, --all)."
    exit 1
fi

# ----------------------------------------------------------------------
# Execute build
# ----------------------------------------------------------------------
case "$TARGET" in
    linux) build_linux ;;
    windows) build_windows ;;
    macos) build_macos ;;
    all)
        build_linux
        build_windows
        build_macos
        ;;
esac

echo "Build completed."
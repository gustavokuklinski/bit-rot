# ----------------------------------------------------------------------
# Parse command-line arguments (non-interactive mode)
# ----------------------------------------------------------------------
if [[ $# -gt 0 ]]; then
    case "$1" in
        --full)
            find . -type d -name "__pycache__" -exec rm -rf {} +
            rm -Rf build/
            rm -Rf data.rot/
            echo "Full clean done (removed __pycache__, build/ and data.rot/)."
            exit 0
            ;;
        --cache)
            find . -type d -name "__pycache__" -exec rm -rf {} +
            echo "Python cache cleaned."
            exit 0
            ;;
        --build)
            rm -Rf build/
            echo "build/ directory removed."
            exit 0
            ;;
        --datarot)
            rm -Rf data.rot/
            echo "data.rot/ directory removed."
            exit 0
            ;;
        --help)
            cat << EOF
Usage: $(basename "$0") [OPTIONS]

Options:
  --full      Remove all __pycache__ folders, build/ and data.rot/.
  --cache     Remove only all __pycache__ folders.
  --build     Remove only the build/ directory.
  --datarot      Remove only the data.rot/ directory.
  --help      Show this help.

If no options are given, an interactive menu will be shown.
EOF
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage."
            exit 1
            ;;
    esac
fi
#!/bin/bash
# game.sh – Run the Bit Rot game

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

VENV_DIR=".venv"
APP_SCRIPT="bitrot/bitrot.py"
REQUIREMENTS_FILE="requirements.txt"

show_help() {
    cat << EOF
Usage: $(basename "$0") [OPTIONS] [--] [APP_ARGS...]

Options:
  --help      Show this help message and exit.
  --venv      Only set up the virtual environment (create if missing, install dependencies) and exit.
              If a virtual environment is already active, it will be used.
  Any additional arguments after -- will be passed to the game.

This script ensures a Python virtual environment is available and then runs the game.
EOF
}

VENV_ONLY=false
while [[ $# -gt 0 ]]; do
    case "$1" in
        --help) show_help; exit 0 ;;
        --venv) VENV_ONLY=true; shift ;;
        --) shift; break ;;
        -*)
            echo "Unknown option: $1"
            show_help
            exit 1
            ;;
        *) break ;;
    esac
done
APP_ARGS=("$@")

# ----- Virtual environment handling -----
if [[ -n "$VIRTUAL_ENV" ]]; then
    echo "Using existing virtual environment: $VIRTUAL_ENV"
    PYTHON_EXEC="$VIRTUAL_ENV/bin/python"
    if [[ "$VENV_ONLY" == true ]]; then
        echo "Virtual environment is ready."
        exit 0
    fi
else
    if [[ ! -d "$VENV_DIR" ]]; then
        echo "Creating virtual environment in $VENV_DIR..."
        python3 -m venv "$VENV_DIR"
        if [[ $? -ne 0 ]]; then
            echo "Failed to create virtual environment."
            exit 1
        fi
    fi
    PYTHON_EXEC="$VENV_DIR/bin/python"
    PIP_EXEC="$VENV_DIR/bin/pip"

    if [[ -f "$REQUIREMENTS_FILE" ]]; then
        echo "Installing requirements from $REQUIREMENTS_FILE..."
        "$PIP_EXEC" install -r "$REQUIREMENTS_FILE"
    fi
    APP_DIR="$(dirname "$APP_SCRIPT")"
    if [[ -f "$APP_DIR/requirements.txt" ]]; then
        echo "Installing app-specific requirements from $APP_DIR/requirements.txt..."
        "$PIP_EXEC" install -r "$APP_DIR/requirements.txt"
    fi

    if [[ "$VENV_ONLY" == true ]]; then
        echo "Virtual environment is set up in $VENV_DIR."
        echo "To activate it, run: source $VENV_DIR/bin/activate"
        exit 0
    fi
fi

# ----- Copy game assets to root (fresh copy) -----
echo "Copying game assets from bitrot/game to ./game ..."
rm -rf ./game          # Remove existing folder
cp -Rf bitrot/game ./game   # Copy entire folder

# ----- Change to the bitrot directory and run the game -----
cd "$(dirname "$APP_SCRIPT")"   # now in bitrot/
echo "Running in directory: $(pwd)"
echo "Running: $PYTHON_EXEC $(basename "$APP_SCRIPT") ${APP_ARGS[@]}"
exec "$PYTHON_EXEC" "$(basename "$APP_SCRIPT")" "${APP_ARGS[@]}"
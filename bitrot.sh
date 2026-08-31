#!/bin/bash
# bitrot.sh – Main entry point for Bit Rot

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

SCRIPTS_DIR="$SCRIPT_DIR/scripts"

# ----------------------------------------------------------------------
# Check for dialog
# ----------------------------------------------------------------------
if ! command -v dialog &> /dev/null; then
    echo "dialog is required for the TUI. Please install it (sudo apt install dialog)."
    exit 1
fi

# ----------------------------------------------------------------------
# Read version from game/lib/VERSION
# ----------------------------------------------------------------------
get_version() {
    local version_file="$SCRIPT_DIR/game/lib/VERSION"
    if [[ -f "$version_file" ]]; then
        # Read the first line, trim whitespace
        local ver=$(head -n1 "$version_file" | tr -d '\n\r' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
        echo "$ver"
    else
        echo "unknown"
    fi
}
VERSION=$(get_version)

# ----------------------------------------------------------------------
# Set up custom dialog colors via a temporary .dialogrc
# Borders: black; normal items: white on green; selected: inverted (black on white)
# ----------------------------------------------------------------------


export DIALOGRC=$(setup_dialog_colors)
trap 'rm -f "$DIALOGRC"' EXIT

# ----------------------------------------------------------------------
# Usage / Help
# ----------------------------------------------------------------------
usage() {
    cat << EOF
Usage: $(basename "$0") [COMMAND] [OPTIONS...]

Bit Rot SDK - Version: $VERSION

Commands:
  shell [--editor]      Run the game (or editor with --editor) with colorful ASCII banner.
  clean [OPTIONS]       Clean cache and/or build directory.
                        Options: --full, --cache, --build, --game (see clean.sh --help)
  build [TARGET]        Build executables for target platform.
                        Targets: --linux, --windows, --macos, --android, --all
  help                  Show this help.
  (no args)             Launch interactive TUI menu.

Examples:
  $ ./bitrot.sh shell
  $ ./bitrot.sh shell --editor
  $ ./bitrot.sh clean --full
  $ ./bitrot.sh build --linux
EOF
}

# ----------------------------------------------------------------------
# ASCII Logo for welcome screen
# ----------------------------------------------------------------------
show_welcome() {
    local logo="
 Rot Engine
 Version: $VERSION
 ---
 
 Bit Rot - Zombie Survivor Game

 Edit your entire game
 ---

 PRESS <ENTER> TO CONTINUE
"
    dialog --colors --clear --title " Welcome to Bit Rot " \
           --msgbox "$logo" 15 60
}

# ----------------------------------------------------------------------
# Run a background GUI application (game/editor)
# ----------------------------------------------------------------------
run_gui_app() {
    local script="$1"
    shift
    nohup "$script" "$@" > /dev/null 2>&1 &
    local pid=$!
    disown $pid
    dialog --colors --clear --title " \Z2Launched\Zn " \
           --msgbox "Application started with PID $pid.\nIt should open in its own window." 10 50
}

# ----------------------------------------------------------------------
# Run a script with live output in a scrollable tailbox (for clean/build)
# ----------------------------------------------------------------------
run_script_with_output() {
    local script="$1"
    shift
    local tmpfile=$(mktemp)
    "$script" "$@" > "$tmpfile" 2>&1 &
    local pid=$!
    dialog --colors --clear --title " \Z6Rot Engine Runner...\Zn " --tailboxbg "$tmpfile" 20 80
    wait $pid
    local exit_code=$?
    rm -f "$tmpfile"
    if [[ $exit_code -eq 0 ]]; then
        dialog --colors --clear --title " \Z2SUCCESS\Zn " \
               --msgbox "Command completed successfully." 10 50
    else
        dialog --colors --clear --title " \Z1ERROR\Zn " \
               --msgbox "Command failed with exit code $exit_code." 10 50
    fi
    return $exit_code
}

# ----------------------------------------------------------------------
# Main TUI menu (full‑screen style)
# ----------------------------------------------------------------------
show_tui() {
    show_welcome
    while true; do
        local title="[Rot Engine][v.$VERSION]"
        local backtitle="  [Rot Engine] [v.$VERSION]  "
        local menu_cmd=(dialog --colors --clear --backtitle "$backtitle" \
               --title "$title" --menu "Use arrow keys to select, Enter to confirm." \
               20 60 5)
        local options=(
            "1" "Play BitRot"
            "2" "Editor - Tweak the game"
            "3" "Clean Project"
            "4" "Build Executable"
            "5" "Back"
            "6" "Exit"
        )
        local choice=$("${menu_cmd[@]}" "${options[@]}" 2>&1 >/dev/tty)
        case $choice in
            1) run_gui_app "$SCRIPTS_DIR/game.sh" ;;
            2) run_gui_app "$SCRIPTS_DIR/editor.sh" ;;
            3) show_clean_menu ;;
            4) show_build_menu ;;
            5) show_welcome ;;
            6|"") break ;;
        esac
    done
}

# ----------------------------------------------------------------------
# Clean submenu
# ----------------------------------------------------------------------
show_clean_menu() {
    local backtitle="  [Rot Engine] [Cleanup] [v.$VERSION]  "
    local cmd=(dialog --colors --clear --backtitle "$backtitle" \
               --title " \Z3Clean Options\Zn " --menu "Choose action:" 16 60 5)
    local options=(
        "1" "Full clean (cache, build, game/)"
        "2" "Clean Python cache only"
        "3" "Remove build/ directory only"
        "4" "Remove game/ directory only"
        "5" "Back"
    )
    local choice=$("${cmd[@]}" "${options[@]}" 2>&1 >/dev/tty)
    case $choice in
        1) run_script_with_output "$SCRIPTS_DIR/clean.sh" "--full" ;;
        2) run_script_with_output "$SCRIPTS_DIR/clean.sh" "--cache" ;;
        3) run_script_with_output "$SCRIPTS_DIR/clean.sh" "--build" ;;
        4) run_script_with_output "$SCRIPTS_DIR/clean.sh" "--game" ;;
        5|"") return ;;
    esac
}

# ----------------------------------------------------------------------
# Build submenu
# ----------------------------------------------------------------------
show_build_menu() {
    local backtitle="  [Rot Engine] [Builder] [v.$VERSION]  "
    local cmd=(dialog --colors --clear --backtitle "$backtitle" \
               --title " \Z4Build Executable\Zn " --menu "Select target:" 16 60 6)
    local options=(
        "1" "Linux"
        "2" "Windows"
        "3" "macOS"
        "4" "Android"
        "5" "All"
        "6" "Back"
    )
    local choice=$("${cmd[@]}" "${options[@]}" 2>&1 >/dev/tty)
    case $choice in
        1) run_script_with_output "$SCRIPTS_DIR/build.sh" "--linux" ;;
        2) run_script_with_output "$SCRIPTS_DIR/build.sh" "--windows" ;;
        3) run_script_with_output "$SCRIPTS_DIR/build.sh" "--macos" ;;
        4) run_script_with_output "$SCRIPTS_DIR/build.sh" "--android" ;;
        5) run_script_with_output "$SCRIPTS_DIR/build.sh" "--all" ;;
        6|"") return ;;
    esac
}

# ----------------------------------------------------------------------
# Command-line parsing
# ----------------------------------------------------------------------
if [[ $# -eq 0 ]]; then
    show_tui
    exit 0
fi

case "$1" in
    shell)
        shift
        if [[ "$1" == "--editor" ]]; then
            shift
            exec "$SCRIPTS_DIR/editor.sh" "$@"
        else
            exec "$SCRIPTS_DIR/game.sh" "$@"
        fi
        ;;
    clean)
        shift
        exec "$SCRIPTS_DIR/clean.sh" "$@"
        ;;
    build)
        shift
        exec "$SCRIPTS_DIR/build.sh" "$@"
        ;;
    help|--help|-h)
        usage
        exit 0
        ;;
    *)
        echo "Unknown command: $1"
        usage
        exit 1
        ;;
esac
#!/bin/bash
# bitrot.sh – Main entry point for Bit Rot (ASCII GUI Version)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

SCRIPTS_DIR="$SCRIPT_DIR/scripts"

# ----------------------------------------------------------------------
# Colors and Styling
# ----------------------------------------------------------------------
C_RESET="\e[0m"
C_BOLD="\e[1m"
C_GREEN="\e[32m"
C_CYAN="\e[36m"
C_YELLOW="\e[33m"
C_RED="\e[31m"
C_BLUE="\e[34m"

# ----------------------------------------------------------------------
# Read version from data.rot/lib/VERSION
# ----------------------------------------------------------------------
get_version() {
    local version_file="./bitrot/data.rot/lib/VERSION"
    if [[ -f "$version_file" ]]; then
        local ver=$(head -n1 "$version_file" | tr -d '\n\r' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
        echo "$ver"
    else
        echo "unknown"
    fi
}
VERSION=$(get_version)

# ----------------------------------------------------------------------
# UI Helper: Draw a Boxed Header
# ----------------------------------------------------------------------
draw_header() {
    local title="$1"
    local width=60
    echo -e "${C_CYAN}┌$(printf '─%.0s' $(seq 1 $((width-2))))┐${C_RESET}"
    printf "${C_CYAN}│${C_RESET} %-${width}s ${C_CYAN}│${C_RESET}\n" "$title" | sed "s/$/ /" # Rough centering not easy in bash, left-aligned
    # To actually center:
    # printf "${C_CYAN}│${C_RESET} %*s ${C_CYAN}│${C_RESET}\n" $(( (width+${#title})/2 )) "$title"
    echo -e "${C_CYAN}└$(printf '─%.0s' $(seq 1 $((width-2))))┘${C_RESET}"
}

# ----------------------------------------------------------------------
# Usage / Help
# ----------------------------------------------------------------------
usage() {
    cat << EOF
${C_BOLD}Usage:${C_RESET} $(basename "$0") [COMMAND] [OPTIONS...]

Bit Rot SDK - Version: $VERSION

Commands:
  shell [--editor]      Run the game (or editor with --editor).
  clean [OPTIONS]       Clean cache and/or build directory.
  build [TARGET]        Build executables for target platform.
  help                  Show this help.
  (no args)             Launch interactive ASCII GUI.

Examples:
  $ ./bitrot.sh shell
  $ ./bitrot.sh clean --full
  $ ./bitrot.sh build --linux
EOF
}

# ----------------------------------------------------------------------
# Welcome Screen
# ----------------------------------------------------------------------
show_welcome() {
    clear
    echo -e "\n"
    echo -e " ${C_GREEN}┌──────────────────────────────────────────────────────────┐${C_RESET}"
    echo -e " ${C_GREEN}│${C_RESET}              ${C_BOLD}ROT ENGINE v.$VERSION${C_RESET}"
    echo -e " ${C_GREEN}├──────────────────────────────────────────────────────────┤${C_RESET}"
    echo -e " ${C_GREEN}│${C_RESET}"
    echo -e " ${C_GREEN}│${C_RESET}       ${C_YELLOW}Bit Rot - Zombie Survivor Game${C_RESET}"
    echo -e " ${C_GREEN}│${C_RESET}"
    echo -e " ${C_GREEN}└──────────────────────────────────────────────────────────┘${C_RESET}"
    echo -e "\n${C_BOLD}PRESS [ENTER] TO CONTINUE...${C_RESET}"
    read -r
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
    echo -e "\n${C_GREEN}✔ Application started with PID $pid.${C_RESET}"
    echo -e "It should open in its own window."
    echo -e "\nPress [ENTER] to return to menu..."
    read -r
}

# ----------------------------------------------------------------------
# Run a script with live output
# ----------------------------------------------------------------------
run_script_with_output() {
    local script="$1"
    shift
    echo -e "\n${C_YELLOW}Running: $script $@...${C_RESET}\n"
    
    # Run the script directly so user sees live output
    if "$script" "$@"; then
        echo -e "\n${C_GREEN}┌──────────────────────────────────────────┐${C_RESET}"
        echo -e "${C_GREEN}│ SUCCESS: Command completed successfully. ${C_RESET}"
        echo -e "${C_GREEN}└──────────────────────────────────────────┘${C_RESET}"
    else
        echo -e "\n${C_RED}┌──────────────────────────────────────────┐${C_RESET}"
        echo -e "${C_RED}│ ERROR: Command failed. ${C_RESET}"
        echo -e "${C_RED}└──────────────────────────────────────────┘${C_RESET}"
    fi
    echo -e "\nPress [ENTER] to return to menu..."
    read -r
}

# ----------------------------------------------------------------------
# Main ASCII Menu
# ----------------------------------------------------------------------
show_tui() {
    show_welcome
    while true; do
        clear
        echo -e "${C_CYAN}┌──────────────────────────────────────────────────────────┐${C_RESET}"
        echo -e "${C_CYAN}│ ${C_BOLD}ROT ENGINE MAIN MENU [v$VERSION]${C_RESET}"
        echo -e "${C_CYAN}├──────────────────────────────────────────────────────────┤${C_RESET}"
        echo -e "${C_CYAN}│${C_RESET}  ${C_BOLD}1)${C_RESET} Play BitRot"
        echo -e "${C_CYAN}│${C_RESET}  ${C_BOLD}2)${C_RESET} Editor - Tweak the game"
        echo -e "${C_CYAN}│${C_RESET}  ${C_BOLD}3)${C_RESET} Clean Project"
        echo -e "${C_CYAN}│${C_RESET}  ${C_BOLD}4)${C_RESET} Build Executable"
        echo -e "${C_CYAN}│${C_RESET}  ${C_BOLD}5)${C_RESET} Help"
        echo -e "${C_CYAN}│${C_RESET}  ${C_BOLD}6)${C_RESET} Exit"
        echo -e "${C_CYAN}└──────────────────────────────────────────────────────────┘${C_RESET}"
        echo -n -e "\n${C_BOLD}Selection [1-6]: ${C_RESET}"
        read -r choice

        case $choice in
            1) run_gui_app "$SCRIPTS_DIR/game.sh" ;;
            2) run_gui_app "$SCRIPTS_DIR/editor.sh" ;;
            3) show_clean_menu ;;
            4) show_build_menu ;;
            5) usage; echo -e "\nPress [ENTER] to return..."; read -r ;;
            6) clear; echo "Exiting Rot Engine..."; exit 0 ;;
            *) echo -e "${C_RED}Invalid option!${C_RESET}"; sleep 1 ;;
        esac
    done
}

# ----------------------------------------------------------------------
# Clean submenu
# ----------------------------------------------------------------------
show_clean_menu() {
    while true; do
        clear
        echo -e "${C_YELLOW}┌──────────────────────────────────────────────────────────┐${C_RESET}"
        echo -e "${C_YELLOW}│ ${C_BOLD}CLEANUP OPTIONS${C_RESET}                                      ${C_YELLOW}│${C_RESET}"
        echo -e "${C_YELLOW}├──────────────────────────────────────────────────────────┤${C_RESET}"
        echo -e "${C_YELLOW}│${C_RESET}  ${C_BOLD}1)${C_RESET} Full clean (cache, build, data.rot/)                    ${C_YELLOW}│${C_RESET}"
        echo -e "${C_YELLOW}│${C_RESET}  ${C_BOLD}2)${C_RESET} Clean Python cache only                            ${C_YELLOW}│${C_RESET}"
        echo -e "${C_YELLOW}│${C_RESET}  ${C_BOLD}3)${C_RESET} Remove build/ directory only                       ${C_YELLOW}│${C_RESET}"
        echo -e "${C_YELLOW}│${C_RESET}  ${C_BOLD}4)${C_RESET} Remove data.rot/ directory only                        ${C_YELLOW}│${C_RESET}"
        echo -e "${C_YELLOW}│${C_RESET}  ${C_BOLD}5)${C_RESET} Back to Main Menu                                  ${C_YELLOW}│${C_RESET}"
        echo -e "${C_YELLOW}└──────────────────────────────────────────────────────────┘${C_RESET}"
        echo -n -e "\n${C_BOLD}Selection [1-5]: ${C_RESET}"
        read -r choice
        case $choice in
            1) run_script_with_output "$SCRIPTS_DIR/clean.sh" "--full" ;;
            2) run_script_with_output "$SCRIPTS_DIR/clean.sh" "--cache" ;;
            3) run_script_with_output "$SCRIPTS_DIR/clean.sh" "--build" ;;
            4) run_script_with_output "$SCRIPTS_DIR/clean.sh" "--datarot" ;;
            5) return ;;
            *) echo -e "${C_RED}Invalid option!${C_RESET}"; sleep 1 ;;
        esac
    done
}

# ----------------------------------------------------------------------
# Build submenu
# ----------------------------------------------------------------------
show_build_menu() {
    while true; do
        clear
        echo -e "${C_BLUE}┌──────────────────────────────────────────────────────────┐${C_RESET}"
        echo -e "${C_BLUE}│ ${C_BOLD}BUILD EXECUTABLE${C_RESET}                                    ${C_BLUE}│${C_RESET}"
        echo -e "${C_BLUE}├──────────────────────────────────────────────────────────┤${C_RESET}"
        echo -e "${C_BLUE}│${C_RESET}  ${C_BOLD}1)${C_RESET} Linux                                             ${C_BLUE}│${C_RESET}"
        echo -e "${C_BLUE}│${C_RESET}  ${C_BOLD}2)${C_RESET} Windows                                           ${C_BLUE}│${C_RESET}"
        echo -e "${C_BLUE}│${C_RESET}  ${C_BOLD}3)${C_RESET} macOS                                             ${C_BLUE}│${C_RESET}"
        echo -e "${C_BLUE}│${C_RESET}  ${C_BOLD}4)${C_RESET} Android                                           ${C_BLUE}│${C_RESET}"
        echo -e "${C_BLUE}│${C_RESET}  ${C_BOLD}5)${C_RESET} All Platforms                                     ${C_BLUE}│${C_RESET}"
        echo -e "${C_BLUE}│${C_RESET}  ${C_BOLD}6)${C_RESET} Back to Main Menu                                  ${C_BLUE}│${C_RESET}"
        echo -e "${C_BLUE}└──────────────────────────────────────────────────────────┘${C_RESET}"
        echo -n -e "\n${C_BOLD}Selection [1-6]: ${C_RESET}"
        read -r choice
        case $choice in
            1) run_script_with_output "$SCRIPTS_DIR/build.sh" "--linux" ;;
            2) run_script_with_output "$SCRIPTS_DIR/build.sh" "--windows" ;;
            3) run_script_with_output "$SCRIPTS_DIR/build.sh" "--macos" ;;
            4) run_script_with_output "$SCRIPTS_DIR/build.sh" "--android" ;;
            5) run_script_with_output "$SCRIPTS_DIR/build.sh" "--all" ;;
            6) return ;;
            *) echo -e "${C_RED}Invalid option!${C_RESET}"; sleep 1 ;;
        esac
    done
}

# ----------------------------------------------------------------------
# Command-line parsing (Maintains CLI functionality)
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
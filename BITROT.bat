@echo off
setlocal EnableDelayedExpansion

:: Enable ANSI colors via Escape character generation
for /F %%a in ('echo prompt $E ^| cmd') do set "ESC=%%a"
set "C_RESET=%ESC%[0m"
set "C_BOLD=%ESC%[1m"
set "C_GREEN=%ESC%[32m"
set "C_CYAN=%ESC%[36m"
set "C_YELLOW=%ESC%[33m"
set "C_RED=%ESC%[31m"
set "C_BLUE=%ESC%[34m"

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"
set "SCRIPTS_DIR=%SCRIPT_DIR%scripts"

:: Read version from data.rot\lib\VERSION
set "VERSION=unknown"
if exist "bitrot\data.rot\lib\VERSION" (
    set /p VERSION=<"bitrot\data.rot\lib\VERSION"
)

:: Command-line parsing (Maintains CLI functionality)
if "%~1"=="" goto tui
if "%~1"=="shell" (
    if "%~2"=="--editor" (
        call "%SCRIPTS_DIR%\editor.bat"
    ) else (
        call "%SCRIPTS_DIR%\game.bat"
    )
    exit /b %ERRORLEVEL%
)
if "%~1"=="clean" (
    call "%SCRIPTS_DIR%\clean.bat" %2 %3
    exit /b %ERRORLEVEL%
)
if "%~1"=="build" (
    call "%SCRIPTS_DIR%\build.bat" %2 %3
    exit /b %ERRORLEVEL%
)
if "%~1"=="help" goto usage
if "%~1"=="--help" goto usage
if "%~1"=="-h" goto usage
echo Unknown command: %1
goto usage

:usage
echo %C_BOLD%Usage:%C_RESET% BITROT.bat [COMMAND] [OPTIONS...]
echo.
echo Bit Rot SDK - Version: %VERSION%
echo.
echo Commands:
echo   shell [--editor]      Run the game (or editor with --editor^).
echo   clean [OPTIONS]       Clean cache and/or build directory.
echo   build [TARGET]        Build executables for target platform.
echo   help                  Show this help.
echo   (no args^)             Launch interactive ASCII GUI.
exit /b 0

:tui
cls
echo.
echo  %C_GREEN%┌──────────────────────────────────────────────────────────┐%C_RESET%
echo  %C_GREEN%│%C_RESET%              %C_BOLD%ROT ENGINE v.%VERSION%%C_RESET%
echo  %C_GREEN%├──────────────────────────────────────────────────────────┤%C_RESET%
echo  %C_GREEN%│%C_RESET%
echo  %C_GREEN%│%C_RESET%       %C_YELLOW%Bit Rot - Zombie Survivor Game%C_RESET%
echo  %C_GREEN%│%C_RESET%
echo  %C_GREEN%└──────────────────────────────────────────────────────────┘%C_RESET%
echo.
echo %C_BOLD%PRESS [ANY KEY] TO CONTINUE...%C_RESET%
pause >nul

:main_menu
cls
echo %C_CYAN%┌──────────────────────────────────────────────────────────┐%C_RESET%
echo %C_CYAN%│ %C_BOLD%ROT ENGINE MAIN MENU [v%VERSION%]%C_RESET%
echo %C_CYAN%├──────────────────────────────────────────────────────────┤%C_RESET%
echo %C_CYAN%│%C_RESET%  %C_BOLD%1)%C_RESET% Play BitRot
echo %C_CYAN%│%C_RESET%  %C_BOLD%2)%C_RESET% Editor - Tweak the game
echo %C_CYAN%│%C_RESET%  %C_BOLD%3)%C_RESET% Clean Project
echo %C_CYAN%│%C_RESET%  %C_BOLD%4)%C_RESET% Build Executable
echo %C_CYAN%│%C_RESET%  %C_BOLD%5)%C_RESET% Help
echo %C_CYAN%│%C_RESET%  %C_BOLD%6)%C_RESET% Exit
echo %C_CYAN%└──────────────────────────────────────────────────────────┘%C_RESET%
echo.
set "choice="
set /p choice="%C_BOLD%Selection [1-6]: %C_RESET%"

if "%choice%"=="1" (
    echo.
    echo %C_GREEN%Starting Game...%C_RESET%
    start "BitRot Game" "%SCRIPTS_DIR%\game.bat"
    echo %C_GREEN%✔ Application started.%C_RESET%
    echo It should open in its own window.
    echo.
    echo Press [ANY KEY] to return to menu...
    pause >nul
    goto main_menu
)
if "%choice%"=="2" (
    echo.
    echo %C_GREEN%Starting Editor...%C_RESET%
    start "BitRot Editor" "%SCRIPTS_DIR%\editor.bat"
    echo %C_GREEN%✔ Application started.%C_RESET%
    echo It should open in its own window.
    echo.
    echo Press [ANY KEY] to return to menu...
    pause >nul
    goto main_menu
)
if "%choice%"=="3" goto clean_menu
if "%choice%"=="4" goto build_menu
if "%choice%"=="5" (
    call :usage
    echo.
    echo Press [ANY KEY] to return...
    pause >nul
    goto main_menu
)
if "%choice%"=="6" (
    cls
    echo Exiting Rot Engine...
    exit /b 0
)

echo %C_RED%Invalid option!%C_RESET%
timeout /t 1 >nul
goto main_menu

:clean_menu
cls
echo %C_YELLOW%┌──────────────────────────────────────────────────────────┐%C_RESET%
echo %C_YELLOW%│ %C_BOLD%CLEANUP OPTIONS%C_RESET%                                      %C_YELLOW%│%C_RESET%
echo %C_YELLOW%├──────────────────────────────────────────────────────────┤%C_RESET%
echo %C_YELLOW%│%C_RESET%  %C_BOLD%1)%C_RESET% Full clean (cache, build, data.rot/^)            %C_YELLOW%│%C_RESET%
echo %C_YELLOW%│%C_RESET%  %C_BOLD%2)%C_RESET% Clean Python cache only                        %C_YELLOW%│%C_RESET%
echo %C_YELLOW%│%C_RESET%  %C_BOLD%3)%C_RESET% Remove build/ directory only                   %C_YELLOW%│%C_RESET%
echo %C_YELLOW%│%C_RESET%  %C_BOLD%4)%C_RESET% Remove data.rot/ directory only                %C_YELLOW%│%C_RESET%
echo %C_YELLOW%│%C_RESET%  %C_BOLD%5)%C_RESET% Back to Main Menu                              %C_YELLOW%│%C_RESET%
echo %C_YELLOW%└──────────────────────────────────────────────────────────┘%C_RESET%
echo.
set "choice="
set /p choice="%C_BOLD%Selection [1-5]: %C_RESET%"

if "%choice%"=="1" (
    call :run_script "%SCRIPTS_DIR%\clean.bat" "--full"
    goto clean_menu
)
if "%choice%"=="2" (
    call :run_script "%SCRIPTS_DIR%\clean.bat" "--cache"
    goto clean_menu
)
if "%choice%"=="3" (
    call :run_script "%SCRIPTS_DIR%\clean.bat" "--build"
    goto clean_menu
)
if "%choice%"=="4" (
    call :run_script "%SCRIPTS_DIR%\clean.bat" "--datarot"
    goto clean_menu
)
if "%choice%"=="5" goto main_menu

echo %C_RED%Invalid option!%C_RESET%
timeout /t 1 >nul
goto clean_menu

:build_menu
cls
echo %C_BLUE%┌──────────────────────────────────────────────────────────┐%C_RESET%
echo %C_BLUE%│ %C_BOLD%BUILD EXECUTABLE%C_RESET%                                    %C_BLUE%│%C_RESET%
echo %C_BLUE%├──────────────────────────────────────────────────────────┤%C_RESET%
echo %C_BLUE%│%C_RESET%  %C_BOLD%1)%C_RESET% Linux                                          %C_BLUE%│%C_RESET%
echo %C_BLUE%│%C_RESET%  %C_BOLD%2)%C_RESET% Windows                                        %C_BLUE%│%C_RESET%
echo %C_BLUE%│%C_RESET%  %C_BOLD%3)%C_RESET% macOS                                          %C_BLUE%│%C_RESET%
echo %C_BLUE%│%C_RESET%  %C_BOLD%4)%C_RESET% Android                                        %C_BLUE%│%C_RESET%
echo %C_BLUE%│%C_RESET%  %C_BOLD%5)%C_RESET% All Platforms                                  %C_BLUE%│%C_RESET%
echo %C_BLUE%│%C_RESET%  %C_BOLD%6)%C_RESET% Back to Main Menu                              %C_BLUE%│%C_RESET%
echo %C_BLUE%└──────────────────────────────────────────────────────────┘%C_RESET%
echo.
set "choice="
set /p choice="%C_BOLD%Selection [1-6]: %C_RESET%"

if "%choice%"=="1" (
    call :run_script "%SCRIPTS_DIR%\build.bat" "--linux"
    goto build_menu
)
if "%choice%"=="2" (
    call :run_script "%SCRIPTS_DIR%\build.bat" "--windows"
    goto build_menu
)
if "%choice%"=="3" (
    call :run_script "%SCRIPTS_DIR%\build.bat" "--macos"
    goto build_menu
)
if "%choice%"=="4" (
    call :run_script "%SCRIPTS_DIR%\build.bat" "--android"
    goto build_menu
)
if "%choice%"=="5" (
    call :run_script "%SCRIPTS_DIR%\build.bat" "--all"
    goto build_menu
)
if "%choice%"=="6" goto main_menu

echo %C_RED%Invalid option!%C_RESET%
timeout /t 1 >nul
goto build_menu

:run_script
echo.
echo %C_YELLOW%Running: %~nx1 %~2...%C_RESET%
echo.
call "%~1" "%~2"
if %ERRORLEVEL% EQU 0 (
    echo.
    echo %C_GREEN%┌──────────────────────────────────────────┐%C_RESET%
    echo %C_GREEN%│ SUCCESS: Command completed successfully. │%C_RESET%
    echo %C_GREEN%└──────────────────────────────────────────┘%C_RESET%
) else (
    echo.
    echo %C_RED%┌──────────────────────────────────────────┐%C_RESET%
    echo %C_RED%│ ERROR: Command failed.                   │%C_RESET%
    echo %C_RED%└──────────────────────────────────────────┘%C_RESET%
)
echo.
echo Press [ANY KEY] to return to menu...
pause >nul
exit /b 0
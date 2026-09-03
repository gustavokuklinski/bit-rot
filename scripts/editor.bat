@echo off
setlocal EnableDelayedExpansion

set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%.."
cd /d "%PROJECT_ROOT%"

set "VENV_DIR=.venv"
set "APP_SCRIPT=bitrot\editor.py"
set "REQUIREMENTS_FILE=requirements.txt"

set "VENV_ONLY=false"
if "%~1"=="--help" goto show_help
if "%~1"=="--venv" set "VENV_ONLY=true"

:: ----- Virtual environment handling -----
if defined VIRTUAL_ENV (
    echo Using existing virtual environment: %VIRTUAL_ENV%
    set "PYTHON_EXEC=%VIRTUAL_ENV%\Scripts\python.exe"
    if "!VENV_ONLY!"=="true" (
        echo Virtual environment is ready.
        exit /b 0
    )
) else (
    if not exist "!VENV_DIR!" (
        echo Creating virtual environment in !VENV_DIR!...
        python -m venv "!VENV_DIR!"
        if errorlevel 1 (
            echo Failed to create virtual environment.
            exit /b 1
        )
    )
    set "PYTHON_EXEC=!VENV_DIR!\Scripts\python.exe"
    set "PIP_EXEC=!VENV_DIR!\Scripts\pip.exe"

    if exist "!REQUIREMENTS_FILE!" (
        echo Installing requirements from !REQUIREMENTS_FILE!...
        "!PIP_EXEC!" install -r "!REQUIREMENTS_FILE!"
    )
    if exist "bitrot\requirements.txt" (
        echo Installing app-specific requirements from bitrot\requirements.txt...
        "!PIP_EXEC!" install -r "bitrot\requirements.txt"
    )

    if "!VENV_ONLY!"=="true" (
        echo Virtual environment is set up in !VENV_DIR!.
        echo To activate it, run: !VENV_DIR!\Scripts\activate.bat
        exit /b 0
    )
)

:: ----- Run the application from the project root -----
echo Running in directory: %CD%
echo Running: !PYTHON_EXEC! %APP_SCRIPT% %*
"!PYTHON_EXEC!" "%APP_SCRIPT%" %*
exit /b %ERRORLEVEL%

:show_help
echo Usage: editor.bat [OPTIONS] [--] [APP_ARGS...]
echo.
echo Options:
echo   --help      Show this help message and exit.
echo   --venv      Only set up the virtual environment (create if missing, install dependencies^) and exit.
echo               If a virtual environment is already active, it will be used.
echo   Any additional arguments will be passed to the editor.
echo.
echo This script ensures a Python virtual environment is available and then runs the editor.
exit /b 0
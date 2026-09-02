@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0.."

:: Activate virtual environment if available and not active
if not defined VIRTUAL_ENV (
    if exist ".venv\Scripts\activate.bat" (
        call ".venv\Scripts\activate.bat"
    )
)

set "TARGET=%~1"
if "%TARGET%"=="" goto help
if "%TARGET%"=="--help" goto help

if "%TARGET%"=="--windows" (
    call :build_windows
    goto done
)
if "%TARGET%"=="--linux" (
    call :build_linux
    goto done
)
if "%TARGET%"=="--macos" (
    call :build_macos
    goto done
)
if "%TARGET%"=="--android" (
    echo Android builds are not supported via Nuitka.
    goto done
)
if "%TARGET%"=="--all" (
    call :build_linux
    call :build_windows
    call :build_macos
    goto done
)

echo Unknown target: %TARGET%
goto help

:build_windows
call :check_nuitka
if %ERRORLEVEL% NEQ 0 exit /b 1
echo Building Windows executable...
nuitka --onefile --windows-console-mode=disable --windows-icon-from-ico=.\bitrot\game\icons\favicon.ico --output-dir=.\build .\bitrot\bitrot.py
nuitka --onefile --windows-console-mode=disable --windows-icon-from-ico=.\bitrot\game\icons\favicon.ico --output-dir=.\build .\bitrot\editor.py
echo Windows builds ready in .\build\
exit /b 0

:build_linux
call :check_nuitka
if %ERRORLEVEL% NEQ 0 exit /b 1
echo Building Linux executable...
nuitka --onefile --include-data-dir=.\bitrot\game=game --output-dir=.\build .\bitrot\bitrot.py
nuitka --onefile --include-data-dir=.\bitrot\game=game --output-dir=.\build .\bitrot\editor.py
echo Linux builds ready in .\build\
exit /b 0

:build_macos
call :check_nuitka
if %ERRORLEVEL% NEQ 0 exit /b 1
echo Building macOS executable...
nuitka --onefile --macos-create-app-bundle --macos-app-icon=.\bitrot\game\icons\favicon.icns --output-dir=.\build .\bitrot\bitrot.py
nuitka --onefile --macos-create-app-bundle --macos-app-icon=.\bitrot\game\icons\favicon.icns --output-dir=.\build .\bitrot\editor.py
echo macOS builds ready in .\build\
echo After build, run: xattr -cr bitrot.app
exit /b 0

:check_nuitka
where nuitka >nul 2>&1
if errorlevel 1 (
    echo Nuitka not found. Install with: pip install nuitka
    exit /b 1
)
exit /b 0

:help
echo Usage: build.bat [TARGET]
echo.
echo Targets:
echo   --linux      Build for Linux (onefile^)
echo   --windows    Build for Windows (onefile, console disabled^)
echo   --macos      Build for macOS (app bundle^)
echo   --all        Build all of the above
exit /b 1

:done
echo Build completed.
exit /b 0
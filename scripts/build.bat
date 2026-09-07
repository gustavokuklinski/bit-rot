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
if "%TARGET%"=="--android" (
    echo Android builds are not supported via Nuitka.
    goto done
)
if "%TARGET%"=="--all" (
    call :build_windows
    goto done
)

echo Unknown target: %TARGET%
goto help

:build_windows
call :check_nuitka
if %ERRORLEVEL% NEQ 0 exit /b 1

:: 1. Generate Certificate
echo Generating signing certificate...
python bitrot/tools/windows_certificate.py cert.pfx
if %ERRORLEVEL% NEQ 0 (
    echo Failed to generate certificate.
    exit /b 1
)

:: 2. Build with Nuitka
echo Building Windows executables...
nuitka --standalone --assume-yes-for-downloads --output-dir=./build --windows-console-mode=disable --windows-icon-from-ico=./bitrot/data.rot/icons/favicon.ico --windows-company-name="Gustavo Kuklinski" --windows-product-name="Bit Rot" --windows-product-version="1.0.0" --windows-file-description="Bit Rot Game Engine" bitrot/bitrot.py
nuitka --standalone --assume-yes-for-downloads --output-dir=./build --windows-console-mode=disable --windows-icon-from-ico=./bitrot/data.rot/icons/favicon.ico --windows-company-name="Gustavo Kuklinski" --windows-product-name="Bit Rot" --windows-product-version="1.0.0" --windows-file-description="Bit Rot Game Engine" bitrot/editor.py

:: 3. Find Signtool.exe (specifically the x64 version)
echo Searching for x64 signtool.exe...
set "SIGNTOOL_PATH="
for /r "C:\Program Files (x86)\Windows Kits\10\bin" %%f in (signtool.exe) do (
    echo %%f | findstr /i "\x64\" >nul
    if !errorlevel! EQU 0 (
        set "SIGNTOOL_PATH=%%f"
    )
)

if "%SIGNTOOL_PATH%"=="" (
    echo ERROR: x64 signtool.exe not found! Please install Windows SDK.
    exit /b 1
)
echo Found x64 signtool at: %SIGNTOOL_PATH%

:: 4. Sign the binaries
echo Signing binaries...
"%SIGNTOOL_PATH%" sign /f cert.pfx /p "bitrot&Certificate@Windows912026" /tr http://timestamp.digicert.com /td sha256 /fd sha256 "build\bitrot.dist\bitrot.exe"
"%SIGNTOOL_PATH%" sign /f cert.pfx /p "bitrot&Certificate@Windows912026" /tr http://timestamp.digicert.com /td sha256 /fd sha256 "build\editor.dist\editor.exe"

echo Windows builds ready and signed in .\build\
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
echo   --windows    Build and Sign for Windows (standalone)
exit /b 1

:done
echo Build completed.
exit /b 0
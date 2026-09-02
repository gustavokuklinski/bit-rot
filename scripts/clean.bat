@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0.."

set "OPT=%~1"
if "%OPT%"=="--help" goto help
if "%OPT%"=="--full" goto full
if "%OPT%"=="--cache" goto cache
if "%OPT%"=="--build" goto build
if "%OPT%"=="--datarot" goto datarot
if "%OPT%"=="" goto help

echo Unknown option: %OPT%
echo Use --help for usage.
exit /b 1

:full
call :do_cache
call :do_build
call :do_datarot
echo Full clean done (removed __pycache__, build/ and data.rot/^).
exit /b 0

:cache
call :do_cache
echo Python cache cleaned.
exit /b 0

:build
call :do_build
echo build/ directory removed.
exit /b 0

:datarot
call :do_datarot
echo data.rot/ directory removed.
exit /b 0

:do_cache
for /d /r . %%d in (__pycache__) do (
    if exist "%%d" rd /s /q "%%d"
)
exit /b 0

:do_build
if exist "build" rd /s /q "build"
exit /b 0

:do_datarot
if exist "data.rot" rd /s /q "data.rot"
exit /b 0

:help
echo Usage: clean.bat [OPTIONS]
echo.
echo Options:
echo   --full      Remove all __pycache__ folders, build/ and data.rot/.
echo   --cache     Remove only all __pycache__ folders.
echo   --build     Remove only the build/ directory.
echo   --datarot   Remove only the data.rot/ directory.
echo   --help      Show this help.
exit /b 0
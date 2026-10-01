@echo off
setlocal EnableExtensions EnableDelayedExpansion
REM ----------------------------------------------------------------------------
REM  build_app.bat - Windows portable (onefile) + real Setup.exe (Inno Setup)
REM  Version comes from src\__init__.py (single source of truth).
REM
REM  Outputs (example):
REM    dist\windows\0.0.4\portable\WardriveLogVisualizer-0.0.4.exe
REM    dist\windows\0.0.4\setup\WardriveLogVisualizer-0.0.4-windows-setup.exe
REM ----------------------------------------------------------------------------

cd /d "%~dp0.."
set "PLATFORM=windows"

echo.
echo === Wardrive Log Visualizer - PyInstaller build (Windows) ===
echo Working directory: %CD%
echo.

if not exist ".venv\Scripts\python.exe" (
    echo Virtual environment not found. Running setup_env.bat ...
    call "scripts\setup_env.bat"
    if errorlevel 1 exit /b 1
)

call ".venv\Scripts\activate.bat"

where pyinstaller >nul 2>&1
if errorlevel 1 (
    echo ERROR: pyinstaller not found in the virtual environment.
    echo Run scripts\setup_env.bat first.
    exit /b 1
)

for /f "usebackq delims=" %%V in (`python scripts\read_version.py`) do set "VERSION=%%V"
if not defined VERSION (
    echo ERROR: Could not read app version from src\__init__.py
    exit /b 1
)

set "APP_NAME=WardriveLogVisualizer-%VERSION%"
echo App version: %VERSION%
echo.

REM Shared PyInstaller flags for CustomTkinter + tkinterdnd2
set "COMMON_ARGS=--noconfirm --clean --windowed --name %APP_NAME% --paths=. --collect-all customtkinter --collect-all tkinterdnd2 --hidden-import=tkinterdnd2"

set "ICON_PNG=%CD%\assets\wardrive-log-visualizer-icon.png"
set "ICON_PNG_256=%CD%\assets\wardrive-log-visualizer-icon-256.png"
set "ICON_ICO=%CD%\assets\WardriveLogVisualizer.ico"
if not exist "%ICON_PNG%" (
    echo Icon PNG missing; generating placeholders ...
    python scripts\make_placeholder_icon.py
    if errorlevel 1 exit /b 1
)
if not exist "%ICON_ICO%" (
    echo Committed .ico missing; generating %ICON_ICO% from %ICON_PNG% ...
    python scripts\generate_windows_ico.py --input "%ICON_PNG%" --output "%ICON_ICO%"
    if errorlevel 1 exit /b 1
) else (
    echo Using icon: %ICON_ICO%
)

echo [1/3] Building portable (onefile) ...
if exist "dist\%PLATFORM%\%VERSION%\portable" rmdir /s /q "dist\%PLATFORM%\%VERSION%\portable"
if exist "build\%PLATFORM%\%VERSION%\portable" rmdir /s /q "build\%PLATFORM%\%VERSION%\portable"
mkdir "dist\%PLATFORM%\%VERSION%\portable" 2>nul
mkdir "build\%PLATFORM%\%VERSION%\portable" 2>nul

python -m PyInstaller %COMMON_ARGS% ^
    --icon "%ICON_ICO%" ^
    --add-data "%ICON_PNG%;." ^
    --add-data "%ICON_ICO%;." ^
    --add-data "%ICON_PNG_256%;." ^
    --onefile ^
    --distpath "dist\%PLATFORM%\%VERSION%\portable" ^
    --workpath "build\%PLATFORM%\%VERSION%\portable" ^
    --specpath "build\%PLATFORM%\%VERSION%\portable" ^
    src\__main__.py
if errorlevel 1 (
    echo ERROR: portable build failed.
    exit /b 1
)

echo [2/3] Building onedir payload for Setup.exe ...
if exist "dist\%PLATFORM%\%VERSION%\payload" rmdir /s /q "dist\%PLATFORM%\%VERSION%\payload"
if exist "build\%PLATFORM%\%VERSION%\payload" rmdir /s /q "build\%PLATFORM%\%VERSION%\payload"
mkdir "dist\%PLATFORM%\%VERSION%\payload" 2>nul
mkdir "build\%PLATFORM%\%VERSION%\payload" 2>nul

python -m PyInstaller %COMMON_ARGS% ^
    --icon "%ICON_ICO%" ^
    --add-data "%ICON_PNG%;." ^
    --add-data "%ICON_ICO%;." ^
    --add-data "%ICON_PNG_256%;." ^
    --onedir ^
    --distpath "dist\%PLATFORM%\%VERSION%\payload" ^
    --workpath "build\%PLATFORM%\%VERSION%\payload" ^
    --specpath "build\%PLATFORM%\%VERSION%\payload" ^
    src\__main__.py
if errorlevel 1 (
    echo ERROR: onedir payload build failed.
    exit /b 1
)

set "PAYLOAD_DIR=%CD%\dist\%PLATFORM%\%VERSION%\payload\%APP_NAME%"
set "SETUP_DIR=%CD%\dist\%PLATFORM%\%VERSION%\setup"
if not exist "%PAYLOAD_DIR%\%APP_NAME%.exe" (
    echo ERROR: Expected payload exe not found:
    echo   %PAYLOAD_DIR%\%APP_NAME%.exe
    exit /b 1
)

echo [3/3] Building Setup.exe with Inno Setup ...
set "ISCC="
if exist "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" set "ISCC=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if not defined ISCC (
    where ISCC >nul 2>&1
    if not errorlevel 1 for /f "delims=" %%I in ('where ISCC') do set "ISCC=%%I"
)
if not defined ISCC (
    echo ERROR: Inno Setup 6 compiler ^(ISCC.exe^) not found.
    echo Install from https://jrsoftware.org/isinfo.php or: choco install innosetup -y
    exit /b 1
)

if exist "%SETUP_DIR%" rmdir /s /q "%SETUP_DIR%"
mkdir "%SETUP_DIR%" 2>nul

"%ISCC%" /Q ^
    "/DMyAppVersion=%VERSION%" ^
    "/DMyAppExeName=%APP_NAME%.exe" ^
    "/DMyAppSource=%PAYLOAD_DIR%" ^
    "/DMyAppOutput=%SETUP_DIR%" ^
    "/DMyAppIcon=%ICON_ICO%" ^
    "scripts\windows\WardriveLogVisualizer.iss"
if errorlevel 1 (
    echo ERROR: Inno Setup compile failed.
    exit /b 1
)

if not exist "%SETUP_DIR%\WardriveLogVisualizer-%VERSION%-windows-setup.exe" (
    echo ERROR: Setup.exe was not created.
    exit /b 1
)

echo.
echo Build complete:
echo   Portable : dist\%PLATFORM%\%VERSION%\portable\%APP_NAME%.exe
echo   Setup    : dist\%PLATFORM%\%VERSION%\setup\WardriveLogVisualizer-%VERSION%-windows-setup.exe
echo.
exit /b 0

@echo off
REM ----------------------------------------------------------------------------
REM  run_app.bat - launch Wardrive Log Visualizer for a quick smoke test (no build)
REM ----------------------------------------------------------------------------

cd /d "%~dp0.."

if not exist ".venv\Scripts\python.exe" (
    echo Virtual environment not found. Running setup_env.bat ...
    call "scripts\setup_env.bat"
    if errorlevel 1 exit /b 1
)

call ".venv\Scripts\activate.bat"
echo Starting Wardrive Log Visualizer ...
python -m src
exit /b %ERRORLEVEL%

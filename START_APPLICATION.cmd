@echo off
setlocal

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo.
    echo ERROR: The private Python environment was not found.
    echo.
    pause
    exit /b 1
)

if not exist "run.py" (
    echo.
    echo ERROR: run.py was not found.
    echo.
    pause
    exit /b 1
)

title Application Starter Platform

echo.
echo Starting Application Starter Platform...
echo Keep this window open while using the application.
echo Press Ctrl+C to stop the server.
echo.

".venv\Scripts\python.exe" "run.py"

if errorlevel 1 (
    echo.
    echo The application stopped because an error occurred.
    pause
)

endlocal

@echo off
rem ============================================================
rem  Project Costing System - one-click launcher for Windows
rem  Double-click this file. It will:
rem    1) find Python
rem    2) install required packages (first run only)
rem    3) start the app and open your browser
rem ============================================================
cd /d "%~dp0"

set PYTHON=
where python >nul 2>nul && set PYTHON=python
if not defined PYTHON (
    where py >nul 2>nul && set PYTHON=py -3
)
if not defined PYTHON (
    echo.
    echo [ERROR] Python not found.
    echo Please install Python 3.11+ from https://www.python.org/downloads/
    echo and check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

echo Using Python: %PYTHON%
%PYTHON% -c "import streamlit" >nul 2>nul
if errorlevel 1 (
    echo Installing required packages... this may take a few minutes.
    %PYTHON% -m pip install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo [ERROR] Package installation failed. See the message above.
        pause
        exit /b 1
    )
)

echo Starting the app... your browser will open at http://localhost:8501
%PYTHON% -m streamlit run app.py
pause

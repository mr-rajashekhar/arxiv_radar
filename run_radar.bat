@echo off
REM Wrapper for Windows Task Scheduler.
REM Adjust PYTHON_EXE if you use a venv.

setlocal
cd /d "%~dp0"

set "PYTHON_EXE=python"
REM If you created a venv:  set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"

"%PYTHON_EXE%" radar.py
exit /b %ERRORLEVEL%

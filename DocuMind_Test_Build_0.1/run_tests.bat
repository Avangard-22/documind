@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo First run install_and_run.bat to install dependencies, or create a Python environment.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m unittest discover -s tests -v
pause

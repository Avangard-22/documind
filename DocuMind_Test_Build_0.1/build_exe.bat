@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo First run install_and_run.bat to create the environment.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean --windowed --name DocuMind main.py
if errorlevel 1 (
  echo EXE build failed.
  pause
  exit /b 1
)
echo Build completed. Check the dist\DocuMind folder.
pause

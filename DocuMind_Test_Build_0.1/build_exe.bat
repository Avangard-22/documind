@echo off
setlocal
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  echo First run install_and_run.bat to create the virtual environment.
  pause
  exit /b 1
)
.venv\Scripts\python -m PyInstaller --noconfirm --clean --onefile --windowed --name DocuMind --collect-all fitz main.py
if errorlevel 1 goto error
echo Build complete: dist\DocuMind.exe
echo Test this EXE on Windows before processing important documents.
pause
exit /b 0
:error
echo EXE build failed.
pause
exit /b 1

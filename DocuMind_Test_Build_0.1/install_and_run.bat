@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
  echo Python launcher "py" not found. Install Python 3.11 or 3.12 first.
  pause
  exit /b 1
)
if not exist ".venv\Scripts\python.exe" (
  py -3.12 -m venv .venv
  if errorlevel 1 (
    echo Could not create virtual environment. Check that Python 3.12 is installed.
    pause
    exit /b 1
  )
)
call ".venv\Scripts\activate.bat"
python -m pip install --upgrade pip
if errorlevel 1 goto failed
pip install -r requirements.txt
if errorlevel 1 goto failed
python main.py
if errorlevel 1 goto failed
exit /b 0
:failed
echo Setup or launch failed. See the message above.
pause
exit /b 1

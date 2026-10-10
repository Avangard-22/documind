@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
  echo Python launcher not found. Install Python 3.12 from python.org and enable the launcher.
  pause
  exit /b 1
)
if not exist .venv py -3.12 -m venv .venv
if errorlevel 1 goto error
.venv\Scripts\python -m pip install --upgrade pip
if errorlevel 1 goto error
.venv\Scripts\python -m pip install -r requirements.txt
if errorlevel 1 goto error
.venv\Scripts\python main.py
if errorlevel 1 goto error
exit /b 0
:error
echo Setup or launch failed. Review the error above.
pause
exit /b 1

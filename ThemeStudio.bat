@echo off
rem Ghoul Cyber - Theme Studio (Windows launcher)
cd /d "%~dp0"
set "PY=python"
where py >nul 2>nul && set "PY=py -3"
%PY% -c "import PIL" >nul 2>nul || %PY% -m pip install --user pillow
%PY% theme_studio.py
if errorlevel 1 pause

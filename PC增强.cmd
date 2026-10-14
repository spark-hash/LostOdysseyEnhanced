@echo off
cd /d "%~dp0"
if defined LO_PYTHON (
    start "" "%LO_PYTHON%" "%~dp0enhancements\panel.py"
    exit /b
)
where pyw.exe >nul 2>nul
if not errorlevel 1 (
    start "" pyw.exe -3 "%~dp0enhancements\panel.py"
    exit /b
)
if exist "%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\pythonw.exe" (
    start "" "%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\pythonw.exe" "%~dp0enhancements\panel.py"
    exit /b
)
echo Python with Tkinter is required. Set LO_PYTHON to your Python executable.
pause

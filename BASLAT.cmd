@echo off
setlocal
cd /d "%~dp0"
set "PYTHONUTF8=1"
set "OGUN_PYTHON=%~dp0.venv\Scripts\python.exe"
if not exist "%OGUN_PYTHON%" set "OGUN_PYTHON=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if not exist "%OGUN_PYTHON%" set "OGUN_PYTHON=python"
if /i "%~1"=="--check" (
    "%OGUN_PYTHON%" --version
    exit /b
)
echo Uygulama: http://127.0.0.1:8767
echo Fiyat yonetimi: http://127.0.0.1:8767/admin
echo Durdurmak icin Ctrl+C. Ayni anda yalnizca bir sunucu calistirin.
if /i "%~1"=="--lan" (
    "%OGUN_PYTHON%" server\app.py --lan
) else (
    "%OGUN_PYTHON%" server\app.py
)
pause
endlocal

@echo off
where pythonw >nul 2>nul
if not errorlevel 1 (
    start "" pythonw "%~dp0src\main.py" --gui
    exit /b 0
)

where pyw >nul 2>nul
if not errorlevel 1 (
    start "" pyw -3 "%~dp0src\main.py" --gui
    exit /b 0
)

echo No se encontro Python para Windows.
echo Instala Python y asegurate de incluirlo en PATH.
pause

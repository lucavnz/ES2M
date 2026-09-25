@echo off
setlocal
chcp 65001 >nul

echo =====================================================================
echo  ELABORAZIONE COMPLETA SESSIONE BURST 720° (-360° a +360°)
echo =====================================================================
echo.

set SCRIPT_DIR=%~dp0
set PY_SCRIPT=%SCRIPT_DIR%elabora_sessione_completa.py
set TARGET_DIR=%SCRIPT_DIR%sessione_burst_20260923_143754

py --version >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Esecuzione con Python di sistema 'py'...
    py "%PY_SCRIPT%" "%TARGET_DIR%"
    goto fine
)

python --version >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Esecuzione con Python 'python'...
    python "%PY_SCRIPT%" "%TARGET_DIR%"
    goto fine
)

echo [ERRORE] Python non trovato nel sistema.
pause
exit /b 1

:fine
echo.
echo Elaborazione completata!
pause

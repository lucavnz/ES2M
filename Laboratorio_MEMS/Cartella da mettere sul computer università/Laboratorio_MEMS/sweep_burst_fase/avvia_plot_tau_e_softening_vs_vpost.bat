@echo off
setlocal
chcp 65001 >nul

echo =====================================================================
echo  GRAFICO COMPARATIVO: TAU, FREQUENZA fs, V_post ed EFFETTO DUFFING
echo =====================================================================
echo.

set SCRIPT_DIR=%~dp0
set PY_SCRIPT=%SCRIPT_DIR%plotta_tau_e_softening_vs_vpost.py

py --version >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Esecuzione con Python di sistema 'py'...
    py "%PY_SCRIPT%"
    goto fine
)

python --version >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Esecuzione con Python 'python'...
    python "%PY_SCRIPT%"
    goto fine
)

echo [ERRORE] Python non trovato nel sistema.
pause
exit /b 1

:fine
echo.
echo Operazione completata.
pause

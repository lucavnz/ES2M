@echo off
title Test Rapido Generatore Agilent 33220A
cd /d "%~dp0"

echo ============================================================
echo   TEST SWEEP FREQUENZA SOLO GENERATORE (AGILENT 33220A)
echo ============================================================
echo.

if exist "python\python.exe" (
    echo [OK] Uso Python Portable integrato...
    python\python.exe test_sweep_solo_generatore.py %*
    goto fine
)

where py >nul 2>nul
if %ERRORLEVEL% equ 0 (
    py test_sweep_solo_generatore.py %*
    goto fine
)

where python >nul 2>nul
if %ERRORLEVEL% equ 0 (
    python test_sweep_solo_generatore.py %*
    goto fine
)

echo [ERRORE] Python non trovato.
pause

:fine

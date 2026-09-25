@echo off
title Visualizzatore Grafico Bode Ultimo Sweep
cd /d "%~dp0"

echo ============================================================
echo   TRACCIAMENTO GRAFICO BODE ULTIMO SWEEP
echo ============================================================
echo.

:: 1. Usa Python Portable integrato (priorita massima per chiavetta USB)
if exist "python\python.exe" (
    echo [OK] Uso Python Portable integrato...
    python\python.exe plotta_sweep.py %*
    goto fine
)

:: 2. Fallback su py di sistema
where py >nul 2>nul
if %ERRORLEVEL% equ 0 (
    py plotta_sweep.py %*
    goto fine
)

:: 3. Fallback su python di sistema
where python >nul 2>nul
if %ERRORLEVEL% equ 0 (
    python plotta_sweep.py %*
    goto fine
)

echo [ERRORE] Python non trovato.

:fine
echo.
pause

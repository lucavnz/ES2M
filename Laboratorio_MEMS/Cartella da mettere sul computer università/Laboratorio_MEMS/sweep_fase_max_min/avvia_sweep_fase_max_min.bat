@echo off
title Sweep Burst Phase (Vmax, Vmin, Picco)
cd /d "%~dp0"

echo ============================================================
echo   AVVIO SWEEP BURST PHASE - MISURA VMAX, VMIN, A_PEAK
echo   (Agilent 33220A + Keysight MSO-X 3014A)
echo ============================================================
echo.

:: 1. Cerca Python Portatile nella cartella genitore ..\python (standard)
if exist "..\python\python.exe" (
    echo [OK] Uso Python Portable integrato...
    ..\python\python.exe sweep_fase_max_min.py %*
    goto fine
)

:: 2. Cerca Python Portatile nella cartella locale .\python
if exist "python\python.exe" (
    echo [OK] Uso Python Portable locale...
    python\python.exe sweep_fase_max_min.py %*
    goto fine
)

:: 3. Fallback su Python di sistema
where py >nul 2>nul
if %ERRORLEVEL% equ 0 (
    echo [OK] Uso Python di sistema py...
    py sweep_fase_max_min.py %*
    goto fine
)

where python >nul 2>nul
if %ERRORLEVEL% equ 0 (
    echo [OK] Uso Python di sistema python...
    python sweep_fase_max_min.py %*
    goto fine
)

echo [ERRORE] Python non trovato!
echo Assicurati che la cartella 'python' sia presente dentro 'Laboratorio_MEMS'.
pause
exit /b 1

:fine
echo.
echo ============================================================
echo Fine esecuzione sweep.
pause

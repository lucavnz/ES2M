@echo off
title Sweep Burst Phase - Misura Vmax, Vmin, Picco (33220A + MSO-X 3014A)
cd /d "%~dp0"

echo ============================================================
echo   AVVIO SWEEP BURST PHASE - MISURA VMAX, VMIN, A_PEAK
echo   (Agilent 33220A + Keysight MSO-X 3014A)
echo ============================================================
echo.

if not exist "sweep_fase_max_min\sweep_fase_max_min.py" (
    echo [ERRORE] File 'sweep_fase_max_min\sweep_fase_max_min.py' non trovato!
    echo Assicurati che la cartella 'sweep_fase_max_min' sia dentro 'Laboratorio_MEMS'.
    pause
    exit /b 1
)

cd sweep_fase_max_min

if exist "..\python\python.exe" (
    echo [OK] Uso Python Portable integrato...
    ..\python\python.exe sweep_fase_max_min.py %*
    goto fine
)

if exist "python\python.exe" (
    echo [OK] Uso Python Portable locale...
    python\python.exe sweep_fase_max_min.py %*
    goto fine
)

where py >nul 2>nul
if %ERRORLEVEL% equ 0 (
    echo [OK] Uso Python di sistema py...
    py sweep_fase_max_min.py %*
    goto fine
)

where python >nul 2>nul
if %ERRORLEVEL% equ 0 (
    echo [OK] Uso Python di sistema...
    python sweep_fase_max_min.py %*
    goto fine
)

echo [ERRORE] Python non trovato!
echo Assicurati che la cartella 'python' sia presente in 'Laboratorio_MEMS'.
pause
exit /b 1

:fine
echo.
echo ============================================================
echo Fine esecuzione sweep.
pause

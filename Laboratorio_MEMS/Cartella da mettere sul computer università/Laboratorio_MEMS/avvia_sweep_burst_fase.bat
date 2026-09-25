@echo off
title Sweep Burst Phase MEMS (Agilent 33220A + Keysight MSO-X 3014A)
cd /d "%~dp0"

echo ============================================================
echo   AVVIO SWEEP BURST PHASE MEMS
echo   (Agilent 33220A + Keysight MSO-X 3014A)
echo ============================================================
echo.

if not exist "sweep_burst_fase\sweep_burst_fase.py" (
    echo [ERRORE] File 'sweep_burst_fase\sweep_burst_fase.py' non trovato!
    echo Assicurati di aver copiato la cartella 'sweep_burst_fase' dentro 'Laboratorio_MEMS'.
    pause
    exit /b 1
)

cd sweep_burst_fase

if exist "..\python\python.exe" (
    echo [OK] Uso Python Portable integrato...
    ..\python\python.exe sweep_burst_fase.py %*
    goto fine
)

if exist "python\python.exe" (
    echo [OK] Uso Python Portable locale...
    python\python.exe sweep_burst_fase.py %*
    goto fine
)

where py >nul 2>nul
if %ERRORLEVEL% equ 0 (
    echo [OK] Uso Python di sistema py...
    py sweep_burst_fase.py %*
    goto fine
)

where python >nul 2>nul
if %ERRORLEVEL% equ 0 (
    echo [OK] Uso Python di sistema...
    python sweep_burst_fase.py %*
    goto fine
)

echo [ERRORE] Python non trovato!
echo Assicurati che la cartella 'python' sia presente dentro 'Laboratorio_MEMS'.
pause
exit /b 1

:fine
echo.
echo ============================================================
echo Fine esecuzione sweep Burst Phase.
pause

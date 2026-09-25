@echo off
title Sweep Burst Phase (Agilent 33220A + Keysight MSO-X 3014A)
cd /d "%~dp0"

echo ============================================================
echo   AVVIO SWEEP BURST PHASE (AGILENT 33220A + MSO-X 3014A)
echo   Acquisizione Forme d'Onda CSV 10k + Screenshot PNG
echo ============================================================
echo.

:: 1. Cerca Python Portatile nella cartella genitore ..\python (standard)
if exist "..\python\python.exe" (
    echo [OK] Uso Python Portable integrato...
    ..\python\python.exe sweep_burst_fase.py %*
    goto fine
)

:: 2. Cerca Python Portatile nella cartella locale .\python
if exist "python\python.exe" (
    echo [OK] Uso Python Portable locale...
    python\python.exe sweep_burst_fase.py %*
    goto fine
)

:: 3. Fallback su Python di sistema (se presente)
where py >nul 2>nul
if %ERRORLEVEL% equ 0 (
    echo [OK] Uso Python del sistema py...
    py sweep_burst_fase.py %*
    goto fine
)

where python >nul 2>nul
if %ERRORLEVEL% equ 0 (
    echo [OK] Uso Python del sistema python...
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

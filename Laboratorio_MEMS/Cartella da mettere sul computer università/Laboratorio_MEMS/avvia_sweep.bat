@echo off
title Sweep Frequenza MEMS (Agilent 33220A + MSO-X 3014A)
cd /d "%~dp0"

echo ============================================================
echo   AVVIO SWEEP DI FREQUENZA MEMS - ZERO TRACCE SUL PC
echo ============================================================
echo.

:: Verifica che sweep_mems.py esista nella cartella
if not exist "sweep_mems.py" (
    echo [ERRORE GRAVE] Il file 'sweep_mems.py' non e' presente in questa cartella!
    echo Assicurati di aver copiato TUTTI i file dalla cartella Laboratorio_MEMS alla chiavetta.
    echo.
    pause
    exit /b 1
)

:: 1. Usa la versione portatile inclusa nella cartella (priorita massima)
if exist "python\python.exe" (
    echo [OK] Uso Python Portable integrato...
    python\python.exe sweep_mems.py %*
    goto fine
)

:: 2. Fallback su Python di sistema se presente
where py >nul 2>nul
if %ERRORLEVEL% equ 0 (
    py sweep_mems.py %*
    goto fine
)

where python >nul 2>nul
if %ERRORLEVEL% equ 0 (
    python sweep_mems.py %*
    goto fine
)

echo [ERRORE] Python non trovato.

:fine
echo.
echo ============================================================
echo Fine esecuzione.
pause

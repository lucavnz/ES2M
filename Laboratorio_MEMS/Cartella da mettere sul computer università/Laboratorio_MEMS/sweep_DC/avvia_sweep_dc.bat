@echo off
title Sweep MEMS 2D (VDC Agilent E3646A + Frequenza 33220A)
cd /d "%~dp0"

echo ============================================================
echo   AVVIO SWEEP 2D MEMS (VDC 0-20V + FREQUENZA)
echo   Agilent E3646A + Agilent 33220A + Keysight MSO-X 3014A
echo ============================================================
echo.

:: 1. Cerca Python Portatile nella cartella genitore ..\python (standard)
if exist "..\python\python.exe" (
    echo [OK] Uso Python Portable integrato...
    ..\python\python.exe sweep_dc_mems.py %*
    goto fine
)

:: 2. Cerca Python Portatile nella cartella locale .\python
if exist "python\python.exe" (
    echo [OK] Uso Python Portable locale...
    python\python.exe sweep_dc_mems.py %*
    goto fine
)

:: 3. Fallback su Python di sistema
where py >nul 2>nul
if %ERRORLEVEL% equ 0 (
    echo [OK] Uso Python del sistema py...
    py sweep_dc_mems.py %*
    goto fine
)

where python >nul 2>nul
if %ERRORLEVEL% equ 0 (
    echo [OK] Uso Python del sistema python...
    python sweep_dc_mems.py %*
    goto fine
)

echo [ERRORE] Python non trovato.
pause
exit /b 1

:fine
echo.
echo ============================================================
echo Fine esecuzione sweep DC.
pause

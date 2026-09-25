@echo off
title Sweep MEMS 2D (VDC Agilent E3646A + Frequenza 33220A)
cd /d "%~dp0"

echo ============================================================
echo   AVVIO SWEEP 2D MEMS (VDC 0-20V + FREQUENZA)
echo   Agilent E3646A + Agilent 33220A + Keysight MSO-X 3014A
echo ============================================================
echo.

if not exist "sweep_DC\sweep_dc_mems.py" (
    echo [ERRORE] File 'sweep_DC\sweep_dc_mems.py' non trovato!
    pause
    exit /b 1
)

cd sweep_DC

if exist "..\python\python.exe" (
    ..\python\python.exe sweep_dc_mems.py %*
    goto fine
)

if exist "python\python.exe" (
    python\python.exe sweep_dc_mems.py %*
    goto fine
)

where py >nul 2>nul
if %ERRORLEVEL% equ 0 (
    py sweep_dc_mems.py %*
    goto fine
)

where python >nul 2>nul
if %ERRORLEVEL% equ 0 (
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

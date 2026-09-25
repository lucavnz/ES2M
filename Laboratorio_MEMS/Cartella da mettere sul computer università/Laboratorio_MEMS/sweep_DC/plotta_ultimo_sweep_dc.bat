@echo off
title Visualizzatore Grafici Sweep DC MEMS
cd /d "%~dp0"

echo ============================================================
echo   APERTURA REPORT GRAFICO SWEEP DC (AGILENT E3646A)
echo ============================================================
echo.

if exist "..\python\python.exe" (
    ..\python\python.exe plotta_sweep_dc.py %*
    goto fine
)

if exist "python\python.exe" (
    python\python.exe plotta_sweep_dc.py %*
    goto fine
)

where py >nul 2>nul
if %ERRORLEVEL% equ 0 (
    py plotta_sweep_dc.py %*
    goto fine
)

where python >nul 2>nul
if %ERRORLEVEL% equ 0 (
    python plotta_sweep_dc.py %*
    goto fine
)

echo [ERRORE] Python non trovato.
pause
exit /b 1

:fine

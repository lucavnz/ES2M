@echo off
title Verifica Strumenti Banco MEMS (3 Strumenti)
cd /d "%~dp0"

echo ============================================================
echo   VERIFICA STRUMENTAZIONE COMPLETA BANCO MEMS (3 STRUMENTI)
echo   1. Agilent 33220A (GPIB)
echo   2. Keysight MSO-X 3014A (USB)
echo   3. Agilent E3646A (GPIB)
echo ============================================================
echo.

if exist "..\python\python.exe" (
    ..\python\python.exe verifica_strumenti_dc.py %*
    goto fine
)

if exist "python\python.exe" (
    python\python.exe verifica_strumenti_dc.py %*
    goto fine
)

where py >nul 2>nul
if %ERRORLEVEL% equ 0 (
    py verifica_strumenti_dc.py %*
    goto fine
)

where python >nul 2>nul
if %ERRORLEVEL% equ 0 (
    python verifica_strumenti_dc.py %*
    goto fine
)

echo [ERRORE] Python non trovato.
pause
exit /b 1

:fine

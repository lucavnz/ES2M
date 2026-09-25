@echo off
title Collaudo Rapido Agilent E3646A (Output 1)
cd /d "%~dp0"

echo ============================================================
echo   COLLAUDO RAPIDO ALIMENTATORE AGILENT E3646A
echo ============================================================
echo.

if exist "..\python\python.exe" (
    ..\python\python.exe test_solo_alimentatore_dc.py %*
    goto fine
)

if exist "python\python.exe" (
    python\python.exe test_solo_alimentatore_dc.py %*
    goto fine
)

where py >nul 2>nul
if %ERRORLEVEL% equ 0 (
    py test_solo_alimentatore_dc.py %*
    goto fine
)

where python >nul 2>nul
if %ERRORLEVEL% equ 0 (
    python test_solo_alimentatore_dc.py %*
    goto fine
)

echo [ERRORE] Python non trovato.
pause
exit /b 1

:fine

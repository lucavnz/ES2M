@echo off
title Visualizzatore Tracce Burst Phase
cd /d "%~dp0"

where py >nul 2>nul
if %ERRORLEVEL% equ 0 (
    py plotta_traccia_burst.py %*
    goto fine
)

where python >nul 2>nul
if %ERRORLEVEL% equ 0 (
    python plotta_traccia_burst.py %*
    goto fine
)

echo [ERRORE] Python con matplotlib non trovato.
pause
exit /b 1

:fine
pause

@echo off
title Rigenera Grafici Bode e Fit BVD Sessione DC
cd /d "%~dp0"

where py >nul 2>nul
if %ERRORLEVEL% equ 0 (
    py plot_sessione_bode_completo.py
    pause
    exit /b 0
)

where python >nul 2>nul
if %ERRORLEVEL% equ 0 (
    python plot_sessione_bode_completo.py
    pause
    exit /b 0
)

echo [ERRORE] Python non trovato nel sistema.
pause

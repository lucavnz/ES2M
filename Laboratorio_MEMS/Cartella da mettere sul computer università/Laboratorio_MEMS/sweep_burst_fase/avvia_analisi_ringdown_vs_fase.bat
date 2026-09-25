@echo off
title Analisi Ringdown vs Burst Phase (Tau, Q, A0)
cd /d "%~dp0"

echo ============================================================
echo   ANALISI RINGDOWN vs BURST PHASE MEMS
echo   Calcolo tau, A0, Q e generazione grafici
echo ============================================================
echo.

where py >nul 2>nul
if %ERRORLEVEL% equ 0 (
    py analizza_ringdown_vs_fase.py %*
    goto fine
)

where python >nul 2>nul
if %ERRORLEVEL% equ 0 (
    python analizza_ringdown_vs_fase.py %*
    goto fine
)

echo [ERRORE] Python non trovato.
pause
exit /b 1

:fine
echo.
echo ============================================================
echo Analisi completata.
pause

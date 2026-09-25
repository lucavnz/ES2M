@echo off
title Diagnostica Strumenti VISA
cd /d "%~dp0"

echo ============================================================
echo   VERIFICA COLLEGAMENTO STRUMENTI VISA
echo ============================================================
echo.

if exist "python\python.exe" (
    echo [OK] Uso Python Portable integrato...
    python\python.exe trova_strumenti.py %*
    goto fine
)

where py >nul 2>nul
if %ERRORLEVEL% equ 0 (
    py trova_strumenti.py %*
    goto fine
)

where python >nul 2>nul
if %ERRORLEVEL% equ 0 (
    python trova_strumenti.py %*
    goto fine
)

echo [ERRORE] Python non trovato.
pause

:fine

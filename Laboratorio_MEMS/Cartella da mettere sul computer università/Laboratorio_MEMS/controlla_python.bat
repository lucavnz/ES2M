@echo off
title Verifica Presenza Python
cd /d "%~dp0"

echo ============================================================
echo   STATO AMBIENTE PYTHON PER IL LABORATORIO
echo ============================================================
echo.

if exist "python\python.exe" (
    echo [ESITO: PERFETTO!]
    echo Hai la versione PORTATILE di Python inclusa direttamente in questa cartella!
    echo.
    echo Questo significa che NON serve installare nulla sul PC dell'universita.
    echo Tutto funzionera' direttamente dalla chiavetta USB con zero modifiche al sistema.
    echo.
    echo Dettagli versione portatile:
    python\python.exe --version
    python\python.exe -c "import pyvisa; print(' -> PyVISA: INSTALLATO E PRONTO (Versione ' + pyvisa.__version__ + ')')"
    echo.
    echo Puoi avviare direttamente 'test_solo_generatore.bat' o 'avvia_sweep.bat'.
    goto fine
)

echo [ATTENZIONE] Cartella python portatile non trovata.
pause

:fine
echo.
echo ============================================================
pause

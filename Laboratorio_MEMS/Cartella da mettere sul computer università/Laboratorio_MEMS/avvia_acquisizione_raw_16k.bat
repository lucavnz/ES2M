@echo off
title Acquisizione Forme d'Onda 16k MEMS (Agilent 33220A + Keysight MSO-X 3014A)
cd /d "%~dp0"

echo ============================================================
echo   AVVIO ACQUISIZIONE FORME D'ONDA RAW 16k MEMS
echo   (Agilent 33220A + Keysight MSO-X 3014A - Zero Calcoli)
echo ============================================================
echo.

if not exist "acquisizione_raw_16k\acquisisci_raw_16k.py" (
    echo [ERRORE] File 'acquisizione_raw_16k\acquisisci_raw_16k.py' non trovato!
    echo Assicurati di aver copiato la cartella 'acquisizione_raw_16k' dentro 'Laboratorio_MEMS'.
    pause
    exit /b 1
)

cd acquisizione_raw_16k
call avvia_acquisizione_raw_16k.bat %*

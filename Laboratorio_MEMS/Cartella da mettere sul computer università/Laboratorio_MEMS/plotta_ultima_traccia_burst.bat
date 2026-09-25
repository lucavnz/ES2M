@echo off
title Visualizzatore Tracce Burst Phase
cd /d "%~dp0"

cd sweep_burst_fase
call plotta_traccia_burst.bat %*

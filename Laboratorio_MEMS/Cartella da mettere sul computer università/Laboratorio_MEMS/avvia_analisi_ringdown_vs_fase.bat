@echo off
title Analisi Ringdown vs Burst Phase (Tau, Q, A0)
cd /d "%~dp0"

cd sweep_burst_fase
call avvia_analisi_ringdown_vs_fase.bat %*

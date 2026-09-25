"""
Visualizzatore e Analizzatore Forme d'Onda Burst Phase
======================================================
Carica e visualizza i file CSV esportati dall'oscilloscopio MSO-X 3014A.
Mostra:
  1. Panoramica completa temporale (Burst eccitazione e Ringdown risonatore MEMS).
  2. Dettaglio zoomato ad alta risoluzione dei singoli cicli sinusoidali.
  3. Calcolo ampiezze Vpp, frequenza fondamentale e sfasamento.
"""

import sys
import os
import glob
import csv

def carica_csv_traccia(file_csv):
    tempi = []
    v_ch1 = []
    v_ch3 = []
    info = []
    
    with open(file_csv, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        for row in reader:
            if not row:
                continue
            if row[0].startswith('#'):
                info.append(" ".join(row))
                continue
            if row[0] == 'tempo_s':
                continue
            try:
                t = float(row[0])
                v1 = float(row[1])
                v3 = float(row[2])
                tempi.append(t)
                v_ch1.append(v1)
                v_ch3.append(v3)
            except ValueError:
                continue
                
    return tempi, v_ch1, v_ch3, info

def main():
    target_file = None
    if len(sys.argv) > 1:
        target_file = sys.argv[1]
    else:
        # Cerca file traccia_fase*.csv nella cartella locale o nelle sottocartelle
        cur_dir = os.path.dirname(os.path.abspath(__file__))
        csv_files = glob.glob(os.path.join(cur_dir, "traccia_fase_*.csv"))
        if not csv_files:
            csv_files = glob.glob(os.path.join(cur_dir, "sessione_burst_*", "traccia_fase_*.csv"))
        
        if csv_files:
            # Prendi il piu' recente
            csv_files.sort(key=os.path.getmtime, reverse=True)
            target_file = csv_files[0]
            
    if not target_file or not os.path.exists(target_file):
        print("[ERRORE] Nessun file CSV di traccia trovato da plottare.")
        input("Premi INVIO per uscire...")
        return

    print("=" * 70)
    print(f" CARICAMENTO TRACCIA: {os.path.basename(target_file)}")
    print("=" * 70)

    try:
        import numpy as np
        import matplotlib.pyplot as plt
    except ImportError:
        print("[ERRORE] matplotlib e numpy sono necessari per visualizzare il grafico.")
        print("Assicurati di usare l'interprete Python con matplotlib.")
        input("Premi INVIO per uscire...")
        return

    tempi, v_ch1, v_ch3, info = carica_csv_traccia(target_file)
    n_pts = len(tempi)
    if n_pts == 0:
        print("[ERRORE] Il file CSV non contiene campioni validi.")
        input("Premi INVIO per uscire...")
        return

    tempi_np = np.array(tempi)
    v1_np = np.array(v_ch1)
    v3_np = np.array(v_ch3)

    vpp1 = v1_np.max() - v1_np.min()
    vpp3 = v3_np.max() - v3_np.min()
    dt = tempi_np[1] - tempi_np[0] if n_pts > 1 else 1e-6
    fs = 1.0 / dt

    # Stima frequenza con FFT
    fft_res = np.abs(np.fft.rfft(v3_np))
    freqs = np.fft.rfftfreq(n_pts, d=dt)
    peak_idx = np.argmax(fft_res[1:]) + 1
    f_stima = freqs[peak_idx]

    print(f" -> Campioni caricati   : {n_pts}")
    print(f" -> Finestra temporale  : {tempi_np[0]*1e3:.3f} ms a {tempi_np[-1]*1e3:.3f} ms (Span: {(tempi_np[-1]-tempi_np[0])*1e3:.3f} ms)")
    print(f" -> Sampling Rate       : {fs/1e6:.3f} MSa/s (dt = {dt*1e9:.1f} ns)")
    print(f" -> Vpp CH1 (Vout MEMS) : {vpp1*1e3:.1f} mVpp")
    print(f" -> Vpp CH3 (Vin Gen)   : {vpp3*1e3:.1f} mVpp")
    print(f" -> Frequenza Stimata   : {f_stima:,.1f} Hz")
    if info:
        print(f" -> Dettagli file       : {info[0]}")

    # Configurazione Grafico
    plt.style.use('dark_background')
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(13, 8), dpi=120)

    t_ms = tempi_np * 1e3
    v1_mv = v1_np * 1e3
    v3_mv = v3_np * 1e3

    # Grafico 1: Panoramica completa
    ax1.plot(t_ms, v3_mv, label=f'CH3: Vin Generatore ({vpp3*1e3:.1f} mVpp)', color='#00d2ff', alpha=0.85, linewidth=0.9)
    ax1.plot(t_ms, v1_mv, label=f'CH1: Vout MEMS ({vpp1*1e3:.1f} mVpp)', color='#ffcc00', alpha=0.85, linewidth=0.9)
    ax1.set_title(f'Forma d\'Onda Burst - {os.path.basename(target_file)} ({n_pts} Campioni - Freq: {f_stima:,.0f} Hz)', fontsize=12, fontweight='bold', pad=10)
    ax1.set_xlabel('Tempo [ms]', fontsize=10)
    ax1.set_ylabel('Tensione [mV]', fontsize=10)
    ax1.grid(True, linestyle='--', alpha=0.35)
    ax1.legend(loc='upper right', frameon=True, facecolor='#1e1e1e')

    # Grafico 2: Zoom sui primi cicli
    t_start = t_ms[0]
    # Zoom su 15 cicli del segnale
    t_zoom_span = (15.0 / f_stima) * 1e3 if f_stima > 0 else 0.04
    mask = (t_ms >= t_start) & (t_ms <= t_start + t_zoom_span)

    ax2.plot(t_ms[mask], v3_mv[mask], 'o-', label='CH3: Vin [417 kHz]', color='#00d2ff', markersize=3, linewidth=1.2)
    ax2.plot(t_ms[mask], v1_mv[mask], 's-', label='CH1: Vout MEMS', color='#ffcc00', markersize=3, linewidth=1.2)
    ax2.set_title(f'Dettaglio Singoli Cicli e Sfasamento (Zoom su primi ~{t_zoom_span*1e3:.1f} µs)', fontsize=11, fontweight='bold', pad=10)
    ax2.set_xlabel('Tempo [ms]', fontsize=10)
    ax2.set_ylabel('Tensione [mV]', fontsize=10)
    ax2.grid(True, linestyle='--', alpha=0.35)
    ax2.legend(loc='upper right', frameon=True, facecolor='#1e1e1e')

    plt.tight_layout()
    
    # Salva anche immagine PNG nella stessa cartella del CSV
    png_out = target_file.replace('.csv', '_grafico.png')
    plt.savefig(png_out, dpi=150)
    print(f"\n[OK] Grafico salvato come immagine:\n -> {png_out}")
    print("\nVisualizzazione grafico su finestra interattiva...")
    plt.show()

if __name__ == "__main__":
    main()

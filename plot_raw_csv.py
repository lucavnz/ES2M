import csv
import numpy as np
import matplotlib.pyplot as plt
import os
import shutil

def plot_raw_csv(csv_path='scope_0.csv', output_img='raw_csv_plot.png'):
    # 1. Caricamento dati grezzi dal file CSV
    with open(csv_path, 'r') as f:
        reader = csv.reader(f)
        h1 = next(reader)
        h2 = next(reader)
        rows = [[float(x) for x in r] for r in reader if r]

    data = np.array(rows)
    t = data[:, 0]        # Tempo in secondi
    y = data[:, 1] * 1e3  # Tensione Canale 1 in mV
    
    # Tempo relativo in millisecondi
    t0 = t[0]
    t_ms = (t - t0) * 1e3

    # Creazione figura con 2 pannelli: Panoramica completa + Zoom sui singoli punti
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(13, 8), gridspec_kw={'height_ratios': [1.2, 1]})

    # --- PANNELLO 1: Tutti i 2000 punti grezzi dell'Excel ---
    ax1.plot(t_ms, y, color='#27ae60', linewidth=0.7, alpha=0.8, label='Linea di collegamento dati CSV')
    ax1.scatter(t_ms, y, color='#1e824c', s=6, alpha=0.6, label=f'Punti campionati ({len(t)} punti totali)')
    ax1.set_title('Tracciato Completo dei Dati Grezzi da scope_0.csv (Tutti i 2000 punti)', fontsize=13, fontweight='bold', pad=10)
    ax1.set_xlabel('Tempo [ms]', fontsize=11, fontweight='bold')
    ax1.set_ylabel('Tensione Ch1 [mV]', fontsize=11, fontweight='bold')
    ax1.grid(True, linestyle=':', alpha=0.6)
    ax1.legend(loc='upper right', framealpha=0.9)
    ax1.set_xlim([0, t_ms[-1]])

    # Evidenzia la zona di zoom
    zoom_start_ms = 0.50
    zoom_end_ms = 0.55
    ax1.axvspan(zoom_start_ms, zoom_end_ms, color='#f39c12', alpha=0.2, label='Zona di Zoom (sotto)')

    # --- PANNELLO 2: Zoom ravvicinato sui singoli campioni ---
    mask_zoom = (t_ms >= zoom_start_ms) & (t_ms <= zoom_end_ms)
    t_zoom_us = (t_ms[mask_zoom] - zoom_start_ms) * 1e3  # in microsecondi
    y_zoom = y[mask_zoom]

    ax2.plot(t_zoom_us, y_zoom, color='#2980b9', linestyle='--', linewidth=1.2, label='Interpolazione lineare')
    ax2.scatter(t_zoom_us, y_zoom, color='#e74c3c', s=45, zorder=5, label='Singoli punti del file Excel (Campioni a 1.25 µs)')
    
    # Aggiungi etichette sui primi punti per mostrare i campioni discreti
    for i in range(min(6, len(t_zoom_us))):
        ax2.annotate(f"({t_zoom_us[i]:.1f} µs, {y_zoom[i]:.1f} mV)", 
                     (t_zoom_us[i], y_zoom[i]),
                     textcoords="offset points", 
                     xytext=(0, 10 if y_zoom[i] >= 0 else -15), 
                     ha='center', fontsize=7.5, color='#2c3e50',
                     bbox=dict(boxstyle="round,pad=0.2", fc="yellow", alpha=0.5))

    ax2.set_title(f'Dettaglio Zoom sui Singoli Punti campionati (Intervallo di 50 µs | $\\Delta t = 1.25$ µs)', fontsize=12, fontweight='bold', pad=10)
    ax2.set_xlabel('Tempo nel segmento di zoom [µs]', fontsize=11, fontweight='bold')
    ax2.set_ylabel('Tensione Ch1 [mV]', fontsize=11, fontweight='bold')
    ax2.grid(True, linestyle=':', alpha=0.6)
    ax2.legend(loc='upper right', framealpha=0.9)

    plt.tight_layout()
    plt.savefig(output_img, dpi=300)
    print(f"Grafico salvato con successo in: {output_img}")

    # Copia nella cartella artifacts
    artifact_dir = os.path.expanduser('~/.gemini/antigravity-ide/brain/239bea84-5c41-4868-aaf1-42b82578712d')
    artifact_img = os.path.join(artifact_dir, output_img)
    shutil.copy(output_img, artifact_img)
    print(f"Copiato in artifact: {artifact_img}")

if __name__ == '__main__':
    plot_raw_csv()

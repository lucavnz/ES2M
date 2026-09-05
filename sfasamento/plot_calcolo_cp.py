"""
Script per il plottaggio dei segnali temporali per il calcolo della capacità parassita Cp:
- Misura a 50 kHz (scope_70.csv): regime puramente capacitivo off-resonance
- Misura a 417.79 kHz (scope_69.csv): in prossimità della risonanza/antirisonanza

Genera il grafico 'calcolo_Cp.png' con i due segnali Vin e Vout a confronto.
"""

import os
import numpy as np
import matplotlib.pyplot as plt

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FILE_70 = os.path.join(SCRIPT_DIR, 'scope_70.csv')
FILE_69 = os.path.join(SCRIPT_DIR, 'scope_69.csv')
OUTPUT_PNG = os.path.join(SCRIPT_DIR, 'calcolo_Cp.png')
OUTPUT_PNG_LOWER = os.path.join(SCRIPT_DIR, 'calcolo_cp.png')

plt.rcParams.update({
    'font.family': 'sans-serif',
    'font.size': 10,
    'axes.labelsize': 11,
    'axes.titlesize': 12,
    'xtick.labelsize': 10,
    'ytick.labelsize': 10,
    'legend.fontsize': 10,
    'lines.linewidth': 1.8,
    'grid.alpha': 0.4,
    'grid.linestyle': ':'
})

def genera_grafico_calcolo_cp():
    d70 = np.loadtxt(FILE_70, delimiter=',', skiprows=2)
    t70 = (d70[:, 0] - d70[0, 0]) * 1e6  # Tempo in microsecondi
    vout70 = d70[:, 1]
    vin70 = d70[:, 3]

    d69 = np.loadtxt(FILE_69, delimiter=',', skiprows=2)
    t69 = (d69[:, 0] - d69[0, 0]) * 1e6  # Tempo in microsecondi
    vout69 = d69[:, 1]
    vin69 = d69[:, 3]

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 7.5))

    # Grafico 1: 50 kHz
    ax1.plot(t70, vin70, label='Vin', color='#1f77b4')
    ax1.plot(t70, vout70, label='Vout', color='#d62728')
    ax1.set_title('50 kHz (Off-resonance)')
    ax1.set_xlabel(r'Tempo [$\mu$s]')
    ax1.set_ylabel('Segnali')
    ax1.grid(True)
    ax1.legend(loc='upper right', framealpha=0.95)

    # Grafico 2: ~417.8 kHz
    ax2.plot(t69, vin69, label='Vin', color='#1f77b4')
    ax2.plot(t69, vout69, label='Vout', color='#d62728')
    ax2.set_title('417.79 kHz (Frequenza vicina alla risonanza)')
    ax2.set_xlabel(r'Tempo [$\mu$s]')
    ax2.set_ylabel('Segnali')
    ax2.grid(True)
    ax2.legend(loc='upper right', framealpha=0.95)

    fig.suptitle('Calcolo Cp', fontsize=14, fontweight='bold')
    fig.tight_layout()

    fig.savefig(OUTPUT_PNG, dpi=300)
    fig.savefig(OUTPUT_PNG_LOWER, dpi=300)
    plt.close(fig)
    print(f"Grafico salvato con successo in:\n  - {OUTPUT_PNG}\n  - {OUTPUT_PNG_LOWER}")

if __name__ == '__main__':
    genera_grafico_calcolo_cp()

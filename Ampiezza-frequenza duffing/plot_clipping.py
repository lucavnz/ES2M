"""
Script per plottare la forma d'onda grezza di a_0, a_2, a_4, a_7
"""

import os
import csv
import numpy as np
import matplotlib.pyplot as plt

folder = r"c:\Users\lucaa\Downloads\ES2M\Ampiezza-frequenza duffing"

fig, axes = plt.subplots(4, 1, figsize=(12, 10), sharex=True)

files_to_plot = ["a_0.csv", "a_2.csv", "a_4.csv", "a_7.csv"]
vins = [100, 200, 400, 1000]

for ax, fname, vin in zip(axes, files_to_plot, vins):
    path = os.path.join(folder, fname)
    data = []
    with open(path, 'r') as fp:
        reader = csv.reader(fp)
        next(reader)
        next(reader)
        for row in reader:
            if len(row) >= 4:
                try:
                    data.append([float(row[0]), float(row[1]), float(row[2]), float(row[3])])
                except:
                    pass
    arr = np.array(data)
    t = (arr[:, 0] - arr[0, 0]) * 1e3 # ms
    vout = arr[:, 1] * 1e3 # mV
    vgate = arr[:, 2]
    vin_ch = arr[:, 3] * 1e3 # mV
    
    # Gate off
    idx_off = np.where(vgate < 1.0)[0][0]
    t_off = t[idx_off]
    
    ax.plot(t - t_off, vout, color='#2980b9', linewidth=1.0, label=f'Vout (TIA)')
    ax.plot(t - t_off, vgate * 100, color='#e67e22', linewidth=1.2, label='Gate [x100 mV]')
    ax.axhline(-620, color='red', linestyle='--', alpha=0.5, label='Clip rail (-620 mV)')
    ax.set_ylabel(f'Vin = {vin} mV\n[mV]')
    ax.grid(True)
    ax.set_ylim([-700, 500])
    ax.legend(loc='upper right', fontsize=8)

axes[-1].set_xlabel('Tempo dal Gate OFF [ms]')
fig.suptitle('Ispezione Forme d\'Onda Grezze e Saturazione Negativa', fontsize=13, fontweight='bold')
plt.tight_layout()
plt.savefig(os.path.join(folder, 'ispezione_clipping.png'), dpi=150)
print("Salvato ispezione_clipping.png")

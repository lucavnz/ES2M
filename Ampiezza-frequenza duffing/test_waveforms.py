"""
Ispezione dettagliata del segnale Vout nei vari file.
"""

import os
import csv
import numpy as np

folder = r"c:\Users\lucaa\Downloads\ES2M\Ampiezza-frequenza duffing"

for fname in ["a_0.csv", "a_2.csv", "a_3.csv", "a_4.csv", "a_7.csv"]:
    path = os.path.join(folder, fname)
    data = []
    with open(path, 'r') as fp:
        reader = csv.reader(fp)
        next(reader)
        next(reader)
        for row in reader:
            if len(row) >= 4:
                try:
                    data.append([float(row[0]), float(row[1]), float(row[2])])
                except:
                    pass
    arr = np.array(data)
    t = arr[:, 0]
    vout = arr[:, 1]
    vgate = arr[:, 2]
    
    # Gate off
    idx_off = np.where(vgate < 1.0)[0][0]
    
    # Valori a diversi istanti dopo gate off: +10 us, +100 us, +500 us, +1 ms, +2 ms, +3 ms
    dt = np.median(np.diff(t))
    fs = 1.0 / dt
    
    print(f"\n--- FILE: {fname} (total range: min={np.min(vout)*1e3:.1f} mV, max={np.max(vout)*1e3:.1f} mV) ---")
    for delta_t_ms in [0.01, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 3.0, 5.0]:
        idx = idx_off + int(delta_t_ms * 1e-3 * fs)
        if idx < len(vout):
            # Valuta range pk-pk in una finestrella di 5 periodi (~12 us)
            window = vout[idx:idx+int(12e-6*fs)]
            v_min_w = np.min(window)*1e3
            v_max_w = np.max(window)*1e3
            v_pp_w = (v_max_w - v_min_w)
            print(f"  t_off + {delta_t_ms:5.2f} ms: window min={v_min_w:6.1f} mV, max={v_max_w:6.1f} mV, Vpp={v_pp_w:6.1f} mV")

"""
Script rapido per ispezionare gli 8 file di misura di Duffing con solo numpy/csv.
"""

import glob
import os
import csv
import numpy as np

folder = r"c:\Users\lucaa\Downloads\ES2M\Ampiezza-frequenza duffing"
files = sorted(glob.glob(os.path.join(folder, "a_*.csv")))

vin_map = {
    "a_0.csv": 100,
    "a_1.csv": 150,
    "a_2.csv": 200,
    "a_3.csv": 250,
    "a_4.csv": 400,
    "a_5.csv": 550,
    "a_6.csv": 750,
    "a_7.csv": 1000,
}

print(f"Trovati {len(files)} file.")
for f in files:
    fname = os.path.basename(f)
    vin = vin_map.get(fname, "?")
    
    data = []
    with open(f, 'r') as fp:
        reader = csv.reader(fp)
        header1 = next(reader)
        header2 = next(reader)
        for row in reader:
            if len(row) >= 4:
                try:
                    data.append([float(row[0]), float(row[1]), float(row[2]), float(row[3])])
                except ValueError:
                    pass
    arr = np.array(data)
    t = arr[:, 0]
    vout = arr[:, 1]
    vgate = arr[:, 2]
    vin_ch = arr[:, 3]
    
    dt = np.median(np.diff(t))
    fs = 1.0 / dt
    
    # Trova discesa gate (transizione da > 2V a < 1.0V)
    gate_off_idx = np.where(vgate < 1.0)[0]
    t_off = t[gate_off_idx[0]] if len(gate_off_idx) > 0 else np.nan
    
    # Trova riaccensione gate (se presente alla fine dopo 2 ms da t_off)
    if len(gate_off_idx) > 0:
        idx0 = gate_off_idx[0]
        gate_on_after = np.where((vgate[idx0:] > 1.5) & (t[idx0:] > t_off + 0.002))[0]
        if len(gate_on_after) > 0:
            idx_end = idx0 + gate_on_after[0]
            t_on_end = t[idx_end]
        else:
            idx_end = len(t)
            t_on_end = np.nan
        
        t_dur_rd = (t[idx_end-1] - t_off) * 1e3
        
        # Minimo e massimo di Vout subito dopo gate_off (primi 50 us)
        idx_early_end = min(idx0 + int(50e-6*fs), idx_end)
        v_early = vout[idx0:idx_early_end]
        min_early = np.min(v_early)
        max_early = np.max(v_early)
        
        # Ringdown utile dopo 40 us e prima della riaccensione
        idx_rd_start = idx0 + int(40e-6*fs)
        idx_rd_stop = idx_end - int(10e-6*fs)
        if idx_rd_stop > idx_rd_start:
            v_rd = vout[idx_rd_start:idx_rd_stop]
            amp_rd_pk = np.max(np.abs(v_rd))
        else:
            amp_rd_pk = np.nan
    else:
        min_early, max_early, amp_rd_pk = np.nan, np.nan, np.nan
        t_dur_rd = np.nan
        t_on_end = np.nan
        
    print(f"{fname:8s} | Vin: {vin:>4} mV | t_off: {t_off*1e3:6.3f} ms | t_end: {t_on_end*1e3:6.2f} ms | Durata RD: {t_dur_rd:5.2f} ms | Spike min/max: [{min_early*1e3:6.1f}, {max_early*1e3:6.1f}] mV | Amp RD pk: {amp_rd_pk*1e3:5.1f} mV")

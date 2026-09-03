"""
Analisi del segnale AC a 418 kHz depurato dal drift DC lento per tutti gli 8 file.
"""

import os
import csv
import numpy as np
from scipy.signal import butter, filtfilt, hilbert

folder = r"c:\Users\lucaa\Downloads\ES2M\Ampiezza-frequenza duffing"

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

files = sorted([f for f in os.listdir(folder) if f.startswith("a_") and f.endswith(".csv")])

print(f"{'File':8s} | {'Vin [mV]':8s} | {'T_sat [us]':10s} | {'Amp @ 0.5ms':12s} | {'Amp @ 1.0ms':12s} | {'Amp @ 2.0ms':12s} | {'f0 [Hz]':10s}")
print("-" * 75)

for fname in files:
    path = os.path.join(folder, fname)
    vin = vin_map.get(fname, 0)
    data = []
    with open(path, 'r') as fp:
        reader = csv.reader(fp)
        next(reader)
        next(reader)
        for row in reader:
            if len(row) >= 3:
                try:
                    data.append([float(row[0]), float(row[1]), float(row[2])])
                except:
                    pass
    arr = np.array(data)
    t = arr[:, 0]
    vout = arr[:, 1]
    vgate = arr[:, 2]
    
    dt = np.median(np.diff(t))
    fs = 1.0 / dt
    
    # Gate off
    idx_off = np.where(vgate < 1.0)[0][0]
    t_off = t[idx_off]
    
    # Gate on end (riaccensione)
    gate_on_after = np.where((vgate[idx_off:] > 1.5) & (t[idx_off:] > t_off + 0.002))[0]
    idx_end = idx_off + gate_on_after[0] if len(gate_on_after) > 0 else len(t)
    
    # Durata saturazione rail inferiore (< -0.618 V)
    is_sat = vout[idx_off:idx_end] < -0.618
    sat_samples = 0
    for s in is_sat:
        if s:
            sat_samples += 1
        else:
            break
    t_sat_us = (sat_samples / fs) * 1e6
    
    # Filtro passa-alto / passa-banda attorno a 418 kHz (380 - 450 kHz) per togliere il drift DC
    sos = butter(4, [380e3, 460e3], btype='bandpass', fs=fs, output='sos')
    from scipy.signal import sosfiltfilt
    vout_ac = sosfiltfilt(sos, vout)
    
    # Segmento ringdown depurato (prendiamo dopo la saturazione + 50 us di sicurezza)
    idx_clean_start = idx_off + int(max(t_sat_us*1e-6 + 50e-6, 50e-6) * fs)
    idx_clean_stop = idx_end - int(20e-6 * fs)
    
    t_clean = t[idx_clean_start:idx_clean_stop] - t_off
    v_clean = vout_ac[idx_clean_start:idx_clean_stop]
    
    # Inviluppo di Hilbert
    env = np.abs(hilbert(v_clean))
    
    # FFT per stimare f0
    nfft = len(v_clean) * 4
    freqs = np.fft.rfftfreq(nfft, dt)
    fft_mag = np.abs(np.fft.rfft(v_clean * np.hanning(len(v_clean)), n=nfft))
    idx_pk = np.argmax(fft_mag)
    f0_est = freqs[idx_pk]
    
    # Ampiezze a t = 0.5 ms, 1.0 ms, 2.0 ms
    def get_amp_at(target_t):
        idx = np.argmin(np.abs(t_clean - target_t))
        return env[idx] * 1e3
        
    a_05 = get_amp_at(0.5e-3)
    a_10 = get_amp_at(1.0e-3)
    a_20 = get_amp_at(2.0e-3)
    
    print(f"{fname:8s} | {vin:6d} mV | {t_sat_us:8.1f} us | {a_05:10.2f} mV | {a_10:10.2f} mV | {a_20:10.2f} mV | {f0_est:9.1f} Hz")

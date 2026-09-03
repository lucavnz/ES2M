"""
Analisi approfondita della frequenza istantanea f(t), dell'inviluppo e delle non-linearità.
"""

import os
import csv
import numpy as np
from scipy.signal import butter, sosfiltfilt, hilbert
from scipy.optimize import curve_fit

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

print(f"{'File':8s} | {'Vin [mV]':8s} | {'A0 [mV]':8s} | {'tau [ms]':8s} | {'Q':6s} | {'f0_mean [Hz]':12s} | {'df_instant [Hz]':15s} | {'R^2':7s}")
print("-" * 88)

results = []

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
    
    # Rilevamento saturazione (< -0.615 V)
    is_sat = vout[idx_off:idx_end] < -0.615
    sat_samples = 0
    for s in is_sat:
        if s:
            sat_samples += 1
        else:
            break
    t_sat_us = (sat_samples / fs) * 1e6
    
    # Filtro passa-banda 380 - 450 kHz per isolare il modo a 418 kHz
    sos = butter(4, [380e3, 460e3], btype='bandpass', fs=fs, output='sos')
    vout_ac = sosfiltfilt(sos, vout)
    
    # Segmento pulito post-saturazione (+50 us margine) fino a 4 ms dal gate off
    t_start_margin = max(t_sat_us * 1e-6 + 50e-6, 50e-6)
    idx_start = idx_off + int(t_start_margin * fs)
    idx_stop = min(idx_off + int(4.5e-3 * fs), idx_end - int(20e-6 * fs))
    
    t_seg = t[idx_start:idx_stop] - t_off
    v_seg = vout_ac[idx_start:idx_stop]
    
    # Segnale analitico
    analytic = hilbert(v_seg)
    env = np.abs(analytic)
    phase = np.unwrap(np.angle(analytic))
    
    # Frequenza istantanea (dphase/dt) con smoothing
    dphase = np.diff(phase) / (2 * np.pi * dt)
    # Media mobile su 100 periodi (~240 us) per togliere rumore ad alta frequenza
    w_smooth = int(240e-6 * fs)
    if w_smooth % 2 == 0: w_smooth += 1
    kernel = np.ones(w_smooth) / w_smooth
    f_inst = np.convolve(dphase, kernel, mode='valid')
    t_inst = t_seg[:len(f_inst)]
    
    # Calcolo variazione di frequenza tra inizio del segmento e fine
    f_start = np.mean(f_inst[:int(200e-6*fs)])
    f_end = np.mean(f_inst[-int(500e-6*fs):])
    df_inst = f_start - f_end
    f0_mean = np.mean(f_end)
    
    # Fit esponenziale inviluppo
    def exp_func(t_val, a0, tau, c):
        return a0 * np.exp(-t_val / tau) + c
        
    try:
        popt, _ = curve_fit(exp_func, t_seg, env, p0=[env[0], 0.0023, 0.0], bounds=([0, 0.0005, -0.01], [2.0, 0.01, 0.01]))
        a0_fit, tau_fit, c_fit = popt
        res = env - exp_func(t_seg, *popt)
        ss_res = np.sum(res**2)
        ss_tot = np.sum((env - np.mean(env))**2)
        r2 = 1.0 - (ss_res / ss_tot)
        q_factor = np.pi * f0_mean * tau_fit
    except Exception as e:
        a0_fit, tau_fit, q_factor, r2 = np.nan, np.nan, np.nan, np.nan
        
    results.append({
        'file': fname, 'vin': vin, 'a0': a0_fit*1e3, 'tau': tau_fit*1e3,
        'q': q_factor, 'f0': f0_mean, 'df_inst': df_inst, 'r2': r2,
        't_sat_us': t_sat_us
    })
    
    print(f"{fname:8s} | {vin:6d} mV | {a0_fit*1e3:6.2f} mV | {tau_fit*1e3:6.3f} ms | {q_factor:6.0f} | {f0_mean:10.1f} Hz | {df_inst:12.2f} Hz | {r2:7.5f}")

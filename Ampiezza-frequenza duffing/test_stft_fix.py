"""
Miglioramento dello Spettrogramma e del Chirp di frequenza.
"""

import os
import csv
import numpy as np
from scipy.signal import butter, sosfiltfilt, hilbert, spectrogram, savgol_filter
import matplotlib.pyplot as plt

folder = r"c:\Users\lucaa\Downloads\ES2M\Ampiezza-frequenza duffing"

# Test su a_7.csv
path = os.path.join(folder, "a_7.csv")
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
idx_off = np.where(vgate < 1.0)[0][0]
t_off = t[idx_off]

# Segmento utile
idx_start = idx_off + int(250e-6 * fs)
idx_end = idx_off + int(4.5e-3 * fs)

t_seg = t[idx_start:idx_end] - t_off
v_seg = vout[idx_start:idx_end]

sos = butter(4, [390e3, 450e3], btype='bandpass', fs=fs, output='sos')
v_ac = sosfiltfilt(sos, v_seg)

# Spectrogram
nperseg = int(400e-6 * fs) # ~1360 samples
noverlap = int(370e-6 * fs)
f_spec, t_spec, Sxx = spectrogram(v_ac, fs=fs, nperseg=nperseg, noverlap=noverlap, nfft=nperseg*8)

print("f_spec range:", np.min(f_spec), np.max(f_spec))
print("t_spec range:", np.min(t_spec)*1e3, np.max(t_spec)*1e3)
print("Sxx range:", np.min(Sxx), np.max(Sxx))

# Frequency tracking via Savitzky-Golay smoothed unwrapped phase
analytic = hilbert(v_ac)
phase = np.unwrap(np.angle(analytic))
# Savitzky-Golay filter on phase
win_len = int(300e-6 * fs)
if win_len % 2 == 0: win_len += 1
# First derivative with Savitzky-Golay
dphase_sg = savgol_filter(phase, window_length=win_len, polyorder=2, deriv=1, delta=dt)
f_inst_sg = dphase_sg / (2 * np.pi)

print("f_inst mean:", np.mean(f_inst_sg))
print("f_inst at start:", np.mean(f_inst_sg[:int(200e-6*fs)]))
print("f_inst at end:", np.mean(f_inst_sg[-int(500e-6*fs):]))

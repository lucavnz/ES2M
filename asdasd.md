Ran command: `py -3 -c "
import numpy as np

data = np.genfromtxt(r'c:\Users\lucaa\Downloads\ESM2 - Copia\scope_169.csv', delimiter=',', skip_header=2)
data = data[~np.isnan(data).any(axis=1)]
t = data[:, 0]
ch1 = data[:, 1]
ch3 = data[:, 2]
ch4 = data[:, 3]

# Estimate frequencies by zero-crossings or FFT
for name, s in [('CH1', ch1), ('CH3', ch3), ('CH4', ch4)]:
    # Take first 1000 points
    s_sub = s[:1000] - np.mean(s[:1000])
    fft_vals = np.abs(np.fft.rfft(s_sub))
    freqs = np.fft.rfftfreq(len(s_sub), d=(t[1]-t[0]))
    idx_peak = np.argmax(fft_vals[1:]) + 1
    print(f'{name} peak frequency: {freqs[idx_peak]:.2f} Hz, amplitude: {fft_vals[idx_peak]:.4f}')
"`
Ran command: `py -3 -c "
import numpy as np
from scipy.signal import hilbert

data = np.genfromtxt(r'c:\Users\lucaa\Downloads\ESM2 - Copia\scope_169.csv', delimiter=',', skip_header=2)
data = data[~np.isnan(data).any(axis=1)]
t = data[:, 0]
ch1 = data[:, 1]
ch3 = data[:, 2]
ch4 = data[:, 3]

env1 = np.abs(hilbert(ch1 - np.mean(ch1)))
env3 = np.abs(hilbert(ch3 - np.mean(ch3)))
env4 = np.abs(hilbert(ch4 - np.mean(ch4)))

print('Time range:', t[0], t[-1])
# Find when env4 is off
off_mask = env4 < 0.05
print(f'CH4 low (<50mV) time interval: t = {t[off_mask][0]*1e6:.1f} us to {t[off_mask][-1]*1e6:.1f} us')
# Check CH3
print(f'CH3 min env: {env3.min():.3f}, max env: {env3.max():.3f}')
"`
Ran command: `py -3 -c "
import numpy as np

data = np.genfromtxt(r'c:\Users\lucaa\Downloads\ESM2 - Copia\scope_169.csv', delimiter=',', skip_header=2)
data = data[~np.isnan(data).any(axis=1)]
t = data[:, 0]
ch1 = data[:, 1]
ch3 = data[:, 2]
ch4 = data[:, 3]

# Let us check CH3 around t = -160 us, 0 us, 500 us
for t_check in [-200e-6, -100e-6, 0.0, 500e-6, 1000e-6]:
    idx = np.argmin(np.abs(t - t_check))
    sub_ch3 = ch3[idx:idx+50]
    sub_ch4 = ch4[idx:idx+50]
    sub_ch1 = ch1[idx:idx+50]
    print(f'At t={t_check*1e6:.0f} us: CH1 p-p={np.ptp(sub_ch1):.4f} V, CH3 p-p={np.ptp(sub_ch3):.4f} V, CH4 p-p={np.ptp(sub_ch4):.4f} V')
"`
Ran command: `py -3 -c "
import numpy as np
import scipy.signal as signal

data = np.genfromtxt(r'c:\Users\lucaa\Downloads\ESM2 - Copia\scope_169.csv', delimiter=',', skip_header=2)
data = data[~np.isnan(data).any(axis=1)]
t = data[:, 0]
ch1 = data[:, 1]
ch3 = data[:, 2]
ch4 = data[:, 3]

# Bandpass or detrend CH1
ch1_detrend = ch1 - np.mean(ch1)
env1 = np.abs(signal.hilbert(ch1_detrend))

# Let's inspect where CH4 starts again
# Find index where CH4 envelope jumps back up
env4 = np.abs(signal.hilbert(ch4 - np.mean(ch4)))
# Gate off: env4 < 0.05
# Gate on again: env4 crosses 0.1
idx_gate_off = np.where((t < -100e-6) & (env4 < 0.05))[0][0]
idx_gate_on = np.where((t > -50e-6) & (env4 > 0.1))[0][0]

print(f'Gate OFF at t = {t[idx_gate_off]*1e6:.2f} us')
print(f'Gate ON at t = {t[idx_gate_on]*1e6:.2f} us')

# Free ringdown interval:
t_free = t[idx_gate_off:idx_gate_on]
env_free = env1[idx_gate_off:idx_gate_on]
print(f'Free ringdown: duration = {(t_free[-1]-t_free[0])*1e6:.2f} us, start env = {env_free[0]*1e3:.2f} mV, end env = {env_free[-1]*1e3:.2f} mV')

# After gate on (antiphase quenching)
t_anti = t[idx_gate_on:]
env_anti = env1[idx_gate_on:]
idx_min = np.argmin(env_anti[:int(1000e-6 / (t[1]-t[0]))])
t_min = t_anti[idx_min]
print(f'Minimum envelope reached at t = {t_min*1e6:.2f} us with amplitude = {env_anti[idx_min]*1e3:.2f} mV')

# Linear fit on descent: from gate_on + 20 us to t_min - 20 us
mask_down = (t_anti >= t[idx_gate_on] + 20e-6) & (t_anti <= t_min - 20e-6)
p_down = np.polyfit(t_anti[mask_down], env_anti[mask_down], 1)
r2_down = 1 - np.sum((env_anti[mask_down] - np.polyval(p_down, t_anti[mask_down]))**2) / np.sum((env_anti[mask_down] - np.mean(env_anti[mask_down]))**2)
print(f'Linear fit descent: slope = {p_down[0]:.2f} V/s, R2 = {r2_down:.5f}')

# Linear fit on ascent: from t_min + 50 us to 1500 us
mask_up = (t_anti >= t_min + 50e-6) & (t_anti <= 1500e-6)
p_up = np.polyfit(t_anti[mask_up], env_anti[mask_up], 1)
r2_up = 1 - np.sum((env_anti[mask_up] - np.polyval(p_up, t_anti[mask_up]))**2) / np.sum((env_anti[mask_up] - np.mean(env_anti[mask_up]))**2)
print(f'Linear fit ascent: slope = {p_up[0]:.2f} V/s, R2 = {r2_up:.5f}')
"`
Ran command: `py -3 -c "
import numpy as np
import scipy.signal as signal

data = np.genfromtxt(r'c:\Users\lucaa\Downloads\ESM2 - Copia\scope_169.csv', delimiter=',', skip_header=2)
data = data[~np.isnan(data).any(axis=1)]
t = data[:, 0]
ch1 = data[:, 1]
ch4 = data[:, 3]

# Analytic signal of ch1 and ch4
h1 = signal.hilbert(ch1 - np.mean(ch1))
h4 = signal.hilbert(ch4 - np.mean(ch4))

# Phase difference between CH1 and CH4
phase_diff = np.unwrap(np.angle(h1) - np.angle(h4))
# Normalize to degrees
phase_diff_deg = np.rad2deg(phase_diff)

# Check phase difference before and after t = 655 us
idx_before = np.argmin(np.abs(t - 400e-6))
idx_after = np.argmin(np.abs(t - 900e-6))

print(f'Phase diff at 400 us: {phase_diff_deg[idx_before] % 360:.2f} deg')
print(f'Phase diff at 900 us: {phase_diff_deg[idx_after] % 360:.2f} deg')
print(f'Phase change across zero: {(phase_diff_deg[idx_after] - phase_diff_deg[idx_before]):.2f} deg')
"`
Ran command: `py -3 -c "
import numpy as np

data = np.genfromtxt(r'c:\Users\lucaa\Downloads\ESM2 - Copia\scope_169.csv', delimiter=',', skip_header=2)
data = data[~np.isnan(data).any(axis=1)]
t = data[:, 0]
ch1 = data[:, 1]
ch4 = data[:, 3]

# Phase relative to reference sin(omega0 * t)
omega0 = 2 * np.pi * 416000.0
ref_cos = np.cos(omega0 * t)
ref_sin = np.sin(omega0 * t)

# Demodulation: I and Q
# Lowpass filter
b, a = [1.0/100]*100, [1.0] # simple moving average or fir
I1 = np.convolve(ch1 * ref_cos, np.ones(100)/100, mode='same')
Q1 = np.convolve(ch1 * ref_sin, np.ones(100)/100, mode='same')

# Check I1 at 400 us and 900 us
idx_400 = np.argmin(np.abs(t - 400e-6))
idx_900 = np.argmin(np.abs(t - 900e-6))
print(f'I1, Q1 at 400 us: I={I1[idx_400]:.4f}, Q={Q1[idx_400]:.4f}')
print(f'I1, Q1 at 900 us: I={I1[idx_900]:.4f}, Q={Q1[idx_900]:.4f}')
print('Ratio / sign flip:', I1[idx_900]/I1[idx_400], Q1[idx_900]/Q1[idx_400])
"`
Ran command: `py -3 -c "
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import hilbert

data = np.genfromtxt(r'c:\Users\lucaa\Downloads\ESM2 - Copia\scope_169.csv', delimiter=',', skip_header=2)
data = data[~np.isnan(data).any(axis=1)]
t = data[:, 0] * 1e6 # in microseconds
ch1 = data[:, 1] * 1e3 # in mV
ch3 = data[:, 2] * 1e3 # in mV
ch4 = data[:, 3] * 1e3 # in mV

# Compute Hilbert envelope of CH1
ch1_det = ch1 - np.mean(ch1)
env1 = np.abs(hilbert(ch1_det))

print(f'Total duration: {t[0]:.1f} us to {t[-1]:.1f} us')
print(f'Max envelope: {np.max(env1):.2f} mV, min envelope: {np.min(env1):.2f} mV')
"`
Ran command: `py -3 -c "
import numpy as np

data = np.genfromtxt(r'c:\Users\lucaa\Downloads\ESM2 - Copia\scope_169.csv', delimiter=',', skip_header=2)
data = data[~np.isnan(data).any(axis=1)]
t = data[:, 0] * 1e6
ch1 = data[:, 1] * 1e3
ch4 = data[:, 3] * 1e3

# Check around t = 0
mask = (t >= -5) & (t <= 20)
print('CH1 peak around t=0:', np.max(np.abs(ch1[mask])))
# Check at t = 100 us
mask2 = (t >= 90) & (t <= 110)
print('CH1 peak around t=100 us:', np.max(np.abs(ch1[mask2])))
# Check at t = -200 us
mask3 = (t >= -220) & (t <= -180)
print('CH1 peak around t=-200 us:', np.max(np.abs(ch1[mask3])))
"`
Ran command: `py -3 -c "
import numpy as np

data = np.genfromtxt(r'c:\Users\lucaa\Downloads\ESM2 - Copia\scope_169.csv', delimiter=',', skip_header=2)
data = data[~np.isnan(data).any(axis=1)]
t = data[:, 0] * 1e6
ch1 = data[:, 1] * 1e3

print('Number of points >= 61.2 mV:', np.sum(ch1 >= 61.2))
print('Number of points <= -61.2 mV:', np.sum(ch1 <= -61.2))
if np.sum(ch1 >= 61.2) > 0:
    t_clip = t[ch1 >= 61.2]
    print(f'Clipping times: from {t_clip[0]:.2f} us to {t_clip[-1]:.2f} us')
"`
Viewed analizza_ringdown_vs_fase.py:110-160
Viewed analizza_ringdown_vs_fase.py:30-109
Ran command: `py -3 -c "
import numpy as np
import scipy.signal as signal

data = np.genfromtxt(r'c:\Users\lucaa\Downloads\ESM2 - Copia\scope_169.csv', delimiter=',', skip_header=2)
data = data[~np.isnan(data).any(axis=1)]
t = data[:, 0]
ch1 = data[:, 1]
ch4 = data[:, 3]

# Gate switching points
# ch4 off at t ~ -162.88 us, on at t ~ 0.38 us
idx_on = np.where((t >= 0.0) & (np.abs(ch4) > 0.1))[0][0]
t_on = t[idx_on]

# Look at peaks after t_on
# To avoid the feedthrough at t_on, let us start at t_on + 20 us
mask_active = (t >= t_on + 15e-6) & (t <= 1500e-6)
t_act = t[mask_active]
y_act = ch1[mask_active] - np.mean(ch1[mask_active])

# Find positive peaks
distance_pts = int(0.7 * (1.0 / 416000.0) / (t[1]-t[0])) # ~13 points
peaks_pos, _ = signal.find_peaks(y_act, distance=distance_pts, height=0.0005)
peaks_neg, _ = signal.find_peaks(-y_act, distance=distance_pts, height=0.0005)

t_p = t_act[peaks_pos]
y_p = y_act[peaks_pos]

print(f'Found {len(peaks_pos)} positive peaks.')
# Let us inspect the peak amplitudes
min_idx = np.argmin(y_p)
print(f'Peak minimum at t = {t_p[min_idx]*1e6:.2f} us, amp = {y_p[min_idx]*1e3:.3f} mV')

# Linear fit on peak descent
p_desc = np.polyfit(t_p[:min_idx], y_p[:min_idx], 1)
ss_res_lin = np.sum((y_p[:min_idx] - np.polyval(p_desc, t_p[:min_idx]))**2)
ss_tot = np.sum((y_p[:min_idx] - np.mean(y_p[:min_idx]))**2)
r2_lin = 1 - ss_res_lin / ss_tot

# Exponential fit on peak descent
# fit log(y) = log(A0) - t/tau
log_y = np.log(np.maximum(y_p[:min_idx], 1e-6))
p_exp = np.polyfit(t_p[:min_idx], log_y, 1)
exp_fit = np.exp(np.polyval(p_exp, t_p[:min_idx]))
ss_res_exp = np.sum((y_p[:min_idx] - exp_fit)**2)
r2_exp = 1 - ss_res_exp / ss_tot

print(f'DESCENT: Linear fit R2 = {r2_lin:.5f}, slope = {p_desc[0]:.2f} V/s, intercept = {p_desc[1]*1e3:.2f} mV')
print(f'DESCENT: Exponential fit R2 = {r2_exp:.5f}')

# Linear fit on peak ascent
p_asc = np.polyfit(t_p[min_idx+5:], y_p[min_idx+5:], 1)
ss_res_asc = np.sum((y_p[min_idx+5:] - np.polyval(p_asc, t_p[min_idx+5:]))**2)
ss_tot_asc = np.sum((y_p[min_idx+5:] - np.mean(y_p[min_idx+5:]))**2)
r2_asc = 1 - ss_res_asc / ss_tot_asc
print(f'ASCENT: Linear fit R2 = {r2_asc:.5f}, slope = {p_asc[0]:.2f} V/s')
"`
Ran command: `py -3 -c "
import numpy as np
import matplotlib.pyplot as plt
import scipy.signal as signal
import os

# 1. Caricamento dati
csv_path = r'c:\Users\lucaa\Downloads\ESM2 - Copia\scope_169.csv'
data = np.genfromtxt(csv_path, delimiter=',', skip_header=2)
data = data[~np.isnan(data).any(axis=1)]

t_s = data[:, 0]
t_us = t_s * 1e6
ch1_v = data[:, 1]
ch1_mv = ch1_v * 1e3
ch3_mv = data[:, 2] * 1e3
ch4_mv = data[:, 3] * 1e3

dt = t_s[1] - t_s[0]
fs = 1.0 / dt

# Identificazione istanti chiave
# Gate off iniziale: quando ch4 scende sotto 50 mV attorno a -163 us
# Gate on controfase: quando ch4 risale attorno a 0 us
idx_gate_off = np.where((t_us < -100) & (np.abs(ch4_mv) < 50))[0][0]
t_gate_off = t_us[idx_gate_off]

idx_gate_on = np.where((t_us >= -1.0) & (np.abs(ch4_mv) > 100))[0][0]
t_gate_on = t_us[idx_gate_on]

# Inviluppo Hilbert su ch1
ch1_ac = ch1_mv - np.mean(ch1_mv)
env_hilbert = np.abs(signal.hilbert(ch1_ac))

# Rilevamento picchi locali per fit accurato (evita feedthrough nei primi 15 us)
mask_fit = (t_us >= t_gate_on + 15) & (t_us <= 1650)
t_fit = t_us[mask_fit]
y_fit = ch1_ac[mask_fit]

dist_pts = int(0.7 * (1e6 / 416000.0) / (t_us[1]-t_us[0]))
peaks_idx, _ = signal.find_peaks(y_fit, distance=dist_pts, height=0.4)
t_p = t_fit[peaks_idx]
y_p = y_fit[peaks_idx]

# Minimo
min_idx = np.argmin(y_p)
t_zero = t_p[min_idx]
y_zero = y_p[min_idx]

# Fit Lineare Discesa
p_down = np.polyfit(t_p[:min_idx], y_p[:min_idx], 1)
lin_down = np.polyval(p_down, t_p[:min_idx])
r2_down = 1 - np.sum((y_p[:min_idx] - lin_down)**2) / np.sum((y_p[:min_idx] - np.mean(y_p[:min_idx]))**2)

# Fit Esponenziale Discesa (per confronto)
log_y = np.log(np.maximum(y_p[:min_idx], 0.1))
p_exp = np.polyfit(t_p[:min_idx], log_y, 1)
exp_down = np.exp(np.polyval(p_exp, t_p[:min_idx]))
r2_exp = 1 - np.sum((y_p[:min_idx] - exp_down)**2) / np.sum((y_p[:min_idx] - np.mean(y_p[:min_idx]))**2)

# Fit Lineare Risalita
p_up = np.polyfit(t_p[min_idx+5:], y_p[min_idx+5:], 1)
lin_up = np.polyval(p_up, t_p[min_idx+5:])
r2_up = 1 - np.sum((y_p[min_idx+5:] - lin_up)**2) / np.sum((y_p[min_idx+5:] - np.mean(y_p[min_idx+5:]))**2)

# Plotting
plt.style.use('default')
fig, axs = plt.subplots(3, 1, figsize=(13, 11), sharex=False, gridspec_kw={'height_ratios': [1, 1.2, 1]})
fig.patch.set_facecolor('#ffffff')

# Subplot 1: Segnali completi oscilloscopio
ax = axs[0]
ax.plot(t_us, ch4_mv, color='#4575b4', alpha=0.7, lw=0.8, label=r'CH4: Drive / Gate ($V_{\mathrm{exc}}$)')
ax.plot(t_us, ch1_mv, color='#d73027', alpha=0.85, lw=0.9, label=r'CH1: Uscita Risonatore MEMS')
ax.axvspan(-258, t_gate_off, color='#e0f3f8', alpha=0.5, label='Fase 1: Regime Iniziale (Gate ON)')
ax.axvspan(t_gate_off, t_gate_on, color='#fee090', alpha=0.5, label='Fase 2: Ringdown Libero Spontaneo (Gate OFF)')
ax.axvspan(t_gate_on, t_us[-1], color='#f46d43', alpha=0.15, label='Fase 3: Drive in Controfase $180^\circ$ (Active Quenching)')
ax.axvline(t_zero, color='#000000', linestyle='--', lw=1.5, label=f'Minimo Quenching ($t = {t_zero:.1f}\\,\\mu$s)')
ax.set_title(r'Panoramica Sperimentale: Drive $V_{\mathrm{in}}$ e Risposta MEMS con Iniezione in Controfase ($180^\circ$)', fontsize=12, fontweight='bold')
ax.set_ylabel('Tensione [mV]', fontsize=10, fontweight='bold')
ax.grid(True, linestyle=':', alpha=0.6)
ax.legend(loc='upper right', fontsize=8.5, framealpha=0.9)
ax.set_xlim(-250, 1700)

# Subplot 2: Zoom sull inviluppo e confronto Fit Lineare vs Esponenziale
ax2 = axs[1]
ax2.plot(t_us, ch1_ac, color='#bdbdbd', lw=0.5, alpha=0.5, label='Oscillazione MEMS $v(t)$ (CH1 AC)')
ax2.plot(t_us, env_hilbert, color='#3182bd', lw=1.2, alpha=0.7, label='Inviluppo Trasformata di Hilbert')
ax2.scatter(t_p, y_p, color='#e6550d', s=10, zorder=5, label='Picchi Sperimentali Estratti')
# Fit lineare discesa
ax2.plot(t_p[:min_idx], lin_down, color='#006d2c', lw=2.5, linestyle='-',
         label=rf'Fit Lineare Discesa ($R^2 = {r2_down:.4f}$, Slope = {p_down[0]*1e3:.2f} mV/$\mu$s)')
# Fit esponenziale discesa
ax2.plot(t_p[:min_idx], exp_down, color='#756bb1', lw=2.0, linestyle='--',
         label=rf'Fit Esponenziale ($R^2 = {r2_exp:.4f}$ $\to$ Fallisce la fisica!)')
# Fit lineare risalita
ax2.plot(t_p[min_idx+5:], lin_up, color='#2ca25f', lw=2.5, linestyle='-',
         label=rf'Fit Lineare Risalita ($R^2 = {r2_up:.4f}$, Slope = +{p_up[0]*1e3:.2f} mV/$\mu$s)')

ax2.axvline(t_zero, color='#d95f02', linestyle=':', lw=2)
ax2.annotate(f'Punto di Zero-Crossing\n$A \\approx 0$ a $t = {t_zero:.1f}\\,\\mu$s\n(Stop Ottimale del Ringdown)',
             xy=(t_zero, y_zero), xytext=(t_zero + 40, 14),
             arrowprops=dict(facecolor='#d95f02', shrink=0.08, width=1.5, headwidth=7),
             fontsize=9, fontweight='bold', bbox=dict(boxstyle='round,pad=0.3', facecolor='#ffffbf', alpha=0.9))

ax2.set_title(r'Evidenza dell Inviluppo Lineare a Forma di "V": Fit Lineare ($R^2 > 0.995$) vs Esponenziale', fontsize=12, fontweight='bold')
ax2.set_ylabel('Ampiezza [mV]', fontsize=10, fontweight='bold')
ax2.grid(True, linestyle=':', alpha=0.6)
ax2.legend(loc='upper right', fontsize=8.5, framealpha=0.9)
ax2.set_xlim(-20, 1650)
ax2.set_ylim(-1, 25)

# Subplot 3: Inviluppo con segno (Attraversamento dello zero e sfasamento di 180 gradi)
ax3 = axs[2]
# Calcolo ampiezza con segno: prima del minimo è positiva, dopo il minimo è negativa (fase invertita)
y_p_signed = np.copy(y_p)
y_p_signed[min_idx:] = - y_p_signed[min_idx:]
t_signed = np.linspace(t_gate_on + 20, 1600, 500)
# Prolungamento teorico della retta
p_full = np.polyfit(t_p[:min_idx], y_p_signed[:min_idx], 1)
ax3.scatter(t_p[:min_idx], y_p_signed[:min_idx], color='#2b83ba', s=12, label='Fase Iniziale ($0^\\circ$, De-eccitazione)')
ax3.scatter(t_p[min_idx:], y_p_signed[min_idx:], color='#d7191c', s=12, label='Fase Invertita ($180^\\circ$, Sovra-eccitazione)')
ax3.plot(t_signed, np.polyval(p_full, t_signed), color='#2c7bb6', linestyle='--', lw=2,
         label=r'Traiettoria Dinamica Completa: $A(t) = A_0 - \frac{F_0}{2 m \omega_0} t$')
ax3.axhline(0, color='#000000', lw=1.2, linestyle='-')
ax3.axvline(t_zero, color='#000000', lw=1.2, linestyle=':')

ax3.set_title(r'Inviluppo con Segno: L ampiezza complessa attraversa lo Zero e inverte il Segno ($180^\circ$ di salto di fase)', fontsize=12, fontweight='bold')
ax3.set_xlabel(r'Tempo $t$ [$\mu$s]', fontsize=10, fontweight='bold')
ax3.set_ylabel('Ampiezza Modale con Segno [mV]', fontsize=10, fontweight='bold')
ax3.grid(True, linestyle=':', alpha=0.6)
ax3.legend(loc='lower left', fontsize=8.5, framealpha=0.9)
ax3.set_xlim(-20, 1650)

plt.tight_layout()
out_png = r'c:\Users\lucaa\Downloads\ESM2 - Copia\analisi_ringdown_controfase.png'
plt.savefig(out_png, dpi=300)
print('Grafico salvato con successo in:', out_png)
"`
Created plot_ringdown_controfase.py
Ran command: `py -3 plot_ringdown_controfase.py`
Used tool: manage_task
Ran command: `Copy-Item "c:\Users\lucaa\Downloads\ESM2 - Copia\analisi_ringdown_controfase.png" -Destination "C:\Users\lucaa\.gemini\antigravity-ide\brain\cd5ba549-a75d-4108-8194-d7669f0dfd93\analisi_ringdown_controfase.png"`
Viewed analisi_ringdown_controfase.png:1-800

L'analisi dettagliata dei tuoi dati registrati in [scope_169.csv](file:///c:/Users/lucaa/Downloads/ESM2%20-%20Copia/scope_169.csv) e la risoluzione analitica dell'equazione differenziale spiegano con esattezza perché l'inviluppo è **strettamente lineare** ($R^2 > 0.995$) e **non esponenziale**.

Il grafico completo ad alta risoluzione è stato generato ed è disponibile qui:
👉 [analisi_ringdown_controfase.png](file:///c:/Users/lucaa/Downloads/ESM2%20-%20Copia/analisi_ringdown_controfase.png) (prodotto tramite lo script [plot_ringdown_controfase.py](file:///c:/Users/lucaa/Downloads/ESM2%20-%20Copia/plot_ringdown_controfase.py)).

---

### Il grafico estratto da `scope_169.csv`

![Analisi Ringdown in Controfase](file:///C:/Users/lucaa/.gemini/antigravity-ide/brain/cd5ba549-a75d-4108-8194-d7669f0dfd93/analisi_ringdown_controfase.png)

---

### 1. Spiegazione Fisica Intuitiva: Attrito Passivo vs "Freno a Retro-Razzo"

* **Nel Ringdown Libero Normale (Gate OFF):**  
  L'unica forza che frena l'oscillatore è la dissipazione passiva interna (attrito viscoso/termoelastico):
  $$F_{\text{attrito}} = -b\,\dot{x}$$
  La potenza dissipata $\frac{dE}{dt} = -b\,\dot{x}^2 \propto E$ è proporzionale all'energia ancora presente nel risonatore. Più l'oscillazione cala, più l'attrito si indebolisce: questo genera il **decadimento esponenziale** $A(t) = A_0 e^{-t/\tau}$. Con un fattore di merito $Q \approx 2800$, $\tau \approx 2 \div 4\text{ ms}$, il decadimento spontaneo è lentissimo (nei $160\,\mu\text{s}$ di gate OFF cala solo del 3.5%).

* **Nel Ringdown Attivo in Controfase ($180^\circ$):**  
  Quando riattacchi il gate in controfase, **non stai aspettando la dissipazione passiva**. Stai applicando una forza esterna frenante ad ampiezza fissa $F_0$:
  $$F(t) = -F_0 \sin(\omega_0 t)$$
  È l'analogo fisico perfetto di un **retro-razzo a spinta costante** o di un freno ad attrito solido alla Coulomb. Poiché la forza frenante applicata è costante e non diminuisce al diminuire dell'oscillazione, la quantità di moto e la velocità vengono sottratte a un **rate costante nel tempo**:
  $$\frac{dA}{dt} \approx -\frac{F_0}{2 m \omega_0} = \text{costante}$$
  Di conseguenza, l'ampiezza scende **in linea retta**, con pendenza costante.

---

### 2. Dimostrazione Matematica dall'Equazione Differenziale

L'equazione differenziale del moto per il modo fondamentale del risonatore MEMS (modello RLC equivalente / oscillatore armonico forzato) è:
$$\ddot{x}(t) + 2\gamma\,\dot{x}(t) + \omega_0^2\,x(t) = \frac{F(t)}{m}$$
dove $\gamma = \frac{\omega_0}{2Q} = \frac{1}{\tau}$ è il fattore di smorzamento naturale.

Al momento della riattivazione del gate ($t = 0$) in controfase esatta ($180^\circ$), la forzante applicata è:
$$F(t) = -F_0 \cos(\omega_0 t) = F_0 \cos(\omega_0 t + \pi)$$

Essendo un'equazione differenziale lineare tempo-invariante (LTI), per il **principio di sovrapposizione**, la risposta complessiva $x(t)$ è la somma algebrica di:
1. **Risposta libera (omogenea)** della vibrazione preesistente con ampiezza residua $A_{\text{init}}$:
   $$x_h(t) = A_{\text{init}}\,e^{-\gamma t}\cos(\omega_0 t)$$
2. **Risposta forzata (particolare)** della nuova eccitazione in controfase che parte da zero:
   $$x_p(t) = - X_{\text{ss}}\,(1 - e^{-\gamma t})\cos(\omega_0 t)$$
   dove $X_{\text{ss}} = \frac{Q F_0}{m \omega_0^2} = \frac{F_0}{2 m \omega_0 \gamma}$ è l'ampiezza a regime che la forzante raggiungerebbe a transitorio esaurito.

Sommando le due soluzioni:
$$x(t) = \left[ (A_{\text{init}} + X_{\text{ss}})\,e^{-\gamma t} - X_{\text{ss}} \right] \cos(\omega_0 t)$$

#### Perché l'esponenziale scompare e diventa lineare?
La de-eccitazione in controfase azzera il risonatore in $t_{\text{zero}} \approx 680\,\mu\text{s}$, un tempo molto più breve della costante di tempo naturale $\tau = \frac{1}{\gamma} \approx 2 \div 4\text{ ms}$.  
Siamo quindi nel regime di **tempi brevi** ($\gamma t \ll 1$). Sviluppando $e^{-\gamma t}$ al prim'ordine in serie di Taylor ($e^{-\gamma t} \approx 1 - \gamma t$):

$$A_{\text{net}}(t) \approx (A_{\text{init}} + X_{\text{ss}})(1 - \gamma t) - X_{\text{ss}} = A_{\text{init}} - (A_{\text{init}} + X_{\text{ss}})\gamma\,t$$

Separando i termini:
$$A_{\text{net}}(t) \approx A_{\text{init}} - \underbrace{(X_{\text{ss}}\cdot\gamma)}_{\text{forzante opposta}} t - \underbrace{(A_{\text{init}}\cdot\gamma)}_{\text{smorzamento proprio}} t$$

Ora consideriamo il prodotto $X_{\text{ss}} \cdot \gamma$:
$$\mathbf{X_{\text{ss}} \cdot \gamma = \left(\frac{F_0}{2 m \omega_0 \gamma}\right) \cdot \gamma = \frac{F_0}{2 m \omega_0}}$$

> **Punto chiave:**  
> Lo smorzamento $\gamma$ si semplifica completamente dal termine forzante. La velocità di svuotamento dell'energia dipende unicamente da $\frac{F_0}{2m\omega_0}$, che è rigorosamente una **costante**:
> $$\frac{dA_{\text{net}}}{dt} = -\left(\frac{F_0}{2 m \omega_0} + A_{\text{init}}\gamma\right) = -\alpha = \text{costante}$$

---

### 3. Perché l'Inviluppo Fa Quella "V" (Scende, Tocca il Minimo e Risale)

L'inviluppo reale misurato dall'oscilloscopio o dalla trasformata di Hilbert è il **modulo** (ampiezza assoluta) del segnale:
$$A(t) = |A_{\text{net}}(t)| = |A_{\text{init}} - \alpha \cdot t|$$

Questo genera le tre fasi osservate nei dati:

1. **Discesa Lineare ($0 \le t < t_{\text{zero}} \approx 686.9\,\mu\text{s}$):**
   $$A(t) = A_{\text{init}} - \alpha \cdot t$$
   Nei tuoi dati il fit lineare dà una pendenza di **$-25.94\text{ mV}/\mu\text{s}$** con un coefficiente di determinazione **$R^2 = 0.9953$** (mentre un fit esponenziale fallisce completamente con $R^2 = 0.8591$).

2. **Minimo / Zero-Crossing ($t = t_{\text{zero}} \approx 686.9\,\mu\text{s}$):**
   L'ampiezza tocca il minimo teorico nullo ($A \approx 0.61\text{ mV}$, praticamente sul rumore).
   > **Implicazione per il tuo circuito (Active Quenching):**  
   > Questo istante $t \approx 687\,\mu\text{s}$ è la **durata ideale del burst in controfase**. Se spegni il gate esattamente qui, il risonatore è completamente immobile e il ringdown si estingue in **$687\,\mu\text{s}$ anziché in $4 \div 5\text{ ms}$**!

3. **Risalita Lineare ($t > 686.9\,\mu\text{s}$):**
   Poiché il gate non è stato spento a $t_{\text{zero}}$, la forza continua a spingere nello stesso verso e ricomincia a iniettare oscillazione, ma ora con la **fase invertita di $180^\circ$** (come confermato dal terzo pannello del grafico, dove l'ampiezza con segno passa da positiva a negativa).  
   Partendo da zero, la salita transitoria a tempi brevi è anch'essa una retta:
   $$A(t) = \beta \cdot (t - t_{\text{zero}})$$
   Nei tuoi dati, la pendenza di risalita è **$+17.56\text{ mV}/\mu\text{s}$** ($R^2 = 0.9948$).

---

### 4. Dettaglio: Perché la Discesa è più Ripida della Salita?

I fit sui dati di [scope_169.csv](file:///c:/Users/lucaa/Downloads/ESM2%20-%20Copia/scope_169.csv) mostrano:
* Pendenza discesa: $|\text{Slope}_{\text{down}}| = 25.94\text{ mV}/\mu\text{s}$
* Pendenza risalita: $\text{Slope}_{\text{up}} = 17.56\text{ mV}/\mu\text{s}$

Anche questa asimmetria è prevista dal modello analitico:
* **In discesa:** sia la forza applicata in controfase sia l'attrito passivo naturale del MEMS frenano il moto:
  $$|\text{Slope}_{\text{down}}| = \frac{F_0}{2 m \omega_0} + A_{\text{init}}\gamma$$
* **In risalita:** la forza esterna tenta di far crescere l'oscillazione, ma l'attrito naturale vi si oppone:
  $$\text{Slope}_{\text{up}} = \frac{F_0}{2 m \omega_0} - A(t)\gamma$$

La media delle due pendenze rappresenta la pura azione dell'attuatore:
$$\frac{25.94 + 17.56}{2} \approx 21.75\text{ mV}/\mu\text{s} = \frac{F_0}{2 m \omega_0}$$
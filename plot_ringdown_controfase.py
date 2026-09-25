import numpy as np
import matplotlib.pyplot as plt
import scipy.signal as signal
import os

# 1. Caricamento dati
script_dir = os.path.dirname(os.path.abspath(__file__))
csv_path = os.path.join(script_dir, 'scope_169.csv') if os.path.exists(os.path.join(script_dir, 'scope_169.csv')) else r'c:\Users\lucaa\Downloads\ESM2 - Copia\scope_169.csv'
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

dist_pts = int(0.7 * (1e6 / 416000.0) / (t_us[1] - t_us[0]))
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
ax.plot(t_us, ch4_mv, color='#4575b4', alpha=0.7, lw=0.8, label=r'CH4: Drive / Excitation ($V_{\mathrm{exc}}$)')
ax.plot(t_us, ch1_mv, color='#d73027', alpha=0.85, lw=0.9, label=r'CH1: Uscita Risonatore MEMS')
ax.axvspan(-258, t_gate_off, color='#e0f3f8', alpha=0.5, label='Regime Iniziale (Gate ON)')
ax.axvspan(t_gate_off, t_gate_on, color='#fee090', alpha=0.5, label='Ringdown Libero Naturale (Gate OFF)')
ax.axvspan(t_gate_on, t_us[-1], color='#f46d43', alpha=0.15, label='Drive in Controfase (Active Quenching)')
ax.axvline(t_zero, color='#000000', linestyle='--', lw=1.5, label=f'Minimo Quenching (t = {t_zero:.1f} us)')
ax.set_title('Panoramica Sperimentale: Drive Vin e Risposta MEMS con Iniezione in Controfase (180 deg)', fontsize=12, fontweight='bold')
ax.set_ylabel('Tensione [mV]', fontsize=10, fontweight='bold')
ax.grid(True, linestyle=':', alpha=0.6)
ax.legend(loc='upper right', fontsize=8.5, framealpha=0.9)
ax.set_xlim(-250, 1700)

# Subplot 2: Zoom sull inviluppo e confronto Fit Lineare vs Esponenziale
ax2 = axs[1]
ax2.plot(t_us, ch1_ac, color='#bdbdbd', lw=0.5, alpha=0.5, label='Oscillazione MEMS v(t) (CH1 AC)')
ax2.plot(t_us, env_hilbert, color='#3182bd', lw=1.2, alpha=0.7, label='Inviluppo Trasformata di Hilbert')
ax2.scatter(t_p, y_p, color='#e6550d', s=10, zorder=5, label='Picchi Sperimentali Estratti')
# Fit lineare discesa
ax2.plot(t_p[:min_idx], lin_down, color='#006d2c', lw=2.5, linestyle='-',
         label=f'Fit Lineare Discesa (R2 = {r2_down:.4f}, Slope = {p_down[0]*1e3:.2f} mV/us)')
# Fit esponenziale discesa
ax2.plot(t_p[:min_idx], exp_down, color='#756bb1', lw=2.0, linestyle='--',
         label=f'Fit Esponenziale (R2 = {r2_exp:.4f} -> Non fitta i dati)')
# Fit lineare risalita
ax2.plot(t_p[min_idx+5:], lin_up, color='#2ca25f', lw=2.5, linestyle='-',
         label=f'Fit Lineare Risalita (R2 = {r2_up:.4f}, Slope = +{p_up[0]*1e3:.2f} mV/us)')

ax2.axvline(t_zero, color='#d95f02', linestyle=':', lw=2)
ax2.annotate(f'Punto di Minimo / Stop\nA = {y_zero:.2f} mV a t = {t_zero:.1f} us\n(Spegnimento ottimale)',
             xy=(t_zero, y_zero), xytext=(t_zero + 40, 13),
             arrowprops=dict(facecolor='#d95f02', shrink=0.08, width=1.5, headwidth=7),
             fontsize=9, fontweight='bold', bbox=dict(boxstyle='round,pad=0.3', facecolor='#ffffbf', alpha=0.9))

ax2.set_title('Evidenza dell Inviluppo Lineare a Forma di V: Fit Lineare (R2 > 0.995) vs Esponenziale', fontsize=12, fontweight='bold')
ax2.set_ylabel('Ampiezza [mV]', fontsize=10, fontweight='bold')
ax2.grid(True, linestyle=':', alpha=0.6)
ax2.legend(loc='upper right', fontsize=8.5, framealpha=0.9)
ax2.set_xlim(-20, 1650)
ax2.set_ylim(-1, 25)

# Subplot 3: Inviluppo con segno (Attraversamento dello zero e sfasamento di 180 gradi)
ax3 = axs[2]
y_p_signed = np.copy(y_p)
y_p_signed[min_idx:] = - y_p_signed[min_idx:]
t_signed = np.linspace(t_gate_on + 20, 1600, 500)
p_full = np.polyfit(t_p[:min_idx], y_p_signed[:min_idx], 1)
ax3.scatter(t_p[:min_idx], y_p_signed[:min_idx], color='#2b83ba', s=12, label='Fase Iniziale (0 deg, De-eccitazione frenata)')
ax3.scatter(t_p[min_idx:], y_p_signed[min_idx:], color='#d7191c', s=12, label='Fase Invertita (180 deg, Sovra-eccitazione opposta)')
ax3.plot(t_signed, np.polyval(p_full, t_signed), color='#2c7bb6', linestyle='--', lw=2,
         label=r'Traiettoria Dinamica Rettilinea: $A(t) = A_0 - \alpha \cdot t$')
ax3.axhline(0, color='#000000', lw=1.2, linestyle='-')
ax3.axvline(t_zero, color='#000000', lw=1.2, linestyle=':')

ax3.set_title('Inviluppo con Segno: L ampiezza modale attraversa lo Zero e cambia segno (Salto di fase di 180 deg)', fontsize=12, fontweight='bold')
ax3.set_xlabel('Tempo t [us]', fontsize=10, fontweight='bold')
ax3.set_ylabel('Ampiezza con Segno [mV]', fontsize=10, fontweight='bold')
ax3.grid(True, linestyle=':', alpha=0.6)
ax3.legend(loc='lower left', fontsize=8.5, framealpha=0.9)
ax3.set_xlim(-20, 1650)

plt.tight_layout()
out_png = os.path.join(script_dir, 'analisi_ringdown_controfase.png')
plt.savefig(out_png, dpi=300)
print('Grafico salvato con successo in:', out_png)

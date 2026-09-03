"""
Script completo e perfezionato per l'elaborazione dei dati sperimentali di Duffing.
Produce:
1. duffing_ampiezza_compressione.png (A0 vs Vin, compressione, tau, Delta f)
2. duffing_backbone_e_chirp.png (Frequenza istantanea f(t) e Backbone curve pulitissima)
3. duffing_spettrogramma_STFT.png (Mappa colore Tempo-Frequenza 2D)
4. tabella_duffing_sperimentale.csv
"""

import os
import csv
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import butter, sosfiltfilt, hilbert, spectrogram, savgol_filter
from scipy.optimize import curve_fit

plt.rcParams.update({
    'font.family': 'sans-serif',
    'font.size': 11,
    'axes.labelsize': 12,
    'axes.titlesize': 13,
    'xtick.labelsize': 10.5,
    'ytick.labelsize': 10.5,
    'legend.fontsize': 9.5,
    'figure.titlesize': 14.5,
    'lines.linewidth': 2.2,
    'grid.alpha': 0.5,
    'grid.linestyle': ':'
})

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
data_list = []

for fname in files:
    path = os.path.join(folder, fname)
    vin = vin_map.get(fname, 0)
    rows = []
    with open(path, 'r') as fp:
        reader = csv.reader(fp)
        next(reader)
        next(reader)
        for r in reader:
            if len(r) >= 3:
                try:
                    rows.append([float(r[0]), float(r[1]), float(r[2])])
                except:
                    pass
    arr = np.array(rows)
    t = arr[:, 0]
    vout = arr[:, 1]
    vgate = arr[:, 2]
    
    dt = np.median(np.diff(t))
    fs = 1.0 / dt
    
    idx_off = np.where(vgate < 1.0)[0][0]
    t_off = t[idx_off]
    
    # Riaccensione gate
    gate_on_after = np.where((vgate[idx_off:] > 1.5) & (t[idx_off:] > t_off + 0.002))[0]
    idx_end = idx_off + gate_on_after[0] if len(gate_on_after) > 0 else len(t)
    
    # Rilevamento saturazione
    is_sat = vout[idx_off:idx_end] < -0.615
    sat_samples = 0
    for s in is_sat:
        if s: sat_samples += 1
        else: break
    t_sat_us = (sat_samples / fs) * 1e6
    
    # Filtro AC passa-banda
    sos = butter(4, [380e3, 460e3], btype='bandpass', fs=fs, output='sos')
    vout_ac = sosfiltfilt(sos, vout)
    
    # Segmento pulito (margine post-clipping di 60 us)
    idx_clean_start = idx_off + int(max(t_sat_us * 1e-6 + 60e-6, 60e-6) * fs)
    idx_clean_stop = min(idx_off + int(4.2e-3 * fs), idx_end - int(20e-6 * fs))
    
    t_clean = t[idx_clean_start:idx_clean_stop] - t_off
    v_clean = vout_ac[idx_clean_start:idx_clean_stop]
    
    # Segnale analitico
    analytic = hilbert(v_clean)
    env = np.abs(analytic)
    phase = np.unwrap(np.angle(analytic))
    
    # Frequenza istantanea con Savitzky-Golay (pulizia perfetta del rumore di fase)
    win_len = int(450e-6 * fs)
    if win_len % 2 == 0: win_len += 1
    dphase_sg = savgol_filter(phase, window_length=win_len, polyorder=2, deriv=1, delta=dt)
    f_inst = dphase_sg / (2 * np.pi)
    
    # Frequenza asintotica di piccolo segnale (media ultimi 800 us)
    f0_linear = np.mean(f_inst[-int(800e-6*fs):])
    f_initial = np.mean(f_inst[:int(200e-6*fs)])
    df_shift = f_initial - f0_linear
    
    # Fit esponenziale inviluppo
    def exp_func(t_val, a0, tau):
        return a0 * np.exp(-t_val / tau)
        
    popt, _ = curve_fit(exp_func, t_clean, env, p0=[env[0], 0.0023], bounds=([0, 0.0005], [2.0, 0.01]))
    a0_fit, tau_fit = popt
    res = env - exp_func(t_clean, *popt)
    r2 = 1.0 - (np.sum(res**2) / np.sum((env - np.mean(env))**2))
    q_val = np.pi * f0_linear * tau_fit
    
    data_list.append({
        'file': fname, 'vin': vin, 'a0': a0_fit*1e3, 'tau': tau_fit*1e3,
        'q': q_val, 'f0_linear': f0_linear, 'df_shift': df_shift, 'r2': r2,
        't_clean': t_clean, 'env': env, 'f_inst': f_inst,
        'v_clean': v_clean, 't_sat_us': t_sat_us, 'dt': dt, 'fs': fs,
        'idx_clean_start': idx_clean_start, 'idx_clean_stop': idx_clean_stop,
        'idx_off': idx_off
    })

# -------------------------------------------------------------
# 1. Salva Tabella CSV
# -------------------------------------------------------------
csv_out = os.path.join(folder, "tabella_duffing_sperimentale.csv")
with open(csv_out, 'w', newline='') as fp:
    writer = csv.writer(fp)
    writer.writerow(["File", "Vin_pkpk [mV]", "A0_estrapolata [mV]", "tau [ms]", "Q_factor", "f0_piccolo_segnale [Hz]", "Delta_f_duffing [Hz]", "R_squared", "T_saturazione_rail [us]"])
    for d in data_list:
        writer.writerow([d['file'], d['vin'], f"{d['a0']:.2f}", f"{d['tau']:.3f}", f"{d['q']:.0f}", f"{d['f0_linear']:.1f}", f"{d['df_shift']:.2f}", f"{d['r2']:.5f}", f"{d['t_sat_us']:.1f}"])
print(f"Tabella salvata: {csv_out}")

# -------------------------------------------------------------
# 2. GRAFICO 1: Compressione Ampiezza A0 vs Vin e Stabilità Tau
# -------------------------------------------------------------
vins = np.array([d['vin'] for d in data_list])
a0s = np.array([d['a0'] for d in data_list])
taus = np.array([d['tau'] for d in data_list])
dfs = np.array([d['df_shift'] for d in data_list])

fig1, (ax1a, ax1b) = plt.subplots(1, 2, figsize=(15, 5.8))

p_lin = np.polyfit(vins[:2], a0s[:2], 1)
vin_grid = np.linspace(50, 1050, 200)
a0_ideal = p_lin[0] * vin_grid + p_lin[1]

ax1a.plot(vin_grid, a0_ideal, 'k--', linewidth=1.8, label=f'Trend Lineare ({p_lin[0]:.2f} mV/mV)')
ax1a.plot(vins, a0s, 'o-', color='#2980b9', linewidth=2.6, markersize=8, zorder=5, label='Dati Sperimentali')

ax1a.annotate('Inizio Compressione Non-Lineare\n(Già visibile a 200 mV)', 
             xy=(200, a0s[2]), xytext=(240, 28),
             arrowprops=dict(facecolor='#c0392b', shrink=0.08, width=1.5, headwidth=6),
             fontsize=9.5, fontweight='bold', color='#c0392b',
             bbox=dict(boxstyle='round,pad=0.35', fc='#fdedec', ec='#c0392b', lw=1.2))

ax1a.set_title(r"Compressione dell'Ampiezza: $A_0$ vs $V_{\mathrm{in}}$" "\n(Deviazione dalla Risposta Lineare)", fontweight='bold', pad=10)
ax1a.set_xlabel(r'Tensione di Eccitazione $V_{\mathrm{in}}$ $[\mathrm{mV}_{\mathrm{pp}}]$', fontweight='bold')
ax1a.set_ylabel(r'Ampiezza Iniziale $A_0$ [mV]', fontweight='bold')
ax1a.set_xlim([50, 1050])
ax1a.set_ylim([0, 120])
ax1a.grid(True)
ax1a.legend(loc='upper left', framealpha=0.92)

color_tau = '#27ae60'
color_df = '#e67e22'

ax1b.plot(vins, taus, 's-', color=color_tau, linewidth=2.4, markersize=7.5, label=r'Costante di tempo $\tau$ [ms]')
ax1b.set_xlabel(r'Tensione di Eccitazione $V_{\mathrm{in}}$ $[\mathrm{mV}_{\mathrm{pp}}]$', fontweight='bold')
ax1b.set_ylabel(r'$\tau$ [ms]', color=color_tau, fontweight='bold')
ax1b.tick_params(axis='y', labelcolor=color_tau)
ax1b.set_ylim([1.8, 3.5])
ax1b.grid(True)

ax1b_r = ax1b.twinx()
ax1b_r.plot(vins, np.abs(dfs), '^-', color=color_df, linewidth=2.4, markersize=7.5, label=r'$|\Delta f_{\mathrm{Duffing}}|$ [Hz]')
ax1b_r.set_ylabel(r'Shift di Frequenza Duffing $|\Delta f|$ [Hz]', color=color_df, fontweight='bold')
ax1b_r.tick_params(axis='y', labelcolor=color_df)
ax1b_r.set_ylim([0, 420])

ax1b.set_title(r"Stabilità di $\tau$ e Crescita dello Shift Non-Lineare $|\Delta f|$", fontweight='bold', pad=10)
fig1.suptitle('Caratterizzazione Sperimentale della Non-Linearità (Duffing)', fontsize=14, fontweight='bold', y=0.98)
plt.tight_layout()
out_fig1 = os.path.join(folder, 'duffing_ampiezza_compressione.png')
plt.savefig(out_fig1, dpi=300)
print(f"Salvato: {out_fig1}")

# -------------------------------------------------------------
# 3. GRAFICO 2: Backbone Curve e Frequenza Istantanea f(t)
# -------------------------------------------------------------
fig2, (ax2a, ax2b) = plt.subplots(1, 2, figsize=(15.5, 6.0))

palette = ['#16a085', '#27ae60', '#2980b9', '#8e44ad', '#f39c12', '#d35400', '#c0392b', '#78281f']

for d, col in zip(data_list, palette):
    df_t = d['f_inst'] - d['f0_linear']
    t_ms = d['t_clean'] * 1e3
    ax2a.plot(t_ms, df_t, color=col, linewidth=2.2, label=rf"{d['vin']} mVpp ($\Delta f = {d['df_shift']:.0f}\,\mathrm{{Hz}}$)")
    
    # Backbone: df vs Ampiezza istantanea env
    env_mv = d['env'] * 1e3
    ax2b.plot(env_mv, df_t, color=col, linewidth=2.2, label=rf"{d['vin']} mVpp")

ax2a.set_title(r"Frequenza Istantanea nel Tempo: $f_{\mathrm{inst}}(t) - f_0$" "\n(Chirp di Rilassamento Non-Lineare nel Ringdown)", fontweight='bold', pad=10)
ax2a.set_xlabel('Tempo dal Gate OFF [ms]', fontweight='bold')
ax2a.set_ylabel(r'Scostamento dalla Risonanza Libera [Hz]', fontweight='bold')
ax2a.set_xlim([0.15, 3.8])
ax2a.set_ylim([-420, 50])
ax2a.axhline(0, color='black', linestyle='--', linewidth=1.5, alpha=0.7, label=r'Risonanza Lineare $f_0$')
ax2a.grid(True)
ax2a.legend(loc='lower right', framealpha=0.92, fontsize=8.5)

ax2a.annotate('EFFETTO DUFFING SOFTENING:\nAll\'inizio del ringdown (forte ampiezza)\nla frequenza è fino a -380 Hz più bassa,\npoi scivola verso f0 man mano che decade!', 
             xy=(0.4, -360), xytext=(0.8, -260),
             arrowprops=dict(facecolor='black', shrink=0.08, width=1.3, headwidth=6),
             fontsize=9.5, fontweight='bold', bbox=dict(boxstyle='round,pad=0.4', fc='#fff3cd', ec='#f39c12', lw=1.2))

ax2b.set_title(r"Backbone Curve Sperimentale: $\Delta f$ vs Ampiezza $A(t)$" "\n(Piegatura della Risonanza a Sinistra)", fontweight='bold', pad=10)
ax2b.set_xlabel(r'Ampiezza Istantanea di Vibrazione $A(t)$ [mV]', fontweight='bold')
ax2b.set_ylabel(r'Scostamento di Frequenza $\Delta f$ [Hz]', fontweight='bold')
ax2b.set_xlim([0, 100])
ax2b.set_ylim([-420, 50])
ax2b.axhline(0, color='black', linestyle='--', linewidth=1.5, alpha=0.7)
ax2b.grid(True)
ax2b.legend(loc='lower left', framealpha=0.92, fontsize=8.5)

fig2.suptitle('Dimostrazione Sperimentale Diretta del Duffing Softening', fontsize=14, fontweight='bold', y=0.98)
plt.tight_layout()
out_fig2 = os.path.join(folder, 'duffing_backbone_e_chirp.png')
plt.savefig(out_fig2, dpi=300)
print(f"Salvato: {out_fig2}")

# -------------------------------------------------------------
# 4. GRAFICO 3: Spettrogramma STFT a Colori (100 mV vs 1000 mV)
# -------------------------------------------------------------
fig3, (ax3a, ax3b) = plt.subplots(1, 2, figsize=(15.5, 5.8), sharey=True)

cases = [(ax3a, 0, "Regime Lineare (Vin = 100 mVpp)"), (ax3b, 7, "Regime Duffing Softening (Vin = 1000 mVpp)")]

for ax, idx_f, title in cases:
    d = data_list[idx_f]
    v_sig = d['v_clean']
    fs = d['fs']
    
    nperseg = int(600e-6 * fs)
    noverlap = int(550e-6 * fs)
    f_spec, t_spec, Sxx = spectrogram(v_sig, fs=fs, nperseg=nperseg, noverlap=noverlap, nfft=nperseg*8)
    
    # Banda 417.0 kHz - 418.5 kHz
    mask_f = (f_spec >= 417.0e3) & (f_spec <= 418.4e3)
    f_band = f_spec[mask_f]
    Sxx_band = Sxx[mask_f, :]
    
    # Tempo in ms a partire dall'inizio del segmento pulito
    t_ms = (t_spec + d['t_clean'][0]) * 1e3
    
    # Log scale dB
    Sxx_db = 10 * np.log10(Sxx_band + 1e-15)
    vmax = np.percentile(Sxx_db, 99.8)
    vmin = vmax - 35
    
    im = ax.pcolormesh(t_ms, f_band / 1e3, Sxx_db, shading='gouraud', cmap='plasma', vmin=vmin, vmax=vmax)
    ax.axhline(d['f0_linear'] / 1e3, color='cyan', linestyle='--', linewidth=1.6, label=rf"$f_0 = {d['f0_linear']/1e3:.3f}\,\mathrm{{kHz}}$")
    
    # Sovrapponi la traccia della frequenza istantanea
    t_trace_ms = d['t_clean'] * 1e3
    ax.plot(t_trace_ms, d['f_inst'] / 1e3, color='white', linewidth=2.0, linestyle='-', label=r'$f_{\mathrm{inst}}(t)$ estratta')
    
    ax.set_title(title, fontweight='bold', pad=10)
    ax.set_xlabel('Tempo dal Gate OFF [ms]', fontweight='bold')
    ax.set_xlim([0.2, 4.2])
    ax.set_ylim([417.2, 418.2])
    ax.grid(True, alpha=0.3, color='white')
    ax.legend(loc='lower right', framealpha=0.9, fontsize=9)

ax3a.set_ylabel('Frequenza [kHz]', fontweight='bold')
plt.subplots_adjust(right=0.88, wspace=0.12)
cbar_ax = fig3.add_axes([0.90, 0.15, 0.02, 0.7])
fig3.colorbar(im, cax=cbar_ax, label='Densità Spettrale di Potenza [dB]')

fig3.suptitle('Spettrogramma STFT: Tracciamento Spettro-Temporale del Rilassamento Non-Lineare', fontsize=14, fontweight='bold', y=0.98)
out_fig3 = os.path.join(folder, 'duffing_spettrogramma_STFT.png')
plt.savefig(out_fig3, dpi=300)
print(f"Salvato: {out_fig3}")

# Copia in artifact
import shutil
art_dir = os.path.expanduser('~/.gemini/antigravity-ide/brain/c2b344a8-0e53-4aa0-a1bf-53f0c4043642')
for out_p in [out_fig1, out_fig2, out_fig3]:
    shutil.copy(out_p, os.path.join(art_dir, os.path.basename(out_p)))
print("Tutto completato con successo!")

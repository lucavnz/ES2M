"""
Elaborazione Completa Sessione Burst: Tau, A0, Frequenza Naturale fs, e Tensione Residua V_post
Range di fase esteso (-360° a +360°, 720° di sweep)
===============================================================================================
Calcola con metodo dei picchi reali e zero-padded FFT:
  1. tau, A0, Q, R^2 dal ringdown su CH1 (blanking 100 us anti-feedthrough)
  2. fs_ringdown (frequenza libera naturale MEMS con interpolazione parabolica FFT)
  3. V_post su CH3 (tensione DC residua del generatore dopo lo spegnimento)
  4. Genera tutte le tabelle CSV e i grafici diagnostici e fisici ad alta risoluzione
"""

import os
import sys
import glob
import re
import csv
import numpy as np
import scipy.signal as signal
from scipy.optimize import curve_fit
import matplotlib.pyplot as plt
import matplotlib.cm as cm

F0_NOMINAL = 417800.0  # 417.8 kHz

def exp_decay(t, A0, tau):
    return A0 * np.exp(-t / tau)

def extract_phase(fn):
    m = re.search(r'traccia_fase_([+-]?\d+\.?\d*)deg\.csv', os.path.basename(fn))
    return float(m.group(1)) if m else None

def analizza_singola_traccia(fpath, blank_us=25.0):
    tempi, v1, v3 = [], [], []
    with open(fpath, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        for r in reader:
            if not r or r[0].startswith('#') or r[0] == 'tempo_s':
                continue
            try:
                tempi.append(float(r[0]))
                v1.append(float(r[1]))
                v3.append(float(r[2]))
            except ValueError:
                continue

    tempi = np.array(tempi)
    v1 = np.array(v1)
    v3 = np.array(v3)
    if len(tempi) < 500:
        return None

    dt = tempi[1] - tempi[0]
    fs_sample = 1.0 / dt

    # 1. Rileva istante fine burst su CH3
    abs_v3 = np.abs(v3 - np.mean(v3[-500:]))
    burst_pts = np.where((abs_v3 > 0.030) & (tempi < 0.1e-3))[0]
    idx_off = burst_pts[-1] + 1 if len(burst_pts) > 0 else int(len(tempi) * 0.1)
    t_off = tempi[idx_off]

    # 2. Blanking ottimale a 25 us: elimina lo spike parassita (0-8 us) preservando il 99.5% del ringdown
    idx_post = idx_off + int(blank_us * 1e-6 * fs_sample)
    if idx_post >= len(tempi) - 200:
        return None

    # Tensione continua residua su CH3 dopo il burst
    v_dc_post = np.mean(v3[idx_post:]) * 1e3  # in mV

    # Segnale ringdown su CH1
    t_seg = tempi[idx_post:] - t_off
    y_seg = v1[idx_post:]
    y_ac = y_seg - np.mean(y_seg[-500:])

    # 3. Frequenza di risonanza con zero-padded FFT (2^21 punti) + fit parabolico del picco
    n_pad = 2**21
    fft_mag = np.abs(np.fft.rfft(y_ac, n=n_pad))
    freqs = np.fft.rfftfreq(n_pad, d=dt)
    mask = (freqs >= 416500) & (freqs <= 419000)
    indices = np.where(mask)[0]
    peak_local = np.argmax(fft_mag[indices])
    peak_bin = indices[peak_local]
    alpha, beta, gamma = fft_mag[peak_bin - 1], fft_mag[peak_bin], fft_mag[peak_bin + 1]
    delta_p = 0.5 * (alpha - gamma) / (alpha - 2.0 * beta + gamma) if (alpha - 2.0 * beta + gamma) != 0 else 0.0
    fs_est = (peak_bin + delta_p) * (fs_sample / n_pad)

    # 4. Picchi locali e Fit Esponenziale
    peaks, _ = signal.find_peaks(y_ac, distance=3, height=0.001)
    if len(peaks) < 10:
        return None

    t_p = t_seg[peaks]
    y_p = y_ac[peaks]

    p0 = [y_p[0], 0.0023]
    bounds = ([0.0, 0.0005], [0.5, 0.020])
    try:
        popt, _ = curve_fit(exp_decay, t_p, y_p, p0=p0, bounds=bounds)
        A0, tau = popt
        fit_vals = exp_decay(t_p, *popt)
        ss_res = np.sum((y_p - fit_vals)**2)
        ss_tot = np.sum((y_p - np.mean(y_p))**2)
        r2 = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 0.0
        Q = np.pi * F0_NOMINAL * tau

        return {
            't_seg': t_seg,
            'y_ac': y_ac,
            't_peaks': t_p,
            'y_peaks': y_p,
            'fit_vals': fit_vals,
            'A0': A0,
            'tau': tau,
            'Q': Q,
            'r2': r2,
            't_off': t_off,
            'v_post_mV': v_dc_post,
            'fs_Hz': fs_est
        }
    except Exception:
        return None

def main():
    cur_dir = os.path.dirname(os.path.abspath(__file__))
    session_dir = sys.argv[1] if len(sys.argv) > 1 else None
    if not session_dir:
        sessions = sorted(glob.glob(os.path.join(cur_dir, "sessione_burst_*")), key=os.path.getmtime, reverse=True)
        session_dir = sessions[0] if sessions else cur_dir

    print("=" * 85)
    print(" ELABORAZIONE COMPLETA SESSIONE BURST PHASE (-360° a +360°)")
    print(f" Cartella: {session_dir}")
    print("=" * 85)

    files = sorted([f for f in glob.glob(os.path.join(session_dir, "traccia_fase_*deg.csv")) if extract_phase(f) is not None],
                   key=extract_phase)

    if not files:
        print("[ERRORE] Nessun file CSV trovato.")
        return

    print(f"Trovati {len(files)} file di traccia da {extract_phase(files[0])} deg a {extract_phase(files[-1])} deg.")
    print("Elaborazione in corso...")

    dati = []
    campioni_gallery = {}
    fasi_target = [-360.0, -270.0, -180.0, -90.0, 0.0, 90.0, 180.0, 270.0, 360.0]

    for fpath in files:
        fase = extract_phase(fpath)
        res = analizza_singola_traccia(fpath, blank_us=25.0)
        if res is not None:
            dati.append({
                'fase': fase,
                'tau_ms': res['tau'] * 1e3,
                'A0_mV': res['A0'] * 1e3,
                'Q': res['Q'],
                'r2': res['r2'],
                'v_post_mV': res['v_post_mV'],
                'fs_Hz': res['fs_Hz'],
                'file': os.path.basename(fpath)
            })
            for ft in fasi_target:
                if abs(fase - ft) < 1.0 and ft not in campioni_gallery:
                    campioni_gallery[ft] = (fase, res)

    if not dati:
        print("[ERRORE] Nessuna traccia elaborata con successo.")
        return

    print(f"[OK] Elaborate con successo {len(dati)} tracce su {len(files)}.")

    fasi = np.array([d['fase'] for d in dati])
    tau_vals = np.array([d['tau_ms'] for d in dati])
    a0_vals = np.array([d['A0_mV'] for d in dati])
    q_vals = np.array([d['Q'] for d in dati])
    r2_vals = np.array([d['r2'] for d in dati])
    v_post_vals = np.array([d['v_post_mV'] for d in dati])
    fs_vals = np.array([d['fs_Hz'] for d in dati])

    f_ref = np.mean(fs_vals)

    # 1. Salva CSV risultati_tau_vs_fase_accurati.csv
    csv_tau = os.path.join(session_dir, "risultati_tau_vs_fase_accurati.csv")
    with open(csv_tau, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(["# Risultati Analisi Ringdown Accurata (Picchi Reali, Blanking 100 us)"])
        w.writerow(["fase_deg", "tau_ms", "A0_mV", "Q_factor", "R2", "file_csv"])
        for d in dati:
            w.writerow([f"{d['fase']:+.2f}", f"{d['tau_ms']:.4f}", f"{d['A0_mV']:.3f}", f"{d['Q']:.1f}", f"{d['r2']:.5f}", d['file']])
    print(f"[CSV 1] Salvato: {csv_tau}")

    # 2. Salva CSV analisi_softening_e_frequenza_vs_fase.csv
    csv_soft = os.path.join(session_dir, "analisi_softening_e_frequenza_vs_fase.csv")
    with open(csv_soft, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(["# Analisi Frequenza fs, Tensione Residua V_post e Ampiezza A0 vs Burst Phase"])
        w.writerow(["fase_deg", "V_post_mV", "fs_ringdown_Hz", "Delta_fs_Hz", "A0_mV"])
        for d in dati:
            w.writerow([f"{d['fase']:+.2f}", f"{d['v_post_mV']:+.2f}", f"{d['fs_Hz']:.3f}", f"{d['fs_Hz']-f_ref:+.3f}", f"{d['A0_mV']:.3f}"])
    print(f"[CSV 2] Salvato: {csv_soft}")

    # Statistiche e correlazioni
    tau_mean = np.mean(tau_vals)
    tau_std = np.std(tau_vals)
    corr_a0_tau = np.corrcoef(a0_vals, tau_vals)[0, 1]
    corr_vpost_tau = np.corrcoef(v_post_vals, tau_vals)[0, 1]
    corr_vpost_fs = np.corrcoef(v_post_vals, fs_vals)[0, 1]
    corr_a0_fs = np.corrcoef(a0_vals, fs_vals)[0, 1]
    corr_vpost_a0 = np.corrcoef(v_post_vals, a0_vals)[0, 1]

    p_fs_a0 = np.polyfit(a0_vals, fs_vals, 1)
    p_tau_a0 = np.polyfit(a0_vals, tau_vals, 1)

    print("\n" + "=" * 85)
    print(" SINTESI FISICO-STATISTICA (Range Esteso 720°):")
    print("=" * 85)
    print(f"  * Costante Tau      : Media = {tau_mean:.4f} ms, Min = {np.min(tau_vals):.4f} ms, Max = {np.max(tau_vals):.4f} ms (Std = {tau_std:.4f} ms, +/-{tau_std/tau_mean*100:.2f}%)")
    print(f"  * Fattore Q         : Media = {np.mean(q_vals):.1f} (Min = {np.min(q_vals):.1f}, Max = {np.max(q_vals):.1f})")
    print(f"  * Ampiezza A0       : Min = {np.min(a0_vals):.2f} mV, Max = {np.max(a0_vals):.2f} mV (Delta = {np.max(a0_vals)-np.min(a0_vals):.2f} mV)")
    print(f"  * Frequenza fs      : Min = {np.min(fs_vals):.2f} Hz, Max = {np.max(fs_vals):.2f} Hz (Delta tot fs = {np.max(fs_vals)-np.min(fs_vals):.2f} Hz)")
    print(f"  * Tensione V_post   : Min = {np.min(v_post_vals):.2f} mV, Max = {np.max(v_post_vals):.2f} mV")
    print(f"  * Correlazione fs-A0    : r = {corr_a0_fs:.5f} (Duffing Hardening: +{p_fs_a0[0]:.2f} Hz/mV)")
    print(f"  * Correlazione tau-A0   : r = {corr_a0_tau:.4f} (Smorzamento non-lineare)")
    print(f"  * Correlazione fs-Vpost : r = {corr_vpost_fs:.3f} (Loop parametrico di Lissajous)")
    print(f"  * Correlazione tau-Vpost: r = {corr_vpost_tau:.3f} (Loop parametrico di Lissajous)")
    print("=" * 85)

    plt.style.use('dark_background')

    # =========================================================================
    # GRAFICO 1: analisi_tau_e_A0_accurata.png (3 pannelli verticali)
    # =========================================================================
    fig1, (ax1_1, ax1_2, ax1_3) = plt.subplots(3, 1, figsize=(13, 11), dpi=150)
    plt.subplots_adjust(hspace=0.35, top=0.93, bottom=0.07, left=0.09, right=0.95)

    ax1_1.plot(fasi, tau_vals, 'o-', color='#00d2ff', markersize=3.5, linewidth=1.4, label=r'$\tau(\phi)$ sperimentale')
    ax1_1.axhline(tau_mean, color='#ff4444', linestyle='--', linewidth=1.5, label=f'Media: {tau_mean:.3f} ms (±{tau_std/tau_mean*100:.2f}%)')
    ax1_1.fill_between(fasi, tau_mean - tau_std, tau_mean + tau_std, color='#00d2ff', alpha=0.15, label=r'Banda $\pm 1\sigma$')
    ax1_1.set_ylabel(r'$\tau$ [ms]', fontsize=11, fontweight='bold')
    ax1_1.set_title(r'Costante di Tempo $\tau$ e Ampiezza Iniziale $A_0$ vs Burst Phase (-360° a +360°)', fontsize=13, fontweight='bold', pad=10)
    ax1_1.grid(True, linestyle=':', alpha=0.5)
    ax1_1.legend(loc='upper right', frameon=True, facecolor='#222')
    ax1_1.set_xticks(np.arange(-360, 361, 60))

    ax1_2.plot(fasi, a0_vals, 's-', color='#ffcc00', markersize=3.5, linewidth=1.4, label=r'$A_0(\phi)$ Ampiezza Iniziale Ringdown')
    ax1_2.set_ylabel(r'$A_0$ [mV]', fontsize=11, fontweight='bold')
    ax1_2.grid(True, linestyle=':', alpha=0.5)
    ax1_2.legend(loc='upper right', frameon=True, facecolor='#222')
    ax1_2.set_xticks(np.arange(-360, 361, 60))

    a0_grid = np.linspace(np.min(a0_vals), np.max(a0_vals), 100)
    ax1_3.scatter(a0_vals, tau_vals, color='#00d2ff', edgecolors='#ffcc00', s=35, label=f'Dati sperimentali (r = {corr_a0_tau:.4f})')
    ax1_3.plot(a0_grid, np.polyval(p_tau_a0, a0_grid), '--', color='#ff6666', linewidth=1.8,
               label=f'Fit lineare: $\\tau = {p_tau_a0[0]*1e3:+.2f} \\mu s/mV \\cdot A_0 + {p_tau_a0[1]:.3f} ms$')
    ax1_3.set_xlabel(r'Ampiezza Iniziale $A_0$ [mV]', fontsize=11, fontweight='bold')
    ax1_3.set_ylabel(r'$\tau$ [ms]', fontsize=11, fontweight='bold')
    ax1_3.set_title(r'Correlazione Diretta: $\tau$ in funzione di $A_0$ (Smorzamento Non Lineare)', fontsize=12, fontweight='bold')
    ax1_3.grid(True, linestyle=':', alpha=0.5)
    ax1_3.legend(loc='lower right', frameon=True, facecolor='#222')

    out1 = os.path.join(session_dir, "analisi_tau_e_A0_accurata.png")
    fig1.savefig(out1, dpi=150)
    plt.close(fig1)
    print(f"[GRAFICO 1] Salvato: {out1}")

    # =========================================================================
    # GRAFICO 2: softening_vs_burst_phase.png (3 pannelli)
    # =========================================================================
    fig2 = plt.figure(figsize=(14, 10), dpi=150)
    gs2 = fig2.add_gridspec(2, 2, hspace=0.32, wspace=0.25, left=0.08, right=0.92, top=0.92, bottom=0.08)

    ax2_1 = fig2.add_subplot(gs2[0, :])
    ax2_2 = fig2.add_subplot(gs2[1, 0])
    ax2_3 = fig2.add_subplot(gs2[1, 1])

    color_v = '#00ffcc'
    color_f = '#ffcc00'
    ax2_1.plot(fasi, v_post_vals, 'o-', color=color_v, linewidth=1.6, markersize=3, label='V_post su CH3 [mV] (Offset DC residuo)')
    ax2_1.set_xlabel(r'Fase Burst Agilent 33220A $\phi$ [°]', fontsize=11, fontweight='bold')
    ax2_1.set_ylabel('V_post su CH3 [mV]', color=color_v, fontsize=11, fontweight='bold')
    ax2_1.tick_params(axis='y', labelcolor=color_v)
    ax2_1.grid(True, linestyle=':', alpha=0.5)
    ax2_1.set_xticks(np.arange(-360, 361, 60))

    ax2_1_f = ax2_1.twinx()
    ax2_1_f.plot(fasi, fs_vals, 's-', color=color_f, linewidth=1.6, markersize=3, label='fs Ringdown su CH1 [Hz]')
    ax2_1_f.set_ylabel('Frequenza fs [Hz]', color=color_f, fontsize=11, fontweight='bold')
    ax2_1_f.tick_params(axis='y', labelcolor=color_f)

    l1, lb1 = ax2_1.get_legend_handles_labels()
    l2, lb2 = ax2_1_f.get_legend_handles_labels()
    ax2_1.legend(l1 + l2, lb1 + lb2, loc='upper left', frameon=True, facecolor='#222')
    ax2_1.set_title(r'Tensione Continua Residua $V_{\mathrm{post}}$(CH3) e Frequenza Naturale $f_s$ vs Phase (-360° a +360°)',
                    fontsize=13, fontweight='bold', pad=10)

    # fs vs V_post
    p_soft = np.polyfit(v_post_vals, fs_vals, 1)
    v_grid = np.linspace(v_post_vals.min(), v_post_vals.max(), 100)
    ax2_2.plot(v_post_vals, fs_vals, color='#555555', linestyle='-', linewidth=1.0, zorder=1)
    ax2_2.scatter(v_post_vals, fs_vals, color='#00ffcc', edgecolors='#111', s=40, zorder=2, label=f'Dati sperimentali (r = {corr_vpost_fs:.3f})')
    ax2_2.plot(v_grid, np.polyval(p_soft, v_grid), '--', color='#ff6666', linewidth=1.6, zorder=3,
               label=f'Pendenza: {p_soft[0]*1e3:+.2f} Hz/V\n(Non è Softening!)')
    ax2_2.set_xlabel(r'Tensione DC Residua $V_{\mathrm{post}}$ [mV]', fontsize=10, fontweight='bold')
    ax2_2.set_ylabel(r'Frequenza di Risonanza $f_s$ [Hz]', fontsize=10, fontweight='bold')
    ax2_2.set_title(r'Frequenza $f_s$ vs $V_{\mathrm{post}}$ (Loop Lissajous)', fontsize=11, fontweight='bold')
    ax2_2.grid(True, linestyle=':', alpha=0.5)
    ax2_2.legend(loc='lower right', frameon=True, facecolor='#222')

    # fs vs A0
    ax2_3.scatter(a0_vals, fs_vals, color='#ffcc00', edgecolors='#111', s=40, label=f'Dati sperimentali (r = {corr_a0_fs:.5f})')
    ax2_3.plot(a0_grid, np.polyval(p_fs_a0, a0_grid), '--', color='#ff6666', linewidth=1.8,
               label=f'Duffing Hardening:\n+{p_fs_a0[0]:.2f} Hz/mV')
    ax2_3.set_xlabel(r'Ampiezza Iniziale Ringdown $A_0$ [mV]', fontsize=10, fontweight='bold')
    ax2_3.set_ylabel(r'Frequenza di Risonanza $f_s$ [Hz]', fontsize=10, fontweight='bold')
    ax2_3.set_title(r'Frequenza $f_s$ vs Ampiezza $A_0$ (Duffing Hardening Reale)', fontsize=11, fontweight='bold')
    ax2_3.grid(True, linestyle=':', alpha=0.5)
    ax2_3.legend(loc='lower right', frameon=True, facecolor='#222')

    out2 = os.path.join(session_dir, "softening_vs_burst_phase.png")
    fig2.savefig(out2, dpi=150)
    plt.close(fig2)
    print(f"[GRAFICO 2] Salvato: {out2}")

    # =========================================================================
    # GRAFICO 3: analisi_tau_e_softening_vs_vpost.png (4 pannelli di confronto)
    # =========================================================================
    fig3 = plt.figure(figsize=(16, 12), dpi=150)
    gs3 = fig3.add_gridspec(2, 2, hspace=0.32, wspace=0.25, left=0.08, right=0.92, top=0.92, bottom=0.08)

    cmap = plt.cm.plasma
    norm = plt.Normalize(vmin=-360, vmax=360)

    # 1. Tau vs V_post
    ax3_1 = fig3.add_subplot(gs3[0, 0])
    ax3_1.plot(v_post_vals, tau_vals, color='#555555', linestyle='-', linewidth=1.2, zorder=1, label='Traiettoria (2 periodi)')
    sc3_1 = ax3_1.scatter(v_post_vals, tau_vals, c=fasi, cmap=cmap, norm=norm, s=45, edgecolor='black', linewidth=0.5, zorder=3)
    p_tau_vpost = np.polyfit(v_post_vals, tau_vals, 1)
    ax3_1.plot(v_grid, np.polyval(p_tau_vpost, v_grid), color='red', linestyle='--', linewidth=1.5, zorder=2,
               label=f'Trend lineare ($r = {corr_vpost_tau:.3f}$)\nFalsa correlazione!')
    ax3_1.set_title(r"$\tau$ vs Tensione Residua $V_{\mathrm{post}}$ (Doppio Loop Chiuso)", fontsize=13, fontweight='bold', pad=10)
    ax3_1.set_xlabel(r"Tensione DC Residua $V_{\mathrm{post}}$ su CH3 [mV]", fontsize=11, fontweight='bold')
    ax3_1.set_ylabel(r"Costante di Tempo $\tau$ [ms]", fontsize=11, fontweight='bold')
    ax3_1.grid(True, linestyle=':', alpha=0.5)
    ax3_1.legend(loc='lower right', fontsize=9, framealpha=0.8)

    # 2. Tau vs A0
    ax3_2 = fig3.add_subplot(gs3[0, 1])
    sc3_2 = ax3_2.scatter(a0_vals, tau_vals, c=fasi, cmap=cmap, norm=norm, s=45, edgecolor='black', linewidth=0.5, zorder=3)
    ax3_2.plot(a0_grid, np.polyval(p_tau_a0, a0_grid), color='#00e5ff', linestyle='--', linewidth=2, zorder=2,
               label=f'Legge fisica reale ($r = {corr_a0_tau:.4f}$)\nSmorzamento non lineare')
    ax3_2.set_title(r"$\tau$ vs Ampiezza Iniziale $A_0$ (Vera Relazione Fisica)", fontsize=13, fontweight='bold', pad=10)
    ax3_2.set_xlabel(r"Ampiezza Iniziale Ringdown $A_0$ [mV]", fontsize=11, fontweight='bold')
    ax3_2.set_ylabel(r"Costante di Tempo $\tau$ [ms]", fontsize=11, fontweight='bold')
    ax3_2.grid(True, linestyle=':', alpha=0.5)
    ax3_2.legend(loc='lower right', fontsize=9, framealpha=0.8)

    # 3. fs vs V_post
    ax3_3 = fig3.add_subplot(gs3[1, 0])
    ax3_3.plot(v_post_vals, fs_vals, color='#555555', linestyle='-', linewidth=1.2, zorder=1, label='Traiettoria Lissajous (2 periodi)')
    sc3_3 = ax3_3.scatter(v_post_vals, fs_vals, c=fasi, cmap=cmap, norm=norm, s=45, edgecolor='black', linewidth=0.5, zorder=3)
    ax3_3.plot(v_grid, np.polyval(p_soft, v_grid), color='red', linestyle='--', linewidth=1.5, zorder=2,
               label=f'Trend lineare apparente ($r = {corr_vpost_fs:.3f}$)\nNon è Softening!')
    ax3_3.set_title(r"Frequenza $f_s$ vs $V_{\mathrm{post}}$ (Loop Chiuso a Doppio Ciclo)", fontsize=13, fontweight='bold', pad=10)
    ax3_3.set_xlabel(r"Tensione DC Residua $V_{\mathrm{post}}$ su CH3 [mV]", fontsize=11, fontweight='bold')
    ax3_3.set_ylabel(r"Frequenza di Risonanza $f_s$ [Hz]", fontsize=11, fontweight='bold')
    ax3_3.grid(True, linestyle=':', alpha=0.5)
    ax3_3.legend(loc='lower right', fontsize=9, framealpha=0.8)

    # 4. fs vs A0
    ax3_4 = fig3.add_subplot(gs3[1, 1])
    sc3_4 = ax3_4.scatter(a0_vals, fs_vals, c=fasi, cmap=cmap, norm=norm, s=45, edgecolor='black', linewidth=0.5, zorder=3)
    ax3_4.plot(a0_grid, np.polyval(p_fs_a0, a0_grid), color='#ff9100', linestyle='--', linewidth=2, zorder=2,
               label=f'Duffing Hardening ($r = {corr_a0_fs:.5f}$)\nPendenza = +{p_fs_a0[0]:.2f} Hz/mV')
    ax3_4.set_title(r"Frequenza $f_s$ vs Ampiezza $A_0$ (Duffing Spring Hardening)", fontsize=13, fontweight='bold', pad=10)
    ax3_4.set_xlabel(r"Ampiezza Iniziale Ringdown $A_0$ [mV]", fontsize=11, fontweight='bold')
    ax3_4.set_ylabel(r"Frequenza di Risonanza $f_s$ [Hz]", fontsize=11, fontweight='bold')
    ax3_4.grid(True, linestyle=':', alpha=0.5)
    ax3_4.legend(loc='lower right', fontsize=9, framealpha=0.8)

    cbar_ax = fig3.add_axes([0.935, 0.15, 0.018, 0.7])
    cbar = fig3.colorbar(cm.ScalarMappable(norm=norm, cmap=cmap), cax=cbar_ax)
    cbar.set_label(r'Fase Burst Agilent 33220A $\phi$ [-360° a +360°]', fontsize=11, fontweight='bold')

    fig3.suptitle(r"Confronto Parametrico Esteso (720°): $V_{\mathrm{post}}$ (Apparente) vs $A_0$ (Fisico Reale)",
                  fontsize=16, fontweight='bold', y=0.98)

    out3 = os.path.join(session_dir, "analisi_tau_e_softening_vs_vpost.png")
    fig3.savefig(out3, dpi=150)
    plt.close(fig3)
    print(f"[GRAFICO 3] Salvato: {out3}")

    # =========================================================================
    # GRAFICO 4: galleria_fit_picchi_reali.png (9 pannelli campione)
    # =========================================================================
    if campioni_gallery:
        fig4, axes = plt.subplots(3, 3, figsize=(16, 12), dpi=150)
        axes = axes.flatten()
        fasi_ordinate = sorted(campioni_gallery.keys())
        for i, ft in enumerate(fasi_ordinate[:9]):
            fase_eff, res = campioni_gallery[ft]
            ax = axes[i]
            t_ms = res['t_seg'] * 1e3
            y_mv = res['y_ac'] * 1e3
            tp_ms = res['t_peaks'] * 1e3
            yp_mv = res['y_peaks'] * 1e3
            fit_mv = res['fit_vals'] * 1e3

            ax.plot(t_ms, y_mv, color='#555555', alpha=0.6, linewidth=0.8, label='Traccia AC')
            ax.scatter(tp_ms, yp_mv, color='#00e5ff', s=12, label='Picchi locali', zorder=3)
            ax.plot(tp_ms, fit_mv, color='#ff3366', linewidth=2, label=f"Fit ($\\tau$={res['tau']*1e3:.2f} ms)", zorder=4)

            ax.set_title(f"Fase $\\phi = {fase_eff:+.0f}^\\circ$ | $A_0 = {res['A0']*1e3:.1f}$ mV | $R^2 = {res['r2']:.4f}$",
                         fontsize=10, fontweight='bold')
            ax.set_xlabel("Tempo post-burst [ms]", fontsize=9)
            ax.set_ylabel("Vout [mV]", fontsize=9)
            ax.grid(True, linestyle=':', alpha=0.4)
            ax.set_xlim(0, 4.5)
            if i == 0:
                ax.legend(loc='upper right', fontsize=8)

        plt.suptitle("Galleria di Fit Esponenziale con Rilevamento dei Picchi Reali (Campioni da -360° a +360°)",
                     fontsize=14, fontweight='bold', y=0.98)
        plt.tight_layout()
        out4 = os.path.join(session_dir, "galleria_fit_picchi_reali.png")
        fig4.savefig(out4, dpi=150)
        plt.close(fig4)
        print(f"[GRAFICO 4] Salvato: {out4}")

    print("\n[SUCCESSO] Tutta l'elaborazione è completata con successo!")

if __name__ == '__main__':
    main()

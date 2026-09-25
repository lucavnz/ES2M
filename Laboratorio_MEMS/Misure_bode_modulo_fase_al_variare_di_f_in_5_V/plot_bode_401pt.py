"""
Plot del diagramma di Bode 401 punti (128 medie) in stile minimale accademico.
Confronto tra Risposta Grezza (Fano) e Ramo Motionale Compensato (Lorentziana pura + transizione di fase).
"""

import os
import csv
import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit

# Directory di lavoro
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(SCRIPT_DIR, "sweep_417520Hz_401pt_20260907_160506.csv")
OUT_PNG = os.path.join(SCRIPT_DIR, "bode_401pt_confronto_completo.png")

GE_TIA = 5.0e6  # Guadagno Transimpedenza TIA (5 MOhm)

# Stile minimale coordinato
plt.rcParams.update({
    'font.family': 'sans-serif',
    'font.size': 10,
    'axes.labelsize': 10.5,
    'axes.titlesize': 11.5,
    'xtick.labelsize': 9.5,
    'ytick.labelsize': 9.5,
    'legend.fontsize': 9.0,
    'lines.linewidth': 1.8,
    'grid.alpha': 0.45,
    'grid.linestyle': ':'
})

def bvd_model(f, f0, Q, A0, theta, r0, r1, i0, i1, f_start, f_stop):
    f_norm = (f - f_start) / (f_stop - f_start)
    base = (r0 + r1 * f_norm) + 1j * (i0 + i1 * f_norm)
    mot = (A0 * np.exp(1j * theta)) / (1.0 + 2j * Q * (f - f0) / f0)
    return base + mot

def model_flat(f, f0, Q, A0, theta, r0, r1, i0, i1, f_start, f_stop):
    H = bvd_model(f, f0, Q, A0, theta, r0, r1, i0, i1, f_start, f_stop)
    return np.concatenate([np.real(H), np.imag(H)])

def main():
    # 1. Caricamento dati
    with open(CSV_PATH, 'r', encoding='utf-8') as fh:
        rows = [r for r in csv.reader(fh) if r and not r[0].startswith('#') and not r[0].lower().startswith('step')]

    freqs = np.array([float(r[1]) for r in rows])
    gains = np.array([float(r[5]) for r in rows])
    phases = np.array([float(r[7]) for r in rows])

    phase_rad = np.radians(phases)
    re = gains * np.cos(phase_rad)
    im = gains * np.sin(phase_rad)
    H_exp = re + 1j * im

    # 2. Stima iniziale e Fit BVD
    n_edge = 20
    base_idx = list(range(n_edge)) + list(range(len(freqs) - n_edge, len(freqs)))
    p_re = np.polyfit(freqs[base_idx], re[base_idx], 1)
    p_im = np.polyfit(freqs[base_idx], im[base_idx], 1)

    r0_init = p_re[1] + p_re[0] * freqs[0]
    r1_init = p_re[0] * (freqs[-1] - freqs[0])
    i0_init = p_im[1] + p_im[0] * freqs[0]
    i1_init = p_im[0] * (freqs[-1] - freqs[0])

    idx_peak = np.argmax(gains)
    f_peak_init = freqs[idx_peak]

    p0 = [f_peak_init, 2800.0, 0.35, -0.4, r0_init, r1_init, i0_init, i1_init]
    bounds = (
        [freqs[0], 200, 0.001, -np.pi, -100, -50, -100, -50],
        [freqs[-1], 25000, 10.0, np.pi, 100, 50, 100, 50]
    )

    popt, _ = curve_fit(
        lambda f, f0, Q, A0, theta, r0, r1, i0, i1: model_flat(f, f0, Q, A0, theta, r0, r1, i0, i1, freqs[0], freqs[-1]),
        freqs, np.concatenate([re, im]), p0=p0, bounds=bounds, maxfev=15000
    )
    f0_opt, Q_opt, A0_opt, theta_opt, r0_opt, r1_opt, i0_opt, i1_opt = popt

    # 3. De-embedding e curve fini
    f_fine = np.linspace(freqs[0], freqs[-1], 2500)
    H_fit_fine = bvd_model(f_fine, *popt, freqs[0], freqs[-1])
    gain_fit_fine = np.abs(H_fit_fine)
    phase_fit_fine = np.degrees(np.angle(H_fit_fine))

    f_norm_pts = (freqs - freqs[0]) / (freqs[-1] - freqs[0])
    H_base_pts = (r0_opt + r1_opt * f_norm_pts) + 1j * (i0_opt + i1_opt * f_norm_pts)
    f_norm_fine = (f_fine - freqs[0]) / (freqs[-1] - freqs[0])
    H_base_fine = (r0_opt + r1_opt * f_norm_fine) + 1j * (i0_opt + i1_opt * f_norm_fine)

    H_mot_pts = (H_exp - H_base_pts) * np.exp(-1j * theta_opt)
    gain_mot_pts = np.abs(H_mot_pts)
    phase_mot_pts = np.degrees(np.angle(H_mot_pts))
    phase_mot_pts = ((phase_mot_pts + 180) % 360) - 180

    H_mot_fine = A0_opt / (1.0 + 2j * Q_opt * (f_fine - f0_opt) / f0_opt)
    gain_mot_fine = np.abs(H_mot_fine)
    phase_mot_fine = np.degrees(np.angle(H_mot_fine))

    Cp_mean = np.mean(np.abs(H_base_fine) / (2.0 * np.pi * f_fine * GE_TIA))
    Cp_pf = Cp_mean * 1e12
    delta_f_3db = f0_opt / Q_opt

    print(f"Parametri estratti:")
    print(f"  f1 = {f0_opt:.2f} Hz")
    print(f"  Q  = {Q_opt:.1f}")
    print(f"  A0 = {A0_opt:.3f} V/V")
    print(f"  Cp = {Cp_pf:.3f} pF")
    print(f"  Delta f_-3dB = {delta_f_3db:.1f} Hz")

    # 4. Creazione Grafico 2x2 coordinato
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(13.5, 8.5), sharex=True)

    # Top-Left: Modulo Risposta Grezza (rosso / rosso)
    ax1.plot(freqs / 1e3, gains, '.', color='#d62728', markersize=3.8, alpha=0.65, label='Dati')
    ax1.plot(f_fine / 1e3, gain_fit_fine, '-', color='#d62728', lw=1.8, label='Fit BVD')
    ax1.plot(f_fine / 1e3, np.abs(H_base_fine), '--', color='#7f7f7f', lw=1.2, label=rf'$C_p$ ({Cp_pf:.3f} pF)')
    ax1.set_ylabel(r'$|H|$ [V/V]')
    ax1.set_title(r'Risposta grezza: modulo $|H|$')
    ax1.grid(True)
    ax1.legend(loc='upper right', framealpha=0.95)

    # Bottom-Left: Fase Risposta Grezza (blu / blu)
    ax3.plot(freqs / 1e3, phases, '.', color='#1f77b4', markersize=3.8, alpha=0.65, label='Dati')
    ax3.plot(f_fine / 1e3, phase_fit_fine, '-', color='#1f77b4', lw=1.8, label='Fit BVD')
    ax3.set_xlabel(r'Frequenza $f$ [kHz]')
    ax3.set_ylabel(r'$\angle H$ [°]')
    ax3.set_title(r'Risposta grezza: fase $\angle H$')
    ax3.grid(True)
    ax3.legend(loc='upper right', framealpha=0.95)

    # Top-Right: Modulo Risposta Compensata (Hm)
    ax2.plot(freqs / 1e3, gain_mot_pts, '.', color='#27ae60', markersize=3.8, alpha=0.65, label='Dati compensati')
    ax2.plot(f_fine / 1e3, gain_mot_fine, '-', color='#1e8449', lw=1.8,
             label=rf'Fit lorentziano ($f_1 = {f0_opt/1e3:.3f}\,\mathrm{{kHz}},\ Q = {Q_opt:.0f}$)')
    ax2.axvline(f0_opt / 1e3, color='gray', linestyle=':', lw=1.2, alpha=0.6)
    ax2.set_ylabel(r'$|H_m|$ [V/V]')
    ax2.set_title(r'Risposta compensata: modulo $|H_m|$')
    ax2.grid(True)
    ax2.legend(loc='upper right', framealpha=0.95)

    # Bottom-Right: Fase Risposta Compensata (Hm)
    ax4.plot(freqs / 1e3, phase_mot_pts, '.', color='#e67e22', markersize=3.8, alpha=0.65, label='Dati compensati')
    ax4.plot(f_fine / 1e3, phase_mot_fine, '-', color='#d35400', lw=1.8, label='Fit lorentziano')
    ax4.axhline(0, color='gray', linestyle='--', lw=1.0, alpha=0.6)
    ax4.axvline(f0_opt / 1e3, color='gray', linestyle=':', lw=1.2, alpha=0.6)
    ax4.set_xlabel(r'Frequenza $f$ [kHz]')
    ax4.set_ylabel(r'$\angle H_m$ [°]')
    ax4.set_title(r'Risposta compensata: fase $\angle H_m$')
    ax4.set_ylim(-130, 130)
    ax4.set_yticks([-90, -45, 0, 45, 90])
    ax4.grid(True)
    ax4.legend(loc='lower left', framealpha=0.95)

    plt.tight_layout()
    fig.savefig(OUT_PNG, dpi=300)
    plt.close(fig)
    print(f"[OK] Grafico salvato in: {OUT_PNG}")

if __name__ == '__main__':
    main()

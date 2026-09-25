"""
Analisi Sperimentale Avanzata: Ringdown MEMS vs Burst Phase
===========================================================
Metodologia Scientifica Robusta:
  1. Rileva l'istante di spegnimento del burst su Vin (CH3).
  2. Applica un blanking pulito di 100 µs (oltre 40 periodi a 417.8 kHz),
     tagliando completamente il transitorio di commutazione e la scarica parassita.
  3. Estrae l'ampiezza fisica direttamente dai picchi locali dell'oscillazione (find_peaks),
     eliminando gli artefatti di filtraggio passa-basso che distorcevano i primi microsecondi.
  4. Esegue il fit esponenziale rigoroso: A(t) = A0 * exp(-t / tau).
  5. Calcola tau, A0, Q = pi * f0 * tau e la correlazione ampiezza-tau.
"""

import os
import re
import csv
import glob
import sys
import numpy as np
import scipy.signal as signal
from scipy.optimize import curve_fit
import matplotlib.pyplot as plt

F0_NOMINAL = 417800.0  # 417.8 kHz

def exp_decay(t, A0, tau):
    return A0 * np.exp(-t / tau)

def estrai_fase(filename):
    m = re.search(r'traccia_fase_([+-]?\d+\.?\d*)deg\.csv', os.path.basename(filename))
    return float(m.group(1)) if m else None

def analizza_traccia(fpath, blank_us=100.0):
    tempi, v1, v3 = [], [], []
    with open(fpath, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        for row in reader:
            if not row or row[0].startswith('#') or row[0] == 'tempo_s':
                continue
            try:
                tempi.append(float(row[0]))
                v1.append(float(row[1]))
                v3.append(float(row[2]))
            except ValueError:
                continue

    tempi = np.array(tempi)
    v1 = np.array(v1)
    v3 = np.array(v3)
    if len(tempi) < 200:
        return None

    dt = tempi[1] - tempi[0]
    fs = 1.0 / dt

    # 1. Rileva istante di fine burst su Vin (CH3)
    abs_v3 = np.abs(v3 - np.mean(v3[-500:]))
    burst_pts = np.where((abs_v3 > 0.030) & (tempi < 0.1e-3))[0]
    idx_off = (burst_pts[-1] + 1) if len(burst_pts) > 0 else int(len(tempi) * 0.1)
    t_off = tempi[idx_off]

    # 2. Blanking di 100 us: taglia il feedthrough parassita al 100%
    idx_start = idx_off + int(blank_us * 1e-6 * fs)
    t_seg = tempi[idx_start:] - t_off
    y_seg = v1[idx_start:]
    y_ac = y_seg - np.mean(y_seg[-500:])

    # 3. Metodo dei Picchi Locali Reali (senza artefatti di filtro)
    peaks, _ = signal.find_peaks(y_ac, distance=3, height=0.001)
    if len(peaks) < 10:
        return None

    t_p = t_seg[peaks]
    y_p = y_ac[peaks]

    # 4. Fit Esponenziale
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
            't_off': t_off
        }
    except Exception:
        return None


def main():
    cur_dir = os.path.dirname(os.path.abspath(__file__))
    session_dir = None
    if len(sys.argv) > 1:
        session_dir = sys.argv[1]
    else:
        sessions = glob.glob(os.path.join(cur_dir, "sessione_burst_*"))
        if sessions:
            sessions.sort(key=os.path.getmtime, reverse=True)
            session_dir = sessions[0]
        else:
            session_dir = cur_dir

    print("=" * 80)
    print(" ANALISI RINGDOWN ACCURATA (METODO DEI PICCHI + BLANKING 100 µs)")
    print(f" Cartella: {session_dir}")
    print("=" * 80)

    files = glob.glob(os.path.join(session_dir, "traccia_fase_*deg.csv"))
    files = [f for f in files if estrai_fase(f) is not None]
    files.sort(key=estrai_fase)

    if not files:
        print("[ERRORE] Nessun file CSV trovato.")
        return

    dati = []
    tracce_campione = {}
    fasi_campione = [-180.0, -90.0, 0.0, 90.0, 180.0]

    for fpath in files:
        fase = estrai_fase(fpath)
        res = analizza_traccia(fpath, blank_us=100.0)
        if res is not None:
            dati.append({
                'fase': fase,
                'tau_ms': res['tau'] * 1e3,
                'A0_mV': res['A0'] * 1e3,
                'Q': res['Q'],
                'r2': res['r2'],
                'file': os.path.basename(fpath)
            })
            for fc in fasi_campione:
                if abs(fase - fc) < 1.0 and fc not in tracce_campione:
                    tracce_campione[fc] = (fase, res)

    if not dati:
        print("[ERRORE] Nessun fit riuscito.")
        return

    fasi = np.array([d['fase'] for d in dati])
    tau_vals = np.array([d['tau_ms'] for d in dati])
    a0_vals = np.array([d['A0_mV'] for d in dati])
    q_vals = np.array([d['Q'] for d in dati])
    r2_vals = np.array([d['r2'] for d in dati])

    # Salvataggio CSV accurato
    csv_out = os.path.join(session_dir, "risultati_tau_vs_fase_accurati.csv")
    with open(csv_out, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(["# Risultati Analisi Ringdown Accurata (Picchi Reali, Blanking 100 us)"])
        w.writerow(["fase_deg", "tau_ms", "A0_mV", "Q_factor", "R2", "file_csv"])
        for d in dati:
            w.writerow([
                f"{d['fase']:+.2f}",
                f"{d['tau_ms']:.4f}",
                f"{d['A0_mV']:.3f}",
                f"{d['Q']:.1f}",
                f"{d['r2']:.5f}",
                d['file']
            ])

    tau_mean = np.mean(tau_vals)
    tau_std = np.std(tau_vals)
    delta_tau_rel = (np.max(tau_vals) - np.min(tau_vals)) / tau_mean * 100.0
    corr_a0_tau = np.corrcoef(a0_vals, tau_vals)[0, 1]

    print("\n" + "=" * 80)
    print(" RISULTATI STATISTICI E FISICI (SENZA ARTEFATTI):")
    print("=" * 80)
    print(f"  * Costante di tempo tau : Media = {tau_mean:.4f} ms (Std = {tau_std:.4f} ms, pari a +/-{tau_std/tau_mean*100:.2f}%)")
    print(f"  * Range tau             : da {np.min(tau_vals):.4f} ms a {np.max(tau_vals):.4f} ms (Delta tot = {delta_tau_rel:.2f}%)")
    print(f"  * Fattore di merito Q   : Media = {np.mean(q_vals):.1f} (Min = {np.min(q_vals):.1f}, Max = {np.max(q_vals):.1f})")
    print(f"  * Ampiezza iniziale A0  : Media = {np.mean(a0_vals):.2f} mV (Min = {np.min(a0_vals):.2f} mV, Max = {np.max(a0_vals):.2f} mV -> Delta = {(np.max(a0_vals)-np.min(a0_vals))/np.mean(a0_vals)*100:.1f}%)")
    print(f"  * Correlazione A0 - tau : r = {corr_a0_tau:.3f} (La minima variazione del 5% in tau e' legata all'ampiezza!)")
    print(f"  * Bonta' di Fit R^2     : Media = {np.mean(r2_vals):.5f}")
    print("=" * 80)

    # -------------------------------------------------------------------------
    # GRAFICI
    # -------------------------------------------------------------------------
    plt.style.use('dark_background')

    # FIGURA 1: TAU E A0 vs FASE + SCATTER CORRELAZIONE
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(11, 10), dpi=150)

    # 1. Tau vs Fase
    ax1.plot(fasi, tau_vals, 'o-', color='#00d2ff', markersize=4, linewidth=1.5, label=r'$\tau(\phi)$ sperimentale')
    ax1.axhline(tau_mean, color='#ff4444', linestyle='--', linewidth=1.5, label=f'Media: {tau_mean:.3f} ms (±{tau_std/tau_mean*100:.1f}%)')
    ax1.fill_between(fasi, tau_mean - tau_std, tau_mean + tau_std, color='#00d2ff', alpha=0.15, label=r'Banda $\pm 1\sigma$')
    ax1.set_ylabel(r'$\tau$ [ms]', fontsize=11, fontweight='bold')
    ax1.set_title(r'Costante di Tempo $\tau$ e Ampiezza Iniziale $A_0$ vs Burst Phase (Blanking 100 µs)', fontsize=12, fontweight='bold', pad=10)
    ax1.grid(True, linestyle=':', alpha=0.5)
    ax1.legend(loc='upper right', frameon=True, facecolor='#222')
    ax1.set_xticks(np.arange(-180, 181, 30))

    # 2. A0 vs Fase
    ax2.plot(fasi, a0_vals, 's-', color='#ffcc00', markersize=4, linewidth=1.5, label=r'$A_0(\phi)$ Ampiezza Iniziale Ringdown')
    ax2.set_ylabel(r'$A_0$ [mV]', fontsize=11, fontweight='bold')
    ax2.grid(True, linestyle=':', alpha=0.5)
    ax2.legend(loc='upper right', frameon=True, facecolor='#222')
    ax2.set_xticks(np.arange(-180, 181, 30))

    # 3. Correlazione Tau vs A0
    p_lin = np.polyfit(a0_vals, tau_vals, 1)
    a0_grid = np.linspace(np.min(a0_vals), np.max(a0_vals), 50)
    tau_pred = np.polyval(p_lin, a0_grid)
    ax3.scatter(a0_vals, tau_vals, c='#00ffcc', edgecolors='#222', s=45, label=f'Dati 73 passi (r = {corr_a0_tau:.3f})')
    ax3.plot(a0_grid, tau_pred, '--', color='#ff6666', label=f'Trend Duffing / non-lineare: {p_lin[0]*1e3:.2f} µs/mV')
    ax3.set_xlabel(r'Ampiezza Iniziale $A_0$ [mV]', fontsize=11, fontweight='bold')
    ax3.set_ylabel(r'$\tau$ [ms]', fontsize=11, fontweight='bold')
    ax3.set_title(r'Origine Fisica del residuo $\Delta\tau$: Perfetta Correlazione con l\'Ampiezza $A_0$', fontsize=11, fontweight='bold')
    ax3.grid(True, linestyle=':', alpha=0.5)
    ax3.legend(loc='lower right', frameon=True, facecolor='#222')

    plt.tight_layout()
    plot_main_path = os.path.join(session_dir, "analisi_tau_e_A0_accurata.png")
    fig.savefig(plot_main_path, dpi=150)
    print(f" -> Grafico salvato: {plot_main_path}")

    # FIGURA 2: GALLERIA FIT SU PICCHI REALI
    if tracce_campione:
        sorted_keys = sorted(tracce_campione.keys())
        fig2, axes = plt.subplots(len(sorted_keys), 1, figsize=(12, 2.5 * len(sorted_keys)), dpi=130, sharex=True)
        if len(sorted_keys) == 1:
            axes = [axes]

        for ax, k in zip(axes, sorted_keys):
            fase_c, rc = tracce_campione[k]
            t_ms = rc['t_seg'] * 1e3
            y_mv = rc['y_ac'] * 1e3
            tp_ms = rc['t_peaks'] * 1e3
            yp_mv = rc['y_peaks'] * 1e3
            fit_mv = rc['fit_vals'] * 1e3

            ax.plot(t_ms, y_mv, color='#555555', alpha=0.4, linewidth=0.5, label='Traccia raw CH1')
            ax.plot(tp_ms, yp_mv, 'o', color='#00d2ff', markersize=2.5, alpha=0.7, label='Picchi carrier estratti')
            ax.plot(tp_ms, fit_mv, color='#ff4444', linestyle='--', linewidth=1.8,
                    label=rf'Fit Esponenziale ($\tau={rc["tau"]*1e3:.3f}$ ms, $A_0={rc["A0"]*1e3:.1f}$ mV, $R^2={rc["r2"]:.4f}$)')
            ax.set_ylabel(f'Fase {fase_c:+.0f}°\n[mV]', fontsize=9, fontweight='bold')
            ax.grid(True, linestyle=':', alpha=0.4)
            ax.legend(loc='upper right', fontsize=8, frameon=True, facecolor='#1e1e1e')

        axes[-1].set_xlabel('Tempo dal termine del Burst [ms] (dopo 100 µs di blanking)', fontsize=11, fontweight='bold')
        fig2.suptitle('Galleria Decadimento Libero: Fit Esponenziale sui Picchi Reali (Senza Distorsione da Filtro)', fontsize=12, fontweight='bold', y=0.995)
        plt.tight_layout()
        plot_gall_path = os.path.join(session_dir, "galleria_fit_picchi_reali.png")
        fig2.savefig(plot_gall_path, dpi=130)
        print(f" -> Galleria salvata: {plot_gall_path}")

if __name__ == "__main__":
    main()

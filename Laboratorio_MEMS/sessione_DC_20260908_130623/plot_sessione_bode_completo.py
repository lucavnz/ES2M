"""
Script di Plot e Fit BVD per Sessione DC:
1. Genera per ciascuna tensione VDC (0V, 1V, 2V, 3V, 4V, 5V) il grafico 2x2 identico a bode_401pt_confronto_completo.png:
   - Risposta Grezza (Modulo e Fase) con punti sperimentali + Fit BVD + Basamento Cp
   - Risposta Compensata (Modulo Campana Lorentziana e Fase Transizione RLC +-90 deg) con punti de-embedded + Fit
2. Genera il grafico comparativo di TUTTE le curve assieme con SOLO I FIT (senza punti sperimentali)
3. Genera il grafico di sintonia elettrostatica (Spring Softening f0 vs Vdc^2 e A0 vs Vdc^2)
"""

import os
import glob
import csv
import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit

# Impostazioni grafiche stile accademico pulito
plt.rcParams.update({
    'font.family': 'sans-serif',
    'font.size': 10,
    'axes.labelsize': 11,
    'axes.titlesize': 12,
    'xtick.labelsize': 10,
    'ytick.labelsize': 10,
    'legend.fontsize': 9.2,
    'figure.titlesize': 13,
    'lines.linewidth': 2.0,
    'grid.alpha': 0.45,
    'grid.linestyle': ':'
})

GE_TIA = 5.0e6  # 5 MOhm

def bvd_model(f, f0, Q, A0, theta, r0, r1, i0, i1, f_start, f_stop):
    f_norm = (f - f_start) / (f_stop - f_start)
    base = (r0 + r1 * f_norm) + 1j * (i0 + i1 * f_norm)
    mot = (A0 * np.exp(1j * theta)) / (1.0 + 2j * Q * (f - f0) / f0)
    return base + mot

def model_flat(f, f0, Q, A0, theta, r0, r1, i0, i1, f_start, f_stop):
    H = bvd_model(f, f0, Q, A0, theta, r0, r1, i0, i1, f_start, f_stop)
    return np.concatenate([np.real(H), np.imag(H)])


def processa_sessione(session_dir):
    session_dir = os.path.abspath(session_dir)
    files = sorted(glob.glob(os.path.join(session_dir, "sweep_VDC_*V_*.csv")))
    print(f"File sweep trovati ({len(files)}):")
    for f in files:
        print(f"  - {os.path.basename(f)}")

    fits = []

    for f_csv in files:
        with open(f_csv, 'r', encoding='utf-8') as fh:
            rows = [r for r in csv.reader(fh) if r and not r[0].startswith('#') and not r[0].lower().startswith('step')]

        # Estrazione VDC dal nome file o dal contenuto
        base_name = os.path.basename(f_csv)
        tag_v = base_name.split('_')[2]  # es. '05p0V'
        vdc_val = float(tag_v.replace('V', '').replace('p', '.'))

        freqs = np.array([float(r[1]) for r in rows])
        gains = np.array([float(r[5]) for r in rows])
        phases = np.array([float(r[7]) for r in rows])

        phase_rad = np.radians(phases)
        re = gains * np.cos(phase_rad)
        im = gains * np.sin(phase_rad)
        H_exp = re + 1j * im

        # Stima iniziale basamento
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

        # Calcoli di de-embedding
        f_fine = np.linspace(freqs[0], freqs[-1], 2500)
        H_fit_fine = bvd_model(f_fine, *popt, freqs[0], freqs[-1])
        gain_fit_fine = np.abs(H_fit_fine)
        phase_fit_fine = np.degrees(np.angle(H_fit_fine))

        f_norm_pts = (freqs - freqs[0]) / (freqs[-1] - freqs[0])
        H_base_pts = (r0_opt + r1_opt * f_norm_pts) + 1j * (i0_opt + i1_opt * f_norm_pts)
        f_norm_fine = (f_fine - freqs[0]) / (freqs[-1] - freqs[0])
        H_base_fine = (r0_opt + r1_opt * f_norm_fine) + 1j * (i0_opt + i1_opt * f_norm_fine)

        # De-embedding punti sperimentali
        H_mot_pts = (H_exp - H_base_pts) * np.exp(-1j * theta_opt)
        gain_mot_pts = np.abs(H_mot_pts)
        phase_mot_pts = np.degrees(np.angle(H_mot_pts))
        phase_mot_pts = ((phase_mot_pts + 180) % 360) - 180

        # Curva analitica lorentziana pura
        H_mot_fine = A0_opt / (1.0 + 2j * Q_opt * (f_fine - f0_opt) / f0_opt)
        gain_mot_fine = np.abs(H_mot_fine)
        phase_mot_fine = np.degrees(np.angle(H_mot_fine))

        # Capacita parassita Cp
        Cp_mean = np.mean(np.abs(H_base_fine) / (2.0 * np.pi * f_fine * GE_TIA))
        Cp_pf = Cp_mean * 1e12
        delta_f_3db = f0_opt / Q_opt

        fit_res = {
            'vdc': vdc_val,
            'f_csv': f_csv,
            'freqs': freqs,
            'gains': gains,
            'phases': phases,
            'gain_mot_pts': gain_mot_pts,
            'phase_mot_pts': phase_mot_pts,
            'f_fine': f_fine,
            'gain_fit_fine': gain_fit_fine,
            'phase_fit_fine': phase_fit_fine,
            'gain_mot_fine': gain_mot_fine,
            'phase_mot_fine': phase_mot_fine,
            'H_base_fine': H_base_fine,
            'f0': f0_opt,
            'Q': Q_opt,
            'A0': A0_opt,
            'theta': theta_opt,
            'Cp_pf': Cp_pf,
            'delta_f_3db': delta_f_3db,
            'n_pts': len(freqs)
        }
        fits.append(fit_res)

        # ---------------------------------------------------------------------
        # 1. GRAFICO SINGOLO 2x2 PER QUESTO VDC (Esattamente come bode_401pt_confronto_completo.png)
        # ---------------------------------------------------------------------
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(14, 9.5), sharex=True)
        fig.suptitle(
            f"Caratterizzazione Risonatore MEMS - Sweep {len(freqs)} Punti (128 Medie) | V_DC = {vdc_val:.1f} V\n"
            f"f0 = {f0_opt:.2f} Hz | Q = {Q_opt:.1f} | Delta f_-3dB = {delta_f_3db:.1f} Hz | Cp = {Cp_pf:.3f} pF (A0 = {A0_opt:.3f} V/V)",
            fontsize=13, fontweight='bold', y=0.98
        )

        # Top-Left: Risposta Grezza Modulo
        ax1.plot(freqs / 1e3, gains, '.', color='#4a90e2', markersize=4.5, alpha=0.8, label=f'Dati Sperimentali ({len(freqs)} pt)')
        ax1.plot(f_fine / 1e3, gain_fit_fine, '-', color='#d32f2f', lw=2.2, label='Fit BVD Completo')
        ax1.plot(f_fine / 1e3, np.abs(H_base_fine), '--', color='#616161', lw=1.5, label=f'Basamento Cp ({Cp_pf:.3f} pF)')
        ax1.set_ylabel('Guadagno Totale |H| [V/V]', fontweight='bold')
        ax1.set_title('Risposta Grezza: Modulo (Risonanza di Fano)', fontweight='bold', fontsize=11.5)
        ax1.grid(True, linestyle=':', alpha=0.5)
        ax1.legend(loc='best', framealpha=0.92)

        # Bottom-Left: Risposta Grezza Fase
        ax3.plot(freqs / 1e3, phases, '.', color='#4a90e2', markersize=4.5, alpha=0.8, label='Dati Sperimentali')
        ax3.plot(f_fine / 1e3, phase_fit_fine, '-', color='#d32f2f', lw=2.2, label='Fit BVD Completo')
        ax3.set_xlabel('Frequenza [kHz]', fontweight='bold')
        ax3.set_ylabel('Sfasamento Totale [°]', fontweight='bold')
        ax3.set_title('Risposta Grezza: Fase', fontweight='bold', fontsize=11.5)
        ax3.grid(True, linestyle=':', alpha=0.5)
        ax3.legend(loc='best', framealpha=0.92)

        # Top-Right: Risposta Compensata Modulo (Ramo Meccanico Puro)
        ax2.plot(freqs / 1e3, gain_mot_pts, '.', color='#43a047', markersize=4.5, alpha=0.8, label='Dati De-embedded')
        ax2.plot(f_fine / 1e3, gain_mot_fine, '-', color='#1b5e20', lw=2.2, label=f'Campana Lorentziana (A0={A0_opt:.3f} V/V)')
        ax2.axvline(f0_opt / 1e3, color='gray', linestyle=':', lw=1.5, label=f'f0 = {f0_opt:.1f} Hz')
        ax2.set_ylabel('Guadagno Motionale Puro |H_mot| [V/V]', fontweight='bold')
        ax2.set_title('Risposta Compensata: Modulo (Ramo Meccanico Puro)', fontweight='bold', fontsize=11.5)
        ax2.grid(True, linestyle=':', alpha=0.5)
        ax2.legend(loc='upper right', framealpha=0.92)

        # Bottom-Right: Risposta Compensata Fase (Transizione Meccanica Pura)
        ax4.plot(freqs / 1e3, phase_mot_pts, '.', color='#fb8c00', markersize=4.5, alpha=0.8, label='Dati De-embedded')
        ax4.plot(f_fine / 1e3, phase_mot_fine, '-', color='#e65100', lw=2.2, label=r'Transizione RLC $\pm 90^\circ$')
        ax4.axhline(0, color='gray', linestyle='--', lw=1.2, alpha=0.7)
        ax4.axvline(f0_opt / 1e3, color='gray', linestyle=':', lw=1.5)
        ax4.set_xlabel('Frequenza [kHz]', fontweight='bold')
        ax4.set_ylabel('Sfasamento Motionale [°]', fontweight='bold')
        ax4.set_title('Risposta Compensata: Fase (Transizione Meccanica Pura)', fontweight='bold', fontsize=11.5)
        ax4.set_ylim(-110, 110)
        ax4.set_yticks([-90, -45, 0, 45, 90])
        ax4.grid(True, linestyle=':', alpha=0.5)
        ax4.legend(loc='lower left', framealpha=0.92)

        plt.tight_layout(rect=[0, 0, 1, 0.95])
        out_single_png = os.path.join(session_dir, f"bode_confronto_completo_VDC_{tag_v}.png")
        fig.savefig(out_single_png, dpi=300)
        plt.close(fig)
        print(f" -> [OK] Grafico 2x2 per VDC = {vdc_val:.1f}V salvato in: {os.path.basename(out_single_png)}")

    # Ordinamento per VDC
    fits.sort(key=lambda x: x['vdc'])

    # -------------------------------------------------------------------------
    # 2. GRAFICO CONFRONTO COMPLETO TUTTE LE VDC: SOLO I FIT (SENZA PUNTI SPERIMENTALI)
    # -------------------------------------------------------------------------
    fig_all, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(14, 9.5), sharex=True)
    fig_all.suptitle(
        f"Confronto Caratterizzazione Risonatore MEMS al Variare di V_DC (0.0 V -> 5.0 V)\n"
        f"SOLO FIT ANALITICI BVD (Curve Pure senza Punti Sperimentali)",
        fontsize=13, fontweight='bold', y=0.98
    )

    colors = ['#1f77b4', '#9467bd', '#2ca02c', '#ff7f0e', '#d62728', '#8c564b']

    for i, res in enumerate(fits):
        c = colors[i % len(colors)]
        lbl = f"V_DC = {res['vdc']:.0f} V (f0={res['f0']:.1f} Hz, A0={res['A0']:.3f})"
        lbl_short = f"V_DC = {res['vdc']:.0f} V"

        # (a) Modulo Grezzo
        ax1.plot(res['f_fine'] / 1e3, res['gain_fit_fine'], '-', color=c, lw=2.2, label=lbl_short)

        # (b) Modulo Compensato (Campane Lorentziane)
        ax2.plot(res['f_fine'] / 1e3, res['gain_mot_fine'], '-', color=c, lw=2.4, label=lbl)
        ax2.axvline(res['f0'] / 1e3, color=c, linestyle=':', lw=1.2, alpha=0.6)

        # (c) Fase Grezza
        ax3.plot(res['f_fine'] / 1e3, res['phase_fit_fine'], '-', color=c, lw=2.2, label=lbl_short)

        # (d) Fase Compensata
        ax4.plot(res['f_fine'] / 1e3, res['phase_mot_fine'], '-', color=c, lw=2.2, label=lbl_short)

    # Assi e Titoli Pannello Completo
    ax1.set_ylabel('Guadagno Totale |H| [V/V]', fontweight='bold')
    ax1.set_title('(a) Risposta Totale Grezza: Modulo (Fit BVD Fano)', fontweight='bold', fontsize=11.5)
    ax1.grid(True, linestyle=':', alpha=0.5)
    ax1.legend(loc='best', framealpha=0.92, fontsize=8.8)

    ax2.set_ylabel('Guadagno Motionale |H_mot| [V/V]', fontweight='bold')
    ax2.set_title('(b) Ramo Motionale Puro: Campane Lorentziane Sovrapposte', fontweight='bold', fontsize=11.5)
    ax2.grid(True, linestyle=':', alpha=0.5)
    ax2.legend(loc='upper right', framealpha=0.92, fontsize=8.2)

    ax3.set_xlabel('Frequenza [kHz]', fontweight='bold')
    ax3.set_ylabel('Sfasamento Totale [°]', fontweight='bold')
    ax3.set_title('(c) Sfasamento Totale Grezzo (Fit BVD)', fontweight='bold', fontsize=11.5)
    ax3.grid(True, linestyle=':', alpha=0.5)
    ax3.legend(loc='best', framealpha=0.92, fontsize=8.8)

    ax4.axhline(0, color='gray', linestyle='--', lw=1.2, alpha=0.7)
    ax4.set_xlabel('Frequenza [kHz]', fontweight='bold')
    ax4.set_ylabel('Sfasamento Motionale [°]', fontweight='bold')
    ax4.set_title(r'(d) Sfasamento Ramo Motionale (Transizione $\pm 90^\circ$)', fontweight='bold', fontsize=11.5)
    ax4.set_ylim(-110, 110)
    ax4.set_yticks([-90, -45, 0, 45, 90])
    ax4.grid(True, linestyle=':', alpha=0.5)
    ax4.legend(loc='lower left', framealpha=0.92, fontsize=8.8)

    plt.tight_layout(rect=[0, 0, 1, 0.95])
    out_all_png = os.path.join(session_dir, "bode_confronto_tutte_VDC_solo_fit.png")
    fig_all.savefig(out_all_png, dpi=300)
    plt.close(fig_all)
    print(f"\n -> [OK] Grafico 2x2 di confronto per TUTTE le VDC (SOLO FIT) salvato in: {os.path.basename(out_all_png)}")

    # -------------------------------------------------------------------------
    # 3. GRAFICO FISICO DEDICATO: SPRING SOFTENING E AMPIEZZA vs VDC
    # -------------------------------------------------------------------------
    vdc_arr = np.array([r['vdc'] for r in fits])
    f0_arr = np.array([r['f0'] for r in fits])
    A0_arr = np.array([r['A0'] for r in fits])
    vdc_sq = vdc_arr ** 2

    fig_phys, (ax_p1, ax_p2) = plt.subplots(1, 2, figsize=(13.5, 5.5))
    fig_phys.suptitle("Proprieta Elettromeccaniche del Risonatore MEMS vs Polarizzazione V_DC", fontsize=13, fontweight='bold')

    # Fit parabolico / lineare su Vdc^2 per spring softening (su tensioni significative > 1V)
    valid_mask = vdc_arr >= 1.0
    if np.sum(valid_mask) >= 3:
        p_soft = np.polyfit(vdc_sq[valid_mask], f0_arr[valid_mask], 1)
        v_fit = np.linspace(0, 5, 200)
        f_soft_fit = p_soft[1] + p_soft[0] * (v_fit ** 2)
        ax_p1.plot(v_fit, f_soft_fit, '--', color='#d32f2f', lw=1.8, label=f'Spring Softening: $\\Delta f_0 / V_{{DC}}^2 = {p_soft[0]:.2f}$ Hz/V$^2$')

    ax_p1.plot(vdc_arr, f0_arr, 'o-', color='#1f77b4', lw=2.2, markersize=7, label='f0 dal Fit BVD')
    ax_p1.set_xlabel('Tensione di Polarizzazione $V_{DC}$ [V]', fontweight='bold')
    ax_p1.set_ylabel('Frequenza di Risonanza Meccanica $f_0$ [Hz]', fontweight='bold')
    ax_p1.set_title('(a) Sintonia Elettrostatica: Spring Softening $f_0(V_{DC})$', fontweight='bold')
    ax_p1.grid(True, linestyle=':', alpha=0.5)
    ax_p1.legend(loc='best')

    # Fit quadratico per A0 vs Vdc^2
    p_a0 = np.polyfit(vdc_sq, A0_arr, 1)
    a0_fit = p_a0[1] + p_a0[0] * (v_fit ** 2)
    ax_p2.plot(vdc_arr, A0_arr, 's-', color='#2ca02c', lw=2.2, markersize=7, label='A0 dal Fit BVD')
    ax_p2.plot(v_fit, a0_fit, '--', color='#1b5e20', lw=1.8, label=f'Crescita Quadratica: $A_0 \\propto V_{{DC}}^2$')
    ax_p2.set_xlabel('Tensione di Polarizzazione $V_{DC}$ [V]', fontweight='bold')
    ax_p2.set_ylabel('Guadagno Motionale di Picco $A_0$ [V/V]', fontweight='bold')
    ax_p2.set_title('(b) Accoppiamento Elettromeccanico: Ampiezza $A_0(V_{DC})$', fontweight='bold')
    ax_p2.grid(True, linestyle=':', alpha=0.5)
    ax_p2.legend(loc='best')

    plt.tight_layout()
    out_phys_png = os.path.join(session_dir, "spring_softening_e_accoppiamento_vs_vdc.png")
    fig_phys.savefig(out_phys_png, dpi=300)
    plt.close(fig_phys)
    print(f" -> [OK] Grafico fisico Spring Softening e Ampiezza salvato in: {os.path.basename(out_phys_png)}")

    # -------------------------------------------------------------------------
    # 4. GRAFICO STANDARD BODE 2x1: MODULO [dB] E FASE [deg] (SOLO FIT)
    # -------------------------------------------------------------------------
    fig_bode, (bx1, bx2) = plt.subplots(2, 1, figsize=(11, 8), sharex=True)
    fig_bode.suptitle("Diagramma di Bode Sperimentale (Fit BVD) al Variare di V_DC (0V -> 5V)", fontsize=13, fontweight='bold')

    for i, res in enumerate(fits):
        c = colors[i % len(colors)]
        g_db = 20.0 * np.log10(np.maximum(1e-6, res['gain_fit_fine']))
        bx1.plot(res['f_fine'] / 1e3, g_db, '-', color=c, lw=2.2, label=f"V_DC = {res['vdc']:.0f} V")
        bx2.plot(res['f_fine'] / 1e3, res['phase_fit_fine'], '-', color=c, lw=2.2, label=f"V_DC = {res['vdc']:.0f} V")

    bx1.set_ylabel('Guadagno |H| [dB]', fontweight='bold')
    bx1.set_title('Modulo di Guadagno [dB]', fontweight='bold')
    bx1.grid(True, linestyle=':', alpha=0.5)
    bx1.legend(loc='best', framealpha=0.92)

    bx2.set_xlabel('Frequenza [kHz]', fontweight='bold')
    bx2.set_ylabel('Sfasamento [°]', fontweight='bold')
    bx2.set_title('Sfasamento di Fase [°]', fontweight='bold')
    bx2.grid(True, linestyle=':', alpha=0.5)
    bx2.legend(loc='best', framealpha=0.92)

    plt.tight_layout()
    out_bode_png = os.path.join(session_dir, "bode_modulo_fase_standard_confronto_fit.png")
    fig_bode.savefig(out_bode_png, dpi=300)
    plt.close(fig_bode)
    print(f" -> [OK] Diagramma di Bode standard (dB + deg) salvato in: {os.path.basename(out_bode_png)}")

    # -------------------------------------------------------------------------
    # TABELLA RIASSUNTIVA FINALE STAMPATA A SCHERMO
    # -------------------------------------------------------------------------
    print("\n" + "=" * 90)
    print(f"{'V_DC [V]':>8} | {'f0 [Hz]':>11} | {'Q [-]':>8} | {'Delta f [Hz]':>12} | {'A0 [V/V]':>10} | {'theta [deg]':>11} | {'Cp [pF]':>8}")
    print("=" * 90)
    for r in fits:
        print(f"{r['vdc']:8.1f} | {r['f0']:11.2f} | {r['Q']:8.1f} | {r['delta_f_3db']:12.1f} | {r['A0']:10.4f} | {np.degrees(r['theta']):11.1f} | {r['Cp_pf']:8.3f}")
    print("=" * 90)

if __name__ == '__main__':
    target_dir = r"c:\Users\lucaa\Downloads\ESM2 - Copia\ES2M\Laboratorio_MEMS\sessione_DC_20260908_130623"
    processa_sessione(target_dir)

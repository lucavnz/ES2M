"""
Analisi Sperimentale del Softening Elettrostatico e Risposta in Frequenza/Ampiezza
Dispositivo: Risonatore Capacitivo ad Arco MEMS (DIE D4)
Parametri di misura:
  - Frequenza eccitazione f_in = 417850 Hz (costante)
  - Ampiezza eccitazione Vin = 100 mVpp (piccolo segnale, regime lineare)
  - Tensione DC variabile: Vdc = 3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0 V
  - Burst: 2500 cicli sinusoidali, Tg = 12 ms, duty 50%
  - Misure: scope_39.csv ... scope_45.csv in Frequenza_Vdc/Misure/
Autore: Antigravity Assistant & Luca
"""

import os
import csv
import glob
import numpy as np
import scipy.signal as signal
from scipy.optimize import curve_fit
import matplotlib.pyplot as plt

# -----------------------------------------------------------------------------
# CONFIGURAZIONE STILE GRAFICI ACCADEMICI
# -----------------------------------------------------------------------------
plt.rcParams.update({
    'font.family': 'sans-serif',
    'font.size': 10,
    'axes.labelsize': 11,
    'axes.titlesize': 12,
    'xtick.labelsize': 10,
    'ytick.labelsize': 10,
    'legend.fontsize': 9,
    'figure.titlesize': 13,
    'lines.linewidth': 1.8,
    'grid.alpha': 0.45,
    'grid.linestyle': ':'
})

# Mappatura file di misura -> Tensione DC [V]
VDC_MAP = {
    39: 3.0,
    40: 3.5,
    41: 4.0,
    42: 4.5,
    43: 5.0,
    44: 5.5,
    45: 6.0
}

F_IN = 417850.0  # Hz

def lorentzian(f, A_max, f0, gamma, offset):
    """Modello Lorentziano per la curva di risonanza."""
    return A_max * (0.5 * gamma)**2 / ((f - f0)**2 + (0.5 * gamma)**2) + offset

def exp_decay_func(t, A0, tau):
    """Modello puro decadimento esponenziale: A(t) = A0 * exp(-t / tau)"""
    return A0 * np.exp(-t / tau)

def process_file(filepath, vdc_val):
    """
    Elabora un singolo file CSV dell'oscilloscopio.
    """
    with open(filepath, 'r') as fp:
        reader = csv.reader(fp)
        next(reader)  # Intestazione canali
        next(reader)  # Intestazione unita
        rows = [[float(x) for x in r[:4]] for r in reader if len(r) >= 4 and r[1] != '']

    data = np.array(rows)
    t_raw = data[:, 0]
    c1 = data[:, 1]  # Vout TIA
    c2 = data[:, 2]  # Gate burst
    c3 = data[:, 3]  # Vin

    # Passo di campionamento esatto
    dt = np.polyfit(np.arange(len(t_raw)), t_raw, 1)[0]
    fs_sample = 1.0 / dt

    # Individuazione fronte di discesa del gate (spegnimento eccitazione)
    gate_low_idx = np.where(c2 < 1.0)[0]
    if len(gate_low_idx) == 0:
        raise ValueError(f"Fronte di discesa gate non trovato in {filepath}")
    idx_off = gate_low_idx[0]
    t_off = t_raw[idx_off]

    # Blanking iniziale: 30 us (circa 240 campioni a 8 MHz) per eliminare saturazione e transitori
    blank_samples = int(30e-6 * fs_sample)
    idx_start = idx_off + blank_samples

    t_rd = t_raw[idx_start:] - t_off
    y_raw = c1[idx_start:]
    y_ac = y_raw - np.mean(y_raw)

    # 1. Estrazione frequenza di risonanza fs(Vdc) con FFT zero-padded (2^21) e interpolazione parabolica
    n_pad = 2**21
    freqs = np.fft.rfftfreq(n_pad, d=dt)
    fft_mag = np.abs(np.fft.rfft(y_ac, n=n_pad))

    # Maschera spettrale attorno a 417-419 kHz
    mask = (freqs >= 415000) & (freqs <= 421000)
    idx_peak = np.where(mask)[0][np.argmax(fft_mag[mask])]

    # Interpolazione parabolica 3 punti
    alpha = fft_mag[idx_peak - 1]
    beta = fft_mag[idx_peak]
    gamma = fft_mag[idx_peak + 1]
    delta_p = 0.5 * (alpha - gamma) / (alpha - 2.0 * beta + gamma)
    f_res = freqs[idx_peak] + delta_p * (freqs[1] - freqs[0])

    # 2. Inviluppo analitico con Trasformata di Hilbert + filtraggio passa-basso
    analytic = signal.hilbert(y_ac)
    env_raw = np.abs(analytic)
    b_lp, a_lp = signal.butter(2, 5000.0 / (fs_sample / 2.0))
    env_filt = signal.filtfilt(b_lp, a_lp, env_raw)

    # 3. Fit esponenziale su env_filt estrapolato a t_rd = 0
    popt, _ = curve_fit(exp_decay_func, t_rd, env_filt, p0=[env_filt[0], 0.0024], bounds=([0.0, 0.0005], [0.5, 0.010]))
    A0_fit, tau_fit = popt

    # R^2 del fit
    fit_vals = exp_decay_func(t_rd, *popt)
    ss_res = np.sum((env_filt - fit_vals)**2)
    ss_tot = np.sum((env_filt - np.mean(env_filt))**2)
    r2 = 1.0 - (ss_res / ss_tot)

    Q_factor = np.pi * f_res * tau_fit
    delta_f = F_IN - f_res  # Detuning rispetto a f_in
    A0_norm = (A0_fit * 1e3) / (vdc_val**2)  # Normalizzazione per accoppiamento Vdc^2 [mV / V^2]

    return {
        'vdc': vdc_val,
        'f_res': f_res,
        'delta_f': delta_f,
        'A0_mV': A0_fit * 1e3,
        'A0_norm': A0_norm,
        'tau_ms': tau_fit * 1e3,
        'Q': Q_factor,
        'r2': r2,
        't_off': t_off,
        't_rd_ms': t_rd * 1e3,
        'y_ac_mV': y_ac * 1e3,
        'env_mV': env_filt * 1e3,
        'fit_mV': fit_vals * 1e3
    }

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    misure_dir = os.path.join(base_dir, 'Misure')
    
    csv_files = sorted(glob.glob(os.path.join(misure_dir, 'scope_*.csv')))
    if not csv_files:
        raise FileNotFoundError(f"Nessun file trovato in {misure_dir}")

    results = []
    print("=" * 80)
    print(f"ANALISI SOFTENING ELETTROSTATICO: f_in = {F_IN} Hz, Vin = 100 mVpp")
    print("=" * 80)

    for fpath in csv_files:
        filename = os.path.basename(fpath)
        num = int(filename.replace('scope_', '').replace('.csv', ''))
        if num not in VDC_MAP:
            continue
        vdc_val = VDC_MAP[num]
        res = process_file(fpath, vdc_val)
        res['file_num'] = num
        results.append(res)
        print(f"[{filename}] Vdc = {vdc_val:3.1f} V | f_res = {res['f_res']:9.2f} Hz | "
              f"df = {res['delta_f']:+6.1f} Hz | A0 = {res['A0_mV']:5.2f} mV | "
              f"A0/Vdc^2 = {res['A0_norm']:5.2f} | tau = {res['tau_ms']:4.2f} ms | Q = {res['Q']:4.0f} | R^2 = {res['r2']:.5f}")

    # Ordina per Vdc crescente
    results.sort(key=lambda r: r['vdc'])

    # -------------------------------------------------------------------------
    # 1. SALVATAGGIO TABELLA RISULTATI CSV
    # -------------------------------------------------------------------------
    tabella_path = os.path.join(base_dir, 'tabella_risultati_softening.csv')
    with open(tabella_path, 'w', newline='', encoding='utf-8') as fp:
        writer = csv.writer(fp)
        writer.writerow([
            'File', 'Vdc_V', 'Vdc2_V2', 'f_in_Hz', 'f_res_Hz', 'Delta_f_Hz',
            'A0_mV', 'A0_norm_mV_V2', 'tau_ms', 'Q_factor', 'R2_exp_fit'
        ])
        for r in results:
            writer.writerow([
                f"scope_{r['file_num']}.csv",
                f"{r['vdc']:.2f}",
                f"{r['vdc']**2:.2f}",
                f"{F_IN:.1f}",
                f"{r['f_res']:.2f}",
                f"{r['delta_f']:.2f}",
                f"{r['A0_mV']:.2f}",
                f"{r['A0_norm']:.3f}",
                f"{r['tau_ms']:.3f}",
                f"{r['Q']:.0f}",
                f"{r['r2']:.6f}"
            ])
    print(f"\nTabella salvata: {tabella_path}")

    # Estrazione vettori per regressioni
    vdc_arr = np.array([r['vdc'] for r in results])
    vdc2_arr = vdc_arr**2
    f_res_arr = np.array([r['f_res'] for r in results])
    f_res2_arr = f_res_arr**2
    A0_arr = np.array([r['A0_mV'] for r in results])
    A0_norm_arr = np.array([r['A0_norm'] for r in results])
    df_arr = np.array([r['delta_f'] for r in results])
    tau_arr = np.array([r['tau_ms'] for r in results])
    Q_arr = np.array([r['Q'] for r in results])

    # -------------------------------------------------------------------------
    # FIT DEL SOFTENING ELETTROSTATICO: f_res^2 = f01^2 - m * Vdc^2
    # -------------------------------------------------------------------------
    poly_soft = np.polyfit(vdc2_arr, f_res2_arr, 1)
    m_slope = -poly_soft[0]
    f01_sq = poly_soft[1]
    f01_mech = np.sqrt(f01_sq)

    # R^2 fit softening
    f_res2_pred = np.polyval(poly_soft, vdc2_arr)
    r2_soft = 1.0 - np.sum((f_res2_arr - f_res2_pred)**2) / np.sum((f_res2_arr - np.mean(f_res2_arr))**2)

    # Coefficiente c1,DD:
    # omega_1^2 = omega_01^2 - c1_DD * Vdc^2
    # (2*pi*f_res)^2 = (2*pi*f01)^2 - (2*pi)^2 * m * Vdc^2
    # c1_DD = (2*pi)^2 * m
    c1_DD_SI = (2.0 * np.pi)**2 * m_slope  # rad^2 / (s^2 * V^2)
    c1_DD_paper = c1_DD_SI * 1e-12          # rad^2 / (us^2 * V^2)

    # Stima pulsazione naturale meccanica
    omega01_mech = 2.0 * np.pi * f01_mech
    c1_beta_SI = omega01_mech**2
    c1_beta_paper = c1_beta_SI * 1e-12

    print("\n" + "=" * 80)
    print("PARAMETRI FISICI IDENTIFICATI DAL MODELLO:")
    print(f"  Frequenza Meccanica a riposo (Vdc = 0): f01 = {f01_mech:.2f} Hz (~ {f01_mech/1e3:.3f} kHz)")
    print(f"  Rigidezza elastica modale c1_beta: {c1_beta_paper:.4f} us^-2 (Valore paper Frangi: 6.85 us^-2)")
    print(f"  Pendenza softening m: {m_slope:.2e} Hz^2 / V^2")
    print(f"  Coefficiente softening c1_DD: {c1_DD_paper:.6f} us^-2 / V^2 (SI: {c1_DD_SI:.4e} s^-2/V^2)")
    print(f"  Bontà di fit R^2 della legge quadratica: {r2_soft:.6f}")
    print("=" * 80)

    # -------------------------------------------------------------------------
    # GRAFICO 1: LEGGE DI SOFTENING ELETTROSTATICO (f_res^2 vs Vdc^2 e f_res vs Vdc)
    # -------------------------------------------------------------------------
    fig1, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))

    # Pannello A: f_res^2 vs Vdc^2 (Teoricamente una retta esatta)
    v2_dense = np.linspace(0, 40, 200)
    f2_dense_pred = f01_sq - m_slope * v2_dense

    ax1.plot(vdc2_arr, f_res2_arr * 1e-10, 'o', color='#2980b9', markersize=6.5,
             label='Dati', zorder=5)
    ax1.plot(v2_dense, f2_dense_pred * 1e-10, '-', color='#c0392b', linewidth=2.0,
             label='Fit lineare')

    ax1.set_xlabel(r'$V_{\mathrm{DC}}^2$ [$\mathrm{V}^2$]')
    ax1.set_ylabel(r'$f_1^2$ [$10^{10}\ \mathrm{Hz}^2$]')
    ax1.set_title(r'$f_1^2$ vs $V_{\mathrm{DC}}^2$')
    ax1.grid(True)
    ax1.legend(framealpha=0.95)
    ax1.set_xlim([0, 38])

    # Pannello B: f_res vs Vdc (Curva parabolica reale)
    v_dense = np.linspace(0, 6.5, 200)
    f_dense_pred = np.sqrt(np.maximum(0, f01_sq - m_slope * (v_dense**2)))

    ax2.plot(vdc_arr, f_res_arr, 's', color='#27ae60', markersize=6.5,
             label='Dati', zorder=5)
    ax2.plot(v_dense, f_dense_pred, '-', color='#e67e22', linewidth=2.0,
             label='Fit lineare')

    # Calcolo incrocio per uso nei grafici successivi
    vdc_cross = np.sqrt((f01_sq - F_IN**2) / m_slope)

    ax2.set_xlabel(r'$V_{\mathrm{DC}}$ [V]')
    ax2.set_ylabel(r'$f_1$ [Hz]')
    ax2.set_title(r'$f_1$ vs $V_{\mathrm{DC}}$')
    ax2.grid(True)
    ax2.legend(framealpha=0.95)
    ax2.set_xlim([0, 6.5])
    ax2.set_ylim([417700, 418050])

    plt.tight_layout()
    fig1_path = os.path.join(base_dir, 'softening_legge_quadratica.png')
    plt.savefig(fig1_path, dpi=300)
    plt.close()
    print(f"Grafico 1 salvato: {fig1_path}")

    # -------------------------------------------------------------------------
    # GRAFICO 2: RISPOSTA IN AMPIEZZA (A0 vs Vdc E CAMPANA LORENTZIANA vs Delta_f)
    # -------------------------------------------------------------------------
    fig2, (ax2a, ax2b) = plt.subplots(1, 2, figsize=(14, 5.5))

    # Pannello A: Ampiezza grezza A0 vs Vdc (compresenza di guadagno Vdc^2 e sintonizzazione)
    ax2a.plot(vdc_arr, A0_arr, 'o-', color='#34495e', markersize=8, linewidth=2.0,
              label=r'Ampiezza $A_0$ Misurata [mV]')
    ax2a.axvline(vdc_cross, color='#e74c3c', linestyle=':', linewidth=2,
                 label=rf'Vertice di Sintonia: $V_{{\mathrm{{DC}}}} \approx {vdc_cross:.2f}\,\mathrm{{V}}$')
    ax2a.annotate(rf'Picco Massimo: $A_0 = {np.max(A0_arr):.1f}\,\mathrm{{mV}}$' + '\n' +
                  r'(a $V_{\mathrm{DC}} = 5.5\,\mathrm{V}$)',
                  xy=(5.5, np.max(A0_arr)), xytext=(4.0, 48),
                  arrowprops=dict(facecolor='black', shrink=0.08, width=1, headwidth=6),
                  fontsize=9.5, fontweight='bold',
                  bbox=dict(boxstyle="round,pad=0.3", fc="#ecf0f1", ec="#7f8c8d", lw=1))

    ax2a.set_xlabel(r'$Tensione\ Continua\ V_{\mathrm{DC}}\ [\mathrm{V}]$', fontweight='bold')
    ax2a.set_ylabel(r'Ampiezza Iniziale Ringdown $A_0\ [\mathrm{mV}]$', fontweight='bold')
    ax2a.set_title(r'Evoluzione Ampiezza $A_0(V_{\mathrm{DC}})$: Guadagno Elettromeccanico vs Detuning', fontweight='bold')
    ax2a.grid(True)
    ax2a.legend(framealpha=0.9, loc='upper left')

    # Pannello B: Ampiezza Normalizzata A0 / Vdc^2 vs Delta f (Campana pura Lorentziana)
    # Fit Lorentziano su A0_norm vs df
    df_dense = np.linspace(np.min(df_arr) - 30, np.max(df_arr) + 30, 200)
    p0_lor = [np.max(A0_norm_arr), 0.0, 130.0, 0.0]
    popt_lor, _ = curve_fit(lorentzian, df_arr, A0_norm_arr, p0=p0_lor)
    A_max_lor, df0_lor, gamma_lor, off_lor = popt_lor

    ax2b.plot(df_arr, A0_norm_arr, 'd', color='#d35400', markersize=8,
              label=r'Dati Normalizzati $A_0 / V_{\mathrm{DC}}^2$', zorder=5)
    ax2b.plot(df_dense, lorentzian(df_dense, *popt_lor), '-', color='#2980b9', linewidth=2.2,
              label=rf'Fit Lorentziano ($Q_{{\mathrm{{eff}}}} \approx {F_IN/gamma_lor:.0f}, \Delta f_0 = {df0_lor:+.1f}\,\mathrm{{Hz}}$)')

    ax2b.axvline(0, color='gray', linestyle='--', linewidth=1.2, label=r'Risonanza Perfetta ($\Delta f = 0$)')
    ax2b.axhline(A_max_lor / np.sqrt(2), color='#16a085', linestyle=':', linewidth=1.5,
                 label=rf'Livello -3 dB ($\mathrm{{FWHM}} \approx {gamma_lor:.0f}\,\mathrm{{Hz}}$)')

    ax2b.set_xlabel(r'Detuning $\Delta f = f_{\mathrm{in}} - f_1(V_{\mathrm{DC}})\ [\mathrm{Hz}]$', fontweight='bold')
    ax2b.set_ylabel(r'Ampiezza Meccanica Pura $A_0 / V_{\mathrm{DC}}^2\ [\mathrm{mV}/\mathrm{V}^2]$', fontweight='bold')
    ax2b.set_title(r'Curva di Risonanza Meccanica Ricostruita Sfruttando il Softening', fontweight='bold')
    ax2b.grid(True)
    ax2b.legend(framealpha=0.9, loc='upper right')

    fig2.suptitle(r'Scomposizione della Risposta: $A_0(V_{\mathrm{DC}}) \propto V_{\mathrm{DC}}^2 \cdot |H(f_{\mathrm{in}} - f_1(V_{\mathrm{DC}}))|$',
                  fontsize=13, fontweight='bold', y=1.00)
    plt.tight_layout()
    fig2_path = os.path.join(base_dir, 'risposta_ampiezza_vs_vdc_e_deltaf.png')
    plt.savefig(fig2_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Grafico 2 salvato: {fig2_path}")

    # -------------------------------------------------------------------------
    # GRAFICO 3: GALLERIA COMPARATIVA DEI SEGNALI TEMPORALI E INVILUPPI
    # -------------------------------------------------------------------------
    fig3, axes = plt.subplots(3, 2, figsize=(15, 12), sharex=True, sharey=True)
    selected_indices = [0, 1, 2, 4, 5, 6]  # 3V, 3.5V, 4V, 5V, 5.5V, 6V

    for ax, idx in zip(axes.flatten(), selected_indices):
        r = results[idx]
        t_ms = r['t_rd_ms']
        y_mV = r['y_ac_mV']
        env_mV = r['env_mV']
        fit_mV = r['fit_mV']

        ax.plot(t_ms, y_mV, color='#bdc3c7', alpha=0.6, linewidth=0.6, label='Segnale Oscilloscopio')
        ax.plot(t_ms, env_mV, color='#e67e22', linewidth=1.8, label='Inviluppo di Hilbert')
        ax.plot(t_ms, fit_mV, color='#c0392b', linestyle='--', linewidth=2.0,
                label=rf'Fit: $A_0 = {r["A0_mV"]:.1f}\,\mathrm{{mV}},\,\tau = {r["tau_ms"]:.2f}\,\mathrm{{ms}}$')

        ax.set_title(rf"$V_{{\mathrm{{DC}}}} = {r['vdc']:.1f}\,\mathrm{{V}}$ "
                     rf"($f_1 = {r['f_res']:.1f}\,\mathrm{{Hz}},\,\Delta f = {r['delta_f']:+.1f}\,\mathrm{{Hz}}$)",
                     fontweight='bold', fontsize=10.5)
        ax.set_xlabel('Tempo dal taglio del Gate [ms]', fontweight='bold')
        ax.set_ylabel('Uscita TIA [mV]', fontweight='bold')
        ax.grid(True)
        ax.legend(loc='upper right', framealpha=0.9, fontsize=8.5)
        ax.set_xlim([0, 1.95])
        ax.set_ylim([-55, 55])

    fig3.suptitle(r'Confronto Segnali di Ringdown al Variare di $V_{\mathrm{DC}}$ ($3.0\,\mathrm{V} \to 6.0\,\mathrm{V}$)' + '\n' +
                  r'(Crescita dell\'Ampiezza per Accoppiamento e Sintonizzazione, Stessa Costante di Tempo $\tau \approx 2.3\,\mathrm{ms}$)',
                  fontsize=13, fontweight='bold', y=0.99)
    plt.tight_layout()
    fig3_path = os.path.join(base_dir, 'gallery_ringdown_vdc.png')
    plt.savefig(fig3_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Grafico 3 salvato: {fig3_path}")

    # -------------------------------------------------------------------------
    # GRAFICO 4: COSTANZA DI TAU E FATTORE DI QUALITA' Q (VALIDAZIONE LINEARE)
    # -------------------------------------------------------------------------
    fig4, (ax4a, ax4b) = plt.subplots(1, 2, figsize=(13, 5))

    ax4a.plot(vdc_arr, tau_arr, 's-', color='#8e44ad', markersize=8, linewidth=2)
    ax4a.axhline(np.mean(tau_arr), color='red', linestyle='--', linewidth=1.5,
                 label=rf'Media $\tau = {np.mean(tau_arr):.2f}\,\mathrm{{ms}}$')
    ax4a.set_xlabel(r'$V_{\mathrm{DC}}\ [\mathrm{V}]$', fontweight='bold')
    ax4a.set_ylabel(r'Costante di Tempo $\tau\ [\mathrm{ms}]$', fontweight='bold')
    ax4a.set_title(r'Invarianza dello Smorzamento Naturale $\tau$', fontweight='bold')
    ax4a.grid(True)
    ax4a.legend(framealpha=0.9)
    ax4a.set_ylim([1.8, 3.0])

    ax4b.plot(vdc_arr, Q_arr, 'o-', color='#16a085', markersize=8, linewidth=2)
    ax4b.axhline(np.mean(Q_arr), color='red', linestyle='--', linewidth=1.5,
                 label=rf'Media $Q = {np.mean(Q_arr):.0f}$ (Teorico: $2800 \div 3310$)')
    ax4b.set_xlabel(r'$V_{\mathrm{DC}}\ [\mathrm{V}]$', fontweight='bold')
    ax4b.set_ylabel(r'Fattore di Merito Meccanico $Q$', fontweight='bold')
    ax4b.set_title(r'Fattore di Qualità Meccanico vs $V_{\mathrm{DC}}$', fontweight='bold')
    ax4b.grid(True)
    ax4b.legend(framealpha=0.9)
    ax4b.set_ylim([2700, 3700])

    fig4.suptitle('Conferma del Regime Lineare: Indipendenza dei Parametri Dissipativi dalla Tensione di Bias',
                  fontsize=13, fontweight='bold', y=1.00)
    plt.tight_layout()
    fig4_path = os.path.join(base_dir, 'stabilita_tau_e_Q.png')
    plt.savefig(fig4_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Grafico 4 salvato: {fig4_path}")

if __name__ == '__main__':
    main()

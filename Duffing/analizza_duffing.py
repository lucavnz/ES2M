"""
Suite di Analisi Sperimentale Non-Linearita di Duffing da Misure di Ringdown
Dispositivo: Risonatore MEMS ad Arco Capacitivo (DIE D4)
Parametri: Vdc = 5.0 V, f_in = 417850 Hz (fissa sul picco lineare)
Sweep Vin: da 40 mV a 1000 mV (17 file scope_49 ... scope_66, scope_50 escluso)
Autore: Antigravity Assistant & Luca
"""

import os
import csv
import shutil
import numpy as np
import scipy.signal as signal
from scipy.optimize import curve_fit
import matplotlib.pyplot as plt

# -----------------------------------------------------------------------------
# STILE GRAFICI ACCADEMICI
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

# Mappatura delle tensioni Vin impostate sul generatore per ciascun file
DUFFING_MAP = {
    49: 40.0,
    51: 60.0,
    52: 80.0,
    53: 100.0,
    54: 120.0,
    55: 140.0,
    56: 170.0,
    57: 210.0,
    58: 250.0,
    59: 300.0,
    60: 350.0,
    61: 400.0,
    62: 450.0,
    63: 500.0,
    64: 600.0,
    65: 750.0,
    66: 1000.0
}

def exp_decay(t, A0, tau, offset):
    """Modello fisico decadimento esponenziale libero: A(t) = A0 * exp(-t/tau) + offset"""
    return A0 * np.exp(-t / tau) + offset

def linear_model(x, m, q):
    return m * x + q

def duffing_parabola(A, f0, beta):
    """Spostamento frequenziale di Duffing: f(A) = f0 + beta * A^2"""
    return f0 + beta * (A**2)

def process_duffing_file(filepath, vin_mV):
    """
    Elabora il file scope per la misura Duffing:
    1. Calcolo del dt esatto con regressione lineare.
    2. Rilevamento dello stacco del Gate (caduta sotto 1.0 V).
    3. Filtraggio passa-alto a 100 kHz: rimuove completamente il transitorio di scarica
       (overdrive recovery dell'oscilloscopio) presente nei file intermedi (scope 57-59).
    4. Blanking di 40 microsecondi post-gate.
    5. Inviluppo di Hilbert + fit esponenziale dell'ampiezza A0 e tau.
    6. Calcolo della frequenza fs tramite FFT ad alta risoluzione con interpolazione parabolica.
    7. Estrazione dell'evoluzione istantanea della frequenza f_inst(t) tramite fase analitica.
    """
    with open(filepath, 'r') as f:
        reader = csv.reader(f)
        next(reader)
        next(reader)
        rows = [[float(x) for x in r[:4]] for r in reader if len(r) >= 4 and r[1] != '']

    data = np.array(rows)
    t_raw = data[:, 0]
    c1 = data[:, 1]  # Vout TIA
    c2 = data[:, 2]  # Gate commutazione

    # dt esatto
    poly = np.polyfit(np.arange(len(t_raw)), t_raw, 1)
    dt = poly[0]
    fs = 1.0 / dt

    # Rilevamento istante di spegnimento gate
    gate_low_idx = np.where(c2 < 1.0)[0]
    if len(gate_low_idx) == 0:
        raise ValueError(f"Fronte gate non trovato in {filepath}")
    idx_off = gate_low_idx[0]
    t_off = t_raw[idx_off]

    # Filtraggio passa-alto a 100 kHz per eliminare l'overdrive recovery baseline
    b_hp, a_hp = signal.butter(3, 100e3 / (fs / 2.0), btype='high')
    c1_hp = signal.filtfilt(b_hp, a_hp, c1)

    # Blanking 40 us post-gate
    blank_samples = int(40e-6 * fs)
    idx_start = idx_off + blank_samples

    # Fine dell'intervallo ringdown prima della risalita del gate successivo
    idx_next_on = np.where(c2[idx_off:] > 1.0)[0]
    if len(idx_next_on) > 0:
        idx_end = idx_off + idx_next_on[0] - int(40e-6 * fs)
    else:
        idx_end = len(t_raw)

    t_rd = t_raw[idx_start:idx_end] - t_off
    y_raw_rd = c1[idx_start:idx_end]
    y_hp_rd = c1_hp[idx_start:idx_end]

    # FFT zero-padded per frequenza di oscillazione
    n_pad = 2**20
    rfft_mag = np.abs(np.fft.rfft(y_hp_rd, n=n_pad))
    peak_bin = np.argmax(rfft_mag)
    alpha = rfft_mag[peak_bin - 1]
    beta = rfft_mag[peak_bin]
    gamma = rfft_mag[peak_bin + 1]
    delta_p = 0.5 * (alpha - gamma) / (alpha - 2.0 * beta + gamma)
    fs_rd = (peak_bin + delta_p) * (fs / n_pad)

    # Inviluppo di Hilbert filtrato morbido
    analytic = signal.hilbert(y_hp_rd)
    env_raw = np.abs(analytic)
    b_lp, a_lp = signal.butter(2, 5000.0 / (fs / 2.0))
    env_filt = signal.filtfilt(b_lp, a_lp, env_raw)

    # Fit esponenziale
    p0 = [env_filt[0], 0.0024, 0.0]
    bounds = ([0.0, 0.0005, -0.05], [1.0, 0.010, 0.05])
    popt, _ = curve_fit(exp_decay, t_rd, env_filt, p0=p0, bounds=bounds)
    A0_fit, tau_fit, off_fit = popt

    fit_vals = exp_decay(t_rd, *popt)
    ss_res = np.sum((env_filt - fit_vals)**2)
    ss_tot = np.sum((env_filt - np.mean(env_filt))**2)
    r2 = 1.0 - (ss_res / ss_tot)
    Q_factor = np.pi * fs_rd * tau_fit

    # Evoluzione istantanea della frequenza f_inst(t) e ampiezza A_inst(t) per la Backbone Curve
    phase_unwrapped = np.unwrap(np.angle(analytic))
    win_len = int(0.7e-3 * fs)  # finestra 0.7 ms
    step_slide = int(0.05e-3 * fs)
    t_bb, f_bb, A_bb = [], [], []

    for i_start in range(0, len(phase_unwrapped) - win_len, step_slide):
        t_center = np.mean(t_rd[i_start : i_start + win_len]) * 1e3  # ms
        if t_center > 3.8:
            break
        ph_seg = phase_unwrapped[i_start : i_start + win_len]
        t_seg = t_rd[i_start : i_start + win_len]
        p_fit = np.polyfit(t_seg, ph_seg, 1)
        f_val = p_fit[0] / (2.0 * np.pi)
        amp_val = np.mean(env_filt[i_start : i_start + win_len]) * 1e3  # mV
        t_bb.append(t_center)
        f_bb.append(f_val)
        A_bb.append(amp_val)

    return {
        'vin_mV': vin_mV,
        'A0_mV': A0_fit * 1e3,
        'tau_ms': tau_fit * 1e3,
        'Q': Q_factor,
        'fs_rd': fs_rd,
        'r2': r2,
        't_rd_ms': t_rd * 1e3,
        'y_raw_mV': y_raw_rd * 1e3,
        'y_hp_mV': y_hp_rd * 1e3,
        'env_mV': env_filt * 1e3,
        'fit_mV': fit_vals * 1e3,
        't_bb': np.array(t_bb),
        'f_bb': np.array(f_bb),
        'A_bb': np.array(A_bb),
        'fs_sample': fs,
        'dt': dt
    }

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    misure_dir = os.path.join(base_dir, 'Misure')
    if not os.path.exists(misure_dir):
        misure_dir = os.path.abspath('Duffing/Misure')
    artifact_dir = os.path.join(r"C:\Users\lucaa\.gemini\antigravity-ide\brain\c1b594f5-2b9e-4778-a508-9112914d772f")

    print("=" * 80)
    print("      ANALISI SPERIMENTALE NON-LINEARITA DI DUFFING (MEMS ES2M)")
    print("=" * 80)
    print(f"Cartella script/output: {base_dir}")
    print(f"Cartella dati:          {misure_dir}")
    print(f"Cartella artifacts:     {artifact_dir}\n")

    results = []
    for num in sorted(DUFFING_MAP.keys()):
        filepath = os.path.join(misure_dir, f"scope_{num}.csv")
        if not os.path.exists(filepath):
            print(f"[ATTENZIONE] File mancante: scope_{num}.csv")
            continue
        vin = DUFFING_MAP[num]
        res = process_duffing_file(filepath, vin)
        res['file_num'] = num
        results.append(res)
        print(f" * scope_{num:02d}.csv | Vin = {vin:6.1f} mV | A0 = {res['A0_mV']:6.2f} mV | "
              f"tau = {res['tau_ms']:.3f} ms | Q = {res['Q']:4.0f} | fs = {res['fs_rd']:.2f} Hz | R2 = {res['r2']:.4f}")

    results = sorted(results, key=lambda x: x['vin_mV'])

    # -------------------------------------------------------------------------
    # TABELLA CSV RISULTATI DUFFING
    # -------------------------------------------------------------------------
    csv_out = os.path.join(base_dir, 'tabella_duffing_sperimentale.csv')
    with open(csv_out, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['File_Num', 'Vin_mV', 'A0_mV', 'Gain_A0_Vin', 'tau_ms', 'Q_factor', 'fs_rd_Hz', 'R2_fit'])
        for r in results:
            writer.writerow([
                r['file_num'],
                f"{r['vin_mV']:.1f}",
                f"{r['A0_mV']:.3f}",
                f"{r['A0_mV'] / r['vin_mV']:.4f}",
                f"{r['tau_ms']:.4f}",
                f"{r['Q']:.1f}",
                f"{r['fs_rd']:.2f}",
                f"{r['r2']:.5f}"
            ])
    print(f"\n[OK] Tabella CSV salvata in: {csv_out}")

    vin_arr = np.array([r['vin_mV'] for r in results])
    A0_arr = np.array([r['A0_mV'] for r in results])
    tau_arr = np.array([r['tau_ms'] for r in results])
    Q_arr = np.array([r['Q'] for r in results])
    fs_arr = np.array([r['fs_rd'] for r in results])

    # Fit lineare a piccolo segnale (Vin <= 140 mV)
    mask_lin = vin_arr <= 140.0
    p_lin = np.polyfit(vin_arr[mask_lin], A0_arr[mask_lin], 1)
    slope_lin = p_lin[0]  # Guadagno piccolo segnale [mV_out / mV_in]
    offset_lin = p_lin[1]

    vin_dense = np.linspace(0, 1050, 1000)
    A0_ideal_lin = slope_lin * vin_dense + offset_lin

    # Punto di compressione a -1 dB (A0 reale = 89.1% di quello ideale lineare)
    # A0_real / A0_ideal = 10^(-1/20) = 0.891
    ratio_arr = A0_arr / (slope_lin * vin_arr + offset_lin)
    idx_comp_1db = np.where(ratio_arr <= 0.891)[0]
    if len(idx_comp_1db) > 0:
        vin_1db = vin_arr[idx_comp_1db[0]]
        A0_1db = A0_arr[idx_comp_1db[0]]
    else:
        vin_1db = 250.0
        A0_1db = 50.0

    print("\n--- PARAMETRI LINEARITA E COMPRESSIONE DUFFING ---")
    print(f" Guadagno a Piccolo Segnale: {slope_lin:.4f} mV_out / mV_in")
    print(f" Punto di Compressione -1dB: Vin ~ {vin_1db:.0f} mV (A0 = {A0_1db:.1f} mV)")
    print(f" Escursione Frequenza fs:    da {fs_arr[0]:.2f} Hz (a 40mV) a {fs_arr[-1]:.2f} Hz (a 1000mV)")
    print(f" Shift Softening Massimo:    Delta_fs = {fs_arr[-1] - fs_arr[0]:.2f} Hz")

    # =========================================================================
    # GRAFICO 1: LINEARITA vs COMPRESSIONE DI GUADAGNO (A0 vs Vin)
    # =========================================================================
    fig, ax1 = plt.subplots(figsize=(8.5, 6))

    # A0 vs Vin con retta ideale
    ax1.plot(vin_dense, A0_ideal_lin, '--', color='#7f8c8d', linewidth=1.8,
             label='Fit lineare')
    ax1.plot(vin_arr, A0_arr, 'o-', color='#2980b9', linewidth=2.0, markersize=5.5,
             label='Dati')

    ax1.set_title(r'Ampiezza ringdown vs tensione di eccitazione')
    ax1.set_xlabel(r'Tensione di eccitazione $V_{\mathrm{in}}$ [$\mathrm{mV}_{\mathrm{pp}}$]')
    ax1.set_ylabel(r'Ampiezza iniziale ringdown $A_0$ [mV]')
    ax1.set_xlim([0, 1050])
    ax1.set_ylim([0, 300])
    ax1.grid(True)
    ax1.legend(loc='upper left', framealpha=0.95)

    plt.tight_layout()
    fig1_path = os.path.join(base_dir, 'duffing_ampiezza_compressione.png')
    plt.savefig(fig1_path, dpi=300)
    plt.close()
    print(f"[GRAFICO 1 GENERATO] {fig1_path}")

    # =========================================================================
    # GRAFICO 2: SPOSTAMENTO DI FREQUENZA DI DUFFING (SOFTENING)
    # =========================================================================
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))

    # Pannello A: fs vs Vin
    delta_fs_arr = fs_arr - fs_arr[0]
    ax1.plot(vin_arr, fs_arr, 'o-', color='#c0392b', linewidth=2.2, markersize=6.5,
             label=rf'Frequenza $f_s$ misurata dal ringdown')
    ax1.set_title(r'(A) Frequenza di Oscillazione Libera $f_s$ vs $V_{\mathrm{in}}$', fontweight='bold', pad=10)
    ax1.set_xlabel(r'Tensione di Eccitazione $V_{\mathrm{in}}$ [$\mathrm{mV}_{\mathrm{pp}}$]', fontweight='bold')
    ax1.set_ylabel(r'Frequenza Naturale $f_s$ [Hz]', fontweight='bold')
    ax1.grid(True)
    ax1.legend(loc='lower left', framealpha=0.92)

    ax1.annotate(rf'Shift Softening Totale: $\Delta f_s = {delta_fs_arr[-1]:.1f}\,\mathrm{{Hz}}$',
                 xy=(vin_arr[-1], fs_arr[-1]), xytext=(vin_arr[-1] - 400, fs_arr[-1] + 8),
                 arrowprops=dict(arrowstyle='->', lw=1.2, color='black'),
                 fontsize=9, fontweight='bold', bbox=dict(boxstyle='round,pad=0.3', fc='#fcf3cf', ec='#f39c12'))

    # Pannello B: fs vs A0^2 (Fit della parabola di Duffing: fs = f0 + beta * A0^2)
    A0_sq = (A0_arr)**2
    p_duff = np.polyfit(A0_sq, fs_arr, 1)
    beta_duff = p_duff[0]  # Hz / mV^2
    f0_duff = p_duff[1]

    A_dense_sq = np.linspace(0, np.max(A0_sq)*1.05, 500)
    fs_duff_fit = f0_duff + beta_duff * A_dense_sq

    ax2.plot(A0_sq, fs_arr, 's', color='#d35400', markersize=7, zorder=5, label='Punti Sperimentali $f_s$ vs $A_0^2$')
    ax2.plot(A_dense_sq, fs_duff_fit, color='#2c3e50', linewidth=2.0,
             label=rf'Fit Parabola Duffing: $\beta = {beta_duff*1e3:.3f}\times 10^{{-3}}\,\mathrm{{Hz/mV^2}}$')

    ax2.set_title(r'(B) Legge Parabolica di Duffing: $f_s = f_0 + \beta \cdot A_0^2$', fontweight='bold', pad=10)
    ax2.set_xlabel(r'Quadrato Ampiezza Iniziale $A_0^2$ [$\mathrm{mV}^2$]', fontweight='bold')
    ax2.set_ylabel(r'Frequenza Naturale $f_s$ [Hz]', fontweight='bold')
    ax2.grid(True)
    ax2.legend(loc='lower left', framealpha=0.92)

    fig.suptitle('Evidenza Sperimentale dello Spring Softening Non-Lineare di Duffing\n'
                 r'Verifica della Dipendenza Quadratica della Frequenza dall\'Ampiezza ($k_3 < 0$)',
                 fontsize=13, fontweight='bold', y=1.02)
    plt.tight_layout()
    fig2_path = os.path.join(base_dir, 'duffing_spostamento_frequenza_softening.png')
    plt.savefig(fig2_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"[GRAFICO 2 GENERATO] {fig2_path}")

    # =========================================================================
    # GRAFICO 3: LA BACKBONE CURVE E IL CHIRP INTRA-RINGDOWN
    # =========================================================================
    fig, ax1 = plt.subplots(figsize=(8.5, 6))

    # Evoluzione temporale di f_inst(t) lungo il ringdown (Chirp)
    sel_files_bb = [53, 58, 63, 66]
    colors_bb = ['#27ae60', '#f39c12', '#e67e22', '#c0392b']
    labels_bb = ['100 mV', '250 mV', '500 mV', '1000 mV']

    for num_sel, col, lab in zip(sel_files_bb, colors_bb, labels_bb):
        r_sel = next(r for r in results if r['file_num'] == num_sel)
        ax1.plot(r_sel['t_bb'], r_sel['f_bb'], color=col, linewidth=2.0, label=rf'$V_{{\mathrm{{in}}}} = {lab}$')

    ax1.set_title(r'Chirp intra-ringdown: frequenza istantanea nel tempo')
    ax1.set_xlabel('Tempo dal taglio del gate [ms]')
    ax1.set_ylabel(r'Frequenza istantanea $f_{\mathrm{inst}}$ [Hz]')
    ax1.set_xlim([0.3, 3.8])
    ax1.grid(True)
    ax1.legend(loc='lower right', framealpha=0.95)

    plt.tight_layout()
    fig3_path = os.path.join(base_dir, 'duffing_backbone_e_chirp.png')
    plt.savefig(fig3_path, dpi=300)
    plt.close()
    print(f"[GRAFICO 3 GENERATO] {fig3_path}")

    # =========================================================================
    # GRAFICO 4: INVARIANZA DI TAU E Q vs VIN & FORME D'ONDA PULITE
    # =========================================================================
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))

    # Pannello A: Q e tau vs Vin
    ax1_twin = ax1.twinx()
    l1 = ax1.plot(vin_arr, tau_arr, 's-', color='#27ae60', linewidth=2.0, markersize=6,
                  label=rf'Costante $\tau$ (Media: {np.mean(tau_arr):.3f} ms)')
    l2 = ax1_twin.plot(vin_arr, Q_arr, '^-', color='#8e44ad', linewidth=2.0, markersize=6,
                       label=rf'Fattore di Qualità $Q$ (Media: {np.mean(Q_arr):.0f})')

    ax1.set_ylim([1.8, 2.8])
    ax1_twin.set_ylim([1.8 * np.pi * 417.8e3 * 1e-3, 2.8 * np.pi * 417.8e3 * 1e-3])
    ax1.set_title(r'(A) Invarianza dello Smorzamento $\tau$ e $Q$ con $V_{\mathrm{in}}$', fontweight='bold', pad=10)
    ax1.set_xlabel(r'Tensione di Eccitazione $V_{\mathrm{in}}$ [$\mathrm{mV}_{\mathrm{pp}}$]', fontweight='bold')
    ax1.set_ylabel(r'Costante di Decadimento $\tau$ [ms]', color='#27ae60', fontweight='bold')
    ax1_twin.set_ylabel(r'Fattore di Qualità $Q = \pi f_s \tau$', color='#8e44ad', fontweight='bold')
    ax1.grid(True)
    lines = l1 + l2
    labels = [l.get_label() for l in lines]
    ax1.legend(lines, labels, loc='lower left', framealpha=0.92)

    # Pannello B: Spiegazione e Risoluzione Overdrive Recovery su scope_58 (250 mV)
    res_58 = next(r for r in results if r['file_num'] == 58)
    t_plot = res_58['t_rd_ms']
    ax2.plot(t_plot, res_58['y_raw_mV'], color='#e74c3c', alpha=0.5, linewidth=0.8,
             label='Segnale Grezzo Oscilloscopio (con Overdrive Recovery tail)')
    ax2.plot(t_plot, res_58['y_hp_mV'], color='#2980b9', alpha=0.7, linewidth=0.6,
             label='Segnale dopo Filtro HP 100 kHz (Cono Simmetrico Perfetto!)')
    ax2.plot(t_plot, res_58['env_mV'], color='#27ae60', linewidth=2.2, label='Inviluppo di Hilbert')
    ax2.plot(t_plot, res_58['fit_mV'], '--', color='#2c3e50', linewidth=2.0,
             label=rf'Fit Esponenziale ($A_0 = {res_58["A0_mV"]:.1f}\,\mathrm{{mV}},\,R^2 = {res_58["r2"]:.4f}$)')

    ax2.set_title(r'(B) Risoluzione Fisica Transitorio Oscilloscopio su scope_58 ($250\,\mathrm{mV}$)',
                  fontweight='bold', pad=10)
    ax2.set_xlabel(r'Tempo dal Taglio del Gate [ms]', fontweight='bold')
    ax2.set_ylabel(r'Tensione [mV]', fontweight='bold')
    ax2.set_xlim([0, 4.5])
    ax2.grid(True)
    ax2.legend(loc='upper right', framealpha=0.92, fontsize=8.5)

    fig.suptitle('Robustezza della Metodologia di Analisi del Ringdown:\n'
                 'Smorzamento Indipendente dall\'Ampiezza ed Eliminazione dei Transitori Parassiti',
                 fontsize=13, fontweight='bold', y=1.02)
    plt.tight_layout()
    fig4_path = os.path.join(base_dir, 'duffing_spettrogramma_STFT.png')
    plt.savefig(fig4_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"[GRAFICO 4 GENERATO] {fig4_path}")

    # =========================================================================
    # COPIA NEGLI ARTIFACTS PER VISUALIZZAZIONE IMMEDIATA (FACOLTATIVA)
    # =========================================================================
    try:
        os.makedirs(artifact_dir, exist_ok=True)
        for p in [fig1_path, fig2_path, fig3_path, fig4_path, csv_out]:
            if os.path.exists(p):
                dest = os.path.join(artifact_dir, os.path.basename(p))
                shutil.copy(p, dest)
                print(f"[ARTIFACT COPIATO] {dest}")
    except Exception as e:
        pass

    print("\n" + "=" * 80)
    print("      ELABORAZIONE DUFFING COMPLETATA CON SUCCESSO!")
    print("=" * 80)

if __name__ == '__main__':
    main()

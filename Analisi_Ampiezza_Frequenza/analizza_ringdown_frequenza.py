"""
Analisi Sperimentale Risposta in Frequenza del Ringdown (MEMS ad Arco)
Dispositivo: MEMS Capacitivo ad Arco (DIE D4)
Parametri: Vin = 100 mVpp, Vdc = 5.0 V, Burst = 2500 cicli, Tg = 12 ms
Autore: Antigravity Assistant & Luca
"""

import os
import csv
import glob
import shutil
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

# Mappatura accurata frequenze impostate sul generatore per ciascun file di misura
FILE_FREQ_MAP = {
    5: 417830.0,
    6: 417820.0,
    7: 417810.0,
    8: 417800.0,
    9: 417790.0,
    10: 417780.0,
    11: 417770.0,
    12: 417760.0,
    13: 417710.0,
    14: 417660.0,
    15: 417560.0,
    16: 417460.0,
    17: 417260.0,
    18: 417840.0,
    19: 417850.0,
    20: 417860.0,
    21: 417870.0,
    22: 417880.0,
    23: 417890.0,
    24: 417900.0,
    25: 417950.0,
    26: 418000.0,
    27: 418100.0,
    28: 418200.0,
    29: 418400.0
}

def exp_decay(t, A0, tau, offset):
    """Modello fisico decadimento esponenziale libero: A(t) = A0 * exp(-t/tau) + offset"""
    return A0 * np.exp(-t / tau) + offset

def lorentzian(f, A_max, f0, gamma, offset):
    """Modello Lorentziano per la curva di risonanza in ampiezza."""
    return A_max * (0.5 * gamma)**2 / ((f - f0)**2 + (0.5 * gamma)**2) + offset

def process_single_scope_file(filepath, f_in):
    """
    Carica ed elabora il file CSV dell'oscilloscopio.
    Implementa:
    1. Calcolo del dt esatto con regressione lineare per eliminare l'errore di arrotondamento CSV.
    2. Rilevamento istante di spegnimento gate.
    3. Blanking di 30 microsecondi per scartare il transitorio di commutazione e l'uscita dalla saturazione.
    4. Estrazione di fs con FFT ad altissima risoluzione e interpolazione parabolica dei 3 punti di picco.
    5. Inviluppo analitico con Trasformata di Hilbert + filtraggio passa-basso morbido.
    6. Fit esponenziale per estrarre A0 a t = t_off e tau.
    """
    with open(filepath, 'r') as f:
        reader = csv.reader(f)
        next(reader)  # Intestazione nomi canali
        next(reader)  # Intestazione unita di misura
        rows = [[float(x) for x in r[:4]] for r in reader if len(r) >= 4 and r[1] != '']

    data = np.array(rows)
    t_raw = data[:, 0]
    c1 = data[:, 1]  # Vout TIA (tensione proporzionale al moto)
    c2 = data[:, 2]  # Gate commutazione burst
    c3 = data[:, 3]  # Vin generatore

    # Calcolo esatto del passo di campionamento (dt = 2.937500e-7 s)
    poly = np.polyfit(np.arange(len(t_raw)), t_raw, 1)
    dt = poly[0]
    fs = 1.0 / dt

    # 1. Individuazione istante di spegnimento Gate (fronte di discesa sotto 1.0 V)
    gate_low_idx = np.where(c2 < 1.0)[0]
    if len(gate_low_idx) == 0:
        raise ValueError(f"Fronte di discesa gate non trovato in {filepath}")
    idx_off = gate_low_idx[0]
    t_off = t_raw[idx_off]

    # 2. Blanking iniziale: 30 us (circa 100 campioni, ~12 periodi sinusoidali)
    blank_samples = int(30e-6 * fs)
    idx_start = idx_off + blank_samples

    # Segmento pulito di oscillazione libera
    t_rd = t_raw[idx_start:] - t_off  # Tempo relativo all'istante di spegnimento del gate
    y_raw = c1[idx_start:]
    y_ac = y_raw - np.mean(y_raw)     # Rimozione offset DC

    # 3. Frequenza di risonanza libera fs tramite FFT zero-padded e interpolazione parabolica
    n_pad = 2**20
    rfft_mag = np.abs(np.fft.rfft(y_ac, n=n_pad))
    peak_bin = np.argmax(rfft_mag)
    alpha = rfft_mag[peak_bin - 1]
    beta = rfft_mag[peak_bin]
    gamma = rfft_mag[peak_bin + 1]
    delta_p = 0.5 * (alpha - gamma) / (alpha - 2.0 * beta + gamma)
    fs_rd = (peak_bin + delta_p) * (fs / n_pad)

    # 4. Inviluppo analitico con Trasformata di Hilbert
    analytic = signal.hilbert(y_ac)
    env_raw = np.abs(analytic)
    # Filtro passa-basso di Bessel/Butterworth del 2° ordine a 5 kHz per eliminare il ripple carrier
    b_lp, a_lp = signal.butter(2, 5000.0 / (fs / 2.0))
    env_filt = signal.filtfilt(b_lp, a_lp, env_raw)

    # 5. Fit esponenziale dell'inviluppo estrapolato a t_rd = 0 (cioe t = t_off)
    p0 = [env_filt[0], 0.0024, 0.0]
    bounds = ([0.0, 0.0005, -0.05], [0.5, 0.010, 0.05])
    popt, _ = curve_fit(exp_decay, t_rd, env_filt, p0=p0, bounds=bounds)
    A0_fit, tau_fit, offset_fit = popt

    # Valutazione bontà di fit R^2
    fit_vals = exp_decay(t_rd, *popt)
    ss_res = np.sum((env_filt - fit_vals)**2)
    ss_tot = np.sum((env_filt - np.mean(env_filt))**2)
    r2 = 1.0 - (ss_res / ss_tot)

    # Parametri fisici derivati
    Q_factor = np.pi * fs_rd * tau_fit
    delta_f = f_in - fs_rd

    # Calcolo valore RMS su primo 1 ms di oscillazione libera
    mask_1ms = (t_rd >= 0.0) & (t_rd <= 1.0e-3)
    A_rms_1ms = np.sqrt(np.mean(y_ac[mask_1ms]**2))

    return {
        'f_in': f_in,
        'fs_rd': fs_rd,
        'delta_f': delta_f,
        'A0_mV': A0_fit * 1e3,
        'tau_ms': tau_fit * 1e3,
        'Q': Q_factor,
        'R2': r2,
        'A_rms_mV': A_rms_1ms * 1e3,
        'offset_mV': offset_fit * 1e3,
        't_rd_ms': t_rd * 1e3,
        'y_ac_mV': y_ac * 1e3,
        'env_mV': env_filt * 1e3,
        'fit_mV': fit_vals * 1e3,
        't_off': t_off,
        't_raw': t_raw,
        'c1_mV': c1 * 1e3,
        'c2': c2,
        'fs_sample': fs,
        'dt': dt
    }

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    misure_dir = os.path.join(base_dir, 'Misure')
    if not os.path.exists(misure_dir):
        misure_dir = os.path.join(base_dir, '..', 'Misure')
    if not os.path.exists(misure_dir):
        misure_dir = os.path.abspath('Misure')
    misure_dir = os.path.abspath(misure_dir)

    artifact_dir = os.path.join(r"C:\Users\lucaa\.gemini\antigravity-ide\brain\09561dde-e0ac-4dd9-b854-cf70ef8ce3ac")
    
    print("=" * 80)
    print("      ELABORAZIONE SPERIMENTALE RISPOSTA IN FREQUENZA DEL RINGDOWN")
    print("=" * 80)
    print(f"Cartella script/output: {base_dir}")
    print(f"Cartella dati (Misure): {misure_dir}")
    print(f"Cartella artifacts:     {artifact_dir}\n")

    results = []
    for num in sorted(FILE_FREQ_MAP.keys()):
        filepath = os.path.join(misure_dir, f"scope_{num}.csv")
        if not os.path.exists(filepath):
            print(f"[ATTENZIONE] File non trovato: scope_{num}.csv")
            continue
        f_in = FILE_FREQ_MAP[num]
        res = process_single_scope_file(filepath, f_in)
        res['file_num'] = num
        results.append(res)
        print(f" * File scope_{num:<2}.csv | f_in = {f_in:8.1f} Hz | fs = {res['fs_rd']:8.2f} Hz | "
              f"df = {res['delta_f']:+6.1f} Hz | A0 = {res['A0_mV']:5.2f} mV | tau = {res['tau_ms']:.3f} ms | "
              f"Q = {res['Q']:4.0f} | R2 = {res['R2']:.4f}")

    # Ordina per frequenza di eccitazione f_in crescente
    results_by_freq = sorted(results, key=lambda x: x['f_in'])

    # -------------------------------------------------------------------------
    # SALVATAGGIO TABELLA CSV DEI RISULTATI
    # -------------------------------------------------------------------------
    csv_path = os.path.join(base_dir, 'tabella_risultati_ringdown.csv')
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            'File_Num', 'f_in_Hz', 'fs_rd_Hz', 'delta_f_Hz',
            'A0_mV', 'tau_ms', 'Q_factor', 'R2_fit', 'A_rms_1ms_mV', 'offset_mV'
        ])
        for r in results_by_freq:
            writer.writerow([
                r['file_num'],
                f"{r['f_in']:.1f}",
                f"{r['fs_rd']:.2f}",
                f"{r['delta_f']:.2f}",
                f"{r['A0_mV']:.3f}",
                f"{r['tau_ms']:.4f}",
                f"{r['Q']:.1f}",
                f"{r['R2']:.5f}",
                f"{r['A_rms_mV']:.3f}",
                f"{r['offset_mV']:.3f}"
            ])
    print(f"\n[OK] Tabella CSV salvata in: {csv_path}")

    # Estrazione array per i grafici
    f_in_arr = np.array([r['f_in'] for r in results_by_freq])
    fs_rd_arr = np.array([r['fs_rd'] for r in results_by_freq])
    delta_f_arr = np.array([r['delta_f'] for r in results_by_freq])
    A0_arr = np.array([r['A0_mV'] for r in results_by_freq])
    tau_arr = np.array([r['tau_ms'] for r in results_by_freq])
    Q_arr = np.array([r['Q'] for r in results_by_freq])

    mean_fs = np.mean(fs_rd_arr)
    std_fs = np.std(fs_rd_arr)
    mean_tau = np.mean(tau_arr)
    std_tau = np.std(tau_arr)
    mean_Q = np.mean(Q_arr)
    std_Q = np.std(Q_arr)

    # -------------------------------------------------------------------------
    # FIT LORENTZIANO SULLA RISPOSTA IN FREQUENZA
    # -------------------------------------------------------------------------
    p0_lor = [np.max(A0_arr), mean_fs, 130.0, 3.0]
    popt_lor, _ = curve_fit(lorentzian, f_in_arr, A0_arr, p0=p0_lor,
                            bounds=([10.0, 417800.0, 20.0, 0.0], [60.0, 417900.0, 400.0, 10.0]))
    A_max_fit, f_res_fit, gamma_fit, offset_lor = popt_lor
    Q_from_fwhm = f_res_fit / gamma_fit

    f_dense = np.linspace(np.min(f_in_arr) - 50, np.max(f_in_arr) + 50, 1000)
    A0_dense_lor = lorentzian(f_dense, *popt_lor)

    print("\n--- PARAMETRI DI RISONANZA ESTRATTI DAL FIT LORENTZIANO ---")
    print(f" Ampiezza Picco A_max:     {A_max_fit:.2f} mV (offset di fondo: {offset_lor:.2f} mV)")
    print(f" Frequenza Picco Forzato:  {f_res_fit:.2f} Hz")
    print(f" Larghezza Banda FWHM:     {gamma_fit:.2f} Hz")
    print(f" Q dal Dominio Frequenza:  {Q_from_fwhm:.0f}")
    print(f" fs Media dal Ringdown:    {mean_fs:.2f} +/- {std_fs:.2f} Hz")
    print(f" tau Medio dal Ringdown:   {mean_tau:.3f} +/- {std_tau:.3f} ms")
    print(f" Q Medio dal Tempo:        {mean_Q:.0f} +/- {std_Q:.0f}")

    # =========================================================================
    # GRAFICO 1: CAMPANA DI RISONANZA A0 vs f_in e A0 vs Δ(f_in - fs)
    # =========================================================================
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5.5))

    # Pannello 1: A0 vs f_in (Stile Bode grezzo: punti dello stesso colore del fit, niente bold, niente -3dB)
    ax1.plot(f_in_arr / 1e3, A0_arr, 'o', color='#1f77b4', markersize=5.5, label='Dati')
    ax1.plot(f_dense / 1e3, A0_dense_lor, '-', color='#1f77b4', lw=2.0, label='Fit')
    ax1.set_title(r'Campana di risonanza con $f_{\mathrm{in}}$')
    ax1.set_xlabel(r'Frequenza $f_{\mathrm{in}}$ [kHz]')
    ax1.set_ylabel(r'Ampiezza decadimento $A_0$ [mV]')
    ax1.set_ylim([0, 42])
    ax1.grid(True)
    ax1.legend(loc='upper right', framealpha=0.95)

    # Pannello 2: A0 vs Δf = f_in - fs
    delta_dense = f_dense - mean_fs
    ax2.plot(delta_f_arr, A0_arr, 'o', color='#1f77b4', markersize=5.5, label='Dati')
    ax2.plot(delta_dense, A0_dense_lor, '-', color='#1f77b4', lw=2.0, label='Fit')
    ax2.set_title(r'Campana di risonanza con $\Delta f = f_{\mathrm{in}} - f_s$')
    ax2.set_xlabel(r'Scostamento in frequenza $\Delta f$ [Hz]')
    ax2.set_ylabel(r'Ampiezza decadimento $A_0$ [mV]')
    ax2.set_ylim([0, 42])
    ax2.grid(True)
    ax2.legend(loc='upper right', framealpha=0.95)

    fig.tight_layout()
    fig1_path = os.path.join(base_dir, 'campana_risonanza_A0_vs_freq.png')
    fig.savefig(fig1_path, dpi=300)
    plt.close(fig)
    print(f"[GRAFICO 1 GENERATO] {fig1_path}")

    # =========================================================================
    # GRAFICO 2: DERIVA TEMPORALE fs ED INVARIANZA DI τ E Q
    # =========================================================================
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8), sharex=True)

    # Ordina cronologicamente in base al numero del file
    results_chrono = sorted(results, key=lambda x: x['file_num'])
    chrono_nums = np.array([r['file_num'] for r in results_chrono])
    chrono_fs = np.array([r['fs_rd'] for r in results_chrono])
    chrono_tau = np.array([r['tau_ms'] for r in results_chrono])
    chrono_Q = np.array([r['Q'] for r in results_chrono])

    # Pannello Superiore: Deriva di fs
    ax1.plot(range(len(chrono_nums)), chrono_fs, 'o-', color='#2c3e50', linewidth=1.6, markersize=6)
    ax1.axhline(mean_fs, color='#e74c3c', linestyle='--', linewidth=1.8,
                label=rf'Frequenza Naturale Media $\bar{{f}}_s = {mean_fs:.2f}$ Hz ($\sigma = \pm {std_fs:.2f}$ Hz)')
    ax1.fill_between(range(len(chrono_nums)), mean_fs - std_fs, mean_fs + std_fs,
                     color='#e74c3c', alpha=0.15, label=r'Intervallo di confidenza $\pm 1\sigma$')
    ax1.set_ylabel(r'Frequenza Naturale $f_s$ [Hz]', fontweight='bold')
    ax1.set_title(r'Verifica Deriva Termica di $f_s$ durante la Sequenza di Misura (Deriva totale $\approx 8$ Hz)',
                  fontweight='bold', pad=10)
    ax1.grid(True)
    ax1.legend(loc='lower left', framealpha=0.92)

    # Pannello Inferiore: Invarianza di tau e Q
    ax2_twin = ax2.twinx()
    l1 = ax2.plot(range(len(chrono_nums)), chrono_tau, 's-', color='#27ae60', linewidth=1.6, markersize=5.5,
                  label=rf'Costante $\tau$ (Media: ${mean_tau:.3f} \pm {std_tau:.3f}$ ms)')
    l2 = ax2_twin.plot(range(len(chrono_nums)), chrono_Q, '^-', color='#8e44ad', linewidth=1.6, markersize=5.5,
                       label=rf'Fattore di Qualità $Q$ (Media: ${mean_Q:.0f} \pm {std_Q:.0f}$)')

    tau_min, tau_max = 1.5, 2.9
    ax2.set_ylim([tau_min, tau_max])
    ax2_twin.set_ylim([tau_min * np.pi * mean_fs * 1e-3, tau_max * np.pi * mean_fs * 1e-3])

    ax2.set_ylabel(r'Costante di Decadimento $\tau$ [ms]', color='#27ae60', fontweight='bold')
    ax2_twin.set_ylabel(r'Fattore di Qualità $Q = \pi f_s \tau$', color='#8e44ad', fontweight='bold')
    ax2.set_xlabel(r'Sequenza Cronologica File di Misura', fontweight='bold')
    ax2.set_xticks(range(len(chrono_nums)))
    ax2.set_xticklabels([f"scope_{n}" for n in chrono_nums], rotation=45, ha='right')
    ax2.grid(True)

    lines = l1 + l2
    labels = [l.get_label() for l in lines]
    ax2.legend(lines, labels, loc='lower left', framealpha=0.92)
    ax2.set_title(r'Invarianza di $\tau$ e $Q$ rispetto alla Frequenza di Eccitazione (Proprietà Intrinseca Dissipativa)',
                  fontweight='bold', pad=10)

    fig.suptitle('Stabilità Strumentale e Robustezza dell\'Estrapolazione Esponenziale del Ringdown',
                 fontsize=13, fontweight='bold', y=1.02)
    plt.tight_layout()
    fig2_path = os.path.join(base_dir, 'deriva_frequenza_e_tau.png')
    plt.savefig(fig2_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"[GRAFICO 2 GENERATO] {fig2_path}")

    # =========================================================================
    # GRAFICO 3: GALLERIA COMPARATIVA FORME D'ONDA ED INVILUPPI
    # =========================================================================
    fig, axes = plt.subplots(2, 2, figsize=(14, 8), sharex=True, sharey=True)
    selected_files = [17, 13, 19, 29]

    for ax, num in zip(axes.flatten(), selected_files):
        res_sel = next(r for r in results if r['file_num'] == num)
        t_ms = res_sel['t_rd_ms']
        y_mV = res_sel['y_ac_mV']
        env_mV = res_sel['env_mV']
        fit_mV = res_sel['fit_mV']

        ax.plot(t_ms, y_mV, color='#bdc3c7', alpha=0.6, linewidth=0.6)
        ax.plot(t_ms, env_mV, color='#e67e22', linewidth=1.8)
        ax.plot(t_ms, fit_mV, color='#c0392b', linestyle='--', linewidth=2.0)

        ax.grid(True)
        ax.set_xlim([0, 4.5])
        ax.set_ylim([-45, 45])

    # Etichette assi senza bold sui bordi esterni
    for ax in axes[-1, :]:
        ax.set_xlabel('Tempo dal taglio del gate [ms]')
    for ax in axes[:, 0]:
        ax.set_ylabel('Uscita TIA [mV]')

    fig.suptitle("Esempi ringdown e fit dell'inviluppo", fontsize=13)
    fig.tight_layout()
    fig.subplots_adjust(top=0.93)
    fig3_path = os.path.join(base_dir, 'gallery_inviluppi_ringdown.png')
    fig.savefig(fig3_path, dpi=300)
    plt.close(fig)
    print(f"[GRAFICO 3 GENERATO] {fig3_path}")

    # =========================================================================
    # GRAFICO 4: ANALISI DUFFING INTRA-RINGDOWN SUL PICCO (SCOPE_19)
    # =========================================================================
    res_peak = next(r for r in results if r['file_num'] == 19)
    t_rd_sec = res_peak['t_rd_ms'] * 1e-3
    y_ac_peak = res_peak['y_ac_mV'] * 1e-3  # Volt
    fs_sample = res_peak['fs_sample']

    # Calcolo dell'evoluzione istantanea della frequenza tramite derivata della fase analitica di Hilbert
    z_peak = signal.hilbert(y_ac_peak)
    phase_unwrapped = np.unwrap(np.angle(z_peak))

    win_len = int(0.8e-3 * fs_sample)  # Finestra di 0.8 ms (~330 cicli)
    step_slide = int(0.05e-3 * fs_sample)  # Passo di scorrimento 50 us
    t_phase_centers = []
    f_phase_inst = []

    for i_start in range(0, len(phase_unwrapped) - win_len, step_slide):
        t_c = np.mean(t_rd_sec[i_start : i_start + win_len]) * 1e3  # ms
        if t_c > 3.7:
            break  # Interrompi prima della soglia di rumore di fondo
        ph_seg = phase_unwrapped[i_start : i_start + win_len]
        t_seg = t_rd_sec[i_start : i_start + win_len]
        # Regressione lineare: dphi/dt = 2*pi*f
        p_fit = np.polyfit(t_seg, ph_seg, 1)
        f_val = p_fit[0] / (2.0 * np.pi)
        t_phase_centers.append(t_c)
        f_phase_inst.append(f_val)

    t_phase_centers = np.array(t_phase_centers)
    f_phase_inst = np.array(f_phase_inst)

    fig, (ax_top, ax_mid, ax_bot) = plt.subplots(3, 1, figsize=(14, 9), sharex=True)

    # 1. Forma d'onda e inviluppo
    ax_top.plot(res_peak['t_rd_ms'], res_peak['y_ac_mV'], color='#bdc3c7', linewidth=0.6, alpha=0.7, label='Segnale $V_{\\mathrm{out}}$')
    ax_top.plot(res_peak['t_rd_ms'], res_peak['env_mV'], color='#c0392b', linewidth=2.0, label='Inviluppo Decadimento')
    ax_top.set_ylabel(r'$V_{\mathrm{out}}$ [mV]', fontweight='bold')
    ax_top.set_title(r'Decadimento Libero al Vertice della Risonanza (scope_19, $f_{\mathrm{in}} = 417850$ Hz)', fontweight='bold', pad=8)
    ax_top.grid(True)
    ax_top.legend(loc='upper right', framealpha=0.9)

    # 2. Spettrogramma STFT
    f_spec, t_spec, Sxx = signal.spectrogram(y_ac_peak, fs=fs_sample,
                                             window='hann', nperseg=1024, noverlap=800,
                                             nfft=4096, scaling='density')
    mask_band = (f_spec >= 415e3) & (f_spec <= 421e3)
    t_spec_ms = t_spec * 1e3
    Sxx_log = 10 * np.log10(Sxx[mask_band, :] + 1e-18)
    im = ax_mid.pcolormesh(t_spec_ms, f_spec[mask_band] / 1e3, Sxx_log, cmap='viridis', shading='gouraud')
    cbar = plt.colorbar(im, ax=ax_mid, pad=0.015)
    cbar.set_label(r'PSD [dB/Hz]', fontweight='bold')
    ax_mid.set_ylabel(r'Frequenza [kHz]', fontweight='bold')
    ax_mid.set_title(r'Spettrogramma STFT: Concentrazione Energetica Rigorosa Attorno ad $f_s \approx 417.85$ kHz', fontweight='bold', pad=8)

    # 3. Evoluzione della frequenza istantanea vs tempo
    ax_bot.plot(t_phase_centers, f_phase_inst, 'o-', color='#8e44ad', linewidth=2.0, markersize=3.5,
                label=rf'Frequenza istantanea da fase analitica $\frac{{1}}{{2\pi}}\frac{{\mathrm{{d}}\phi}}{{\mathrm{{d}}t}}$')
    ax_bot.axhline(res_peak['fs_rd'], color='#2c3e50', linestyle='--', linewidth=1.5,
                   label=rf'Frequenza globale dal fit $f_s = {res_peak["fs_rd"]:.2f}$ Hz')

    ax_bot.set_ylabel(r'$f_{\mathrm{inst}}$ [Hz]', fontweight='bold')
    ax_bot.set_xlabel('Tempo dal taglio del Gate [ms]', fontweight='bold')
    ax_bot.set_title(r'Verifica Non-Linearità Duffing Intra-Ringdown ($\Delta f_{\mathrm{intra}} \approx 10$ Hz su 417.8 kHz, deviazione $< 0.003\%$)',
                     fontweight='bold', pad=8)
    ax_bot.set_ylim([res_peak['fs_rd'] - 20, res_peak['fs_rd'] + 20])
    ax_bot.set_xlim([0, 4.5])
    ax_bot.grid(True)
    ax_bot.legend(loc='lower right', framealpha=0.9)

    # Annotazione Duffing
    ax_bot.annotate(r'Softening elettrostatico a grande ampiezza ($A_0 \approx 37$ mV): shift iniziale di $\approx -10$ Hz',
                    xy=(t_phase_centers[0], f_phase_inst[0]), xytext=(t_phase_centers[0] + 0.3, f_phase_inst[0] - 7),
                    arrowprops=dict(arrowstyle='->', lw=1.2, color='black'),
                    fontsize=8.5, bbox=dict(boxstyle='round,pad=0.3', fc='#fcf3cf', ec='#f39c12'))

    fig.suptitle('Analisi di Stabilità Spettrale Intra-Ringdown al Picco di Risonanza\n'
                 r'Conferma del Regime Prevalentemente Lineare a $V_{\mathrm{in}} = 100\,\mathrm{mV}_{\mathrm{pp}}$',
                 fontsize=13, fontweight='bold', y=0.99)
    plt.tight_layout()
    fig4_path = os.path.join(base_dir, 'analisi_duffing_intra_ringdown.png')
    plt.savefig(fig4_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"[GRAFICO 4 GENERATO] {fig4_path}")

    # =========================================================================
    # COPIA DEI GRAFICI NELLA DIRECTORY ARTIFACTS PER VISUALIZZAZIONE DIRETTA
    # =========================================================================
    os.makedirs(artifact_dir, exist_ok=True)
    for p in [fig1_path, fig2_path, fig3_path, fig4_path, csv_path]:
        dest = os.path.join(artifact_dir, os.path.basename(p))
        shutil.copy(p, dest)
        print(f"[COPIATO IN ARTIFACTS] {dest}")

    print("\n" + "=" * 80)
    print("      ELABORAZIONE COMPLETATA CON SUCCESSO!")
    print("=" * 80)

if __name__ == '__main__':
    main()

"""
Suite di Analisi Completa Misure Ringdown vs Frequenza (MEMS ES2M)
Autore: Antigravity Assistant & Luca
Cartella: Ampiezza-frequenza
"""

import os
import csv
import glob
import numpy as np
import scipy.signal as signal
from scipy.optimize import curve_fit
import matplotlib.pyplot as plt

# Configurazione stile grafici accademici
plt.rcParams.update({
    'font.family': 'sans-serif',
    'font.size': 10,
    'axes.labelsize': 11,
    'axes.titlesize': 12,
    'xtick.labelsize': 10,
    'ytick.labelsize': 10,
    'legend.fontsize': 9,
    'figure.titlesize': 14,
    'lines.linewidth': 1.8,
    'grid.alpha': 0.5,
    'grid.linestyle': ':'
})

# Mappatura corretta delle frequenze impostate dal generatore per ciascun file
# (corretto il refuso di digitazione 147820 -> 417820 e 147810 -> 417810)
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
    """Modello fisico di decadimento esponenziale dell'inviluppo."""
    return A0 * np.exp(-t / tau) + offset

def lorentzian(f, A_max, f0, gamma, offset):
    """Modello risonanza di Lorentz (gamma = FWHM)."""
    return A_max * (0.5 * gamma)**2 / ((f - f0)**2 + (0.5 * gamma)**2) + offset

def process_single_scope_file(filepath, f_in):
    """
    Legge un singolo file CSV dell'oscilloscopio ed estrae tutti i parametri fisici.
    """
    with open(filepath, 'r') as f:
        reader = csv.reader(f)
        next(reader)  # Header 1
        next(reader)  # Header 2
        rows = [[float(x) for x in r[:4]] for r in reader if len(r) >= 4 and r[1] != '']
        
    data = np.array(rows)
    t = data[:, 0]
    c1 = data[:, 1]  # Vout (TIA)
    c2 = data[:, 2]  # Gate (onda quadra 0-2.5V)
    c3 = data[:, 3]  # Vin (eccitazione forzata)
    
    dt = t[1] - t[0]
    fs = 1.0 / dt
    
    # 1. Rilevamento istante di stacco Gate (soglia 1.0 V sul fronte di discesa)
    gate_low_idx = np.where(c2 < 1.0)[0]
    if len(gate_low_idx) == 0:
        raise ValueError(f"Fronte di gate non trovato in {filepath}")
    idx_off = gate_low_idx[0]
    t_off = t[idx_off]
    
    # 2. Blanking iniziale (30 microsecondi per eliminare il picco di scarica di Cp)
    blank_samples = int(30e-6 * fs)
    idx_start = idx_off + blank_samples
    
    # Segmento pulito di ringdown
    t_rd = t[idx_start:] - t_off
    y_rd = c1[idx_start:]
    y_ac = y_rd - np.mean(y_rd)
    
    # 3. Frequenza naturale f0 nel ringdown tramite FFT ad alta risoluzione
    n_pad = 2**18
    rfft_mag = np.abs(np.fft.rfft(y_ac, n=n_pad))
    rfft_freqs = np.fft.rfftfreq(n_pad, dt)
    peak_bin = np.argmax(rfft_mag)
    # Interpolazione parabolica dei 3 punti attorno al picco per precisione sub-Hz
    alpha = rfft_mag[peak_bin - 1]
    beta = rfft_mag[peak_bin]
    gamma = rfft_mag[peak_bin + 1]
    delta_p = 0.5 * (alpha - gamma) / (alpha - 2*beta + gamma)
    f0_rd = (peak_bin + delta_p) * (fs / n_pad)
    
    # 4. Inviluppo di Hilbert + filtro passa-basso morbido anti-ondulazione
    analytic = signal.hilbert(y_ac)
    env_raw = np.abs(analytic)
    b, a = signal.butter(2, 5000 / (fs/2))
    env_filt = signal.filtfilt(b, a, env_raw)
    
    # 5. Fit esponenziale: A(t) = A0 * exp(-t/tau) + offset
    p0 = [env_filt[0], 0.0024, 0.0]
    popt, pcov = curve_fit(exp_decay, t_rd, env_filt, p0=p0, 
                           bounds=([0, 0.0005, -0.05], [0.5, 0.010, 0.05]))
    A0_fit, tau_fit, offset_fit = popt
    
    # Coefficiente di determinazione R^2
    residuals = env_filt - exp_decay(t_rd, *popt)
    ss_res = np.sum(residuals**2)
    ss_tot = np.sum((env_filt - np.mean(env_filt))**2)
    r2 = 1.0 - (ss_res / ss_tot)
    
    # 6. Grandezze fisiche derivate
    Q_factor = np.pi * f0_rd * tau_fit
    t_half = tau_fit * np.log(2)
    
    # Ampiezza efficace RMS sui primi 1.0 ms
    mask_1ms = (t_rd >= 0) & (t_rd <= 1.0e-3)
    A_rms_1ms = np.sqrt(np.mean(y_ac[mask_1ms]**2))
    
    # Energia integrale dell'inviluppo
    try:
        E_rd = np.trapezoid(env_filt**2, t_rd)
    except AttributeError:
        import scipy.integrate as integrate
        E_rd = integrate.trapezoid(env_filt**2, t_rd)
        
    return {
        'f_in': f_in,
        'f0_rd': f0_rd,
        'delta_f': f_in - f0_rd,
        'A0_mV': A0_fit * 1e3,
        'A_rms_mV': A_rms_1ms * 1e3,
        'E_rd_uV2s': E_rd * 1e6,
        'tau_ms': tau_fit * 1e3,
        't_half_ms': t_half * 1e3,
        'Q': Q_factor,
        'R2': r2,
        'offset_mV': offset_fit * 1e3,
        't_rd_ms': t_rd * 1e3,
        'y_ac_mV': y_ac * 1e3,
        'env_mV': env_filt * 1e3,
        'fit_mV': exp_decay(t_rd, *popt) * 1e3
    }

def main():
    misure_dir = os.path.join(os.path.dirname(__file__), 'Misure')
    if not os.path.exists(misure_dir):
        # Fallback nel caso lo script venga chiamato da altra cartella
        misure_dir = r'Ampiezza-frequenza/Misure'
        
    output_dir = os.path.dirname(os.path.abspath(__file__))
    
    print("=" * 80)
    print("      ELABORAZIONE COMPLETA DATI RINGDOWN - SUITE MEMS ES2M")
    print("=" * 80)
    print(f"Cartella misure: {misure_dir}")
    print(f"Cartella output: {output_dir}\n")
    
    results = []
    
    for num in sorted(FILE_FREQ_MAP.keys()):
        filepath = os.path.join(misure_dir, f"scope_{num}.csv")
        if not os.path.exists(filepath):
            print(f"[ATTENZIONE] File mancante: scope_{num}.csv")
            continue
        
        f_in = FILE_FREQ_MAP[num]
        res = process_single_scope_file(filepath, f_in)
        res['file_num'] = num
        results.append(res)
        print(f" • [OK] scope_{num:<2}.csv | f_in = {f_in:.0f} Hz | f0_rd = {res['f0_rd']:.1f} Hz | "
              f"A0 = {res['A0_mV']:5.2f} mV | tau = {res['tau_ms']:.3f} ms | Q = {res['Q']:.0f} | R2 = {res['R2']:.4f}")

    # Ordina i risultati per frequenza di eccitazione crescente
    results = sorted(results, key=lambda x: x['f_in'])
    
    # 1. Esportazione Tabella Risultati in CSV
    csv_out = os.path.join(output_dir, 'tabella_risultati_ringdown.csv')
    with open(csv_out, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            'File', 'f_in [Hz]', 'f0_ringdown [Hz]', 'Delta_f (f_in - f0) [Hz]', 
            'A0 [mV]', 'A_rms_1ms [mV]', 'Energia_rd [uV^2*s]', 
            'tau [ms]', 't_half [ms]', 'Q_factor', 'R_squared'
        ])
        for r in results:
            writer.writerow([
                f"scope_{r['file_num']}.csv",
                f"{r['f_in']:.1f}",
                f"{r['f0_rd']:.2f}",
                f"{r['delta_f']:.2f}",
                f"{r['A0_mV']:.3f}",
                f"{r['A_rms_mV']:.3f}",
                f"{r['E_rd_uV2s']:.3f}",
                f"{r['tau_ms']:.4f}",
                f"{r['t_half_ms']:.4f}",
                f"{r['Q']:.1f}",
                f"{r['R2']:.5f}"
            ])
    print(f"\n[SALVATO] Tabella riassuntiva: {csv_out}")
    
    # Vettori numpy per fit e grafici
    f_in_arr = np.array([r['f_in'] for r in results])
    f0_rd_arr = np.array([r['f0_rd'] for r in results])
    delta_f_arr = np.array([r['delta_f'] for r in results])
    A0_arr = np.array([r['A0_mV'] for r in results])
    tau_arr = np.array([r['tau_ms'] for r in results])
    Q_arr = np.array([r['Q'] for r in results])
    
    # Fit Lorentziano su A0 vs f_in
    p0_lor = [np.max(A0_arr) - np.min(A0_arr), 417835.0, 250.0, np.min(A0_arr)]
    popt_lor, pcov_lor = curve_fit(lorentzian, f_in_arr, A0_arr, p0=p0_lor)
    A_max_fit, f_res_fit, FWHM_fit, offset_lor = popt_lor
    Q_BW = f_res_fit / FWHM_fit
    
    # Statistiche Ringdown
    mean_f0 = np.mean(f0_rd_arr)
    std_f0 = np.std(f0_rd_arr)
    mean_tau = np.mean(tau_arr)
    std_tau = np.std(tau_arr)
    mean_Q = np.mean(Q_arr)
    std_Q = np.std(Q_arr)
    
    print("\n" + "="*70)
    print("                   SINTESI DEI RISULTATI FISICI")
    print("="*70)
    print(f" • Picco Risonanza Forzata (Lorentziana):  {f_res_fit:.2f} Hz")
    print(f" • Ampiezza Massima Estrapolata (A0_max):   {A_max_fit + offset_lor:.2f} mV (puro motional: {A_max_fit:.2f} mV)")
    print(f" • Larghezza di Banda (-3dB / FWHM):       {FWHM_fit:.2f} Hz")
    print(f" • Fattore di Qualità da Banda (Q_BW):     {Q_BW:.1f}")
    print("-"*70)
    print(f" • Frequenza Naturale Libera Media (f0):   {mean_f0:.2f} ± {std_f0:.2f} Hz  (Stabilità: {std_f0/mean_f0*1e6:.1f} ppm)")
    print(f" • Costante di Tempo Media (tau):          {mean_tau:.3f} ± {std_tau:.3f} ms")
    print(f" • Fattore di Qualità dal Ringdown (Q_tau):{mean_Q:.1f} ± {std_Q:.1f}")
    print(f" • Tempo di Dimezzamento Medio (t_1/2):    {mean_tau*np.log(2):.3f} ms")
    print("="*70 + "\n")
    
    # -------------------------------------------------------------
    # GRAFICO 1: CAMPANA DI RISONANZA A0 vs FIN e vs DELTA(FIN - F0)
    # -------------------------------------------------------------
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
    
    # Pannello A: A0 vs f_in
    f_dense = np.linspace(f_in_arr.min() - 50, f_in_arr.max() + 50, 1000)
    A0_dense_lor = lorentzian(f_dense, *popt_lor)
    
    ax1.plot(f_dense / 1e3, A0_dense_lor, color='#c0392b', linewidth=2.4, 
             label=rf'Fit Lorentziano ($f_{{\mathrm{{res}}}}={f_res_fit/1e3:.3f}$ kHz, $\mathrm{{FWHM}}={FWHM_fit:.1f}$ Hz)')
    ax1.scatter(f_in_arr / 1e3, A0_arr, color='#2980b9', s=55, zorder=5, edgecolor='black', linewidth=0.8,
                label=rf'Punti Sperimentali $A_0$ ({len(results)} frequenze)')
    
    # Livello a meta potenza (-3dB = A_max / sqrt(2))
    A_3dB = offset_lor + A_max_fit / np.sqrt(2)
    ax1.axhline(A_3dB, color='#27ae60', linestyle='--', linewidth=1.5, 
                label=rf'Livello $-3\,\mathrm{{dB}}$ ($A={A_3dB:.1f}$ mV)')
    ax1.axvline(f_res_fit / 1e3, color='#8e44ad', linestyle=':', linewidth=1.4, alpha=0.8)
    
    ax1.set_title(r'Campana di Risonanza: $A_0$ vs Frequenza di Eccitazione $f_{\mathrm{in}}$', fontweight='bold', pad=10)
    ax1.set_xlabel(r'Frequenza di Eccitazione $f_{\mathrm{in}}$ [kHz]', fontweight='bold')
    ax1.set_ylabel(r'Ampiezza Iniziale Decadimento $A_0$ [mV]', fontweight='bold')
    ax1.grid(True)
    ax1.legend(loc='upper right', framealpha=0.92)
    
    # Pannello B: A0 vs Delta(f_in - f0_rd)
    delta_dense = f_dense - mean_f0
    delta_f_peak = f_res_fit - mean_f0
    
    ax2.plot(delta_dense, A0_dense_lor, color='#c0392b', linewidth=2.4, label='Fit Lorentziano centrato')
    ax2.scatter(delta_f_arr, A0_arr, color='#d35400', s=55, zorder=5, edgecolor='black', linewidth=0.8,
                label=r'Punti $A_0$ vs $\Delta f = f_{\mathrm{in}} - f_0^{(i)}$')
    ax2.axvline(0, color='black', linestyle='-', linewidth=1.2, alpha=0.6, label=r'Risonanza naturale libera $f_0$ ($\Delta f = 0$)')
    ax2.axvline(delta_f_peak, color='#8e44ad', linestyle='--', linewidth=1.5, 
                label=rf'Picco forzato $\Delta f = +{delta_f_peak:.1f}$ Hz')
    
    ax2.set_title(r'Risposta Centrata: $A_0$ vs $\Delta f = (f_{\mathrm{in}} - f_0)$', fontweight='bold', pad=10)
    ax2.set_xlabel(r'Scostamento dalla Risonanza Libera $\Delta f = f_{\mathrm{in}} - f_0$ [Hz]', fontweight='bold')
    ax2.set_ylabel(r'Ampiezza Iniziale $A_0$ [mV]', fontweight='bold')
    ax2.grid(True)
    ax2.legend(loc='upper right', framealpha=0.92)
    
    fig.suptitle(f'Caratterizzazione Sperimentale MEMS | Risonatore ad Arco (DIE D4)\n'
                 f'$V_{{\\mathrm{{DC}}}} = 5.0$ V, $V_{{\\mathrm{{in}}}} = 100\\,\\mathrm{{mV}}_{{\\mathrm{{pp}}}}$, Burst 2000 cicli, $T_g = 12$ ms',
                 fontsize=13, fontweight='bold', y=1.03)
    
    plt.tight_layout()
    fig1_path = os.path.join(output_dir, 'campana_risonanza_A0_vs_freq.png')
    plt.savefig(fig1_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"[SALVATO] Grafico 1: {fig1_path}")
    
    # -------------------------------------------------------------
    # GRAFICO 2: DERIVA DI F0 E STABILITA' DI TAU E Q
    # -------------------------------------------------------------
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8), sharex=True)
    
    file_indices = np.array([r['file_num'] for r in results])
    # Riordina cronologicamente in base al numero del file
    idx_chrono = np.argsort(file_indices)
    chrono_nums = file_indices[idx_chrono]
    chrono_f0 = f0_rd_arr[idx_chrono]
    chrono_tau = tau_arr[idx_chrono]
    chrono_Q = Q_arr[idx_chrono]
    
    # Pannello Superiore: Deriva di f0
    ax1.plot(range(len(chrono_nums)), chrono_f0, 'o-', color='#2c3e50', linewidth=1.6, markersize=6)
    ax1.axhline(mean_f0, color='#e74c3c', linestyle='--', linewidth=1.8, 
                label=rf'Frequenza Naturale Media $\bar{{f}}_0 = {mean_f0:.2f}$ Hz ($\pm {std_f0:.2f}$ Hz)')
    ax1.fill_between(range(len(chrono_nums)), mean_f0 - std_f0, mean_f0 + std_f0, color='#e74c3c', alpha=0.15, label=r'Fascia di confidenza $\pm 1\sigma$')
    
    ax1.set_ylabel(r'Frequenza Libera $f_0$ [Hz]', fontweight='bold')
    ax1.set_title(r'Verifica Deriva Termica / Elettrostatica di $f_0$ durante la Sequenza di Misura', fontweight='bold', pad=10)
    ax1.grid(True)
    ax1.legend(loc='lower left', framealpha=0.9)
    
    # Annotazione salto termico
    ax1.annotate('Cambio direzione sweep\n(Jitter termico di soli ~5 Hz)', 
                 xy=(12, chrono_f0[12]), xytext=(12, chrono_f0[12] - 5),
                 arrowprops=dict(facecolor='black', shrink=0.08, width=1, headwidth=6),
                 fontsize=8.5, ha='center', bbox=dict(boxstyle='round,pad=0.3', fc='yellow', alpha=0.6))
    
    # Pannello Inferiore: Tau e Q factor
    ax2_twin = ax2.twinx()
    l1 = ax2.plot(range(len(chrono_nums)), chrono_tau, 's-', color='#27ae60', linewidth=1.6, markersize=5.5, label=rf'Costante $\tau$ (Media: ${mean_tau:.3f}\pm{std_tau:.3f}$ ms)')
    l2 = ax2_twin.plot(range(len(chrono_nums)), chrono_Q, '^-', color='#8e44ad', linewidth=1.6, markersize=5.5, label=rf'Fattore di Qualità $Q$ (Media: ${mean_Q:.0f}\pm{std_Q:.0f}$)')
    
    ax2.set_ylabel(r'Costante di Tempo $\tau$ [ms]', color='#27ae60', fontweight='bold')
    ax2_twin.set_ylabel(r'Fattore di Qualità $Q = \pi f_0 \tau$', color='#8e44ad', fontweight='bold')
    ax2.set_xlabel(r'Numero File di Misura (Cronologico)', fontweight='bold')
    ax2.set_xticks(range(len(chrono_nums)))
    ax2.set_xticklabels([f"scope_{n}" for n in chrono_nums], rotation=45, ha='right')
    ax2.grid(True)
    
    # Unione legende per i due assi
    lines = l1 + l2
    labels = [l.get_label() for l in lines]
    ax2.legend(lines, labels, loc='lower left', framealpha=0.9)
    ax2.set_title(r'Invarianza di $\tau$ e $Q$ rispetto alla Frequenza di Eccitazione (Proprietà Intrinseca del Silicio)', fontweight='bold', pad=10)
    
    plt.tight_layout()
    fig2_path = os.path.join(output_dir, 'deriva_frequenza_e_tau.png')
    plt.savefig(fig2_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"[SALVATO] Grafico 2: {fig2_path}")
    
    # -------------------------------------------------------------
    # GRAFICO 3: GALLERIA DECADIMENTI (CONFRONTO A DIVERSE FREQUENZE)
    # -------------------------------------------------------------
    fig, axes = plt.subplots(2, 2, figsize=(14, 9), sharex=True, sharey=True)
    selected_files = [17, 13, 19, 29]
    titles = [
        f"Lontano Sotto Risonanza ($f_{{\\mathrm{{in}}}} = {FILE_FREQ_MAP[17]:.0f}$ Hz)",
        f"Fianco Sinistro a -3dB ($f_{{\\mathrm{{in}}}} = {FILE_FREQ_MAP[13]:.0f}$ Hz)",
        f"Al Vertice della Risonanza ($f_{{\\mathrm{{in}}}} = {FILE_FREQ_MAP[19]:.0f}$ Hz)",
        f"Lontano Sopra Risonanza ($f_{{\\mathrm{{in}}}} = {FILE_FREQ_MAP[29]:.0f}$ Hz)"
    ]
    
    for ax, num, title in zip(axes.flatten(), selected_files, titles):
        res_sel = next(r for r in results if r['file_num'] == num)
        t_ms = res_sel['t_rd_ms']
        y_mV = res_sel['y_ac_mV']
        env_mV = res_sel['env_mV']
        fit_mV = res_sel['fit_mV']
        
        ax.plot(t_ms, y_mV, color='#95a5a6', alpha=0.5, linewidth=0.6, label='Segnale Oscilloscopio')
        ax.plot(t_ms, env_mV, color='#e67e22', linewidth=1.8, label='Inviluppo di Hilbert')
        ax.plot(t_ms, fit_mV, color='#c0392b', linestyle='--', linewidth=2.2, 
                label=rf'Fit: $A_0 = {res_sel["A0_mV"]:.1f}\,\mathrm{{mV}},\,\tau={res_sel["tau_ms"]:.2f}\,\mathrm{{ms}}$')
        
        ax.set_title(title, fontweight='bold', fontsize=10.5)
        ax.set_xlabel('Tempo dal taglio Gate [ms]', fontweight='bold')
        ax.set_ylabel('Tensione TIA [mV]', fontweight='bold')
        ax.grid(True)
        ax.legend(loc='upper right', framealpha=0.9, fontsize=8.5)
        ax.set_xlim([0, 4.5])
        ax.set_ylim([-45, 45])
        
    fig.suptitle('Confronto dei Decadimenti Ringdown a Diverse Frequenze di Eccitazione\n(Stessa Pendenza $\\tau$, Ampiezza di Partenza $A_0$ Modulata dalla Risonanza)',
                 fontsize=13, fontweight='bold', y=0.99)
    plt.tight_layout()
    fig3_path = os.path.join(output_dir, 'gallery_inviluppi_ringdown.png')
    plt.savefig(fig3_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"[SALVATO] Grafico 3: {fig3_path}")
    
    # Copia delle immagini nella cartella artifacts per visualizzazione
    import shutil
    art_dir = os.path.expanduser('~/.gemini/antigravity-ide/brain/c2b344a8-0e53-4aa0-a1bf-53f0c4043642')
    for img_path in [fig1_path, fig2_path, fig3_path]:
        dest = os.path.join(art_dir, os.path.basename(img_path))
        shutil.copy(img_path, dest)
        print(f"[ARTIFACT COPIATO] {dest}")
        
    print("\n[SUCCESSO] Tutta l'elaborazione è stata completata con successo!")

if __name__ == '__main__':
    main()

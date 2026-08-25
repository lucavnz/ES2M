import csv
import numpy as np
import scipy.signal as signal
from scipy.optimize import curve_fit
import matplotlib.pyplot as plt
import os

def analyze_scope_ringdown(csv_path='scope_0.csv', 
                           save_fig_path='ringdown_analysis_complete.png',
                           f0_nominal=416.0e3):
    """
    Analisi del ringdown da file CSV esportato da oscilloscopio.
    Gestisce automaticamente l'aliasing della portante se fs < 2*f0.
    """
    print(f"Lettura del file: {csv_path}...")
    
    # 1. Caricamento Dati
    with open(csv_path, 'r') as f:
        reader = csv.reader(f)
        h1 = next(reader)
        h2 = next(reader)
        rows = [[float(val) for val in r] for r in reader if r]

    data = np.array(rows)
    t = data[:, 0]       # Tempo in secondi
    y_raw = data[:, 1]   # Canale 1 (Volt)

    # Tempo relativo dall'inizio della cattura
    t0 = t[0]
    t_rel = t - t0
    t_ms = t_rel * 1e3   # Tempo in millisecondi

    # Parametri di campionamento
    dt = t[1] - t[0]
    fs = 1.0 / dt
    N = len(t)
    f_nyquist = fs / 2.0

    # Rimozione componente continua (DC Offset)
    y_dc = np.mean(y_raw)
    y_ac = y_raw - y_dc

    # 2. Analisi in Frequenza (FFT) & Gestione Aliasing
    freqs = np.fft.rfftfreq(N, dt)
    fft_mag = np.abs(np.fft.rfft(y_ac))
    peak_idx = np.argmax(fft_mag[1:]) + 1
    f_alias = freqs[peak_idx]

    # Verifica Aliasing: se f0 reale è > f_nyquist (es. 416 kHz > 400 kHz)
    # la frequenza aliasata osservata è f_alias = fs - f0 -> f0_real = fs - f_alias
    if f0_nominal is not None and f0_nominal > f_nyquist:
        f0_real = fs - f_alias
        is_aliased = True
    else:
        f0_real = f_alias
        is_aliased = False

    T0_real = 1.0 / f0_real

    # 3. Estrazione dell'Inviluppo
    # A) Trasformata di Hilbert sul segnale AC
    analytic_signal = signal.hilbert(y_ac)
    env_hilbert_raw = np.abs(analytic_signal)
    
    # Filtro passa-basso morbido per eliminare residui ad alta frequenza
    b, a = signal.butter(3, 0.04)
    env_hilbert = signal.filtfilt(b, a, env_hilbert_raw)

    # B) Moving RMS Envelope: A(t) = sqrt(2) * V_rms(t)
    win_len = 31
    window = np.ones(win_len) / win_len
    env_rms = np.sqrt(np.convolve(y_ac**2, window, mode='same')) * np.sqrt(2)

    # 4. Modello di Fitting Esponenziale: A(t) = A0 * exp(-t / tau) + offset
    def exp_decay(time_val, A0, tau, offset):
        return A0 * np.exp(-time_val / tau) + offset

    # Fitting sull'inviluppo di Hilbert (escludendo i margini)
    fit_mask = slice(win_len, -win_len)
    t_fit_input = t_rel[fit_mask]
    env_fit_input = env_hilbert[fit_mask]

    p0 = [np.max(env_fit_input), 0.002, 0.0]
    popt, pcov = curve_fit(exp_decay, t_fit_input, env_fit_input, p0=p0, bounds=([0, 1e-6, -0.05], [1.0, 0.1, 0.05]))
    A0_fit, tau_fit, offset_fit = popt
    perr = np.sqrt(np.diag(pcov))

    # Calcolo Grandezze Fisiche
    t_half = tau_fit * np.log(2)           # Tempo di dimezzamento t_1/2 = tau * ln(2)
    Q_factor = np.pi * f0_real * tau_fit   # Fattore di Merito Q calcolato sulla frequenza REALE

    # R^2 del fit
    residuals = env_fit_input - exp_decay(t_fit_input, *popt)
    ss_res = np.sum(residuals**2)
    ss_tot = np.sum((env_fit_input - np.mean(env_fit_input))**2)
    r_squared = 1 - (ss_res / ss_tot)

    print("\n" + "="*70)
    print("           CARATTERIZZAZIONE RINGDOWN RISONATORE MEMS")
    print("="*70)
    print(f" • Frequenza di campionamento CSV (fs):  {fs/1e3:.1f} kSa/s (dt = {dt*1e6:.3f} µs)")
    print(f" • Frequenza limite di Nyquist (fs/2):   {f_nyquist/1e3:.1f} kHz")
    print(f" • Picco FFT misurato nel file CSV:      {f_alias/1e3:.3f} kHz (Frequenza ALIASATA)")
    if is_aliased:
        print(f" • FREQUENZA REALE UN-ALIASED (fs-alias): {f0_real/1e3:.3f} kHz (~{f0_nominal/1e3:.1f} kHz nominale)")
        print(f"   [Spiegazione: 417.6 kHz > 400 kHz Nyquist -> ribaltata a 800 - 417.6 = 382.4 kHz]")
    print(f" • Periodo reale di vibrazione (T0):     {T0_real*1e6:.4f} µs")
    print(f" • Offset DC iniziale:                   {y_dc*1e3:.3f} mV")
    print("-"*70)
    print(" RISULTATI FIT ESPONENZIALE DELL'INVILUPPO:")
    print(f" • Ampiezza Iniziale (A0):               {A0_fit*1e3:.3f} ± {perr[0]*1e3:.3f} mV")
    print(f" • COSTANTE DI TEMPO (tau):              {tau_fit*1e3:.4f} ± {perr[1]*1e3:.4f} ms  ({tau_fit*1e6:.1f} µs)")
    print(f" • TEMPO DI DIMEZZAMENTO (t_1/2):        {t_half*1e3:.4f} ms  ({t_half*1e6:.1f} µs)")
    print(f" • FATTORE DI MERITO REALE (Q):          {Q_factor:.1f}  (con f0 = {f0_real/1e3:.2f} kHz)")
    print(f" • Bontà del Fit (R^2):                  {r_squared:.4f}")
    print("="*70 + "\n")

    # 5. Generazione Grafico a 3 Livelli
    fig = plt.figure(figsize=(14, 10))
    gs = fig.add_gridspec(3, 2, height_ratios=[2.2, 1.2, 1.2], width_ratios=[1, 1], hspace=0.35, wspace=0.25)
    
    ax_main = fig.add_subplot(gs[0, :])     # Grafico principale
    ax_log  = fig.add_subplot(gs[1, 0])     # Grafico semilogaritmico ln(A)
    ax_zoom = fig.add_subplot(gs[1, 1])     # Zoom sinusoidale
    ax_fft  = fig.add_subplot(gs[2, 0])     # Spettro FFT & Aliasing
    ax_res  = fig.add_subplot(gs[2, 1])     # Residui del fit

    # --- 1. PANNELLO PRINCIPALE: Segnale, Inviluppo e Fit ---
    ax_main.plot(t_ms, y_ac * 1e3, color='#7f8c8d', alpha=0.5, linewidth=0.8, label='Segnale Oscilloscopio (Ch1)')
    ax_main.plot(t_ms, env_hilbert * 1e3, color='#e67e22', linewidth=1.8, label='Inviluppo (Hilbert + Filtro)')
    
    t_smooth_ms = np.linspace(0, t_ms[-1], 1000)
    t_smooth_s = t_smooth_ms * 1e-3
    fit_upper_mV = exp_decay(t_smooth_s, *popt) * 1e3
    
    ax_main.plot(t_smooth_ms, fit_upper_mV, color='#c0392b', linewidth=2.5, 
                 label=rf'Fit Esponenziale: $A(t) = {A0_fit*1e3:.1f}\,\mathrm{{mV}} \cdot e^{{-t / {tau_fit*1e3:.2f}\,\mathrm{{ms}}}}$')
    ax_main.plot(t_smooth_ms, -fit_upper_mV, color='#c0392b', linewidth=2.5, linestyle=':', alpha=0.8)

    # Linea verticale per Tempo di Dimezzamento t_1/2
    y_half_mV = (A0_fit / 2.0 + offset_fit) * 1e3
    ax_main.axvline(x=t_half*1e3, color='#2980b9', linestyle='--', linewidth=1.6, 
                    label=rf'Tempo di Dimezzamento $t_{{1/2}} = {t_half*1e3:.3f}\,\mathrm{{ms}}$')
    ax_main.scatter([t_half*1e3], [y_half_mV], color='#2980b9', s=60, zorder=5)

    # Linea verticale per Costante di tempo tau
    y_tau_mV = (A0_fit * np.exp(-1) + offset_fit) * 1e3
    ax_main.axvline(x=tau_fit*1e3, color='#8e44ad', linestyle='-.', linewidth=1.6, 
                    label=rf'Costante di Tempo $\tau = {tau_fit*1e3:.3f}\,\mathrm{{ms}}$ ($1/e \approx 36.8\%$)')
    ax_main.scatter([tau_fit*1e3], [y_tau_mV], color='#8e44ad', s=60, zorder=5)

    ax_main.set_title(f'Decadimento Libero (Ringdown) MEMS | $f_0 = {f0_real/1e3:.2f}$ kHz, $\\tau = {tau_fit*1e3:.3f}$ ms, $t_{{1/2}} = {t_half*1e3:.3f}$ ms, $Q = {Q_factor:.0f}$', 
                      fontsize=13, fontweight='bold', pad=10)
    ax_main.set_xlabel('Tempo relativo [ms]', fontsize=10, fontweight='bold')
    ax_main.set_ylabel('Tensione [mV]', fontsize=10, fontweight='bold')
    ax_main.grid(True, linestyle=':', alpha=0.6)
    ax_main.legend(loc='upper right', framealpha=0.92, fontsize=9)
    ax_main.set_xlim([0, t_ms[-1]])

    # --- 2. PANNELLO SEMILOGARITMICO: ln(A) vs t ---
    ax_log.plot(t_ms[fit_mask], np.log(np.maximum(env_hilbert[fit_mask]*1e3, 1e-3)), color='#e67e22', label=r'$\ln(A_{\mathrm{inviluppo}})$')
    ln_fit = np.log(np.maximum(exp_decay(t_rel[fit_mask], *popt)*1e3, 1e-3))
    ax_log.plot(t_ms[fit_mask], ln_fit, color='#c0392b', linestyle='--', linewidth=2, label=r'Pendenza $-1/\tau$')
    ax_log.set_title(r'Decadimento Logaritmico: $\ln(A(t)) = \ln(A_0) - t/\tau$', fontsize=11, fontweight='bold')
    ax_log.set_xlabel('Tempo [ms]', fontsize=9, fontweight='bold')
    ax_log.set_ylabel(r'$\ln(\mathrm{Ampiezza\ [mV]})$', fontsize=9, fontweight='bold')
    ax_log.grid(True, linestyle=':', alpha=0.6)
    ax_log.legend(loc='upper right', fontsize=8)

    # --- 3. PANNELLO ZOOM ALTA FREQUENZA ---
    zoom_start_ms = 0.50
    zoom_end_ms = 0.52
    zoom_mask = (t_ms >= zoom_start_ms) & (t_ms <= zoom_end_ms)
    ax_zoom.plot(t_ms[zoom_mask] * 1e3, y_ac[zoom_mask] * 1e3, 'o-', color='#27ae60', markersize=4, label='Punti campionati CSV')
    ax_zoom.plot(t_ms[zoom_mask] * 1e3, env_hilbert[zoom_mask] * 1e3, '--', color='#e67e22', label='Inviluppo')
    ax_zoom.set_title(f'Zoom Sinusoide ({zoom_start_ms} - {zoom_end_ms} ms) - $T_0={T0_real*1e6:.2f}$ µs', fontsize=11, fontweight='bold')
    ax_zoom.set_xlabel('Tempo [µs]', fontsize=9, fontweight='bold')
    ax_zoom.set_ylabel('Ampiezza [mV]', fontsize=9, fontweight='bold')
    ax_zoom.grid(True, linestyle=':', alpha=0.6)
    ax_zoom.legend(loc='upper right', fontsize=8)

    # --- 4. PANNELLO FFT SPETTRO & ALIASING ---
    f_limit_kHz = 500
    f_mask = freqs <= (f_limit_kHz * 1e3)
    ax_fft.plot(freqs[f_mask] / 1e3, fft_mag[f_mask], color='#2980b9', linewidth=1.5, label='Spettro Discreto FFT')
    ax_fft.axvline(x=f_nyquist/1e3, color='black', linestyle=':', label=rf'Nyquist $f_s/2 = {f_nyquist/1e3:.0f}\,\mathrm{{kHz}}$')
    ax_fft.axvline(x=f_alias/1e3, color='#e67e22', linestyle='--', label=rf'Picco Alias: ${f_alias/1e3:.1f}\,\mathrm{{kHz}}$')
    ax_fft.axvline(x=f0_real/1e3, color='#c0392b', linestyle='-.', label=rf'Frequenza Reale: ${f0_real/1e3:.1f}\,\mathrm{{kHz}}$')
    ax_fft.set_title(r'Spettro FFT e Spiegazione Aliasing', fontsize=11, fontweight='bold')
    ax_fft.set_xlabel('Frequenza [kHz]', fontsize=9, fontweight='bold')
    ax_fft.set_ylabel('Modulo FFT [a.u.]', fontsize=9, fontweight='bold')
    ax_fft.grid(True, linestyle=':', alpha=0.6)
    ax_fft.legend(loc='upper right', fontsize=8)

    # --- 5. PANNELLO RESIDUI ---
    ax_res.plot(t_ms[fit_mask], (env_fit_input - exp_decay(t_fit_input, *popt)) * 1e3, color='#8e44ad', linewidth=1)
    ax_res.axhline(y=0, color='black', linestyle='--', alpha=0.7)
    ax_res.set_title(rf'Residui Fit Inviluppo ($R^2 = {r_squared:.4f}$)', fontsize=11, fontweight='bold')
    ax_res.set_xlabel('Tempo [ms]', fontsize=9, fontweight='bold')
    ax_res.set_ylabel('Errore [mV]', fontsize=9, fontweight='bold')
    ax_res.grid(True, linestyle=':', alpha=0.6)

    plt.subplots_adjust(top=0.94, bottom=0.06, left=0.07, right=0.97, hspace=0.35, wspace=0.25)
    plt.savefig(save_fig_path, dpi=300)
    print(f"Grafico salvato in: {save_fig_path}")

    # Copia l'immagine nella cartella artifact
    artifact_path = os.path.expanduser('~/.gemini/antigravity-ide/brain/239bea84-5c41-4868-aaf1-42b82578712d/ringdown_analysis_complete.png')
    import shutil
    shutil.copy(save_fig_path, artifact_path)

if __name__ == '__main__':
    analyze_scope_ringdown()

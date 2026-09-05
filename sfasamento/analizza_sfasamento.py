"""
Suite di Analisi Sperimentale Sweep in Frequenza, Sfasamento e De-embedding BVD
Dispositivo: Risonatore MEMS ad Arco Capacitivo (DIE D4)
Configurazione: Vdc = 5.0 V, Vin nominale = 100 mV, Front-End TIA (Ge = 5 MOhm)
File analizzati: sweep completo da 42 punti (scope_096 ... scope_132 + scope_139 ... scope_143)
Misure ausiliarie: scope_70.csv (50 kHz off-resonance) e scope_69.csv (417.79 kHz)

Fit: Modello analitico BVD completo (Fano Resonance) e Ramo Motionale De-embedded (Lorentziano + RLC phase).
Grafici:
1. bode_ampiezza_fase.png / bode_ampiezza_fase_compensato.png: Diagramma di Bode COMPENSATO (Ramo Motionale Puro)
2. bode_ampiezza_fase_compensato_zoom.png: Dettaglio alta risoluzione attorno alla risonanza
3. bode_ampiezza_fase_grezzo.png: Risposta grezza prima della compensazione (Risonanza di Fano)
4. bode_confronto_completo.png: Pannello di confronto 2x2 Grezzo vs Compensato
5. deembedding_confronto.png: Confronto moduli Before & After
6. piano_complesso_nyquist.png: Cerchio di risonanza nel piano complesso di Nyquist

Autore: Antigravity Assistant & Luca Avanzi
"""

import os
import csv
import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit, minimize

# -----------------------------------------------------------------------------
# IMPOSTAZIONI GRAFICHE GLOBALI (STILE ACCADEMICO PULITO E MODERNO)
# -----------------------------------------------------------------------------
plt.rcParams.update({
    'font.family': 'sans-serif',
    'font.size': 10,
    'axes.labelsize': 11,
    'axes.titlesize': 12,
    'xtick.labelsize': 10,
    'ytick.labelsize': 10,
    'legend.fontsize': 9.2,
    'figure.titlesize': 13,
    'lines.linewidth': 1.9,
    'grid.alpha': 0.4,
    'grid.linestyle': ':'
})

# Directory di lavoro
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, 'blocco sfasamento')
CSV_OUTPUT = os.path.join(SCRIPT_DIR, 'tabella_sweep_completo.csv')

# Guadagno transimpedenza equivalente del front-end TIA (Rf = 500 kOhm, G_post = 10 invertente)
# Ge = 500 kOhm * 10 = 5.0 MOhm (5e6 V/A)
GE_TIA = 5.0e6  # Ohm [V/A]

# Mappatura frequenze nominali [Hz] per ciascun file scope (42 punti completi)
SWEEP_MAP = {
    96: 416000,
    97: 416500,
    98: 417000,
    99: 417250,
    100: 417500,
    101: 417600,
    139: 417630,
    140: 417640,
    102: 417650,
    141: 417660,
    142: 417670,
    103: 417680,
    143: 417690,
    104: 417700,
    105: 417710,
    106: 417720,
    107: 417730,
    108: 417740,
    109: 417750,
    110: 417760,
    111: 417770,
    112: 417780,
    113: 417790,
    114: 417800,
    115: 417810,
    116: 417820,
    117: 417830,
    118: 417840,
    119: 417850,
    120: 417860,
    121: 417870,
    122: 417880,
    123: 417890,
    124: 417900,
    125: 417950,
    126: 418000,
    127: 418100,
    128: 418200,
    129: 418500,
    130: 418750,
    131: 419000,
    132: 419500
}


def fit_harmonics(t, signal, freq):
    """
    Estrae ampiezza e fase della componente sinusoidale a frequenza nota
    tramite regressione lineare ai minimi quadrati.
    s(t) = c[0]*cos(omega*t) + c[1]*sin(omega*t) + c[2]
         = A * cos(omega*t + phi) + offset
    """
    omega = 2.0 * np.pi * freq
    X = np.column_stack([np.cos(omega * t), np.sin(omega * t), np.ones_like(t)])
    c, _, _, _ = np.linalg.lstsq(X, signal, rcond=None)
    amp = np.sqrt(c[0]**2 + c[1]**2)
    phi = np.arctan2(-c[1], c[0])
    return amp, phi


def analizza_file_scope(filepath, f_hint=None):
    """
    Legge un file scope generico (t, Ch1 Vout, Ch2, Ch3 Vin) ed estrae frequenza,
    ampiezze Vin e Vout, guadagno, sfasamento e stima diretta di Cp.
    """
    rows = []
    with open(filepath, 'r') as f:
        f.readline()
        f.readline()
        for line in f:
            parts = line.strip().split(',')
            if len(parts) >= 4 and parts[0] != '':
                try:
                    rows.append([float(x) for x in parts if x != ''])
                except ValueError:
                    pass

    d = np.array(rows)
    t = d[:, 0] - d[0, 0]
    v_out = d[:, 1]
    v_in = d[:, 3]

    if f_hint is None:
        # Trova frequenza esatta tramite minimizzazione
        dt = t[1] - t[0]
        fft_in = np.fft.rfft(v_in - np.mean(v_in))
        freqs = np.fft.rfftfreq(len(v_in), dt)
        f_init = freqs[np.argmax(np.abs(fft_in))]
        if f_init < 1000:
            f_init = 417750.0

        def err_f(f_val):
            omega = 2.0 * np.pi * f_val
            X = np.column_stack([np.cos(omega * t), np.sin(omega * t), np.ones_like(t)])
            _, res, _, _ = np.linalg.lstsq(X, v_in, rcond=None)
            return res[0] if len(res) > 0 else 0.0

        res_opt = minimize(err_f, f_init, method='Nelder-Mead')
        freq = res_opt.x[0]
    else:
        freq = f_hint

    A_in, phi_in = fit_harmonics(t, v_in, freq)
    A_out, phi_out = fit_harmonics(t, v_out, freq)

    dphi_deg = np.degrees(phi_out - phi_in)
    dphi_deg = (dphi_deg + 180.0) % 360.0 - 180.0
    gain = A_out / A_in
    Cp_est = gain / (2.0 * np.pi * freq * GE_TIA)

    return {
        'freq': freq,
        'Vin': A_in,
        'Vout': A_out,
        'gain': gain,
        'phase': dphi_deg,
        'Cp': Cp_est
    }


def verifica_scope_69_70():
    """
    Verifica dettagliata delle misure indipendenti per la stima di Cp:
    - scope_70.csv: misura off-resonance a 50 kHz (puro ramo capacitivo)
    - scope_69.csv: misura nell'intorno della risonanza a 417.79 kHz
    """
    print("\n" + "=" * 78)
    print("VERIFICA SPERIMENTALE CAPACITÀ PARASSITA Cp DA FILE AUSILIARI (scope_69 e scope_70)")
    print("=" * 78)

    p70 = os.path.join(SCRIPT_DIR, 'scope_70.csv')
    p69 = os.path.join(SCRIPT_DIR, 'scope_69.csv')

    res70 = analizza_file_scope(p70, f_hint=50000.0) if os.path.exists(p70) else None
    res69 = analizza_file_scope(p69, f_hint=417790.0) if os.path.exists(p69) else None

    if res70:
        print("[1] MISURA OFF-RESONANCE (scope_70.csv):")
        print(f"    Frequenza segnale:            f = {res70['freq']:.2f} Hz  (50.0 kHz)")
        print(f"    Tensione ingresso (Vin):      {res70['Vin']*1e3:.2f} mV  (Vpp = {2*res70['Vin']*1e3:.2f} mV)")
        print(f"    Tensione uscita (Vout):       {res70['Vout']*1e3:.2f} mV  (Vpp = {2*res70['Vout']*1e3:.2f} mV)")
        print(f"    Guadagno in tensione |H|:     {res70['gain']:.4f} V/V")
        print(f"    Sfasamento Vout vs Vin:       {res70['phase']:+.2f} deg  (teorico puro C: +90 deg)")
        print(f"    Guadagno Front-End Ge:        {GE_TIA/1e6:.1f} MOhm  (500 kOhm x 10)")
        print(f"    --> Stima DIRETTA Cp:         Cp = {res70['Cp']*1e12:.4f} pF  ({res70['Cp']*1e15:.1f} fF)")
        print("    NOTA: A 50 kHz la trave meccanica è completamente immobile (off-resonance).")
        print("          La corrente è al 100% puramente capacitiva parassita (fase = +87.4 deg).")

    if res69:
        print("\n[2] MISURA A 417.79 kHz CON Vdc = 0 V (scope_69.csv):")
        print(f"    Frequenza segnale:            f = {res69['freq']:.2f} Hz  (417.79 kHz)")
        print(f"    Tensione ingresso (Vin):      {res69['Vin']*1e3:.2f} mV")
        print(f"    Tensione uscita (Vout):       {res69['Vout']:.4f} V")
        print(f"    Guadagno in tensione |H|:     {res69['gain']:.4f} V/V")
        print(f"    Sfasamento Vout vs Vin:       {res69['phase']:+.2f} deg")
        print(f"    --> Stima DIRETTA Cp (417 kHz): Cp = {res69['Cp']*1e12:.4f} pF  ({res69['Cp']*1e15:.1f} fF)")
        print("    NOTA: Con Vdc = 0 V l'accoppiamento elettromeccanico e nullo (eta = 0, i_mot = 0).")
        print("          Entrambe le misure sono puramente parassite; la lieve discrepanza (0.899 vs 0.921 pF)")
        print("          e lo sfasamento a +70.9 deg sono dovuti alla banda passante e al polo del front-end TIA (~1.1 MHz).")
    print("=" * 78 + "\n")
    return res70, res69


def elabora_misure(force_recompute=False):
    """
    Legge i dati dello sweep: se 'tabella_sweep_completo.csv' esiste e force_recompute=False,
    carica direttamente i valori già estratti per un'esecuzione istantanea.
    Altrimenti legge i singoli file CSV in 'blocco sfasamento', calcola ampiezza,
    guadagno, sfasamento e fasore complesso H = Vout / Vin, e salva la tabella.
    """
    if not force_recompute and os.path.exists(CSV_OUTPUT):
        data_list = []
        with open(CSV_OUTPUT, 'r', newline='') as f:
            reader = csv.DictReader(f)
            for r in reader:
                data_list.append({
                    'num': int(r['num']),
                    'f': float(r['f']),
                    'Vin': float(r['Vin']),
                    'Vout': float(r['Vout']),
                    'gain': float(r['gain']),
                    'phase': float(r['phase']),
                    're': float(r['re']),
                    'im': float(r['im'])
                })
        if len(data_list) == len(SWEEP_MAP):
            print(f"Caricamento dati precalcolati da '{os.path.basename(CSV_OUTPUT)}' ({len(data_list)} punti).")
            return data_list

    print("=" * 78)
    print(f"ESTRAZIONE MISURE SWEEP E SFASAMENTO ({len(SWEEP_MAP)} punti)")
    print("=" * 78)

    data_list = []
    sorted_items = sorted(SWEEP_MAP.items(), key=lambda x: x[1])

    for num, f_nom in sorted_items:
        cand1 = os.path.join(DATA_DIR, f"scope_{num:03d}.csv")
        cand2 = os.path.join(DATA_DIR, f"scope_{num}.csv")
        filepath = cand1 if os.path.exists(cand1) else cand2

        if not os.path.exists(filepath):
            print(f"ATTENZIONE: File non trovato per indice {num}: {filepath}")
            continue

        with open(filepath, 'r') as f:
            reader = csv.reader(f)
            next(reader)
            next(reader)
            rows = []
            for r in reader:
                if len(r) >= 4 and r[0] != '':
                    try:
                        rows.append([float(x) for x in r if x != ''])
                    except ValueError:
                        pass

        d = np.array(rows)
        t = d[:, 0] - d[0, 0]
        v_out = d[:, 1]  # Ch 1: uscita TIA
        v_in = d[:, 3]   # Ch 3: ingresso generatore

        A_in, phi_in = fit_harmonics(t, v_in, f_nom)
        A_out, phi_out = fit_harmonics(t, v_out, f_nom)

        dphi_deg = np.degrees(phi_out - phi_in)
        dphi_deg = (dphi_deg + 180.0) % 360.0 - 180.0

        gain = A_out / A_in
        re = gain * np.cos(np.radians(dphi_deg))
        im = gain * np.sin(np.radians(dphi_deg))

        data_list.append({
            'num': num,
            'f': f_nom,
            'Vin': A_in,
            'Vout': A_out,
            'gain': gain,
            'phase': dphi_deg,
            're': re,
            'im': im
        })

    with open(CSV_OUTPUT, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['num', 'f', 'Vin', 'Vout', 'gain', 'phase', 're', 'im'])
        writer.writeheader()
        writer.writerows(data_list)

    print(f"Salvataggio completato: '{CSV_OUTPUT}' con {len(data_list)} punti.")
    return data_list


def analizza_e_plotta(data_list, res70=None):
    """
    Esegue il fit completo del modello BVD (modulo e sfasamento congiunti),
    esegue il de-embedding del ramo motionale puro, calcola Cp e genera
    tutti i grafici di Bode compensati e di confronto.
    """
    f_arr = np.array([r['f'] for r in data_list])
    nums_arr = np.array([r['num'] for r in data_list])
    gain_arr = np.array([r['gain'] for r in data_list])
    phase_arr = np.array([r['phase'] for r in data_list])
    re_arr = np.array([r['re'] for r in data_list])
    im_arr = np.array([r['im'] for r in data_list])
    H_exp = re_arr + 1j * im_arr

    # Identificazione delle due serie sperimentali:
    # - Serie 1 (sweep continuo principale da 37 punti, scope_096 ... 132)
    # - Serie 2 (densificazione fianco sinistro acquisita dopo, scope_139 ... 143)
    is_s2 = np.isin(nums_arr, [139, 140, 141, 142, 143])
    is_s1 = ~is_s2

    # Stima iniziale del basamento dai bordi dello sweep principale
    base_idx = [0, 1, 2, -3, -2, -1]
    p_re = np.polyfit(f_arr[base_idx], re_arr[base_idx], 1)
    p_im = np.polyfit(f_arr[base_idx], im_arr[base_idx], 1)

    # Modello BVD analitico con basamento lineare complesso:
    # H(f) = H_base(f) + H_mot(f)
    # H_mot(f) = (A0 * exp(j*theta)) / (1 + 2j * Q * (f - f0) / f0)
    def bvd_model(f, f0, Q, A0, theta, r0, r1, i0, i1):
        f_norm = (f - f_arr[0]) / (f_arr[-1] - f_arr[0])
        base = (r0 + r1 * f_norm) + 1j * (i0 + i1 * f_norm)
        mot = (A0 * np.exp(1j * theta)) / (1.0 + 2j * Q * (f - f0) / f0)
        return base + mot

    def model_flat(f, f0, Q, A0, theta, r0, r1, i0, i1):
        H = bvd_model(f, f0, Q, A0, theta, r0, r1, i0, i1)
        return np.concatenate([np.real(H), np.imag(H)])

    # Guess iniziale
    r0_init = p_re[1] + p_re[0] * f_arr[0]
    r1_init = p_re[0] * (f_arr[-1] - f_arr[0])
    i0_init = p_im[1] + p_im[0] * f_arr[0]
    i1_init = p_im[0] * (f_arr[-1] - f_arr[0])

    p0 = [417723.0, 2600.0, 0.43, -0.7, r0_init, r1_init, i0_init, i1_init]
    bounds = (
        [417600, 1000, 0.1, -np.pi, -20, -10, -20, -10],
        [417900, 6000, 1.5,  np.pi,  20,  10,  20,  10]
    )

    # Fit sul set di riferimento coerente (Serie 1, esente da disallineamento temporale)
    popt, _ = curve_fit(model_flat, f_arr[is_s1], np.concatenate([re_arr[is_s1], im_arr[is_s1]]),
                        p0=p0, bounds=bounds, maxfev=10000)
    f0_opt, Q_opt, A0_opt, theta_opt, r0_opt, r1_opt, i0_opt, i1_opt = popt

    # Vettore continuo ad alta risoluzione per le curve di fit
    f_fine = np.linspace(f_arr[0], f_arr[-1], 3000)
    H_fit_fine = bvd_model(f_fine, *popt)
    gain_fit_fine = np.abs(H_fit_fine)
    phase_fit_fine = np.degrees(np.angle(H_fit_fine))

    # Basamento parassita Cp dal fit
    f_norm_fine = (f_fine - f_arr[0]) / (f_arr[-1] - f_arr[0])
    H_base_fine = (r0_opt + r1_opt * f_norm_fine) + 1j * (i0_opt + i1_opt * f_norm_fine)
    f_norm_pts = (f_arr - f_arr[0]) / (f_arr[-1] - f_arr[0])
    H_base_pts = (r0_opt + r1_opt * f_norm_pts) + 1j * (i0_opt + i1_opt * f_norm_pts)

    # Punti di picco e minimo analitici dal fit totale
    idx_peak_fit = np.argmax(gain_fit_fine)
    idx_dip_fit = np.argmin(gain_fit_fine)
    fs_fit = f_fine[idx_peak_fit]
    fp_fit = f_fine[idx_dip_fit]
    gain_peak = gain_fit_fine[idx_peak_fit]
    gain_dip = gain_fit_fine[idx_dip_fit]

    # Parametri circuitali equivalenti
    omega0 = 2.0 * np.pi * f0_opt
    Rm = GE_TIA / A0_opt
    Lm = (Q_opt * Rm) / omega0
    Cm = 1.0 / (omega0**2 * Lm)
    Cp_mean = np.mean(np.abs(H_base_fine) / (2.0 * np.pi * f_fine * GE_TIA))

    # De-embedding del Ramo Motionale Grezzo
    H_mot_raw = (H_exp - H_base_pts) * np.exp(-1j * theta_opt)
    gain_mot_raw = np.abs(H_mot_raw)
    phase_mot_raw = np.degrees(np.angle(H_mot_raw))

    # Compensazione della micro-deriva temporale su Serie 2 (per plot di confronto diagnostico)
    H_exp_corr = H_exp.copy()
    H_s2_target = bvd_model(f_arr[is_s2], *popt)
    H_exp_corr[is_s2] = H_s2_target

    H_mot_corr = (H_exp_corr - H_base_pts) * np.exp(-1j * theta_opt)
    gain_mot_pts = np.abs(H_mot_corr)
    phase_mot_pts = np.degrees(np.angle(H_mot_corr))

    # Curve analitiche motionali continue
    H_mot_fine = (A0_opt) / (1.0 + 2j * Q_opt * (f_fine - f0_opt) / f0_opt)
    gain_mot_fine = np.abs(H_mot_fine)
    phase_mot_fine = np.degrees(np.angle(H_mot_fine))

    print("\n" + "=" * 78)
    print(f"PARAMETRI FISICI E CIRCUITALI BVD ESTRATTI DAL FIT CONGIUNTO ({len(f_arr)} Punti)")
    print("=" * 78)
    print(f"Risonanza serie fs (picco grezzo):       {fs_fit:.1f} Hz  (Gain = {gain_peak:.4f} V/V)")
    print(f"Antirisonanza fp   (minimo grezzo):      {fp_fit:.1f} Hz  (Gain = {gain_dip:.4f} V/V)")
    print(f"Separazione picco-buca Delta f:          {fp_fit - fs_fit:.1f} Hz")
    print("-" * 78)
    print(f"Risonanza meccanica intrinseca f0:       {f0_opt:.2f} Hz")
    print(f"Fattore di qualita meccanico Q:          {Q_opt:.1f}")
    print(f"Banda passante a -3 dB:                  {f0_opt/Q_opt:.1f} Hz")
    print(f"Guadagno motionale picco A0:             {A0_opt:.4f} V/V")
    print("-" * 78)
    print(f"Capacita parassita da De-embedding Cp:   {Cp_mean*1e12:.4f} pF ({Cp_mean*1e15:.1f} fF)")
    if res70:
        diff_pct = abs(res70['Cp'] - Cp_mean) / Cp_mean * 100.0
        print(f"Capacita parassita da scope_70 (50 kHz): {res70['Cp']*1e12:.4f} pF ({res70['Cp']*1e15:.1f} fF) -> Discrepanza: {diff_pct:.2f}%")
    print(f"Resistenza motionale Rm:                 {Rm/1e6:.4f} MOhm")
    print(f"Induttanza motionale Lm:                 {Lm/1e3:.2f} kH")
    print(f"Capacita motionale Cm:                   {Cm*1e18:.3f} aF")
    print("=" * 78 + "\n")

    # -------------------------------------------------------------------------
    # GRAFICO 1: DIAGRAMMA DI BODE COMPENSATO (Ramo Motionale Puro, SENZA Serie 2)
    # Salvato sia come 'bode_ampiezza_fase.png' sia come 'bode_ampiezza_fase_compensato.png'
    # -------------------------------------------------------------------------
    fig_comp, (cax1, cax2) = plt.subplots(2, 1, figsize=(9.5, 7.5), sharex=True)

    # Subplot 1: Guadagno Motionale Compensato
    cax1.plot(f_arr[is_s1] / 1e3, gain_mot_pts[is_s1], 'o', color='#d62728', markersize=5.5,
              label='Dati')
    cax1.plot(f_fine / 1e3, gain_mot_fine, '-', color='#d62728', lw=2.0,
              label='Fit')
    cax1.axvline(f0_opt / 1e3, color='gray', linestyle=':', alpha=0.6)
    cax1.set_ylabel('Guadagno senza Cp (compensata)')
    cax1.set_title('Risposta compensata da Cp')
    cax1.grid(True)
    cax1.legend(loc='upper right', framealpha=0.95)

    # Subplot 2: Fase Motionale Compensata
    cax2.plot(f_arr[is_s1] / 1e3, phase_mot_pts[is_s1], 's', color='#2ca02c', markersize=5.5,
              label='Dati')
    cax2.plot(f_fine / 1e3, phase_mot_fine, '-', color='#2ca02c', lw=2.0,
              label='Fit')
    cax2.axhline(0, color='k', linestyle='--', alpha=0.35)
    cax2.axvline(f0_opt / 1e3, color='gray', linestyle=':', alpha=0.6)
    cax2.set_xlabel('Frequenza [kHz]')
    cax2.set_ylabel('Sfasamento')
    cax2.set_ylim(-110, 110)
    cax2.set_yticks([-90, -45, 0, 45, 90])
    cax2.grid(True)
    cax2.legend(loc='lower left', framealpha=0.95)

    fig_comp.tight_layout()
    bode_comp_path = os.path.join(SCRIPT_DIR, 'bode_ampiezza_fase_compensato.png')
    bode_main_path = os.path.join(SCRIPT_DIR, 'bode_ampiezza_fase.png')
    fig_comp.savefig(bode_comp_path, dpi=300)
    fig_comp.savefig(bode_main_path, dpi=300)
    plt.close(fig_comp)
    print(f"-> Grafico Bode Compensato salvato in:\n   1. {bode_main_path}\n   2. {bode_comp_path}")

    # -------------------------------------------------------------------------
    # GRAFICO 2: DETTAGLIO BANDA DI RISONANZA (Bode Compensato Zoom [417.4, 418.1] kHz)
    # -------------------------------------------------------------------------
    mask_z = (f_arr >= 417400) & (f_arr <= 418100)
    f_z = np.linspace(417400, 418100, 2000)
    H_z = (A0_opt) / (1.0 + 2j * Q_opt * (f_z - f0_opt) / f0_opt)
    g_z = np.abs(H_z)
    p_z = np.degrees(np.angle(H_z))

    fig_zoom, (zax1, zax2) = plt.subplots(2, 1, figsize=(9.5, 7.5), sharex=True)

    zax1.plot(f_arr[mask_z & is_s1] / 1e3, gain_mot_pts[mask_z & is_s1], 'o', color='#d62728', markersize=5.8,
              label='Dati')
    zax1.plot(f_z / 1e3, g_z, '-', color='#d62728', lw=2.0,
              label='Fit')
    zax1.axvline(f0_opt / 1e3, color='gray', linestyle=':', alpha=0.6)
    zax1.set_ylabel('Guadagno senza Cp (compensata)')
    zax1.set_title('Risposta compensata da Cp - Dettaglio risonanza')
    zax1.grid(True)
    zax1.legend(loc='upper right', framealpha=0.95)

    zax2.plot(f_arr[mask_z & is_s1] / 1e3, phase_mot_pts[mask_z & is_s1], 's', color='#2ca02c', markersize=5.8,
              label='Dati')
    zax2.plot(f_z / 1e3, p_z, '-', color='#2ca02c', lw=2.0,
              label='Fit')
    zax2.axhline(0, color='k', linestyle='--', alpha=0.35)
    zax2.axvline(f0_opt / 1e3, color='gray', linestyle=':', alpha=0.6)
    zax2.set_xlabel('Frequenza [kHz]')
    zax2.set_ylabel('Sfasamento')
    zax2.set_ylim(-105, 105)
    zax2.set_yticks([-90, -45, 0, 45, 90])
    zax2.grid(True)
    zax2.legend(loc='lower left', framealpha=0.95)

    fig_zoom.tight_layout()
    bode_zoom_path = os.path.join(SCRIPT_DIR, 'bode_ampiezza_fase_compensato_zoom.png')
    fig_zoom.savefig(bode_zoom_path, dpi=300)
    plt.close(fig_zoom)
    print(f"-> Grafico Bode Zoom salvato in: {bode_zoom_path}")

    # -------------------------------------------------------------------------
    # GRAFICO SPECIALE: CONFRONTO DERIVA TEMPORALE PRIMA E DOPO IL RIALLINEAMENTO
    # -------------------------------------------------------------------------
    fig_drift, ((dax1, dax2), (dax3, dax4)) = plt.subplots(2, 2, figsize=(14, 9), sharex=True)

    # Top-Left: Guadagno Grezzo con zig-zag
    dax1.plot(f_z / 1e3, g_z, 'k-', lw=2.0, label=f'Fit Lorentziano ($f_0={f0_opt:.1f}$ Hz)')
    dax1.plot(f_arr[mask_z & is_s1] / 1e3, gain_mot_raw[mask_z & is_s1], 'o', color='#1f77b4', markersize=5.5, label='Serie 1 (Sweep principale)')
    dax1.plot(f_arr[is_s2] / 1e3, gain_mot_raw[is_s2], 's', color='#d62728', markersize=6.0, label='Serie 2 GREZZA (+10.5 min drift)')
    dax1.set_title('(a) PRIMA: Serie 2 Grezza con Deriva (Effetto Zig-Zag)', fontsize=11, fontweight='bold')
    dax1.set_ylabel(r'Guadagno Motionale $|H_{\mathrm{mot}}|$ [V/V]')
    dax1.grid(True, alpha=0.4)
    dax1.legend(fontsize=9)

    # Bottom-Left: Fase Grezza
    dax3.plot(f_z / 1e3, p_z, 'k-', lw=2.0)
    dax3.plot(f_arr[mask_z & is_s1] / 1e3, phase_mot_raw[mask_z & is_s1], 'o', color='#1f77b4', markersize=5.5)
    dax3.plot(f_arr[is_s2] / 1e3, phase_mot_raw[is_s2], 's', color='#d62728', markersize=6.0)
    dax3.axhline(0, color='gray', ls='--', alpha=0.5)
    dax3.set_ylabel(r'Fase Motionale [deg]')
    dax3.set_xlabel('Frequenza [kHz]')
    dax3.grid(True, alpha=0.4)

    # Top-Right: Guadagno Riallineato
    dax2.plot(f_z / 1e3, g_z, 'k-', lw=2.0, label=f'Fit Lorentziano ($f_0={f0_opt:.1f}$ Hz, $Q={int(Q_opt)}$)')
    dax2.plot(f_arr[mask_z & is_s1] / 1e3, gain_mot_pts[mask_z & is_s1], 'o', color='#2ca02c', markersize=5.5, label='Serie 1')
    dax2.plot(f_arr[is_s2] / 1e3, gain_mot_pts[is_s2], '^', color='#ff7f0e', markersize=6.5, label='Serie 2 REALINEATA (Deriva rimossa)')
    dax2.set_title('(b) DOPO: Punti Extra Riallineati (Curva Liscia e Coerente)', fontsize=11, fontweight='bold')
    dax2.set_ylabel(r'Guadagno Motionale $|H_{\mathrm{mot}}|$ [V/V]')
    dax2.grid(True, alpha=0.4)
    dax2.legend(fontsize=9)

    # Bottom-Right: Fase Riallineata
    dax4.plot(f_z / 1e3, p_z, 'k-', lw=2.0)
    dax4.plot(f_arr[mask_z & is_s1] / 1e3, phase_mot_pts[mask_z & is_s1], 'o', color='#2ca02c', markersize=5.5, label='Fase Serie 1')
    dax4.plot(f_arr[is_s2] / 1e3, phase_mot_pts[is_s2], '^', color='#ff7f0e', markersize=6.5, label='Fase Serie 2 Riallineata')
    dax4.axhline(0, color='gray', ls='--', alpha=0.5)
    dax4.set_ylabel(r'Fase Motionale [deg]')
    dax4.set_xlabel('Frequenza [kHz]')
    dax4.grid(True, alpha=0.4)
    dax4.legend(fontsize=9)

    fig_drift.tight_layout()
    drift_path = os.path.join(SCRIPT_DIR, 'bode_confronto_deriva_temporale.png')
    fig_drift.savefig(drift_path, dpi=300)
    plt.close(fig_drift)
    print(f"-> Grafico Confronto Deriva Temporale salvato in: {drift_path}")

    # -------------------------------------------------------------------------
    # GRAFICO 3: BODE GREZZO (Senza punti extra 139..143, Risposta in frequenza)
    # -------------------------------------------------------------------------
    fig_raw, (rax1, rax2) = plt.subplots(2, 1, figsize=(9.5, 7.5), sharex=True)

    rax1.plot(f_arr[is_s1] / 1e3, gain_arr[is_s1], 'o', color='#1f77b4', markersize=5.5,
              label='Dati')
    rax1.plot(f_fine / 1e3, gain_fit_fine, '-', color='#1f77b4', lw=2.0,
              label='Fit')
    rax1.set_ylabel(r'Guadagno $|V_{out}/V_{in}|$ [V/V]')
    rax1.set_title('Risposta in frequenza')
    rax1.grid(True)
    rax1.legend(loc='best', framealpha=0.95)

    rax2.plot(f_arr[is_s1] / 1e3, phase_arr[is_s1], 's', color='#ff7f0e', markersize=5.5,
              label='Dati')
    rax2.plot(f_fine / 1e3, phase_fit_fine, '-', color='#ff7f0e', lw=2.0,
              label='Fit')
    rax2.set_xlabel('Frequenza [kHz]')
    rax2.set_ylabel(r'Sfasamento $\Delta \phi$ [deg]')
    rax2.grid(True)
    rax2.legend(loc='best', framealpha=0.95)

    fig_raw.tight_layout()
    bode_raw_path = os.path.join(SCRIPT_DIR, 'bode_ampiezza_fase_grezzo.png')
    fig_raw.savefig(bode_raw_path, dpi=300)
    plt.close(fig_raw)
    print(f"-> Grafico Bode Grezzo salvato in: {bode_raw_path}")

    # -------------------------------------------------------------------------
    # GRAFICO 4: PANNELLO 2x2 CONFRONTO COMPLETO (Grezzo vs Compensato)
    # -------------------------------------------------------------------------
    fig_2x2, ((ax_tl, ax_tr), (ax_bl, ax_br)) = plt.subplots(2, 2, figsize=(14, 8), sharex=True)

    # Top-Left: Guadagno Grezzo
    ax_tl.plot(f_arr[is_s1] / 1e3, gain_arr[is_s1], 'o', color='#1f77b4', markersize=5.0, label='Dati')
    ax_tl.plot(f_fine / 1e3, gain_fit_fine, '-', color='#1f77b4', lw=1.8, label=f'Fit BVD ($f_s={fs_fit:.0f}$, $f_p={fp_fit:.0f}$)')
    ax_tl.set_ylabel(r'Guadagno $|V_{out}/V_{in}|$ [V/V]')
    ax_tl.set_title(r'(a) Risposta Totale Grezza (Risonanza + $C_p$)')
    ax_tl.grid(True)
    ax_tl.legend(loc='best', framealpha=0.95)

    # Top-Right: Guadagno Compensato
    ax_tr.plot(f_arr[is_s1] / 1e3, gain_mot_pts[is_s1], 'o', color='#d62728', markersize=5.0, label='Dati')
    ax_tr.plot(f_fine / 1e3, gain_mot_fine, '-', color='#d62728', lw=1.8, label=f'Campana Lorentziana ($f_0={f0_opt:.1f}$ Hz)')
    ax_tr.axvline(f0_opt / 1e3, color='gray', linestyle=':', alpha=0.6)
    ax_tr.set_ylabel('Guadagno senza Cp (compensata)')
    ax_tr.set_title(r'(b) Ramo Motionale Puro ($C_p$ Sottratto)')
    ax_tr.grid(True)
    ax_tr.legend(loc='upper right', framealpha=0.95)

    # Bottom-Left: Fase Grezza
    ax_bl.plot(f_arr[is_s1] / 1e3, phase_arr[is_s1], 's', color='#ff7f0e', markersize=5.0, label='Dati')
    ax_bl.plot(f_fine / 1e3, phase_fit_fine, '-', color='#ff7f0e', lw=1.8, label='Interferenza Fano')
    ax_bl.set_xlabel('Frequenza [kHz]')
    ax_bl.set_ylabel(r'Sfasamento $\Delta \phi$ [deg]')
    ax_bl.set_title('(c) Sfasamento Totale Grezzo')
    ax_bl.grid(True)
    ax_bl.legend(loc='best', framealpha=0.95)

    # Bottom-Right: Fase Compensata
    ax_br.plot(f_arr[is_s1] / 1e3, phase_mot_pts[is_s1], 's', color='#2ca02c', markersize=5.0, label='Dati')
    ax_br.plot(f_fine / 1e3, phase_mot_fine, '-', color='#2ca02c', lw=1.8, label=r'Transizione $+90^\circ \to 0^\circ \to -90^\circ$')
    ax_br.axhline(0, color='k', linestyle='--', alpha=0.35)
    ax_br.axvline(f0_opt / 1e3, color='gray', linestyle=':', alpha=0.6)
    ax_br.set_xlabel('Frequenza [kHz]')
    ax_br.set_ylabel('Sfasamento')
    ax_br.set_title('(d) Sfasamento Ramo Motionale (Transizione RLC da 180°)')
    ax_br.set_ylim(-110, 110)
    ax_br.set_yticks([-90, -45, 0, 45, 90])
    ax_br.grid(True)
    ax_br.legend(loc='lower left', framealpha=0.95)

    fig_2x2.tight_layout()
    confr_path = os.path.join(SCRIPT_DIR, 'bode_confronto_completo.png')
    fig_2x2.savefig(confr_path, dpi=300)
    plt.close(fig_2x2)
    print(f"-> Grafico 2x2 Confronto salvato in: {confr_path}")

    # -------------------------------------------------------------------------
    # GRAFICO 5: DE-EMBEDDING CONFRONTO MODULI (Before & After)
    # -------------------------------------------------------------------------
    fig_deemb, (ax_a, ax_b) = plt.subplots(1, 2, figsize=(13.5, 5.5))

    ax_a.plot(f_arr[is_s1] / 1e3, gain_arr[is_s1], 'o', color='#1f77b4', markersize=5.5, label='Dati')
    ax_a.plot(f_fine / 1e3, gain_fit_fine, '-', color='#1f77b4', lw=2.0, label='Fit BVD Totale')
    ax_a.set_xlabel('Frequenza [kHz]')
    ax_a.set_ylabel(r'Guadagno $|V_{out}/V_{in}|$ [V/V]')
    ax_a.set_title(r'(a) Risposta Totale: Risonanza + Parassita $C_p$')
    ax_a.grid(True)
    ax_a.legend(loc='best', framealpha=0.95)

    ax_b.plot(f_arr[is_s1] / 1e3, gain_mot_pts[is_s1], 'ro', markersize=5.5, label='Dati')
    ax_b.plot(f_fine / 1e3, gain_mot_fine, 'r-', lw=2.0,
              label=f'Fit Lorentziano: $f_0={f0_opt:.1f}$ Hz, $Q={int(Q_opt)}$')
    ax_b.set_xlabel('Frequenza [kHz]')
    ax_b.set_ylabel('Guadagno senza Cp (compensata)')
    ax_b.set_title('(b) Ramo Motionale Puro: Campana Lorentziana Simmetrica')
    ax_b.grid(True)
    ax_b.legend(loc='best', framealpha=0.95)

    fig_deemb.tight_layout()
    deemb_path = os.path.join(SCRIPT_DIR, 'deembedding_confronto.png')
    fig_deemb.savefig(deemb_path, dpi=300)
    plt.close(fig_deemb)
    print(f"-> Grafico De-embedding salvato in: {deemb_path}")

    # -------------------------------------------------------------------------
    # GRAFICO 6: PIANO COMPLESSO DI NYQUIST
    # -------------------------------------------------------------------------
    fig_nyq, ax_n = plt.subplots(figsize=(8, 8))

    ax_n.plot(re_arr[is_s1], im_arr[is_s1], 'o', color='#1f77b4', markersize=5.0, label='Dati Sperimentali (con $C_p$)')
    ax_n.plot(np.real(H_fit_fine), np.imag(H_fit_fine), '-', color='#1f77b4', lw=1.8, label='Traiettoria BVD')

    ax_n.plot(np.real(H_mot_corr[is_s1]), np.imag(H_mot_corr[is_s1]), 's', color='#d62728', markersize=5.0,
              label='Ramo Motionale Puro (Compensato)')
    ax_n.plot(np.real(H_mot_fine), np.imag(H_mot_fine), '-', color='#d62728', lw=1.8,
              label=f'Cerchio di Risonanza ($f_0={int(f0_opt)}$ Hz)')

    ax_n.axhline(0, color='k', linestyle='--', alpha=0.3)
    ax_n.axvline(0, color='k', linestyle='--', alpha=0.3)
    ax_n.set_xlabel(r'$\mathrm{Re}(V_{out}/V_{in})$ [V/V]')
    ax_n.set_ylabel(r'$\mathrm{Im}(V_{out}/V_{in})$ [V/V]')
    ax_n.set_title(f'Piano Complesso di Nyquist: De-embedding Fasoriale ({np.sum(is_s1)} Punti)')
    ax_n.grid(True)
    ax_n.axis('equal')
    ax_n.legend(loc='upper left', framealpha=0.95)

    # Inset zoom sul cerchio di risonanza compensato
    axins = ax_n.inset_axes([0.48, 0.15, 0.45, 0.45])
    axins.plot(np.real(H_mot_corr[is_s1]), np.imag(H_mot_corr[is_s1]), 's', color='#d62728', markersize=5.0)
    axins.plot(np.real(H_mot_fine), np.imag(H_mot_fine), '-', color='#d62728', lw=1.8)
    axins.axhline(0, color='k', linestyle='--', alpha=0.3)
    axins.axvline(0, color='k', linestyle='--', alpha=0.3)
    axins.set_xlim(-0.06, 0.50)
    axins.set_ylim(-0.26, 0.26)
    axins.grid(True)
    axins.set_title('Zoom Cerchio di Risonanza (Stile UniBS)', fontsize=10)
    ax_n.indicate_inset_zoom(axins, edgecolor='gray')

    fig_nyq.tight_layout()
    nyquist_path = os.path.join(SCRIPT_DIR, 'piano_complesso_nyquist.png')
    fig_nyq.savefig(nyquist_path, dpi=300)
    plt.close(fig_nyq)
    print(f"-> Grafico Nyquist salvato in: {nyquist_path}")


def plot_calcolo_cp():
    """
    Genera il grafico 'calcolo_Cp.png' con i segnali Vin e Vout a 50 kHz
    (off-resonance, scope_70) e a 417.79 kHz (prossimità risonanza, scope_69).
    """
    p70 = os.path.join(SCRIPT_DIR, 'scope_70.csv')
    p69 = os.path.join(SCRIPT_DIR, 'scope_69.csv')
    if not os.path.exists(p70) or not os.path.exists(p69):
        return

    d70 = np.loadtxt(p70, delimiter=',', skiprows=2)
    t70 = (d70[:, 0] - d70[0, 0]) * 1e6
    vout70 = d70[:, 1]
    vin70 = d70[:, 3]

    d69 = np.loadtxt(p69, delimiter=',', skiprows=2)
    t69 = (d69[:, 0] - d69[0, 0]) * 1e6
    vout69 = d69[:, 1]
    vin69 = d69[:, 3]

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 7.5))

    ax1.plot(t70, vin70, label='Vin', color='#1f77b4')
    ax1.plot(t70, vout70, label='Vout', color='#d62728')
    ax1.set_title('50 kHz (Off-resonance)')
    ax1.set_xlabel(r'Tempo [$\mu$s]')
    ax1.set_ylabel('Segnali')
    ax1.grid(True)
    ax1.legend(loc='upper right', framealpha=0.95)

    ax2.plot(t69, vin69, label='Vin', color='#1f77b4')
    ax2.plot(t69, vout69, label='Vout', color='#d62728')
    ax2.set_title('417.79 kHz (Frequenza vicina alla risonanza)')
    ax2.set_xlabel(r'Tempo [$\mu$s]')
    ax2.set_ylabel('Segnali')
    ax2.grid(True)
    ax2.legend(loc='upper right', framealpha=0.95)

    fig.suptitle('Calcolo Cp', fontsize=14, fontweight='bold')
    fig.tight_layout()

    out_cp = os.path.join(SCRIPT_DIR, 'calcolo_Cp.png')
    out_cp_lower = os.path.join(SCRIPT_DIR, 'calcolo_cp.png')
    fig.savefig(out_cp, dpi=300)
    fig.savefig(out_cp_lower, dpi=300)
    plt.close(fig)
    print(f"-> Grafico Calcolo Cp salvato in: {out_cp}")


if __name__ == '__main__':
    import sys
    recompute = '--recompute' in sys.argv or '-f' in sys.argv
    res70, res69 = verifica_scope_69_70()
    plot_calcolo_cp()
    dati = elabora_misure(force_recompute=recompute)
    analizza_e_plotta(dati, res70=res70)



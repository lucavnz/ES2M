r"""
Script dedicato per la generazione rapida dei grafici:
1. campana_risonanza_A0_vs_freq.png (Campana di risonanza con f_in e con Delta f)
2. gallery_inviluppi_ringdown.png   (Esempi ringdown e fit dell'inviluppo)

Stile grafico:
- Ispirato al grafico di Bode grezzo (bode_ampiezza_fase_grezzo.png)
- Punti sperimentali dello stesso colore della curva di fit
- Nessun livello -3dB, nessuna riga viola, nessun box di annotazione
- Nomi degli assi e titoli senza grassetto, non caps
- Titoli: "Campana di risonanza con f_in" e "Campana di risonanza con \Delta f = f_in - f_s"
- Asse Y: "Ampiezza decadimento A_0 [mV]"
- Galleria: titolo globale "Esempi ringdown e fit dell'inviluppo", nessun titolo sui singoli grafici, nessuna legenda
"""

import os
import csv
import shutil
import numpy as np
import scipy.signal as signal
from scipy.optimize import curve_fit
import matplotlib.pyplot as plt

# -----------------------------------------------------------------------------
# IMPOSTAZIONI GRAFICHE GLOBALI (STILE BODE ACCADEMICO PULITO)
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

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MISURE_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '..', 'Misure'))
CSV_TABLE = os.path.join(SCRIPT_DIR, 'tabella_risultati_ringdown.csv')
ARTIFACT_DIR = r"C:\Users\lucaa\.gemini\antigravity-ide\brain\ec5d88fb-3a1f-4053-a354-563659895c42"

def exp_decay(t, A0, tau, offset):
    return A0 * np.exp(-t / tau) + offset

def lorentzian(f, A_max, f0, gamma, offset):
    return A_max * (0.5 * gamma)**2 / ((f - f0)**2 + (0.5 * gamma)**2) + offset

def plot_campana_risonanza():
    """Genera campana_risonanza_A0_vs_freq.png caricando tabella_risultati_ringdown.csv"""
    data = []
    with open(CSV_TABLE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            data.append({
                'file_num': int(row['File_Num']),
                'f_in': float(row['f_in_Hz']),
                'fs_rd': float(row['fs_rd_Hz']),
                'delta_f': float(row['delta_f_Hz']),
                'A0_mV': float(row['A0_mV'])
            })
    data = sorted(data, key=lambda x: x['f_in'])

    f_in_arr = np.array([r['f_in'] for r in data])
    delta_f_arr = np.array([r['delta_f'] for r in data])
    A0_arr = np.array([r['A0_mV'] for r in data])
    mean_fs = np.mean([r['fs_rd'] for r in data])

    p0_lor = [np.max(A0_arr), mean_fs, 130.0, 3.0]
    popt_lor, _ = curve_fit(lorentzian, f_in_arr, A0_arr, p0=p0_lor,
                            bounds=([10.0, 417800.0, 20.0, 0.0], [60.0, 417900.0, 400.0, 10.0]))
    f_dense = np.linspace(np.min(f_in_arr) - 50, np.max(f_in_arr) + 50, 1000)
    A0_dense_lor = lorentzian(f_dense, *popt_lor)
    delta_dense = f_dense - mean_fs

    fig, ax1 = plt.subplots(1, 1, figsize=(8.5, 5.2))

    # A0 vs f_in (Stile Bode grezzo: punti dello stesso colore del fit, niente bold, niente -3dB)
    ax1.plot(f_in_arr / 1e3, A0_arr, 'o', color='#1f77b4', markersize=5.5, label='Dati')
    ax1.plot(f_dense / 1e3, A0_dense_lor, '-', color='#1f77b4', lw=2.0, label='Fit')
    ax1.set_title(r'$A_0$ vs $f_{\mathrm{in}}$')
    ax1.set_xlabel(r'$f_{\mathrm{in}}$ [kHz]')
    ax1.set_ylabel(r'$A_0$ [mV]')
    ax1.set_ylim([0, 42])
    ax1.grid(True)
    ax1.legend(loc='upper right', framealpha=0.95)

    fig.tight_layout()
    out_path = os.path.join(SCRIPT_DIR, 'campana_risonanza_A0_vs_freq.png')
    fig.savefig(out_path, dpi=300)
    plt.close(fig)
    print(f"-> Grafico Campana di Risonanza salvato in: {out_path}")

    if os.path.exists(ARTIFACT_DIR):
        shutil.copy(out_path, os.path.join(ARTIFACT_DIR, 'campana_risonanza_A0_vs_freq.png'))

def process_scope_subset(num):
    filepath = os.path.join(MISURE_DIR, f"scope_{num}.csv")
    with open(filepath, 'r') as f:
        reader = csv.reader(f)
        next(reader)
        next(reader)
        rows = [[float(x) for x in r[:4]] for r in reader if len(r) >= 4 and r[1] != '']

    data = np.array(rows)
    t_raw = data[:, 0]
    c1 = data[:, 1]
    c2 = data[:, 2]

    poly = np.polyfit(np.arange(len(t_raw)), t_raw, 1)
    dt = poly[0]
    fs = 1.0 / dt

    gate_low_idx = np.where(c2 < 1.0)[0]
    idx_off = gate_low_idx[0]
    t_off = t_raw[idx_off]

    blank_samples = int(30e-6 * fs)
    idx_start = idx_off + blank_samples

    t_rd = t_raw[idx_start:] - t_off
    y_raw = c1[idx_start:]
    y_ac = y_raw - np.mean(y_raw)

    analytic = signal.hilbert(y_ac)
    env_raw = np.abs(analytic)
    b_lp, a_lp = signal.butter(2, 5000.0 / (fs / 2.0))
    env_filt = signal.filtfilt(b_lp, a_lp, env_raw)

    p0 = [env_filt[0], 0.0024, 0.0]
    bounds = ([0.0, 0.0005, -0.05], [0.5, 0.010, 0.05])
    popt, _ = curve_fit(exp_decay, t_rd, env_filt, p0=p0, bounds=bounds)
    fit_vals = exp_decay(t_rd, *popt)

    return {
        't_rd_ms': t_rd * 1e3,
        'y_ac_mV': y_ac * 1e3,
        'env_mV': env_filt * 1e3,
        'fit_mV': fit_vals * 1e3
    }

def plot_gallery_inviluppi():
    """Genera gallery_inviluppi_ringdown.png ordinato dal più grande al più piccolo con titoli puliti."""
    selected_files = [19, 13, 27, 17]
    fig, axes = plt.subplots(2, 2, figsize=(13.5, 8.2), sharex=True, sharey=True)

    file_info = {}
    with open(CSV_TABLE, 'r', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            file_info[int(r['File_Num'])] = {
                'fin': float(r['f_in_Hz']),
                'A0': float(r['A0_mV'])
            }

    for i, (ax, num) in enumerate(zip(axes.flatten(), selected_files)):
        res = process_scope_subset(num)
        fin_val = file_info[num]['fin']
        a0_val = file_info[num]['A0']

        l1, = ax.plot(res['t_rd_ms'], res['y_ac_mV'], color='#bdc3c7', alpha=0.6, linewidth=0.6, label='Segnale misurato')
        l2, = ax.plot(res['t_rd_ms'], res['env_mV'], color='#e67e22', linewidth=1.8, label='Inviluppo di Hilbert')
        l3, = ax.plot(res['t_rd_ms'], res['fit_mV'], color='#c0392b', linestyle='--', linewidth=2.0, label='Fit esponenziale')

        ax.set_title(rf'$f_{{\mathrm{{in}}}} = {fin_val:.0f}\,\mathrm{{Hz}}$ ($A_0 = {a0_val:.1f}\,\mathrm{{mV}}$)')
        ax.grid(True)
        ax.set_xlim([0, 4.5])
        ax.set_ylim([-45, 45])

        if i == 0:
            ax.legend(handles=[l1, l2, l3], loc='upper right', framealpha=0.95)

    for ax in axes[-1, :]:
        ax.set_xlabel('Tempo dal taglio del gate [ms]')
    for ax in axes[:, 0]:
        ax.set_ylabel('Uscita TIA [mV]')

    fig.suptitle("Esempi ringdown e fit dell'inviluppo", fontsize=12.5)
    fig.tight_layout()
    fig.subplots_adjust(top=0.92)

    out_path = os.path.join(SCRIPT_DIR, 'gallery_inviluppi_ringdown.png')
    fig.savefig(out_path, dpi=300)
    plt.close(fig)
    print(f"-> Grafico Galleria Inviluppi salvato in: {out_path}")

    if os.path.exists(ARTIFACT_DIR):
        shutil.copy(out_path, os.path.join(ARTIFACT_DIR, 'gallery_inviluppi_ringdown.png'))

def plot_deriva_frequenza_e_tau():
    """Genera deriva_frequenza_e_tau.png con f0 in alto e tau/Q combinati in basso, tick asse X in Hertz interi."""
    data = []
    with open(CSV_TABLE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            data.append({
                'file_num': int(row['File_Num']),
                'f_in': float(row['f_in_Hz']),
                'fs': float(row['fs_rd_Hz']),
                'tau': float(row['tau_ms']),
                'Q': float(row['Q_factor'])
            })

    # Esclusione delle frequenze 417260 e 417460 Hz (estremi a basso SNR)
    data_filtered = [d for d in data if int(round(d['f_in'])) not in (417260, 417460)]

    # Ordinamento per frequenza di eccitazione crescente (da più bassa a più alta)
    data_sorted = sorted(data_filtered, key=lambda x: x['f_in'])
    nums = [d['file_num'] for d in data_sorted]
    fs_arr = np.array([d['fs'] for d in data_sorted])
    tau_arr = np.array([d['tau'] for d in data_sorted])
    q_arr = np.array([d['Q'] for d in data_sorted])
    fin_arr = np.array([d['f_in'] for d in data_sorted])

    mean_fs = np.mean(fs_arr)
    delta_max_min = np.max(fs_arr) - np.min(fs_arr)
    mean_tau = np.mean(tau_arr)
    mean_q = np.mean(q_arr)

    # Etichette asse X in Hertz interi ordinati
    xtick_labels = [f"{int(round(f))}" for f in fin_arr]

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(13.5, 7.5), sharex=True)

    # 1. Grafico superiore: Frequenza di risonanza f1 vs f_in
    ax1.plot(range(len(nums)), fs_arr, 'o-', color='#1f77b4', markersize=5.5,
             label=rf'$f_1$ (media: {mean_fs:.2f} Hz)')
    ax1.set_title(rf'Stabilità di $f_1$ al variare di $f_{{\mathrm{{in}}}}$ (escursione max-min: {delta_max_min:.1f} Hz)')
    ax1.set_ylabel(r'$f_1$ [Hz]')
    ax1.ticklabel_format(useOffset=False, style='plain', axis='y')
    ax1.set_ylim([mean_fs - 10, mean_fs + 10])
    ax1.grid(True)
    ax1.legend(loc='lower left', framealpha=0.95)

    # 2. Grafico inferiore: Tau e Q assieme sullo stesso grafico
    ax2_twin = ax2.twinx()

    l1 = ax2.plot(range(len(nums)), tau_arr, 's-', color='#27ae60', linewidth=1.8, markersize=5.5,
                  label=rf'$\tau$ (media: {mean_tau:.3f} ms)')
    l2 = ax2_twin.plot(range(len(nums)), q_arr, '^-', color='#8e44ad', linewidth=1.8, markersize=5.5,
                       label=rf'$Q$ (media: {mean_q:.0f})')

    tau_min, tau_max = 2.0, 2.8
    ax2.set_ylim([tau_min, tau_max])
    ax2_twin.set_ylim([tau_min * np.pi * mean_fs * 1e-3, tau_max * np.pi * mean_fs * 1e-3])

    ax2.set_ylabel(r'Costante di decadimento $\tau$ [ms]', color='#27ae60')
    ax2_twin.set_ylabel(r'Fattore di qualità $Q$', color='#8e44ad')
    ax2.tick_params(axis='y', labelcolor='#27ae60')
    ax2_twin.tick_params(axis='y', labelcolor='#8e44ad')

    ax2.set_title(r'$\tau$ e $Q$ vs $f_{\mathrm{in}}$')
    ax2.set_xlabel(r'Frequenza di eccitazione $f_{\mathrm{in}}$ [Hz]')
    ax2.set_xticks(range(len(nums)))
    ax2.set_xticklabels(xtick_labels, rotation=45, ha='right')
    ax2.grid(True)

    lines = l1 + l2
    labels = [l.get_label() for l in lines]
    ax2.legend(lines, labels, loc='upper right', framealpha=0.95)

    plt.tight_layout()

    out_path = os.path.join(SCRIPT_DIR, 'deriva_frequenza_e_tau.png')
    fig.savefig(out_path, dpi=300, bbox_inches='tight')
    plt.close(fig)
    print(f"-> Grafico Deriva e Invarianza salvato in: {out_path}")

    if os.path.exists(ARTIFACT_DIR):
        shutil.copy(out_path, os.path.join(ARTIFACT_DIR, 'deriva_frequenza_e_tau.png'))

def main():
    print("=" * 70)
    print("  GENERAZIONE RAPIDA GRAFICI RISPOSTA IN FREQUENZA E RINGDOWN")
    print("=" * 70)
    plot_campana_risonanza()
    plot_gallery_inviluppi()
    plot_deriva_frequenza_e_tau()
    print("Completato con successo!")

if __name__ == '__main__':
    main()

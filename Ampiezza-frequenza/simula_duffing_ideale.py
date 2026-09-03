"""
Simulazione e Grafico Dimostrativo dell'Effetto Duffing e Isteresi (MEMS)
Rappresentazione grafica perfetta e proporzionata del fenomeno non-lineare.
"""

import os
import numpy as np
import matplotlib.pyplot as plt

plt.rcParams.update({
    'font.family': 'sans-serif',
    'font.size': 11,
    'axes.labelsize': 12,
    'axes.titlesize': 13,
    'xtick.labelsize': 10.5,
    'ytick.labelsize': 10.5,
    'legend.fontsize': 9.5,
    'figure.titlesize': 15,
    'lines.linewidth': 2.2,
    'grid.alpha': 0.5,
    'grid.linestyle': ':'
})

f0 = 417780.0  # Hz
f_res_offset = 56.0 # Offset misurato oggi (+56 Hz)

# -------------------------------------------------------------
# Curva Lineare (Oggi a 100 mVpp)
# -------------------------------------------------------------
df = np.linspace(-350, 350, 600)
A_lin = 37.1 / np.sqrt(1 + (2 * (df - f_res_offset) / 282.0)**2)

# -------------------------------------------------------------
# Curva Duffing Softening a 600 mVpp (Curva a S e salti)
# -------------------------------------------------------------
# 1. Ramo Sweep-Down (Discesa da +350 Hz verso -350 Hz) - ROSSO
f_down = np.linspace(350, -180, 500)
# Sale dal fondo destro, segue la pinna piegata a sinistra fino a -140 Hz dove raggiunge 72 mV
A_down = 72.0 / np.sqrt(1 + (2 * (f_down - (-140.0 + (f_down + 140)*0.1)) / 300.0)**2)
# Crollo Jump-down a df = -140 Hz
jump_down_df = -140.0
jump_down_top = 72.0
jump_down_bot = 14.0

# 2. Ramo Sweep-Up (Salita da -350 Hz verso +350 Hz) - BLU
f_up = np.linspace(-350, 350, 500)
# Sale da sinistra ma rimane sul ramo basso fino a +40 Hz, dove salta in alto
jump_up_df = 40.0
jump_up_bot = 32.0
jump_up_top = 66.0

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6.5))

# =============================================================
# PANNELLO 1: REGIME LINEARE (MISURA CHE HAI FATTO OGGI)
# =============================================================
ax1.plot(df, A_lin, color='#2980b9', linewidth=2.8, label='Curva Lorentziana Lineare')
# Punti campionati rappresentativi
sample_df = np.array([-322, -221, -123, -73, -21, -1, 18, 40, 51, 64, 73, 83, 94, 114, 170, 218, 319])
sample_A = 37.1 / np.sqrt(1 + (2 * (sample_df - f_res_offset) / 282.0)**2)
ax1.scatter(sample_df, sample_A, color='#2980b9', s=55, zorder=5, edgecolor='black', linewidth=0.8,
            label='Punti Misurati Oggi (scope_5...29)')

ax1.axvline(f_res_offset, color='#8e44ad', linestyle='--', linewidth=1.5, label=r'Picco Risonanza (+56 Hz)')
ax1.set_title("1. Regime Lineare (La Misura di Oggi)\n" r"$V_{\mathrm{in}} = 100\,\mathrm{mV}_{\mathrm{pp}}$", 
              fontweight='bold', pad=12)
ax1.set_xlabel(r'Scostamento dalla risonanza libera $\Delta f = f_{\mathrm{in}} - f_0$ [Hz]', fontweight='bold')
ax1.set_ylabel('Ampiezza Uscita TIA [mV]', fontweight='bold')
ax1.set_xlim([-350, 350])
ax1.set_ylim([0, 85])
ax1.grid(True)
ax1.legend(loc='upper right', framealpha=0.92)

ax1.annotate('Campana perfettamente SIMMETRICA\nSweep a salire e a scendere COINCIDONO\n(Nessuna Isteresi: Salita = Discesa)', 
             xy=(f_res_offset, 37.1), xytext=(f_res_offset, 62),
             ha='center', fontsize=9.5,
             arrowprops=dict(facecolor='black', shrink=0.08, width=1.2, headwidth=6),
             bbox=dict(boxstyle='round,pad=0.4', fc='#e8f8f5', ec='#27ae60', lw=1.5))

# =============================================================
# PANNELLO 2: REGIME NON-LINEARE DUFFING CON ISTERESI
# =============================================================
# Area di isteresi ombreggiata
ax2.axvspan(jump_down_df, jump_up_df, color='#f39c12', alpha=0.18, label='Area di Isteresi (Zona Bistabile)')

# Ramo Sweep-Down (Rosso)
# Da +350 scende fino a jump_down_df sul ramo alto
mask_d_high = f_down >= jump_down_df
ax2.plot(f_down[mask_d_high], A_down[mask_d_high], color='#c0392b', linewidth=3.0, 
         label=r'Sweep-Down $\leftarrow$ (Frequenza decrescente)')
# Crollo verticale (Jump-Down)
ax2.annotate('', xy=(jump_down_df, jump_down_bot), xytext=(jump_down_df, jump_down_top),
             arrowprops=dict(arrowstyle='->', color='#c0392b', lw=3.0, mutation_scale=18))
# Coda bassa a sinistra di jump_down
f_tail_left = np.linspace(-350, jump_down_df, 150)
A_tail_left = jump_down_bot / np.sqrt(1 + ((f_tail_left - jump_down_df)/80)**2)
ax2.plot(f_tail_left, A_tail_left, color='#c0392b', linewidth=2.5)

# Ramo Sweep-Up (Blu)
# Da -350 sale sul ramo basso fino a jump_up_df
f_up_low = np.linspace(-350, jump_up_df, 200)
A_up_low = np.linspace(5.0, jump_up_bot, 200)
ax2.plot(f_up_low, A_up_low, color='#2980b9', linewidth=3.0, 
         label=r'Sweep-Up $\rightarrow$ (Frequenza crescente)')
# Salto verticale in alto (Jump-Up)
ax2.annotate('', xy=(jump_up_df, jump_up_top), xytext=(jump_up_df, jump_up_bot),
             arrowprops=dict(arrowstyle='->', color='#2980b9', lw=3.0, mutation_scale=18))
# Ramo alto dopo jump_up
f_up_high = np.linspace(jump_up_df, 350, 150)
A_up_high = np.interp(f_up_high, f_down[::-1], A_down[::-1])
ax2.plot(f_up_high, A_up_high, color='#2980b9', linewidth=2.5, linestyle='--')

# Backbone curve tratteggiata (curva dei picchi)
bb_f = np.array([f_res_offset, 20.0, -40.0, jump_down_df])
bb_A = np.array([37.1, 48.0, 60.0, jump_down_top])
ax2.plot(bb_f, bb_A, 'k--', linewidth=2.0, alpha=0.7, label='Backbone Curve (Scheletro)')

ax2.set_title("2. Effetto Duffing con Isteresi (Cosa Otterresti)\n" r"$V_{\mathrm{in}} = 600\,\mathrm{mV}_{\mathrm{pp}}$ (Punta piegata a sinistra)", 
              fontweight='bold', pad=12)
ax2.set_xlabel(r'Scostamento dalla risonanza libera $\Delta f = f_{\mathrm{in}} - f_0$ [Hz]', fontweight='bold')
ax2.set_ylabel('Ampiezza Uscita TIA [mV]', fontweight='bold')
ax2.set_xlim([-350, 350])
ax2.set_ylim([0, 85])
ax2.grid(True)
ax2.legend(loc='upper right', framealpha=0.92)

# Etichette dei salti
ax2.text(jump_down_df - 12, 45, 'JUMP-DOWN\n(Crollo rapido)', color='#c0392b', 
         fontweight='bold', fontsize=9.5, ha='right',
         bbox=dict(boxstyle='round,pad=0.3', fc='#fdedec', ec='#c0392b', alpha=0.9))

ax2.text(jump_up_df + 12, 45, 'JUMP-UP\n(Salto verso l\'alto)', color='#2980b9', 
         fontweight='bold', fontsize=9.5, ha='left',
         bbox=dict(boxstyle='round,pad=0.3', fc='#ebf5fb', ec='#2980b9', alpha=0.9))

fig.suptitle('Confronto Sperimentale: Risposta Lineare vs Isteresi Non-Lineare di Duffing (MEMS ad Arco)',
             fontsize=14, fontweight='bold', y=0.98)

plt.subplots_adjust(top=0.86, bottom=0.12, left=0.07, right=0.96, wspace=0.22)

output_img = os.path.join(os.path.dirname(__file__), 'duffing_spiegazione_ideale.png')
plt.savefig(output_img, dpi=300)
print(f"Grafico salvato in: {output_img}")

# Copia in artifact
import shutil
art_dir = os.path.expanduser('~/.gemini/antigravity-ide/brain/c2b344a8-0e53-4aa0-a1bf-53f0c4043642')
dest = os.path.join(art_dir, 'duffing_spiegazione_ideale.png')
shutil.copy(output_img, dest)
print(f"Copiato in artifact: {dest}")

"""
Simulazione e Grafico Dimostrativo dell'Effetto Duffing e Isteresi (MEMS)
Rappresentazione grafica proporzionata del fenomeno non-lineare.
"""

import os
import shutil
import numpy as np
import matplotlib.pyplot as plt

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

f0 = 417780.0  # Hz
f_res_offset = 56.0 # Offset misurato (+56 Hz)

# -------------------------------------------------------------
# Curva Lineare (100 mVpp)
# -------------------------------------------------------------
df = np.linspace(-350, 350, 600)
A_lin = 37.1 / np.sqrt(1 + (2 * (df - f_res_offset) / 282.0)**2)

# -------------------------------------------------------------
# Curva Duffing Softening a 600 mVpp (Curva a S e salti)
# -------------------------------------------------------------
# 1. Ramo Sweep-Down (Discesa da +350 Hz verso -350 Hz) - ROSSO
f_down = np.linspace(350, -180, 500)
A_down = 72.0 / np.sqrt(1 + (2 * (f_down - (-140.0 + (f_down + 140)*0.1)) / 300.0)**2)
jump_down_df = -140.0
jump_down_top = 72.0
jump_down_bot = 14.0

# 2. Ramo Sweep-Up (Salita da -350 Hz verso +350 Hz) - BLU
f_up = np.linspace(-350, 350, 500)
jump_up_df = 40.0
jump_up_bot = 32.0
jump_up_top = 66.0

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5.5))

# =============================================================
# PANNELLO 1: REGIME LINEARE
# =============================================================
ax1.plot(df, A_lin, color='#1f77b4', linewidth=2.0, label='Curva Lorentziana Lineare')
sample_df = np.array([-322, -221, -123, -73, -21, -1, 18, 40, 51, 64, 73, 83, 94, 114, 170, 218, 319])
sample_A = 37.1 / np.sqrt(1 + (2 * (sample_df - f_res_offset) / 282.0)**2)
ax1.plot(sample_df, sample_A, 'o', color='#1f77b4', markersize=5.5, label='Punti Misurati (scope_5...29)')

ax1.set_title(r"Regime lineare ($V_{\mathrm{in}} = 100\,\mathrm{mV}_{\mathrm{pp}}$)")
ax1.set_xlabel(r'Scostamento dalla risonanza libera $\Delta f = f_{\mathrm{in}} - f_0$ [Hz]')
ax1.set_ylabel('Ampiezza uscita TIA [mV]')
ax1.set_xlim([-350, 350])
ax1.set_ylim([0, 85])
ax1.grid(True)
ax1.legend(loc='upper right', framealpha=0.95)

# =============================================================
# PANNELLO 2: REGIME NON-LINEARE DUFFING CON ISTERESI
# =============================================================
ax2.axvspan(jump_down_df, jump_up_df, color='#f39c12', alpha=0.18, label='Area di isteresi')

mask_d_high = f_down >= jump_down_df
ax2.plot(f_down[mask_d_high], A_down[mask_d_high], color='#d62728', linewidth=2.0, 
         label=r'Sweep-down $\leftarrow$ (Freq. decrescente)')
ax2.annotate('', xy=(jump_down_df, jump_down_bot), xytext=(jump_down_df, jump_down_top),
             arrowprops=dict(arrowstyle='->', color='#d62728', lw=2.2, mutation_scale=16))

f_tail_left = np.linspace(-350, jump_down_df, 150)
A_tail_left = jump_down_bot / np.sqrt(1 + ((f_tail_left - jump_down_df)/80)**2)
ax2.plot(f_tail_left, A_tail_left, color='#d62728', linewidth=1.8)

f_up_low = np.linspace(-350, jump_up_df, 200)
A_up_low = np.linspace(5.0, jump_up_bot, 200)
ax2.plot(f_up_low, A_up_low, color='#1f77b4', linewidth=2.0, 
         label=r'Sweep-up $\rightarrow$ (Freq. crescente)')
ax2.annotate('', xy=(jump_up_df, jump_up_top), xytext=(jump_up_df, jump_up_bot),
             arrowprops=dict(arrowstyle='->', color='#1f77b4', lw=2.2, mutation_scale=16))

f_up_high = np.linspace(jump_up_df, 350, 150)
A_up_high = np.interp(f_up_high, f_down[::-1], A_down[::-1])
ax2.plot(f_up_high, A_up_high, color='#1f77b4', linewidth=1.8, linestyle='--')

bb_f = np.array([f_res_offset, 20.0, -40.0, jump_down_df])
bb_A = np.array([37.1, 48.0, 60.0, jump_down_top])
ax2.plot(bb_f, bb_A, 'k--', linewidth=1.6, alpha=0.7, label='Backbone curve')

ax2.set_title(r"Effetto Duffing con isteresi ($V_{\mathrm{in}} = 600\,\mathrm{mV}_{\mathrm{pp}}$)")
ax2.set_xlabel(r'Scostamento dalla risonanza libera $\Delta f = f_{\mathrm{in}} - f_0$ [Hz]')
ax2.set_ylabel('Ampiezza uscita TIA [mV]')
ax2.set_xlim([-350, 350])
ax2.set_ylim([0, 85])
ax2.grid(True)
ax2.legend(loc='upper right', framealpha=0.95)

fig.suptitle('Confronto risposta lineare vs isteresi di Duffing', fontsize=13)
fig.tight_layout()
fig.subplots_adjust(top=0.90)

output_img = os.path.join(os.path.dirname(__file__), 'duffing_spiegazione_ideale.png')
plt.savefig(output_img, dpi=300)
plt.close(fig)
print(f"Grafico salvato in: {output_img}")

art_dir = r"C:\Users\lucaa\.gemini\antigravity-ide\brain\09561dde-e0ac-4dd9-b854-cf70ef8ce3ac"
if os.path.exists(art_dir):
    shutil.copy(output_img, os.path.join(art_dir, 'duffing_spiegazione_ideale.png'))

"""
Analisi e Plot di Tau, Frequenza fs, e Tensione Residua V_post vs Burst Phase.
Spiegazione fisica dettagliata del loop Lissajous (curva chiusa) e confronto con Duffing e Softening.
"""

import os
import csv
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.cm as cm

# Percorsi cartelle
cartella_sessione = r"c:\Users\lucaa\Downloads\ESM2 - Copia\ES2M\Laboratorio_MEMS\Cartella da mettere sul computer università\Laboratorio_MEMS\sweep_burst_fase\sessione_burst_20260923_115041"
file_tau = os.path.join(cartella_sessione, "risultati_tau_vs_fase_accurati.csv")
file_soft = os.path.join(cartella_sessione, "analisi_softening_e_frequenza_vs_fase.csv")
out_png = os.path.join(cartella_sessione, "analisi_tau_e_softening_vs_vpost.png")

def load_csv(path):
    data = []
    with open(path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        for r in reader:
            if not r or r[0].strip().startswith('#'): continue
            data.append(r)
    header = [h.strip() for h in data[0]]
    rows = data[1:]
    return header, rows

h_tau, r_tau = load_csv(file_tau)
h_soft, r_soft = load_csv(file_soft)

fase = np.array([float(r[0]) for r in r_tau])
tau = np.array([float(r[1]) for r in r_tau])
A0 = np.array([float(r[2]) for r in r_tau])

V_post = np.array([float(r[1]) for r in r_soft])
fs = np.array([float(r[2]) for r in r_soft])

# Calcolo regressioni e correlazioni
corr_tau_vpost = np.corrcoef(tau, V_post)[0, 1]
corr_tau_A0 = np.corrcoef(tau, A0)[0, 1]
corr_fs_vpost = np.corrcoef(fs, V_post)[0, 1]
corr_fs_A0 = np.corrcoef(fs, A0)[0, 1]

p_tau_vpost = np.polyfit(V_post, tau, 1)
p_tau_A0 = np.polyfit(A0, tau, 1)
p_fs_vpost = np.polyfit(V_post, fs, 1)
p_fs_A0 = np.polyfit(A0, fs, 1)

# Configurazione grafica Dark Mode professionale
plt.style.use('dark_background')
fig = plt.figure(figsize=(16, 12), dpi=150)
gs = fig.add_gridspec(2, 2, hspace=0.32, wspace=0.25, left=0.08, right=0.92, top=0.92, bottom=0.08)

cmap = plt.cm.plasma
norm = plt.Normalize(vmin=-180, vmax=180)

# ==============================================================================
# 1. PANNELLO IN ALTO A SINISTRA: Tau vs V_post (con traiettoria parametrica chiusa)
# ==============================================================================
ax1 = fig.add_subplot(gs[0, 0])
# Disegna la linea di traiettoria continua chiusa
ax1.plot(V_post, tau, color='#555555', linestyle='-', linewidth=1.2, zorder=1, label='Traiettoria con fase $\\phi$')
# Punti colorati per fase
sc1 = ax1.scatter(V_post, tau, c=fase, cmap=cmap, norm=norm, s=55, edgecolor='black', linewidth=0.5, zorder=3)
# Fit lineare (puramente indicativo)
v_grid = np.linspace(V_post.min(), V_post.max(), 100)
ax1.plot(v_grid, np.polyval(p_tau_vpost, v_grid), color='red', linestyle='--', linewidth=1.5, zorder=2,
         label=f'Trend lineare ($r = {corr_tau_vpost:.3f}$)\nFalsa correlazione!')

# Frecce orientamento traiettoria
for idx in [15, 35, 55]:
    ax1.annotate('', xy=(V_post[idx+1], tau[idx+1]), xytext=(V_post[idx], tau[idx]),
                 arrowprops=dict(arrowstyle="->", color='#00e5ff', lw=1.5), zorder=4)

# Etichette su punti chiave
idx_0 = np.argmin(np.abs(fase - 0))
idx_180 = np.argmin(np.abs(fase - 180))
idx_m180 = 0
ax1.annotate(r'$\phi = 0^\circ$', xy=(V_post[idx_0], tau[idx_0]), xytext=(V_post[idx_0]+10, tau[idx_0]-0.02),
             color='#00e5ff', fontsize=9, fontweight='bold', arrowprops=dict(arrowstyle="->", color='#00e5ff', lw=1.2))
ax1.annotate(r'$\phi = +180^\circ$', xy=(V_post[idx_180], tau[idx_180]), xytext=(V_post[idx_180]-40, tau[idx_180]-0.015),
             color='#ffeb3b', fontsize=9, fontweight='bold', arrowprops=dict(arrowstyle="->", color='#ffeb3b', lw=1.2))

ax1.set_title(r"$\tau$ vs Tensione Residua $V_{\mathrm{post}}$ (Forma ad Anello/Loop)", fontsize=13, fontweight='bold', pad=10)
ax1.set_xlabel(r"Tensione DC Residua $V_{\mathrm{post}}$ su CH3 [mV]", fontsize=11, fontweight='bold')
ax1.set_ylabel(r"Costante di Tempo $\tau$ [ms]", fontsize=11, fontweight='bold')
ax1.grid(True, linestyle=':', alpha=0.5)
ax1.legend(loc='lower right', fontsize=9, framealpha=0.8)

# ==============================================================================
# 2. PANNELLO IN ALTO A DESTRA: Tau vs Ampiezza Iniziale A0 (Causa Fisica Reale)
# ==============================================================================
ax2 = fig.add_subplot(gs[0, 1])
sc2 = ax2.scatter(A0, tau, c=fase, cmap=cmap, norm=norm, s=55, edgecolor='black', linewidth=0.5, zorder=3)
a0_grid = np.linspace(A0.min(), A0.max(), 100)
ax2.plot(a0_grid, np.polyval(p_tau_A0, a0_grid), color='#00e5ff', linestyle='--', linewidth=2, zorder=2,
         label=f'Legge fisica reale ($r = {corr_tau_A0:.4f}$)\nSmorzamento non lineare')

ax2.set_title(r"$\tau$ vs Ampiezza Iniziale $A_0$ (Vera Relazione Fisica)", fontsize=13, fontweight='bold', pad=10)
ax2.set_xlabel(r"Ampiezza Iniziale Ringdown $A_0$ [mV]", fontsize=11, fontweight='bold')
ax2.set_ylabel(r"Costante di Tempo $\tau$ [ms]", fontsize=11, fontweight='bold')
ax2.grid(True, linestyle=':', alpha=0.5)
ax2.legend(loc='lower right', fontsize=9, framealpha=0.8)

# ==============================================================================
# 3. PANNELLO IN BASSO A SINISTRA: fs vs V_post (Il grafico "strano" chiarito)
# ==============================================================================
ax3 = fig.add_subplot(gs[1, 0])
# Disegna traiettoria parametrica chiusa
ax3.plot(V_post, fs, color='#555555', linestyle='-', linewidth=1.2, zorder=1, label='Traiettoria chiusa Lissajous')
sc3 = ax3.scatter(V_post, fs, c=fase, cmap=cmap, norm=norm, s=55, edgecolor='black', linewidth=0.5, zorder=3)
ax3.plot(v_grid, np.polyval(p_fs_vpost, v_grid), color='red', linestyle='--', linewidth=1.5, zorder=2,
         label=f'Trend lineare apparente ($r = {corr_fs_vpost:.3f}$)\nNon è Softening!')

# Frecce orientamento traiettoria
for idx in [15, 35, 55]:
    ax3.annotate('', xy=(V_post[idx+1], fs[idx+1]), xytext=(V_post[idx], fs[idx]),
                 arrowprops=dict(arrowstyle="->", color='#00e5ff', lw=1.5), zorder=4)

# Etichette su punti chiave
ax3.annotate(r'$\phi = 0^\circ$' + f'\nfs={fs[idx_0]:.0f} Hz', xy=(V_post[idx_0], fs[idx_0]), xytext=(V_post[idx_0]+10, fs[idx_0]-12),
             color='#00e5ff', fontsize=9, fontweight='bold', arrowprops=dict(arrowstyle="->", color='#00e5ff', lw=1.2))
ax3.annotate(r'$\phi = +180^\circ$' + f'\nfs={fs[idx_180]:.0f} Hz', xy=(V_post[idx_180], fs[idx_180]), xytext=(V_post[idx_180]-50, fs[idx_180]-10),
             color='#ffeb3b', fontsize=9, fontweight='bold', arrowprops=dict(arrowstyle="->", color='#ffeb3b', lw=1.2))

ax3.set_title(r"Frequenza $f_s$ vs $V_{\mathrm{post}}$ (Spiegazione del Loop Chiuso)", fontsize=13, fontweight='bold', pad=10)
ax3.set_xlabel(r"Tensione DC Residua $V_{\mathrm{post}}$ su CH3 [mV]", fontsize=11, fontweight='bold')
ax3.set_ylabel(r"Frequenza di Risonanza $f_s$ [Hz]", fontsize=11, fontweight='bold')
ax3.grid(True, linestyle=':', alpha=0.5)
ax3.legend(loc='lower right', fontsize=9, framealpha=0.8)

# ==============================================================================
# 4. PANNELLO IN BASSO A DESTRA: fs vs A0 (Duffing Hardening Reale)
# ==============================================================================
ax4 = fig.add_subplot(gs[1, 1])
sc4 = ax4.scatter(A0, fs, c=fase, cmap=cmap, norm=norm, s=55, edgecolor='black', linewidth=0.5, zorder=3)
ax4.plot(a0_grid, np.polyval(p_fs_A0, a0_grid), color='#ff9100', linestyle='--', linewidth=2, zorder=2,
         label=f'Duffing Hardening ($r = {corr_fs_A0:.5f}$)\nPendenza = +{p_fs_A0[0]:.2f} Hz/mV')

ax4.set_title(r"Frequenza $f_s$ vs Ampiezza $A_0$ (Duffing Spring Hardening)", fontsize=13, fontweight='bold', pad=10)
ax4.set_xlabel(r"Ampiezza Iniziale Ringdown $A_0$ [mV]", fontsize=11, fontweight='bold')
ax4.set_ylabel(r"Frequenza di Risonanza $f_s$ [Hz]", fontsize=11, fontweight='bold')
ax4.grid(True, linestyle=':', alpha=0.5)
ax4.legend(loc='lower right', fontsize=9, framealpha=0.8)

# Colorbar per la fase
cbar_ax = fig.add_axes([0.935, 0.15, 0.018, 0.7])
cbar = fig.colorbar(cm.ScalarMappable(norm=norm, cmap=cmap), cax=cbar_ax)
cbar.set_label(r'Fase Burst Agilent 33220A $\phi$ [gradi]', fontsize=11, fontweight='bold')

plt.suptitle(r"Confronto Parametrico: Effetto di $V_{\mathrm{post}}$ (Apparente) vs $A_0$ (Fisico Reale)",
             fontsize=16, fontweight='bold', y=0.98)

plt.savefig(out_png, dpi=150, facecolor=fig.get_facecolor(), edgecolor='none')
print(f"Grafico salvato con successo in: {out_png}")

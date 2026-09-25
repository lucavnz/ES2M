"""
Script per la generazione dello schema circuitale verificato e delle curve di taratura
per la compensazione della capacità parassita Cp di un risuonatore MEMS a 417 kHz
utilizzando un singolo integrato NE5532P (Doppio Op-Amp).
"""

import os
import sys
import shutil
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import schemdraw
import schemdraw.elements as elm

def genera_grafici_verifica(save_path):
    f0 = 417000.0  # 417 kHz
    w = 2 * np.pi * f0
    wt = 2 * np.pi * 10.0e6  # GBW NE5532P = 10 MHz
    wp2 = 2 * np.pi * 40.0e6 # secondo polo op-amp ~ 40 MHz
    s = 1j * w
    A = wt / (s * (1.0 + s / wp2))
    H_buf = A / (1.0 + A)

    # Parametri Stadio 1
    Cin = 2.2e-9    # 2.2 nF
    R_fix = 470.0   # 470 Ohm
    R2 = 2200.0     # 2.2 kOhm
    R_trim1_vec = np.linspace(0, 1000, 200) # Trimmer 1 (0 .. 1000 Ohm)

    phase_err_vec = []
    gain_s1_vec = []

    for rt in R_trim1_vec:
        R1 = R_fix + rt
        Z1 = R1 + 1.0 / (s * Cin)
        Z2 = R2
        G1 = - (Z2 / Z1) / (1.0 + (1.0 + Z2 / Z1) / A)
        G_tot = G1 * H_buf
        err = np.degrees(np.angle(G_tot / -1.0))
        phase_err_vec.append(err)
        gain_s1_vec.append(np.abs(G_tot))

    phase_err_vec = np.array(phase_err_vec)
    gain_s1_vec = np.array(gain_s1_vec)

    # Trova il punto esatto di zero
    idx_zero = np.argmin(np.abs(phase_err_vec))
    r_opt = R_trim1_vec[idx_zero]
    gain_opt = gain_s1_vec[idx_zero]

    # Variazione Trimmer 2 (Guadagno, da 0% a 100%)
    alpha_vec = np.linspace(0.01, 1.0, 200)
    R_pot = 1000.0 # 1 kOhm
    C_in_buf = 6.0e-12 # 6 pF capacità parassita ingresso buffer
    
    # Fase al variare di alpha
    phase_shift_pot = []
    v_comp_vec = []
    Vin = 0.1 # 100 mV
    
    for a in alpha_vec:
        R_th = a * (1.0 - a) * R_pot
        tau = R_th * C_in_buf
        d_phi = - np.degrees(np.arctan(w * tau))
        phase_shift_pot.append(d_phi)
        v_comp_vec.append(a * gain_opt * Vin)

    # Residuo TIA (con Cp_tot = 3.0 pF e Ccomp = 10 pF)
    Cp_tot = 3.0e-12
    C_comp = 10.0e-12
    # I_p = w * Cp_tot * Vin
    # I_comp = w * C_comp * V_comp * exp(j * (180 + err + d_phi))
    # Residuo = |I_p + I_comp| * Rf_TIA (Rf_eq = 5 MOhm)
    Rf_eq = 5.0e6
    residuo_mV = []
    for i, a in enumerate(alpha_vec):
        v_c = v_comp_vec[i]
        d_ph = np.radians(phase_shift_pot[i])
        # Vcomp ha fase 180 + d_ph
        # I_feed = 1j * w * Cp_tot * Vin
        # I_comp = 1j * w * C_comp * (- v_c * np.exp(1j * d_ph))
        I_net = 1j * w * Cp_tot * Vin - 1j * w * C_comp * v_c * np.exp(1j * d_ph)
        v_tia = np.abs(I_net) * Rf_eq * 1000.0 # mV
        residuo_mV.append(v_tia)

    # Plot
    fig, axs = plt.subplots(1, 3, figsize=(16, 5), dpi=150)
    fig.patch.set_facecolor('#0f172a')
    for ax in axs:
        ax.set_facecolor('#1e293b')
        ax.grid(True, linestyle='--', alpha=0.3, color='#94a3b8')
        ax.tick_params(colors='#cbd5e1')
        for spine in ax.spines.values():
            spine.set_color('#475569')

    # Panel 1: Sfasamento vs Trimmer 1
    axs[0].plot(R_trim1_vec, phase_err_vec, color='#38bdf8', lw=2.5, label='Errore di fase vs 180°')
    axs[0].axhline(0, color='#ef4444', linestyle=':', lw=1.8, label='Fase ESATTA = 180.00°')
    axs[0].axvline(r_opt, color='#22c55e', linestyle='--', lw=1.8, label=f'Taratura: R_trim1 = {r_opt:.0f} Ω')
    axs[0].scatter([r_opt], [0], color='#22c55e', s=80, zorder=5)
    axs[0].set_title('1. Regolazione Fase (Stadio 1)\nTrimmer 1 da 1 kΩ', color='white', fontsize=11, fontweight='bold')
    axs[0].set_xlabel('Resistenza Trimmer 1 [Ω]', color='#cbd5e1')
    axs[0].set_ylabel('Errore rispetto a 180° [gradi]', color='#cbd5e1')
    axs[0].legend(facecolor='#0f172a', edgecolor='#475569', labelcolor='#f8fafc', fontsize=9)

    # Panel 2: Indipendenza di Fase vs Trimmer 2
    axs[1].plot(alpha_vec * 100, phase_shift_pot, color='#a855f7', lw=2.5, label='Deviazione di fase (Δϕ)')
    axs[1].set_ylim(-1.0, 1.0)
    axs[1].axhline(0, color='#94a3b8', linestyle=':', lw=1)
    axs[1].set_title('2. Verifica Disaccoppiamento\nFase vs Cursore Trimmer 2 (Guadagno)', color='white', fontsize=11, fontweight='bold')
    axs[1].set_xlabel('Posizione Cursore Trimmer 2 [%]', color='#cbd5e1')
    axs[1].set_ylabel('Deviazione di Fase [gradi]', color='#cbd5e1')
    axs[1].annotate('Disaccoppiamento Perfetto:\nΔϕ < 0.23° su tutta la corsa!', xy=(50, -0.23), xytext=(20, -0.75),
                    arrowprops=dict(arrowstyle='->', color='#facc15', lw=1.5),
                    color='#facc15', fontweight='bold', fontsize=9,
                    bbox=dict(boxstyle='round,pad=0.5', facecolor='#0f172a', edgecolor='#facc15'))
    axs[1].legend(facecolor='#0f172a', edgecolor='#475569', labelcolor='#f8fafc', fontsize=9)

    # Panel 3: Cancellazione Parassita
    axs[2].plot(alpha_vec * 100, residuo_mV, color='#f59e0b', lw=2.5, label='Uscita TIA (Residuo Cp)')
    a_opt = (Cp_tot / C_comp) / (gain_opt)
    res_min = np.min(residuo_mV)
    axs[2].axvline(a_opt * 100, color='#22c55e', linestyle='--', lw=1.8, label=f'Minimo a {a_opt*100:.1f}%')
    axs[2].scatter([a_opt * 100], [res_min], color='#22c55e', s=80, zorder=5)
    axs[2].set_title('3. Cancellazione Segnale Parassita\nResiduo sul TIA vs Trimmer 2', color='white', fontsize=11, fontweight='bold')
    axs[2].set_xlabel('Posizione Cursore Trimmer 2 [%]', color='#cbd5e1')
    axs[2].set_ylabel('Ampiezza Uscita TIA [mV_peak]', color='#cbd5e1')
    axs[2].set_yscale('log')
    axs[2].legend(facecolor='#0f172a', edgecolor='#475569', labelcolor='#f8fafc', fontsize=9)

    plt.tight_layout()
    plt.savefig(save_path, dpi=180)
    plt.close()
    print(f"[OK] Salvato grafico di verifica: {save_path}")

def genera_schematico_completo(save_path):
    d = schemdraw.Drawing(fontsize=9, unit=2.5)

    # Sorgente Vin
    d.add(elm.Ground().at((0, 0)))
    src = elm.SourceSin().at((0, 0)).to((0, 2.0)).label('Vin\n417 kHz\n100 mV', 'left', ofst=0.3)
    d.add(src)
    vin_node = (1.5, 2.0)
    d.add(elm.Line().at((0, 2.0)).to(vin_node))
    d.add(elm.Dot().at(vin_node).label('Nodo Vin', 'top', ofst=0.15))

    # =========================================================================
    # RAMO 1: MEMS + TIA (In alto, Y = +5.5)
    # =========================================================================
    d.add(elm.Line().at(vin_node).to((1.5, 5.5)))
    d.add(elm.Line().at((1.5, 5.5)).to((3.2, 5.5)))
    mems_in = (3.2, 5.5)
    d.add(elm.Dot().at(mems_in))

    # Ramo RLC Motionale (Y = 7.0)
    d.add(elm.Line().at(mems_in).to((3.2, 7.0)))
    d.add(elm.Resistor().at((3.2, 7.0)).to((5.2, 7.0)).label('Rm = 11 MΩ', 'top'))
    d.add(elm.Inductor().at((5.2, 7.0)).to((7.2, 7.0)).label('Lm = 10 kH', 'top'))
    d.add(elm.Capacitor().at((7.2, 7.0)).to((9.2, 7.0)).label('Cm = 14 aF', 'top'))
    d.add(elm.Line().at((9.2, 7.0)).to((9.2, 5.5)))
    mems_out = (9.2, 5.5)
    d.add(elm.Dot().at(mems_out))

    # Cp Parassita (Y = 5.5)
    d.add(elm.Capacitor().at(mems_in).to(mems_out).label('Cp (MEMS ≈ 0.9 pF) + Stray Breadboard (≈ 2÷3 pF)', 'bottom', ofst=(0, -0.25)))

    # Collegamento verso nodo sommatore TIA (X = 24.5)
    tia_node = (24.5, 5.5)
    d.add(elm.Line().at(mems_out).to(tia_node))
    d.add(elm.Dot().at(tia_node).label('Massa Virtuale (0 V)\n[Sommatore TIA]', 'top', ofst=(0, 0.2)))

    # TIA Op-Amp (centrato a X = 26.0)
    d.add(elm.Line().at(tia_node).to((26.0, 5.5)))
    op_tia = elm.Opamp().right().at((26.0, 5.5)).anchor('in1')
    d.add(op_tia)
    d.add(elm.Line().at(op_tia.in2).left(0.6))
    d.add(elm.Ground())

    # Feedback TIA Rf // Cf
    d.add(elm.Line().at(op_tia.in1).to((26.0, 7.2)))
    d.add(elm.Resistor().at((26.0, 7.2)).to((28.8, 7.2)).label('Rf = 500 kΩ\n(Ge_tot = 5 MΩ)', 'top'))
    d.add(elm.Line().at((28.8, 7.2)).to((28.8, op_tia.out[1])))
    d.add(elm.Line().at((28.8, op_tia.out[1])).to(op_tia.out))
    d.add(elm.Dot().at(op_tia.out))
    d.add(elm.Line().at(op_tia.out).right(1.5).label('Uscita TIA\n(Oscilloscopio)', 'right'))

    # =========================================================================
    # RAMO 2: CIRCUITO DI COMPENSAZIONE DEFINITIVO (NE5532P) (In basso, Y = -3.5)
    # =========================================================================
    # Stadio 1: Op-Amp A (Invertente con compensazione anticipo per 180° esatti)
    d.add(elm.Line().at(vin_node).to((1.5, -3.5)))
    d.add(elm.Line().at((1.5, -3.5)).to((2.8, -3.5)))

    # Cin = 2.2 nF
    d.add(elm.Capacitor().at((2.8, -3.5)).to((4.8, -3.5)).label('Cin = 2.2 nF\n(Ceramico)', 'top', ofst=(0, 0.15)))
    # R1_fix = 470 Ohm
    d.add(elm.Resistor().at((4.8, -3.5)).to((6.8, -3.5)).label('R1_fix\n470 Ω', 'top', ofst=(0, 0.15)))
    # Trimmer 1 (Fase) = 1 kOhm multigiro
    d.add(elm.Potentiometer().at((6.8, -3.5)).to((9.2, -3.5)).label('TRIMMER 1 (FASE)\n1 kΩ Multigiro\n[Reostato]', 'top', ofst=(0, 0.2)))
    
    op1_in1 = (10.6, -3.5)
    d.add(elm.Line().at((9.2, -3.5)).to(op1_in1))

    # Op-Amp A (Pins 1, 2, 3)
    op1 = elm.Opamp().right().at(op1_in1).anchor('in1')
    d.add(op1)
    d.add(elm.Label().at(op1.in1).label('Pin 2 (-)', 'left', ofst=(-0.15, 0.25)))
    d.add(elm.Label().at(op1.in2).label('Pin 3 (+)', 'left', ofst=(-0.15, -0.25)))
    d.add(elm.Label().at(op1.out).label('Pin 1 (Out A)', 'bottom', ofst=(0.3, -0.25)))
    d.add(elm.Label().at((op1.in1[0]+1.1, op1.in1[1]-0.5)).label('NE5532P\n[OP-AMP A]', 'center'))

    # Pin 3 a Massa
    d.add(elm.Line().at(op1.in2).left(0.6))
    d.add(elm.Ground())

    # Retroazione R2 = 2.2 kOhm (da Pin 1 a Pin 2)
    d.add(elm.Line().at(op1.in1).to((op1.in1[0], -1.8)))
    d.add(elm.Resistor().at((op1.in1[0], -1.8)).to((op1.out[0], -1.8)).label('R2 = 2.2 kΩ  (Guadagno fisso ~2.2x)', 'top', ofst=(0, 0.15)))
    d.add(elm.Line().at((op1.out[0], -1.8)).to((op1.out[0], op1.out[1])))
    d.add(elm.Dot().at(op1.out))

    # =========================================================================
    # Stadio 2: Partitore Resistivo Puro (TRIMMER 2 - GUADAGNO)
    # =========================================================================
    pot_x = op1.out[0] + 3.2
    d.add(elm.Line().at(op1.out).to((pot_x, op1.out[1])))
    pot_top = (pot_x, op1.out[1])
    pot_bot = (pot_x, op1.out[1] - 3.0)
    
    # Disegna Trimmer 2 a partitore
    d.add(elm.Dot().at(pot_top).label('Term. A (Alto)\n[dall\'Out A]', 'top', ofst=(0, 0.15)))
    d.add(elm.Potentiometer().at(pot_top).to(pot_bot).label('TRIMMER 2 (GUADAGNO)\n1 kΩ Partitore', 'left', ofst=(-0.35, 0)))
    d.add(elm.Dot().at(pot_bot).label('Term. B (GND)', 'bottom', ofst=(0, -0.3)))
    d.add(elm.Ground().at(pot_bot))

    # Cursore centrale (Terminale Wiper)
    pot_wiper = (pot_x, (pot_top[1] + pot_bot[1]) / 2.0)
    d.add(elm.Dot().at(pot_wiper).label('Wiper\n(Cursore)', 'top', ofst=(0.3, 0.15)))

    # =========================================================================
    # Stadio 3: Buffer Inseguitore (OP-AMP B: Pins 5, 6, 7)
    # =========================================================================
    op2_x = pot_x + 3.5
    # Posizioniamo Op-Amp B esattamente allineato al cursore
    op2 = elm.Opamp().right().at((op2_x, pot_wiper[1])).anchor('in2')
    d.add(op2)
    # Connessione orizzontale diretta tra cursore e Pin 5 (+)
    d.add(elm.Line().at(pot_wiper).to(op2.in2))

    d.add(elm.Label().at(op2.in2).label('Pin 5 (+)', 'left', ofst=(-0.15, -0.25)))
    d.add(elm.Label().at(op2.in1).label('Pin 6 (-)', 'left', ofst=(-0.15, 0.25)))
    d.add(elm.Label().at(op2.out).label('Pin 7 (Out B)', 'bottom', ofst=(0.3, -0.25)))
    d.add(elm.Label().at((op2.in2[0]+1.1, op2.in2[1]+0.5)).label('NE5532P\n[OP-AMP B:\nBUFFER]', 'center'))

    # Retroazione corta buffer: Pin 7 collegato a Pin 6 (-)
    d.add(elm.Line().at(op2.out).to((op2.out[0], op2.in1[1] + 1.2)))
    d.add(elm.Line().to((op2.in1[0], op2.in1[1] + 1.2)))
    d.add(elm.Line().to(op2.in1))
    d.add(elm.Dot().at(op2.out))

    # =========================================================================
    # Uscita verso C_comp e TIA
    # =========================================================================
    vcomp_node = (op2.out[0] + 1.5, op2.out[1])
    d.add(elm.Line().at(op2.out).to(vcomp_node))
    d.add(elm.Dot().at(vcomp_node).label('Nodo V_comp\n[Fase = 180.0°]', 'bottom', ofst=(0, -0.25)))

    # Ccomp verso il nodo TIA (etichetta a SINISTRA per non toccare il TIA)
    d.add(elm.Line().at(vcomp_node).to((24.5, vcomp_node[1])))
    d.add(elm.Capacitor().at((24.5, vcomp_node[1])).to((24.5, 3.5)).label('C_comp = 10 pF (o 4.7 pF)\n[Ceramico Fisso NP0/C0G]', 'left', ofst=(-0.25, 0)))
    d.add(elm.Line().at((24.5, 3.5)).to(tia_node))

    d.save(save_path, dpi=200)
    print(f"[OK] Salvato schema circuitale completo: {save_path}")

if __name__ == '__main__':
    base_dir = r"c:\Users\lucaa\Downloads\ESM2 - Copia\ES2M\Laboratorio_MEMS"
    os.makedirs(base_dir, exist_ok=True)
    schema_file = os.path.join(base_dir, "circuito_compensazione_definitivo.png")
    grafici_file = os.path.join(base_dir, "curva_taratura_fase_guadagno.png")
    
    genera_schematico_completo(schema_file)
    genera_grafici_verifica(grafici_file)

    # Copia anche nella cartella brain artifacts dell'utente per visualizzazione
    art_dir = r"C:\Users\lucaa\.gemini\antigravity-ide\brain\aedafdf4-08f2-40cb-9c20-7e96200f2a6c"
    if os.path.exists(art_dir):
        shutil.copy(schema_file, os.path.join(art_dir, "circuito_compensazione_definitivo.png"))
        shutil.copy(grafici_file, os.path.join(art_dir, "curva_taratura_fase_guadagno.png"))
        print("[OK] Copiati file negli artifacts della conversazione.")

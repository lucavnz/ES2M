"""
Disegna Circuito di Compensazione MEMS con Stadio Invertente Passa-Alto Integrato (1 Solo Op-Amp)
Calcolo componenti e simulazione sfasamento vs posizione trimmer per taratura a 180.0° precisi.
"""

import os
import shutil
import matplotlib
matplotlib.use('Agg')
import numpy as np
import matplotlib.pyplot as plt
import schemdraw
import schemdraw.elements as elm

def crea_schema_e_grafici():
    # -------------------------------------------------------------
    # 1. PARAMETRI CIRCUITALI PER f = 417.62 kHz (e f = 147.62 kHz)
    # -------------------------------------------------------------
    f_res = 417620.0  # Hz (417.62 kHz, frequenza di risonanza DIE D4)
    w = 2 * np.pi * f_res
    gbw = 3.0e6       # 3 MHz nominale (TL081 / TL082)
    wt = 2 * np.pi * gbw

    Cin = 1.0e-9      # 1 nF ceramico (condensatore passa-alto)
    R1_fix = 470.0    # 470 Ohm fisso
    R2_nom = 1200.0   # 1.2 kOhm nominale in retroazione

    # Variazione trimmer di fase da 0 a 2500 Ohm
    r_trim_vec = np.linspace(0, 2500, 250)
    phase_err_vec = []
    gain_vec = []

    for r_t in r_trim_vec:
        r1_tot = R1_fix + r_t
        s = 1j * w
        Z1 = r1_tot + 1.0 / (s * Cin)
        Z2 = R2_nom
        A = wt / s
        G = - (Z2 / Z1) / (1.0 + (1.0 + Z2 / Z1) / A)
        err = np.degrees(np.angle(G / -1.0))
        phase_err_vec.append(err)
        gain_vec.append(np.abs(G))

    phase_err_vec = np.array(phase_err_vec)
    gain_vec = np.array(gain_vec)

    # -------------------------------------------------------------
    # 2. DISEGNO SCHEMA PULITO CON SCHEMDRAW
    # -------------------------------------------------------------
    d = schemdraw.Drawing(fontsize=9, unit=2.5)

    # Sorgente Vin al centro
    d.add(elm.Ground().at((0, -0.8)))
    src = elm.SourceSin().at((0, -0.8)).to((0, 0.8)).label('Vin\n417.6 kHz\n100 mV', 'left')
    d.add(src)
    vin_node = (0.8, 0.8)
    d.add(elm.Line().at((0, 0.8)).to(vin_node))
    d.add(elm.Dot().at(vin_node))

    # --- RAMO 1: MEMS + TIA (In alto, Y = +3.5) ---
    d.add(elm.Line().at(vin_node).to((0.8, 3.5)))
    d.add(elm.Line().at((0.8, 3.5)).to((2.0, 3.5)))
    mems_in = (2.0, 3.5)
    d.add(elm.Dot().at(mems_in))

    # RLC Motionale (braccio sopra a Y = 4.7)
    d.add(elm.Line().at(mems_in).to((2.0, 4.7)))
    d.add(elm.Resistor().at((2.0, 4.7)).to((3.8, 4.7)).label('Rm = 11.3 MΩ', 'top'))
    d.add(elm.Inductor().at((3.8, 4.7)).to((5.6, 4.7)).label('Lm = 10.7 kH', 'top'))
    d.add(elm.Capacitor().at((5.6, 4.7)).to((7.4, 4.7)).label('Cm = 13.6 aF', 'top'))
    d.add(elm.Line().at((7.4, 4.7)).to((7.4, 3.5)))
    mems_out = (7.4, 3.5)
    d.add(elm.Dot().at(mems_out))

    # Cp parassita (braccio a Y = 3.5)
    d.add(elm.Capacitor().at(mems_in).to(mems_out).label('Cp (Feedthrough Parassita) ≈ 0.90 pF', 'bottom'))

    # Connessione al nodo di massa virtuale del TIA (X = 10.5)
    d.add(elm.Line().at(mems_out).to((10.5, 3.5)))
    tia_sum_node = (10.5, 3.5)
    d.add(elm.Dot().at(tia_sum_node).label('Massa Virtuale (0 V)\n[Nodo Sommatore TIA]', 'top'))

    # Front-end TIA (Opamp centrato a X = 11.8, Y = 3.2)
    d.add(elm.Line().at(tia_sum_node).to((11.5, 3.5)))
    op_tia = elm.Opamp().right().at((11.5, 3.5)).anchor('in1')
    d.add(op_tia)
    d.add(elm.Line().at(op_tia.in2).left(0.5))
    d.add(elm.Ground())

    # Retroazione TIA: Rf // Cf
    d.add(elm.Line().at(op_tia.in1).to((11.5, 5.0)))
    d.add(elm.Resistor().at((11.5, 5.0)).to((14.0, 5.0)).label('Rf = 500 kΩ', 'top'))
    d.add(elm.Line().at((14.0, 5.0)).to((14.0, op_tia.out[1])))
    d.add(elm.Line().at((14.0, op_tia.out[1])).to(op_tia.out))

    d.add(elm.Line().at((11.5, 5.0)).to((11.5, 6.2)))
    d.add(elm.Capacitor().at((11.5, 6.2)).to((14.0, 6.2)).label('Cf ≈ 0.3 pF (Polo ~1.1 MHz)', 'top'))
    d.add(elm.Line().at((14.0, 6.2)).to((14.0, 5.0)))

    d.add(elm.Dot().at(op_tia.out))
    d.add(elm.Line().at(op_tia.out).right(1.8).label('Vout TIA\n[Oscilloscopio CH1]', 'right'))

    # --- RAMO 2: STADIO INVERTENTE PASSA-ALTO COMPENSATORE (In basso, Y = -3.8) ---
    d.add(elm.Line().at(vin_node).to((0.8, -3.8)))
    d.add(elm.Capacitor().at((0.8, -3.8)).to((2.6, -3.8)).label('Cin = 1.0 nF\n(Passa-Alto)', 'top'))
    d.add(elm.Resistor().at((2.6, -3.8)).to((4.3, -3.8)).label('R1_fix = 470 Ω', 'top'))
    d.add(elm.Potentiometer().at((4.3, -3.8)).to((6.2, -3.8)).label('R_fase = 2 kΩ Trimmer\n[MANOPOLA FASE 180°]', 'bottom'))

    # Opamp Invertente singolo (in1 a X = 6.8, Y = -3.8)
    d.add(elm.Line().at((6.2, -3.8)).to((6.8, -3.8)))
    op_inv = elm.Opamp().right().at((6.8, -3.8)).anchor('in1')
    d.add(op_inv)
    d.add(elm.Line().at(op_inv.in2).left(0.5))
    d.add(elm.Ground())

    # Retroazione Invertente: Trimmer Guadagno R_gain (tra X=6.8 e X=8.8)
    d.add(elm.Line().at(op_inv.in1).to((6.8, -2.4)))
    d.add(elm.Potentiometer().at((6.8, -2.4)).to((8.8, -2.4)).label('R_gain = 5 kΩ Trimmer\n[MANOPOLA GUADAGNO]', 'top'))
    d.add(elm.Line().at((8.8, -2.4)).to((8.8, op_inv.out[1])))
    d.add(elm.Line().at((8.8, op_inv.out[1])).to(op_inv.out))

    # Uscita invertitore: prosegue a destra fino a X = 10.5 (perfettamente sotto a tia_sum_node!)
    d.add(elm.Dot().at(op_inv.out))
    d.add(elm.Line().at(op_inv.out).to((10.5, op_inv.out[1])))
    vcomp_point = (10.5, op_inv.out[1])
    d.add(elm.Dot().at(vcomp_point).label('V_comp\n[CH2 per tarare 180°]', 'right'))

    # Salita verticale libera a X = 10.5 fino a tia_sum_node con C_comp
    d.add(elm.Capacitor().at(vcomp_point).to((10.5, 1.2)).label('C_comp ≈ 2.2 pF\n(oppure 1 ÷ 4.7 pF)', 'left'))
    d.add(elm.Line().at((10.5, 1.2)).to(tia_sum_node))

    schematic_path = 'circuito_passa_alto_invertente.png'
    d.save(schematic_path, dpi=220)
    print(f"[OK] Salvato schema circuitale: {schematic_path}")

    # -------------------------------------------------------------
    # 3. GRAFICI DI TARATURA E GUIDA OSCILLOSCOPIO
    # -------------------------------------------------------------
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.5, 5.2))

    idx_zero = np.argmin(np.abs(phase_err_vec))
    r_opt = r_trim_vec[idx_zero]

    # Plot 1: Curva teorica Sfasamento vs Trimmer
    ax1.plot(r_trim_vec, phase_err_vec, 'b-', lw=2.4, label=r'Errore di Fase: $\Delta\phi = \phi - 180^\circ$')
    ax1.axhline(0, color='r', linestyle='--', lw=1.6, label=r'180.00° Esatti (Sfasamento Perfetto)')
    ax1.axvline(r_opt, color='g', linestyle=':', lw=1.6, label=f'Taratura Ottima: R_fase ≈ {r_opt:.0f} ' + r'$\Omega$')
    ax1.plot(r_opt, phase_err_vec[idx_zero], 'go', markersize=9)

    ax1.set_title(f'Taratura Trimmer di Fase a f = {f_res/1e3:.2f} kHz\n' + r'($C_{in} = 1.0\text{ nF}$, $R_{1,\text{fix}} = 470\,\Omega$ + Trimmer $2\text{ k}\Omega$)', fontsize=11, fontweight='bold')
    ax1.set_xlabel(r'Resistenza Trimmer di Fase $R_{\text{fase}}$ [$\Omega$]', fontsize=10)
    ax1.set_ylabel(r'Errore rispetto a 180° [Gradi]', fontsize=10)
    ax1.grid(True, alpha=0.3)
    ax1.legend(loc='best', fontsize=9.5)
    ax1.set_ylim(-15, 20)

    # Plot 2: Figura di Lissajous sull'Oscilloscopio (Modo XY)
    t = np.linspace(0, 1, 600)
    v_in = np.sin(2 * np.pi * t)
    v_comp_err = - np.sin(2 * np.pi * t + np.radians(22)) # sfasamento sbilanciato
    v_comp_perf = - np.sin(2 * np.pi * t)                 # 180.00 gradi perfetti

    ax2.plot(v_in, v_comp_err, 'r--', lw=2.0, label=r'Trimmer Sfasato: Ellisse Aperta ($\phi \neq 180^\circ$)')
    ax2.plot(v_in, v_comp_perf, 'g-', lw=2.8, label=r'Trimmer Tarato: Segmento Retto Diagonale ($\phi = 180.0^\circ$)')
    ax2.set_title('Verifica Diretta su Oscilloscopio in Modo XY\n' + r'($X = V_{\text{in}}$ su CH3, $Y = V_{\text{comp}}$ su CH2)', fontsize=11, fontweight='bold')
    ax2.set_xlabel(r'CH3: $V_{\text{in}}$ [V]', fontsize=10)
    ax2.set_ylabel(r'CH2: $V_{\text{comp}}$ [V]', fontsize=10)
    ax2.grid(True, alpha=0.3)
    ax2.legend(loc='best', fontsize=9.5)
    ax2.set_aspect('equal', 'box')

    plt.tight_layout()
    plot_path = 'taratura_fase_trimmer.png'
    plt.savefig(plot_path, dpi=220)
    print(f"[OK] Salvato grafico taratura: {plot_path}")

    # Copia nella cartella artifacts per visualizzazione diretta
    artifact_dir = r"C:\Users\lucaa\.gemini\antigravity-ide\brain\775e7c73-b267-4b89-91d1-d15484c74696"
    if os.path.exists(artifact_dir):
        shutil.copy(schematic_path, os.path.join(artifact_dir, schematic_path))
        shutil.copy(plot_path, os.path.join(artifact_dir, plot_path))
        print("[OK] Immagini copiate nella cartella artifacts.")

if __name__ == '__main__':
    crea_schema_e_grafici()

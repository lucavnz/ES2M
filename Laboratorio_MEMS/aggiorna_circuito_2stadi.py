"""
Disegna la topologia reale dell'utente:
Vin -> Passa-Alto CR (Trimmer 1) -> Buffer (Opamp 1) -> Invertente (Opamp 2 con Trimmer 2) -> C_comp -> TIA
"""

import os
import shutil
import matplotlib
matplotlib.use('Agg')
import numpy as np
import matplotlib.pyplot as plt
import schemdraw
import schemdraw.elements as elm

def crea_schema_utente():
    d = schemdraw.Drawing(fontsize=9, unit=2.4)

    # Sorgente Vin
    d.add(elm.Ground().at((0, -0.8)))
    src = elm.SourceSin().at((0, -0.8)).to((0, 0.8)).label('Vin\n417.6 kHz\n100 mV', 'left')
    d.add(src)
    vin_node = (0.8, 0.8)
    d.add(elm.Line().at((0, 0.8)).to(vin_node))
    d.add(elm.Dot().at(vin_node))

    # --- RAMO 1: MEMS + TIA (In alto, Y = +3.6) ---
    d.add(elm.Line().at(vin_node).to((0.8, 3.6)))
    d.add(elm.Line().at((0.8, 3.6)).to((2.0, 3.6)))
    mems_in = (2.0, 3.6)
    d.add(elm.Dot().at(mems_in))

    # RLC Motionale (braccio sopra a Y = 4.8)
    d.add(elm.Line().at(mems_in).to((2.0, 4.8)))
    d.add(elm.Resistor().at((2.0, 4.8)).to((3.8, 4.8)).label('Rm = 11.3 MΩ', 'top'))
    d.add(elm.Inductor().at((3.8, 4.8)).to((5.6, 4.8)).label('Lm = 10.7 kH', 'top'))
    d.add(elm.Capacitor().at((5.6, 4.8)).to((7.4, 4.8)).label('Cm = 13.6 aF', 'top'))
    d.add(elm.Line().at((7.4, 4.8)).to((7.4, 3.6)))
    mems_out = (7.4, 3.6)
    d.add(elm.Dot().at(mems_out))

    # Cp parassita (braccio a Y = 3.6)
    d.add(elm.Capacitor().at(mems_in).to(mems_out).label('Cp (Feedthrough) ≈ 0.90 pF', 'bottom'))

    # Connessione al nodo TIA (X = 14.5)
    d.add(elm.Line().at(mems_out).to((14.5, 3.6)))
    tia_sum_node = (14.5, 3.6)
    d.add(elm.Dot().at(tia_sum_node).label('Massa Virtuale (0 V)\n[Sommatore TIA]', 'top'))

    # TIA Opamp
    d.add(elm.Line().at(tia_sum_node).to((15.5, 3.6)))
    op_tia = elm.Opamp().right().at((15.5, 3.6)).anchor('in1')
    d.add(op_tia)
    d.add(elm.Line().at(op_tia.in2).left(0.5))
    d.add(elm.Ground())

    # Retroazione TIA
    d.add(elm.Line().at(op_tia.in1).to((15.5, 5.0)))
    d.add(elm.Resistor().at((15.5, 5.0)).to((18.0, 5.0)).label('Rf = 500 kΩ', 'top'))
    d.add(elm.Line().at((18.0, 5.0)).to((18.0, op_tia.out[1])))
    d.add(elm.Line().at((18.0, op_tia.out[1])).to(op_tia.out))

    d.add(elm.Line().at((15.5, 5.0)).to((15.5, 6.2)))
    d.add(elm.Capacitor().at((15.5, 6.2)).to((18.0, 6.2)).label('Cf ≈ 0.3 pF', 'top'))
    d.add(elm.Line().at((18.0, 6.2)).to((18.0, 5.0)))

    d.add(elm.Dot().at(op_tia.out))
    d.add(elm.Line().at(op_tia.out).right(1.5).label('Vout TIA\n[CH1 Oscilloscopio]', 'right'))

    # --- RAMO 2: CIRCUITO UTENTE (In basso, Y = -3.5) ---
    # Stadio 1: Passa-Alto CR passivo
    d.add(elm.Line().at(vin_node).to((0.8, -3.5)))
    d.add(elm.Capacitor().at((0.8, -3.5)).to((2.8, -3.5)).label('Chp = 1.0 nF\n(Passa-Alto)', 'top'))
    cr_mid = (2.8, -3.5)
    d.add(elm.Dot().at(cr_mid))
    d.add(elm.Potentiometer().at(cr_mid).to((2.8, -5.5)).label('R_hp = 2 kΩ Trimmer\n[TRIMMER 1: FASE]', 'right'))
    d.add(elm.Ground().at((2.8, -5.5)))

    # Stadio 2: Buffer (Opamp 1)
    # Collegato a pin (+) in2 del buffer!
    d.add(elm.Line().at(cr_mid).to((4.5, -3.5)))
    # Opamp buffer con in2 a (4.5, -3.5)
    op_buf = elm.Opamp().right().at((4.5, -3.5)).anchor('in2')
    d.add(op_buf)
    # Retroazione negativa buffer: out collegato a in1
    d.add(elm.Line().at(op_buf.out).to((op_buf.out[0], -2.0)))
    d.add(elm.Line().to((op_buf.in1[0], -2.0)))
    d.add(elm.Line().to(op_buf.in1))

    # Stadio 3: Invertente (Opamp 2)
    d.add(elm.Dot().at(op_buf.out))
    d.add(elm.Line().at(op_buf.out).to((8.0, op_buf.out[1])))
    d.add(elm.Resistor().at((8.0, op_buf.out[1])).to((10.0, op_buf.out[1])).label('R1 = 1 kΩ', 'top'))
    inv_in1 = (10.0, op_buf.out[1])

    op_inv = elm.Opamp().right().at(inv_in1).anchor('in1')
    d.add(op_inv)
    d.add(elm.Line().at(op_inv.in2).left(0.5))
    d.add(elm.Ground())

    # Retroazione Invertente: Trimmer Guadagno
    d.add(elm.Line().at(op_inv.in1).to((10.0, -1.8)))
    d.add(elm.Potentiometer().at((10.0, -1.8)).to((12.5, -1.8)).label('R_gain = 2 kΩ Trimmer\n[TRIMMER 2: GUADAGNO]', 'top'))
    d.add(elm.Line().at((12.5, -1.8)).to((12.5, op_inv.out[1])))
    d.add(elm.Line().at((12.5, op_inv.out[1])).to(op_inv.out))

    # Uscita invertitore verso C_comp e TIA
    d.add(elm.Dot().at(op_inv.out))
    d.add(elm.Line().at(op_inv.out).to((14.5, op_inv.out[1])))
    vcomp_point = (14.5, op_inv.out[1])
    d.add(elm.Dot().at(vcomp_point).label('V_comp\n[CH2 per tarare 180°]', 'right'))

    # Condensatore C_comp verso il TIA
    d.add(elm.Capacitor().at(vcomp_point).to((14.5, 1.2)).label('C_comp ≈ 2.2 pF\n(o gimmick twisted)', 'left'))
    d.add(elm.Line().at((14.5, 1.2)).to(tia_sum_node))

    schematic_path = 'circuito_2stadi_buffer.png'
    d.save(schematic_path, dpi=220)
    print(f"[OK] Salvato schema circuito utente: {schematic_path}")

    # Copia negli artifacts
    artifact_dir = r"C:\Users\lucaa\.gemini\antigravity-ide\brain\775e7c73-b267-4b89-91d1-d15484c74696"
    if os.path.exists(artifact_dir):
        shutil.copy(schematic_path, os.path.join(artifact_dir, schematic_path))
        print("[OK] Copiato negli artifacts.")

if __name__ == '__main__':
    crea_schema_utente()

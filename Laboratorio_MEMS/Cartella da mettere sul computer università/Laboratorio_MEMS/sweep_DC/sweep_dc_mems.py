"""
Sweep Automatico DC + Frequenza per Risonatore MEMS
Strumentazione integrata:
  - Agilent E3646A (Alimentatore DC Duale, Output 1: sweep VDC da 0V a 20V)
  - Agilent 33220A (Generatore di Funzioni DDS su GPIB: sweep Frequenza)
  - Keysight MSO-X 3014A (Oscilloscopio USB: misura sincrona con Handshake Hardware :DIGitize + *OPC?)

Descrizione:
  1. Configura l'alimentatore Agilent E3646A su Output 1 in HIGH RANGE (0-20V, 1.5A)
     con corrente di compliance limitata a 100 mA per protezione del MEMS.
  2. Per ogni tensione VDC (default: da 0V a 20V a passi di 2V):
     a. Imposta VDC e attende la stabilizzazione elettrostatica (0.5 s).
     b. Esegue lo sweep automatico in frequenza con handshake delle medie hardware.
     c. Salva i file CSV per il singolo VDC (master, modulo, fase) compatibili con le misure precedenti.
     d. Accoda i dati nel file CSV cumulativo generale.
     e. Calcola picco di risonanza fs, antirisonanza fp e guadagno massimo per quel VDC.
  3. Al termine (o su interruzione Ctrl+C), esegue la procedura di sicurezza:
     rampa a 0V e disattivazione dell'uscita (OUTP OFF) per proteggere il dispositivo.
  4. Genera automaticamente il report interattivo HTML e i grafici multi-curva (plotta_sweep_dc.py).
"""

import sys
import os
import time
import math
import cmath
import csv
import argparse
from datetime import datetime

# Assicura che la cartella corrente sia nel path dei moduli Python
cartella_script = os.path.dirname(os.path.abspath(__file__))
if cartella_script not in sys.path:
    sys.path.insert(0, cartella_script)

# Indirizzi Primari Verificati in Laboratorio
GEN_PRIMARY_ADDR = "GPIB1::10::INSTR"
GEN_FALLBACK_ADDRS = ["GPIB1::10::INSTR", "GPIB0::10::INSTR", "GPIB::10::INSTR"]

SCOPE_PRIMARY_ADDR = "USB0::2391::6056::MY52100688::INSTR"

PSU_FALLBACK_ADDRS = [
    "GPIB1::5::INSTR", "GPIB0::5::INSTR",
    "GPIB1::6::INSTR", "GPIB0::6::INSTR",
    "GPIB1::7::INSTR", "GPIB0::7::INSTR",
    "GPIB1::8::INSTR", "GPIB0::8::INSTR",
    "GPIB1::9::INSTR", "GPIB0::9::INSTR",
    "GPIB1::4::INSTR", "GPIB0::4::INSTR",
    "GPIB1::3::INSTR", "GPIB0::3::INSTR",
    "GPIB1::2::INSTR", "GPIB0::2::INSTR",
]

# Parametri Default Sweep Frequenza
DEFAULT_F_CENTER = 417400.0  # 417.40 kHz
DEFAULT_DELTA_F = 600.0      # +/- 600 Hz
DEFAULT_PTS_SIDE = 50        # 101 punti totali
DEFAULT_N_AVG = 64           # 64 medie hardware oscilloscopio
SETTLE_MEMS_S = 0.040        # 40 ms assestamento meccanico risonatore

# Parametri Default Sweep DC (Agilent E3646A Output 1)
DEFAULT_VDC_START = 0.0      # 0.0 V
DEFAULT_VDC_STOP = 20.0      # 20.0 V
DEFAULT_VDC_STEP = 2.0       # passo 2.0 V (0, 2, 4, 6, 8, ..., 20 V -> 11 passi)
SETTLE_VDC_S = 0.500         # 500 ms assestamento polarizzazione DC
PSU_CURRENT_LIMIT_A = 0.100  # 100 mA limite di compliance

SCPI_INVALID_VAL = 9.9e36


class SimulatedInstrument:
    """Simulatore completo per test offline della catena di misura."""
    state = {
        "freq": 417400.0,
        "navg": 64,
        "vdc": 0.0,
        "output_on": False,
        "range_high": True
    }

    def __init__(self, name):
        self.name = name

    def write(self, cmd):
        u = cmd.strip().upper()
        if "FREQ" in u:
            parts = cmd.split()
            if len(parts) > 1:
                try:
                    SimulatedInstrument.state["freq"] = float(parts[1])
                except ValueError:
                    pass
        elif "COUN" in u:
            parts = cmd.split()
            if len(parts) > 1:
                try:
                    SimulatedInstrument.state["navg"] = int(parts[1])
                except ValueError:
                    pass
        elif "VOLT" in u and "RANG" not in u and "?" not in u:
            parts = cmd.split()
            if len(parts) > 1:
                try:
                    SimulatedInstrument.state["vdc"] = float(parts[1])
                except ValueError:
                    pass
        elif "OUTP" in u and "?" not in u:
            SimulatedInstrument.state["output_on"] = ("ON" in u or "1" in u)
        elif "RANG" in u:
            SimulatedInstrument.state["range_high"] = ("HIGH" in u or "P20V" in u)

    def query(self, cmd):
        if ";" in cmd:
            subcmds = cmd.split(";")
            results = [self.query(sc.strip()) for sc in subcmds]
            query_res = [r for sc, r in zip(subcmds, results) if "?" in sc]
            return ";".join(query_res) if query_res else (results[-1] if results else "0.0")

        u = cmd.strip().upper()
        if "*IDN?" in u:
            if "33220" in self.name:
                return "Agilent Technologies,33220A,SIM_SN1,REV2.0"
            elif "3014" in self.name:
                return "KEYSIGHT TECHNOLOGIES,MSO-X 3014A,SIM_SN2,07.20"
            elif "E3646" in self.name or "PSU" in self.name:
                return "Agilent Technologies,E3646A,SIM_SN3,1.4-5.0-1.0"
            return f"SIMULATED_{self.name}_REV1.0"

        st = SimulatedInstrument.state
        if "*OPC?" in u:
            return "1"
        if "SYST:ERR?" in u:
            return '+0,"No error"'
        if "FREQ" in u and "?" in u:
            return f"{st['freq']:.3f}"
        if "VOLT" in u and "RANG" in u and "?" in u:
            return "P20V" if st['range_high'] else "P8V"
        if "VOLT" in u and "?" in u:
            return f"{st['vdc']:.3f}"
        if "CURR" in u and "?" in u:
            return f"{st['vdc'] * 1e-7:.6f}"
        if "OUTP" in u and "?" in u:
            return "1" if st['output_on'] else "0"

        # Modello fisico MEMS con Spring Softening (delta f0 prop -Vdc^2)
        # ed incremento dell'efficienza di transduzione motrice (Amot prop Vdc^2)
        v_eff = st["vdc"] if st["output_on"] else 0.0
        f0_vdc = 417400.0 - 0.75 * (v_eff ** 2)  # diminuzione della frequenza con Vdc^2 (spring softening)
        q = 2800.0

        # Basamento capacitivo statico (feedthrough parassita Cp)
        H_base = 11.75 * cmath.exp(1j * math.radians(67.5))

        # Picco motrice proporzionale alla polarizzazione DC
        gain_mot_peak = 0.01 + 0.002 * (v_eff ** 2)
        delta_f_rel = (st["freq"] - f0_vdc) / f0_vdc
        H_mot = (gain_mot_peak * cmath.exp(1j * math.radians(-42.0))) / (1.0 + 2j * q * delta_f_rel)

        H_tot = H_base + H_mot
        gain = abs(H_tot)
        phase_deg = math.degrees(cmath.phase(H_tot))

        if "MEAS" in u and ("CHAN3" in u or "CHANNEL3" in u):
            return "0.200000"
        if "MEAS" in u and ("CHAN1" in u or "CHANNEL1" in u):
            vpp = 0.200 * gain
            return f"{vpp:.6e}"
        if "MEAS" in u and "PHAS" in u:
            return f"{phase_deg:.3f}"
        return "0.0"

    def close(self):
        pass


def parsa_valore_scpi(val_str):
    try:
        val = float(val_str.strip())
        if abs(val) >= SCPI_INVALID_VAL:
            return float('nan')
        return val
    except (ValueError, AttributeError):
        return float('nan')


def connetti_strumenti(rm, psu_addr_override=None):
    """Trova e connette i 3 strumenti (33220A, MSO-X 3014A, E3646A)."""
    gen = None
    scope = None
    psu = None

    # 1. Ricerca Generatore Agilent 33220A (GPIB)
    print("\n[CONNESSIONE 1/3] Ricerca Generatore Agilent 33220A...")
    for addr in GEN_FALLBACK_ADDRS:
        try:
            test_inst = rm.open_resource(addr, timeout=2500)
            idn = test_inst.query("*IDN?").strip()
            if "33220" in idn:
                gen = test_inst
                print(f" -> [OK] Generatore DDS connesso su {addr}: {idn}")
                break
            test_inst.close()
        except Exception:
            continue

    if not gen:
        for res in rm.list_resources():
            if "gpib" in res.lower():
                try:
                    test_inst = rm.open_resource(res, timeout=2500)
                    idn = test_inst.query("*IDN?").strip()
                    if "33220" in idn:
                        gen = test_inst
                        print(f" -> [OK] Generatore DDS connesso su {res}: {idn}")
                        break
                    test_inst.close()
                except Exception:
                    continue

    if not gen:
        print("\n[ERRORE] Generatore Agilent 33220A non trovato su GPIB!")
        return None, None, None

    # 2. Ricerca Oscilloscopio Keysight MSO-X 3014A (USB)
    print("\n[CONNESSIONE 2/3] Ricerca Oscilloscopio Keysight MSO-X 3014A...")
    try:
        test_inst = rm.open_resource(SCOPE_PRIMARY_ADDR, timeout=15000)
        idn = test_inst.query("*IDN?").strip()
        scope = test_inst
        print(f" -> [OK] Oscilloscopio connesso su {SCOPE_PRIMARY_ADDR}: {idn}")
    except Exception:
        for res in rm.list_resources():
            if "usb" in res.lower():
                try:
                    test_inst = rm.open_resource(res, timeout=15000)
                    idn = test_inst.query("*IDN?").strip()
                    if any(k in idn for k in ["3014", "Keysight", "Agilent", "InfiniiVision"]):
                        scope = test_inst
                        print(f" -> [OK] Oscilloscopio connesso su {res}: {idn}")
                        break
                    test_inst.close()
                except Exception:
                    continue

    if not scope:
        print("\n[ERRORE] Oscilloscopio Keysight MSO-X 3014A non trovato su porta USB!")
        if gen:
            gen.close()
        return None, None, None

    # 3. Ricerca Alimentatore Agilent E3646A (GPIB)
    print("\n[CONNESSIONE 3/3] Ricerca Alimentatore DC Agilent E3646A (Output 1)...")
    addrs_to_test = []
    if psu_addr_override:
        addrs_to_test.append(psu_addr_override)
    addrs_to_test.extend(PSU_FALLBACK_ADDRS)

    for addr in addrs_to_test:
        try:
            test_inst = rm.open_resource(addr, timeout=2500)
            idn = test_inst.query("*IDN?").strip()
            if any(k in idn for k in ["E3646", "3646", "E364"]):
                psu = test_inst
                print(f" -> [OK] Alimentatore DC connesso su {addr}: {idn}")
                break
            test_inst.close()
        except Exception:
            continue

    if not psu:
        # Scansione approfondita su tutte le risorse GPIB disponibili
        print(" -> Scansione automatica risorse GPIB per E3646A...")
        for res in rm.list_resources():
            if "gpib" in res.lower():
                try:
                    test_inst = rm.open_resource(res, timeout=2500)
                    idn = test_inst.query("*IDN?").strip()
                    if any(k in idn for k in ["E3646", "3646", "E364"]):
                        psu = test_inst
                        print(f" -> [OK] Alimentatore DC connesso su {res}: {idn}")
                        break
                    test_inst.close()
                except Exception:
                    continue

    if not psu:
        print("\n[ERRORE] Alimentatore Agilent E3646A non trovato su bus GPIB!")
        print(" -> Verifica che il cavo GPIB sia ben avvitato dietro l'E3646A.")
        print(" -> Controlla sul display del generatore: I/O config -> GPIB / 488.")
        if gen:
            gen.close()
        if scope:
            scope.close()
        return None, None, None

    return gen, scope, psu


def setup_alimentatore(psu, curr_limit=PSU_CURRENT_LIMIT_A, simulate=False):
    """Configura l'Agilent E3646A per erogare fino a 20V su Output 1 in sicurezza."""
    print(f"\n[SETUP E3646A] Configurazione Output 1:")
    if simulate:
        psu.write("INST:SEL OUT1")
        psu.write("VOLT:RANG HIGH")
        psu.write(f"CURR {curr_limit:.3f}")
        psu.write("VOLT 0.0")
        psu.write("OUTP ON")
        print(" -> [OK] Modalita Simulazione: Output 1 configurato su High Range (0-20V).")
        return True

    try:
        psu.write("*CLS")
        # 1. Selezione Output 1
        psu.write("INST:SEL OUT1")
        time.sleep(0.05)
        # 2. Impostazione Gamma Alta (0-20V / 1.5A).
        #    Senza questo comando, l'E3646A all'avvio e' in Low Range (0-8V) e darebbe errore oltre 8V!
        try:
            psu.write("VOLT:RANG HIGH")
        except Exception:
            psu.write("VOLT:RANG P20V")
        time.sleep(0.05)
        # 3. Limite Corrente di Protezione (100 mA)
        psu.write(f"CURR {curr_limit:.3f}")
        time.sleep(0.05)
        # 4. Tensione iniziale sicura a 0.0 V
        psu.write("VOLT 0.0")
        time.sleep(0.05)
        # 5. Attivazione Uscita
        psu.write("OUTP ON")
        time.sleep(0.1)

        err = psu.query("SYST:ERR?").strip()
        rang_query = psu.query("VOLT:RANG?").strip()
        curr_query = psu.query("CURR?").strip()
        print(f" -> Canale Selezionato : Output 1")
        print(f" -> Gamma Tensione    : {rang_query} (0-20V)")
        print(f" -> Limite Compliance : {float(curr_query)*1000:.0f} mA")
        print(f" -> Uscita Hardware   : ATTIVA (Inizialmente a 0.0 V)")
        if not err.startswith('+0'):
            print(f"    [AVVISO E3646A]: {err}")
        return True
    except Exception as e:
        print(f"[ERRORE SETUP E3646A]: {e}")
        return False


def spegni_sicuro_alimentatore(psu, simulate=False):
    """Procedura di sicurezza: rampa a 0V e spegnimento uscita E3646A."""
    print("\n[SICUREZZA E3646A] Azzeramento tensione e spegnimento uscita...")
    try:
        if psu:
            psu.write("INST:SEL OUT1")
            psu.write("VOLT 0.0")
            time.sleep(0.1)
            psu.write("OUTP OFF")
            print(" -> [OK] Tensione azzerata a 0.0 V e OUTP disattivato.")
    except Exception as e:
        print(f" -> [AVVISO] Errore durante spegnimento sicuro: {e}")


def main():
    parser = argparse.ArgumentParser(description="Sweep Combinato VDC (Agilent E3646A) + Frequenza MEMS")
    parser.add_argument("--vdc-start", type=float, default=None, help="Tensione VDC iniziale in Volt [default: 0.0]")
    parser.add_argument("--vdc-stop", type=float, default=None, help="Tensione VDC finale in Volt [default: 20.0]")
    parser.add_argument("--vdc-step", type=float, default=None, help="Passo di tensione VDC in Volt [default: 2.0]")
    parser.add_argument("--f-center", type=float, default=None, help="Frequenza centrale in Hz [default: 417400]")
    parser.add_argument("--delta-f", type=float, default=None, help="Semi-intervallo frequenza +/- Hz [default: 600]")
    parser.add_argument("--pts-side", type=int, default=None, help="Punti a sx e dx del centro [default: 50]")
    parser.add_argument("--navg", type=int, default=None, help="Medie hardware oscilloscopio [default: 64]")
    parser.add_argument("--psu-addr", type=str, default=None, help="Indirizzo GPIB per E3646A")
    parser.add_argument("--simulate", action="store_true", help="Esegui simulazione software completa")
    args = parser.parse_args()

    print("=" * 85)
    print(" SWEEP AUTOMATICO DC + FREQUENZA - CARATTERIZZAZIONE COMPLETA RISONATORE MEMS")
    print(" Agilent E3646A (VDC 0-20V Output 1) + Agilent 33220A (DDS) + Keysight MSO-X 3014A")
    print(" Studio dell'Accoppiamento Elettromeccanico e Spring Softening (f0 vs VDC^2)")
    print("=" * 85)

    is_interactive = (args.vdc_start is None and args.vdc_stop is None and args.f_center is None)

    vdc_start = args.vdc_start if args.vdc_start is not None else DEFAULT_VDC_START
    vdc_stop = args.vdc_stop if args.vdc_stop is not None else DEFAULT_VDC_STOP
    vdc_step = args.vdc_step if args.vdc_step is not None else DEFAULT_VDC_STEP
    f_center = args.f_center if args.f_center is not None else DEFAULT_F_CENTER
    delta_f = args.delta_f if args.delta_f is not None else DEFAULT_DELTA_F
    pts_side = args.pts_side if args.pts_side is not None else DEFAULT_PTS_SIDE
    navg = args.navg if args.navg is not None else DEFAULT_N_AVG
    simulate = args.simulate

    if is_interactive:
        print("\n[CONFIGURAZIONE PARAMETRI] Premi INVIO per confermare i valori ottimali:")
        try:
            inp_v0 = input(f" -> Tensione VDC INIZIALE [V]               [{vdc_start:.1f}]: ").strip()
            if inp_v0:
                vdc_start = float(inp_v0)

            inp_v1 = input(f" -> Tensione VDC FINALE   [V]               [{vdc_stop:.1f}]: ").strip()
            if inp_v1:
                vdc_stop = float(inp_v1)

            inp_vs = input(f" -> Passo VDC             [V]               [{vdc_step:.1f}]: ").strip()
            if inp_vs:
                vdc_step = float(inp_vs)

            inp_fc = input(f" -> Frequenza CENTRALE    [Hz]              [{f_center:,.0f}]: ").strip()
            if inp_fc:
                f_center = float(inp_fc)

            inp_df = input(f" -> Semi-intervallo (+/- Hz)                [{delta_f:,.0f}]: ").strip()
            if inp_df:
                delta_f = float(inp_df)

            inp_pts = input(f" -> Punti Freq a sx/dx (es. 50 = 101 pt)    [{pts_side}]: ").strip()
            if inp_pts:
                pts_side = int(inp_pts)

            inp_avg = input(f" -> Medie Hardware Oscilloscopio (es. 64)   [{navg}]: ").strip()
            if inp_avg:
                navg = int(inp_avg)
        except ValueError:
            print("[ATTENZIONE] Valore non valido, uso i parametri predefiniti.")

    # Generazione elenco tensioni VDC
    num_vdc_steps = int(round((vdc_stop - vdc_start) / vdc_step)) + 1
    vdc_values = [vdc_start + i * vdc_step for i in range(num_vdc_steps)]
    # Assicura clamp a 20V per limiti fisici dello strumento
    vdc_values = [min(20.0, max(0.0, v)) for v in vdc_values]

    # Generazione elenco frequenze sweep
    f_start = f_center - delta_f
    f_stop = f_center + delta_f
    total_f_points = 2 * pts_side + 1
    step_f = (2.0 * delta_f) / (total_f_points - 1)
    frequenze = [f_start + i * step_f for i in range(total_f_points)]

    # Calcolo tempi stimati
    tempo_per_punto_f = 0.04 + (0.003 * navg) + 0.05
    tempo_per_sweep_f = total_f_points * tempo_per_punto_f + SETTLE_VDC_S
    tempo_totale_s = len(vdc_values) * tempo_per_sweep_f

    print("\n" + "=" * 85)
    print(" RIEPILOGO PIANO DI MISURA 2D (VDC x Frequenza):")
    print("=" * 85)
    print(f"  * Punti VDC (Alimentatore E3646A) : {len(vdc_values)} passi da {vdc_start:.1f}V a {vdc_stop:.1f}V (passo {vdc_step:.1f}V)")
    print(f"    Valori VDC : {', '.join(f'{v:.1f}V' for v in vdc_values)}")
    print(f"  * Sweep Frequenza (Agilent 33220A) : da {f_start:,.1f} Hz a {f_stop:,.1f} Hz ({total_f_points} punti, passo {step_f:.2f} Hz)")
    print(f"  * Oscilloscopio (Keysight 3014A)   : {navg} medie hardware (:DIGitize + *OPC?)")
    print(f"  * Margine di Sicurezza Buffer      : +50% tempo extra di attesa dopo riempimento al 100%")
    print(f"  * Display Oscilloscopio            : Traccia viva e refresh attivo a ogni punto (:RUN)")
    print(f"  * Punti Misura Totali              : {len(vdc_values) * total_f_points} combinazioni (VDC, Freq)")
    print(f"  * Durata Totale Stimata            : circa {tempo_totale_s:.0f} s ({tempo_totale_s/60:.1f} min)")
    print("=" * 85)

    if is_interactive and not simulate:
        conferma = input("\nPremi INVIO per iniziare la misura completa (oppure 'q' per annullare): ")
        if conferma.strip().lower() == 'q':
            print("Operazione annullata.")
            return

    # Inizializzazione Connessioni VISA
    gen = None
    scope = None
    psu = None
    rm = None

    if simulate:
        print("\n[SIMULAZIONE] Inizializzazione strumenti virtuali di banco...")
        gen = SimulatedInstrument("33220A")
        scope = SimulatedInstrument("MSO-X-3014A")
        psu = SimulatedInstrument("E3646A")
    else:
        try:
            import pyvisa
            rm = pyvisa.ResourceManager()
        except Exception as e:
            print(f"\n[ERRORE FATALE] Impossibile inizializzare VISA: {e}")
            input("\nPremi INVIO per uscire...")
            return

        gen, scope, psu = connetti_strumenti(rm, args.psu_addr)
        if not gen or not scope or not psu:
            input("\nPremi INVIO per uscire...")
            return

    # Cartella di output e file CSV
    cartella_lavoro = os.path.dirname(os.path.abspath(__file__))
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    cartella_sessione = os.path.join(cartella_lavoro, f"sessione_DC_{timestamp_str}")
    os.makedirs(cartella_sessione, exist_ok=True)

    file_master = os.path.join(cartella_sessione, f"sweep_master_DC_{int(f_center)}Hz_{len(vdc_values)}V_{timestamp_str}.csv")
    file_riassunto = os.path.join(cartella_sessione, f"riassunto_picchi_vs_vdc_{timestamp_str}.csv")

    f_master_csv = open(file_master, 'w', newline='', encoding='utf-8')
    w_master = csv.writer(f_master_csv)
    w_master.writerow([f"# Sweep MEMS 2D (VDC E3646A x Frequenza 33220A) - {timestamp_str}"])
    w_master.writerow([f"# VDC da {vdc_start}V a {vdc_stop}V (passo {vdc_step}V, {len(vdc_values)} curve)"])
    w_master.writerow([f"# f_center={f_center} Hz, span=+/-{delta_f} Hz, pts={total_f_points}, navg={navg}"])
    w_master.writerow([
        "vdc_target_V", "vdc_meas_V", "idc_meas_A",
        "step_f", "frequency_Hz", "freq_readback_Hz",
        "Vin_Vpp_V", "Vout_Vpp_V", "Gain_linear", "Gain_dB", "Phase_deg"
    ])
    f_master_csv.flush()

    f_riassunto_csv = open(file_riassunto, 'w', newline='', encoding='utf-8')
    w_riassunto = csv.writer(f_riassunto_csv)
    w_riassunto.writerow([f"# Riassunto Picchi di Risonanza vs VDC - {timestamp_str}"])
    w_riassunto.writerow(["vdc_target_V", "vdc_meas_V", "fs_resonance_Hz", "fp_antiresonance_Hz", "delta_f_Hz", "Gain_peak_lin", "Gain_peak_dB", "Phase_peak_deg"])
    f_riassunto_csv.flush()

    # Setup Hardware Iniziale
    setup_alimentatore(psu, curr_limit=PSU_CURRENT_LIMIT_A, simulate=simulate)

    try:
        if not simulate:
            gen.write("*CLS")
            scope.write("*CLS")
            scope.timeout = 15000
            gen.write(":FUNCtion SINusoid")
            gen.write(":BURSt:STATe OFF")
            gen.write(f":FREQuency {f_start:.3f}")
            gen.write(":OUTPut ON")

            vpp_str = gen.query(":VOLTage?").strip()
            vpp_val = float(vpp_str) if vpp_str else 0.1
            print(f" -> Ampiezza AC su 33220A: {vpp_val*1000:.1f} mVpp (NON modificata)")

            scope.write(":CHANnel1:DISPlay ON")
            scope.write(":CHANnel3:DISPlay ON")
            scope.write(":ACQuire:TYPE AVERage")
            scope.write(f":ACQuire:COUNt {navg}")
            scope.write(":RUN")

            scope.write(":MEASure:VPP CHANnel3")
            scope.write(":MEASure:VPP CHANnel1")
            scope.write(":MEASure:PHASe CHANnel1,CHANnel3")
        else:
            vpp_val = 0.200

        start_time_total = time.time()
        print("\n" + "=" * 85)
        print(" INIZIO SEQUENZA DI MISURA 2D")
        print("=" * 85)

        for i_vdc, vdc_t in enumerate(vdc_values, 1):
            print(f"\n[{i_vdc:02d}/{len(vdc_values):02d}] IMPOSTAZIONE VDC = {vdc_t:5.1f} V (Output 1 E3646A)...")
            
            # Imposta la tensione VDC
            psu.write(f"VOLT {vdc_t:.3f}")
            time.sleep(SETTLE_VDC_S)

            # Lettura tensione e corrente effettive
            try:
                vdc_meas_str = psu.query("MEAS:VOLT?").strip()
                idc_meas_str = psu.query("MEAS:CURR?").strip()
                vdc_meas = parsa_valore_scpi(vdc_meas_str)
                idc_meas = parsa_valore_scpi(idc_meas_str)
            except Exception:
                vdc_meas = vdc_t
                idc_meas = 0.0

            if math.isnan(vdc_meas):
                vdc_meas = vdc_t
            if math.isnan(idc_meas):
                idc_meas = 0.0

            print(f" -> Tensione Misurata: {vdc_meas:.3f} V | Corrente: {idc_meas*1000:.2f} mA")

            # File per singolo VDC (compatibili al 100% con cartella Misure_bode_modulo_fase)
            tag_vdc = f"VDC_{vdc_t:04.1f}V".replace(".", "p")
            f_single_master_path = os.path.join(cartella_sessione, f"sweep_{tag_vdc}_{int(f_center)}Hz_{total_f_points}pt_{timestamp_str}.csv")
            f_single_mod_path = os.path.join(cartella_sessione, f"modulo_{tag_vdc}_{int(f_center)}Hz_{total_f_points}pt_{timestamp_str}.csv")
            f_single_fas_path = os.path.join(cartella_sessione, f"fase_{tag_vdc}_{int(f_center)}Hz_{total_f_points}pt_{timestamp_str}.csv")

            f_s_master = open(f_single_master_path, 'w', newline='', encoding='utf-8')
            w_s_master = csv.writer(f_s_master)
            w_s_master.writerow([f"# Sweep MEMS Completo a VDC={vdc_t:.1f}V ({navg} Medie) - {timestamp_str}"])
            w_s_master.writerow([f"# VDC_target={vdc_t} V, VDC_meas={vdc_meas:.3f} V, IDC_meas={idc_meas*1000:.2f} mA, f_center={f_center} Hz, pts={total_f_points}"])
            w_s_master.writerow(["step", "frequency_Hz", "freq_readback_Hz", "Vin_Vpp_V", "Vout_Vpp_V", "Gain_linear", "Gain_dB", "Phase_deg"])

            f_s_mod = open(f_single_mod_path, 'w', newline='', encoding='utf-8')
            w_s_mod = csv.writer(f_s_mod)
            w_s_mod.writerow([f"# Sweep MEMS Solo MODULO a VDC={vdc_t:.1f}V - {timestamp_str}"])
            w_s_mod.writerow(["frequency_Hz", "Vin_Vpp_V", "Vout_Vpp_V", "Gain_linear", "Gain_dB"])

            f_s_fas = open(f_single_fas_path, 'w', newline='', encoding='utf-8')
            w_s_fas = csv.writer(f_s_fas)
            w_s_fas.writerow([f"# Sweep MEMS Solo FASE a VDC={vdc_t:.1f}V - {timestamp_str}"])
            w_s_fas.writerow(["frequency_Hz", "Phase_deg"])

            print("-" * 85)
            print(f"{'Pt':>4}/{total_f_points} | {'Freq Target':>11} | {'Vin [mV]':>9} | {'Vout [mV]':>9} | {'G [dB]':>8} | {'Fase [°]':>8} | VDC")
            print("-" * 85)

            cur_gains = []
            cur_phases = []
            cur_freqs = []

            for idx_f, f in enumerate(frequenze, 1):
                # 1. Imposta la frequenza DDS
                gen.write(f":FREQuency {f:.3f}")
                time.sleep(SETTLE_MEMS_S)

                # 2. Handshake Hardware: :DIGitize + *OPC?
                #    In più, attendiamo un MARGINE DI SICUREZZA pari a META' DEL TEMPO DI BUFFER (+50%)!
                if not simulate:
                    try:
                        t_dig_start = time.time()
                        scope.write(":DIGitize CHANnel1,CHANnel3")
                        scope.query("*OPC?")
                        t_dig_elapsed = time.time() - t_dig_start

                        # Margine di sicurezza: attende ancora il 50% del tempo impiegato per riempire il buffer
                        t_safety_margin = max(0.050, 0.50 * t_dig_elapsed)
                        time.sleep(t_safety_margin)
                    except Exception:
                        pass

                # 3. Lettura hardware a traccia congelata
                try:
                    resp = scope.query(":MEASure:VPP? CHANnel3;:MEASure:VPP? CHANnel1;:MEASure:PHASe? CHANnel1,CHANnel3")
                    parts = [p.strip() for p in resp.split(';')]
                    vin = parsa_valore_scpi(parts[0]) if len(parts) > 0 else float('nan')
                    vout = parsa_valore_scpi(parts[1]) if len(parts) > 1 else float('nan')
                    phase = parsa_valore_scpi(parts[2]) if len(parts) > 2 else float('nan')
                except Exception:
                    vin = float('nan')
                    vout = float('nan')
                    phase = float('nan')

                # 4. Riavvia display oscilloscopio (:RUN) per mostrare il refresh/lampeggio continuo a schermo
                if not simulate:
                    try:
                        scope.write(":RUN")
                    except Exception:
                        pass

                if not math.isnan(vin) and not math.isnan(vout) and vin > 1e-9:
                    gain_lin = vout / vin
                    gain_db = 20.0 * math.log10(max(1e-12, gain_lin))
                else:
                    gain_lin = float('nan')
                    gain_db = float('nan')

                cur_freqs.append(f)
                cur_gains.append(gain_lin)
                cur_phases.append(phase)

                # Scrittura sui singoli CSV
                w_s_master.writerow([
                    idx_f, f"{f:.3f}", f"{f:.3f}",
                    f"{vin:.6e}" if not math.isnan(vin) else "nan",
                    f"{vout:.6e}" if not math.isnan(vout) else "nan",
                    f"{gain_lin:.6e}" if not math.isnan(gain_lin) else "nan",
                    f"{gain_db:.3f}" if not math.isnan(gain_db) else "nan",
                    f"{phase:.3f}" if not math.isnan(phase) else "nan"
                ])
                f_s_master.flush()

                w_s_mod.writerow([
                    f"{f:.3f}",
                    f"{vin:.6e}" if not math.isnan(vin) else "nan",
                    f"{vout:.6e}" if not math.isnan(vout) else "nan",
                    f"{gain_lin:.6e}" if not math.isnan(gain_lin) else "nan",
                    f"{gain_db:.3f}" if not math.isnan(gain_db) else "nan"
                ])
                f_s_mod.flush()

                w_s_fas.writerow([
                    f"{f:.3f}",
                    f"{phase:.3f}" if not math.isnan(phase) else "nan"
                ])
                f_s_fas.flush()

                # Scrittura sul Master Cumulativo
                w_master.writerow([
                    f"{vdc_t:.2f}", f"{vdc_meas:.3f}", f"{idc_meas:.6e}",
                    idx_f, f"{f:.3f}", f"{f:.3f}",
                    f"{vin:.6e}" if not math.isnan(vin) else "nan",
                    f"{vout:.6e}" if not math.isnan(vout) else "nan",
                    f"{gain_lin:.6e}" if not math.isnan(gain_lin) else "nan",
                    f"{gain_db:.3f}" if not math.isnan(gain_db) else "nan",
                    f"{phase:.3f}" if not math.isnan(phase) else "nan"
                ])
                f_master_csv.flush()

                vin_str = f"{vin*1e3:.1f}" if not math.isnan(vin) else "---"
                vout_str = f"{vout*1e3:.1f}" if not math.isnan(vout) else "---"
                gdb_str = f"{gain_db:+.2f}" if not math.isnan(gain_db) else "---"
                phase_str = f"{phase:+.2f}" if not math.isnan(phase) else "---"

                # Stampa solo alcuni punti per non intasare il terminale, ma stampa sempre il primo, l'ultimo e ogni 5
                if idx_f == 1 or idx_f == total_f_points or (idx_f % 5 == 0):
                    print(f"{idx_f:4d}/{total_f_points} | {f:11.1f} | {vin_str:>9} | {vout_str:>9} | {gdb_str:>8} | {phase_str:>8} | {vdc_t:4.1f}V")

            f_s_master.close()
            f_s_mod.close()
            f_s_fas.close()

            # Calcolo picco risonanza e minimo antirisonanza per questo VDC
            val_gains = [g for g in cur_gains if not math.isnan(g)]
            if val_gains:
                g_max = max(val_gains)
                g_min = min(val_gains)
                idx_max = cur_gains.index(g_max)
                idx_min = cur_gains.index(g_min)
                f_peak = cur_freqs[idx_max]
                f_dip = cur_freqs[idx_min]
                p_peak = cur_phases[idx_max]
                g_max_db = 20.0 * math.log10(max(1e-12, g_max))

                w_riassunto.writerow([
                    f"{vdc_t:.2f}", f"{vdc_meas:.3f}",
                    f"{f_peak:.2f}", f"{f_dip:.2f}", f"{abs(f_dip - f_peak):.2f}",
                    f"{g_max:.6e}", f"{g_max_db:.3f}", f"{p_peak:.3f}"
                ])
                f_riassunto_csv.flush()
                print(f" -> [RISULTATO VDC={vdc_t:.1f}V]: fs = {f_peak:,.1f} Hz | Gmax = {g_max_db:+.2f} dB | fp = {f_dip:,.1f} Hz")

    except KeyboardInterrupt:
        print("\n\n[INTERRUZIONE] Sweep fermato manualmente dall'utente con Ctrl+C.")
    finally:
        f_master_csv.close()
        f_riassunto_csv.close()

        # Sicurezza Hardware E3646A: Azzera Tensione e Spegni Uscita
        spegni_sicuro_alimentatore(psu, simulate=simulate)

        try:
            if scope:
                scope.write(":RUN")
                scope.close()
            if gen:
                gen.close()
            if psu:
                psu.close()
            if rm:
                rm.close()
        except Exception:
            pass

        durata = time.time() - start_time_total
        print("-" * 85)
        print(f"[COMPLETATO] Sequenza 2D terminata in {durata:.1f} s ({durata/60:.1f} min).")
        print(f"\n[CARTELLA SESSIONE]: {cartella_sessione}")
        print(f" 1. Master Totale      : {os.path.basename(file_master)}")
        print(f" 2. Riassunto fs vs VDC: {os.path.basename(file_riassunto)}")
        print(f" 3. File Singoli VDC   : {len(vdc_values)} triplette CSV (sweep, modulo, fase)")

        # Generazione automatica dei grafici comparativi multi-curva
        try:
            from plotta_sweep_dc import elabora_sessione_dc
            print("\n[POST-PROCESSING] Generazione grafici comparativi multi-VDC...")
            elabora_sessione_dc(cartella_sessione)
        except Exception as e:
            print(f"\n[NOTA] Per visualizzare i grafici esegui 'plotta_ultimo_sweep_dc.bat' ({e})")

    print("\nMisura conclusa con successo.")
    if is_interactive:
        input("\nPremi INVIO per uscire...")


if __name__ == "__main__":
    main()

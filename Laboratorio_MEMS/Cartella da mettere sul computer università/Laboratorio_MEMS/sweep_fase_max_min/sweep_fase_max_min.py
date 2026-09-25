"""
Sweep Burst Phase con Misura Automatica di Vmax, Vmin e Ampiezza di Picco
========================================================================
Strumenti: Agilent 33220A (GPIB) + Keysight MSO-X 3014A (USB)

Funzionalita':
  1. Configura Agilent 33220A in modalita' Burst con Trigger Interno (:BURSt:MODE TRIG, :TRIG:SOUR INT).
  2. Esegue lo sweep della fase (:BURSt:PHASe <gradi>) da inizio a fine con passo selezionabile (es. -180° a +180°, passo 5°).
  3. L'oscilloscopio acquisisce con il numero di medie scelto (:ACQuire:COUNt <medie>)
     e attende con handshake hardware (:DIGitize + *OPC? + tempo di margine).
  4. Misura automaticamente dalla schermata dell'oscilloscopio su Canale 1:
     - Vmax [mV]
     - Vmin [mV]
     - Ampiezza di Picco A_peak = max(|Vmax|, |Vmin|) [mV]
     - Vpp = Vmax - Vmin [mV]
  5. Salva tutti i dati in un file CSV compatto e ordinato pronto per l'analisi.
  6. Include modalita' simulatore (--simulate) per test offline immediati.
  7. Compatibile al 100% con Python Portatile (usa solo PyVISA e libreria standard Python).
"""

import sys
import os
import time
import math
import csv
import argparse
from datetime import datetime

# Indirizzi Primari Verificati in Laboratorio
GEN_PRIMARY_ADDR = "GPIB1::10::INSTR"
GEN_FALLBACK_ADDRS = ["GPIB1::10::INSTR", "GPIB0::10::INSTR", "GPIB::10::INSTR"]
SCOPE_PRIMARY_ADDR = "USB0::2391::6056::MY52100688::INSTR"

DEFAULT_PHASE_START = -180.0
DEFAULT_PHASE_STOP  =  180.0
DEFAULT_PHASE_STEP  =    5.0
DEFAULT_N_AVG       =     32
DEFAULT_SETTLE_S    =   0.050
SCPI_INVALID_VAL    =  9.9e36


class SimulatedInstrument:
    """Simulatore per test offline."""
    def __init__(self, name):
        self.name = name
        self.phase = 0.0
        self.navg = 32

    def write(self, cmd):
        u = cmd.strip().upper()
        if "PHAS" in u:
            parts = cmd.split()
            if len(parts) > 1:
                try:
                    self.phase = float(parts[1])
                except ValueError:
                    pass
        elif "COUN" in u:
            parts = cmd.split()
            if len(parts) > 1:
                try:
                    self.navg = int(parts[1])
                except ValueError:
                    pass

    def query(self, cmd):
        if ";" in cmd:
            subcmds = cmd.split(";")
            results = [self.query(sc.strip()) for sc in subcmds]
            query_res = [r for sc, r in zip(subcmds, results) if "?" in sc]
            return ";".join(query_res) if query_res else (results[-1] if results else "0.0")

        u = cmd.strip().upper()
        if "*IDN?" in u:
            if "33220" in self.name:
                return "Agilent Technologies,33220A,MY44042651,2.06-2.06-26-2"
            return "AGILENT TECHNOLOGIES,MSO-X 3014A,MY52100688,02.42.2017032900"
        if "*OPC?" in u:
            return "1"
        if "SYST:ERR?" in u:
            return '+0,"No error"'
        if "PHAS" in u and "?" in u:
            return f"{self.phase:.3f}"
        if "VOLT" in u and "?" in u:
            return "0.200000"
        if "FREQ" in u and "?" in u:
            return "417800.0"
        if "MEAS:VMAX?" in u or "VMAX?" in u:
            # Modello con modulazione di fase
            phi_rad = math.radians(self.phase)
            vmax = 0.022 + 0.005 * math.sin(phi_rad - 0.5)
            return f"{vmax:.6e}"
        if "MEAS:VMIN?" in u or "VMIN?" in u:
            phi_rad = math.radians(self.phase)
            vmin = -(0.021 + 0.004 * math.sin(phi_rad - 0.5))
            return f"{vmin:.6e}"
        if "MEAS:VPP?" in u or "VPP?" in u:
            phi_rad = math.radians(self.phase)
            vpp = 0.043 + 0.009 * math.sin(phi_rad - 0.5)
            return f"{vpp:.6e}"
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


def connetti_generatore(rm, simulate=False):
    if simulate:
        return SimulatedInstrument("33220A")

    print("[CONNESSIONE 1/2] Ricerca Generatore Agilent 33220A...")
    for addr in GEN_FALLBACK_ADDRS:
        try:
            inst = rm.open_resource(addr, timeout=4000)
            idn = inst.query("*IDN?").strip()
            if "33220" in idn:
                print(f" -> [OK] Generatore connesso su {addr}: {idn}")
                return inst
            inst.close()
        except Exception:
            continue

    print(" -> Scansione porte VISA per 33220A...")
    for res in rm.list_resources():
        if "gpib" in res.lower() or "usb" in res.lower():
            try:
                inst = rm.open_resource(res, timeout=3000)
                idn = inst.query("*IDN?").strip()
                if "33220" in idn:
                    print(f" -> [OK] Generatore trovato su {res}: {idn}")
                    return inst
                inst.close()
            except Exception:
                continue
    return None


def connetti_oscilloscopio(rm, simulate=False):
    if simulate:
        return SimulatedInstrument("MSO-X-3014A")

    print("[CONNESSIONE 2/2] Ricerca Oscilloscopio Keysight MSO-X 3014A...")
    try:
        inst = rm.open_resource(SCOPE_PRIMARY_ADDR, timeout=60000)
        idn = inst.query("*IDN?").strip()
        print(f" -> [OK] Oscilloscopio connesso su {SCOPE_PRIMARY_ADDR}: {idn}")
        return inst
    except Exception:
        pass

    print(" -> Scansione porte USB per oscilloscopio...")
    for res in rm.list_resources():
        if "usb" in res.lower():
            try:
                inst = rm.open_resource(res, timeout=60000)
                idn = inst.query("*IDN?").strip()
                if any(k in idn for k in ["3014", "Keysight", "Agilent", "InfiniiVision"]):
                    print(f" -> [OK] Oscilloscopio trovato su {res}: {idn}")
                    return inst
                inst.close()
            except Exception:
                continue
    return None


def main():
    parser = argparse.ArgumentParser(description="Sweep Burst Phase con Misura Automatica Vmax e Vmin")
    parser.add_argument("--phase-start", type=float, default=None, help="Fase iniziale [°] (default: -180.0)")
    parser.add_argument("--phase-stop", type=float, default=None, help="Fase finale [°] (default: +180.0)")
    parser.add_argument("--phase-step", type=float, default=None, help="Passo di fase [°] (default: 5.0)")
    parser.add_argument("--navg", type=int, default=None, help="Numero medie hardware (default: 32)")
    parser.add_argument("--margin", type=float, default=0.050, help="Tempo margine attesa post medie [s]")
    parser.add_argument("--settle", type=float, default=DEFAULT_SETTLE_S, help="Tempo assestamento post cambio fase [s]")
    parser.add_argument("--simulate", action="store_true", help="Modalita simulazione offline")
    args = parser.parse_args()

    print("=" * 80)
    print(" SWEEP BURST PHASE - MISURA AUTOMATICA VMAX, VMIN E PICCO | CH1")
    print(" Agilent 33220A + Keysight MSO-X 3014A")
    print(" Calcolo automatico: Vmax, Vmin, Vpp e A_peak = max(|Vmax|, |Vmin|)")
    print("=" * 80)

    is_interactive = (args.phase_start is None and args.phase_stop is None and args.phase_step is None)

    phase_start = args.phase_start if args.phase_start is not None else DEFAULT_PHASE_START
    phase_stop  = args.phase_stop  if args.phase_stop  is not None else DEFAULT_PHASE_STOP
    phase_step  = args.phase_step  if args.phase_step  is not None else DEFAULT_PHASE_STEP
    navg        = args.navg        if args.navg        is not None else DEFAULT_N_AVG
    margin_s    = args.margin
    settle_s    = args.settle
    simulate    = args.simulate

    if is_interactive:
        print("\n[CONFIGURAZIONE PARAMETRI SWEEP]")
        print("Premi INVIO per confermare il valore di default tra parentesi quadre:\n")
        try:
            inp = input(f" -> Fase INIZIALE burst [gradi]           [{phase_start:+.1f}°]: ").strip()
            if inp:
                phase_start = float(inp)

            inp = input(f" -> Fase FINALE burst [gradi]             [{phase_stop:+.1f}°]: ").strip()
            if inp:
                phase_stop = float(inp)

            inp = input(f" -> PASSO di fase [gradi]                 [{phase_step:.1f}°]: ").strip()
            if inp:
                phase_step = abs(float(inp))
                if phase_step == 0:
                    phase_step = 5.0

            inp = input(f" -> Medie hardware oscilloscopio          [{navg}]: ").strip()
            if inp:
                navg = int(inp)

            inp = input(f" -> Tempo di margine extra [secondi]      [{margin_s:.2f} s]: ").strip()
            if inp:
                margin_s = float(inp)

        except ValueError:
            print("[ATTENZIONE] Valore non valido, uso i parametri predefiniti.")

    # Generazione lista fasi
    if phase_stop < phase_start:
        step_dir = -abs(phase_step)
    else:
        step_dir = abs(phase_step)

    fasi = []
    curr = phase_start
    while (step_dir > 0 and curr <= phase_stop + 1e-6) or (step_dir < 0 and curr >= phase_stop - 1e-6):
        fasi.append(round(curr, 3))
        curr += step_dir

    total_steps = len(fasi)
    if total_steps == 0:
        print("[ERRORE] Nessun passo di fase da eseguire.")
        return

    print("\n" + "=" * 80)
    print(" RIEPILOGO PARAMETRI MISURA:")
    print("=" * 80)
    print(f"  * Intervallo Fase : da {phase_start:+.1f}° a {phase_stop:+.1f}°")
    print(f"  * Passo di Fase   : {phase_step:.2f}° ({total_steps} passi totali)")
    print(f"  * Medie Hardware  : {navg} medie (:ACQuire:COUNt {navg})")
    print(f"  * Canale Misura   : Canale 1 (Vout MEMS)")
    print(f"  * Misure Calcolate: Vmax, Vmin, Vpp e A_peak = max(|Vmax|, |Vmin|)")
    print(f"  * Tempo Margine   : {margin_s:.3f} s dopo il completamento delle medie")
    print("=" * 80)

    if is_interactive and not simulate:
        conferma = input("\nPremi INVIO per avviare la misura (oppure 'q' per annullare): ")
        if conferma.strip().lower() == 'q':
            print("Operazione annullata.")
            return

    # Inizializzazione Strumenti
    gen = None
    scope = None
    rm = None

    if simulate:
        gen = SimulatedInstrument("33220A")
        scope = SimulatedInstrument("MSO-X-3014A")
        print("\n[MODALITA SIMULATORE ATTIVA]")
    else:
        try:
            import pyvisa
            rm = pyvisa.ResourceManager()
        except Exception as e:
            print(f"\n[ERRORE FATALE] PyVISA non disponibile: {e}")
            input("Premi INVIO per uscire...")
            return

        gen = connetti_generatore(rm, simulate=False)
        if not gen:
            print("\n[ERRORE] Generatore Agilent 33220A non trovato.")
            input("Premi INVIO per uscire...")
            return

        scope = connetti_oscilloscopio(rm, simulate=False)
        if not scope:
            print("\n[ERRORE] Oscilloscopio Keysight MSO-X 3014A non trovato.")
            input("Premi INVIO per uscire...")
            return

    # Setup parametri
    print("\n[SETUP] Configurazione banco di misura...")
    try:
        if not simulate:
            gen.write("*CLS")
            scope.write("*CLS")
            # Timeout proporzionato alle medie (nessun timeout su medie elevate)
            scope.timeout = max(35000, navg * 120)

            # 1. Configura Burst Trigger Interno su 33220A
            gen.write(":UNIT:ANGLe DEG")
            gen.write(":BURSt:MODE TRIGgered")
            gen.write(":TRIGger:SOURce INTernal")
            gen.write(":BURSt:STATe ON")
            gen.write(":OUTPut ON")

            # 2. Configura Medie su Oscilloscopio
            scope.write(":CHANnel1:DISPlay ON")
            scope.write(":ACQuire:TYPE AVERage")
            scope.write(f":ACQuire:COUNt {navg}")

            # 3. Prepara comandi di misura VMAX e VMIN sulla schermata
            scope.write(":MEASure:VMAX CHANnel1")
            scope.write(":MEASure:VMIN CHANnel1")
            scope.write(":MEASure:VPP CHANnel1")

            scope.write(":RUN")

        print(" -> Configurazione completata con successo. Inizio sweep...")
    except Exception as e:
        print(f"[ATTENZIONE] Avviso setup: {e}")

    # Preparazione File CSV
    base_dir = os.path.dirname(os.path.abspath(__file__))
    ts_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_filename = f"misure_max_min_vs_fase_{ts_str}.csv"
    csv_path = os.path.join(base_dir, csv_filename)

    f_csv = open(csv_path, 'w', newline='', encoding='utf-8')
    w_csv = csv.writer(f_csv)
    w_csv.writerow([f"# Sweep Burst Phase - Misura Vmax, Vmin e Picco CH1 - {ts_str}"])
    w_csv.writerow([f"# Range: {phase_start}° a {phase_stop}°, passo: {phase_step}°, medie: {navg}"])
    w_csv.writerow([
        "step",
        "phase_deg",
        "Vmax_mV",
        "Vmin_mV",
        "A_peak_mV",
        "Vpp_mV"
    ])
    f_csv.flush()

    print("\n" + "-" * 75)
    print(f"{'Step':>4}/{total_steps:<4} | {'Fase [°]':>9} | {'Vmax [mV]':>10} | {'Vmin [mV]':>10} | {'A_peak [mV]':>12} | {'Vpp [mV]':>10}")
    print("-" * 75)

    start_time_tot = time.time()

    try:
        for idx, fase in enumerate(fasi, 1):
            # 1. Imposta la nuova fase sul 33220A
            gen.write(f":BURSt:PHASe {fase:.3f}")
            time.sleep(settle_s)

            # 2. Handshake Hardware: :DIGitize accumula esattamente le N medie impostate
            if not simulate:
                try:
                    scope.write(":DIGitize CHANnel1")
                    scope.query("*OPC?")
                    if margin_s > 0:
                        time.sleep(margin_s)
                except Exception as e:
                    print(f"\n[AVVISO DIGITIZE step {idx}]: {e}")
                    try:
                        scope.clear()
                        scope.write("*CLS")
                    except Exception:
                        pass

            # 3. Lettura hardware automatica di Vmax, Vmin e Vpp
            vmax_v = float('nan')
            vmin_v = float('nan')
            vpp_v  = float('nan')

            try:
                meas_query = scope.query(":MEASure:VMAX? CHANnel1;:MEASure:VMIN? CHANnel1;:MEASure:VPP? CHANnel1")
                parts = [p.strip() for p in meas_query.split(';')]
                if len(parts) > 0:
                    vmax_v = parsa_valore_scpi(parts[0])
                if len(parts) > 1:
                    vmin_v = parsa_valore_scpi(parts[1])
                if len(parts) > 2:
                    vpp_v = parsa_valore_scpi(parts[2])
            except Exception:
                pass

            # Riavvia visualizzazione viva a schermo
            if not simulate:
                try:
                    scope.write(":RUN")
                except Exception:
                    pass

            # Conversione in mV
            vmax_mv = vmax_v * 1e3 if not math.isnan(vmax_v) else float('nan')
            vmin_mv = vmin_v * 1e3 if not math.isnan(vmin_v) else float('nan')
            vpp_mv  = vpp_v * 1e3  if not math.isnan(vpp_v)  else float('nan')

            # 4. Calcolo Ampiezza di Picco: max( |Vmax|, |Vmin| )
            # Es. se Vmax = +1 mV e Vmin = -4 mV -> A_peak = max(1, 4) = 4 mV
            if not math.isnan(vmax_mv) and not math.isnan(vmin_mv):
                a_peak_mv = max(abs(vmax_mv), abs(vmin_mv))
            elif not math.isnan(vmax_mv):
                a_peak_mv = abs(vmax_mv)
            elif not math.isnan(vmin_mv):
                a_peak_mv = abs(vmin_mv)
            else:
                a_peak_mv = float('nan')

            # Se Vpp non e' stato letto direttamente, calcolalo da Vmax - Vmin
            if math.isnan(vpp_mv) and not math.isnan(vmax_mv) and not math.isnan(vmin_mv):
                vpp_mv = vmax_mv - vmin_mv

            # 5. Scrittura incrementale nel CSV
            w_csv.writerow([
                idx,
                f"{fase:+.2f}",
                f"{vmax_mv:.3f}" if not math.isnan(vmax_mv) else "nan",
                f"{vmin_mv:.3f}" if not math.isnan(vmin_mv) else "nan",
                f"{a_peak_mv:.3f}" if not math.isnan(a_peak_mv) else "nan",
                f"{vpp_mv:.3f}" if not math.isnan(vpp_mv) else "nan"
            ])
            f_csv.flush()

            # Stampa progresso a video
            s_vmax = f"{vmax_mv:+8.2f}" if not math.isnan(vmax_mv) else "     nan"
            s_vmin = f"{vmin_mv:+8.2f}" if not math.isnan(vmin_mv) else "     nan"
            s_apeak= f"{a_peak_mv:8.2f}" if not math.isnan(a_peak_mv) else "     nan"
            s_vpp  = f"{vpp_mv:8.2f}" if not math.isnan(vpp_mv) else "     nan"

            print(f"{idx:4d}/{total_steps:<4} | {fase:+8.1f}° | {s_vmax:>10} | {s_vmin:>10} | {s_apeak:>12} | {s_vpp:>10}")

    except KeyboardInterrupt:
        print("\n\n[INTERRUZIONE] Misura fermata con Ctrl+C. Tutti i dati sono stati salvati.")

    finally:
        f_csv.close()
        durata = time.time() - start_time_tot

        print("-" * 75)
        print(f"[COMPLETATO] Sweep terminato in {durata:.1f} secondi.")
        print(f"\n[FILE CSV SALVATO SUL COMPUTER]:\n -> {csv_path}")
        print("=" * 75)

        if not simulate and scope:
            try:
                scope.write(":RUN")
            except Exception:
                pass


if __name__ == "__main__":
    main()

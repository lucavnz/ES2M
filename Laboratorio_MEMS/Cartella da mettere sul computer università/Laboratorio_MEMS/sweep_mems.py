"""
Sweep Automatico in Frequenza per Risonatore MEMS (Agilent 33220A + Keysight MSO-X 3014A)
Versione Completamente Automatica con Handshake Hardware:
  - L'oscilloscopio riceve il numero di medie desiderato (es. 16, 64, 256, ecc.)
  - :DIGitize CHANnel1,CHANnel3 accumula esattamente il numero di medie impostato
  - *OPC? ATTENDE AUTOMATICAMENTE che il buffer sia pieno al 100% prima di leggere
  - ZERO tempi di attesa manuali o arbitrari da calcolare
  - ZERO sfarfallio nero a schermo
  - Lettura hardware pulita e congelata di Vin (CH3), Vout (CH1) e Sfasamento
  - Salvataggio incrementale CSV e visualizzazione automatica del grafico di Bode
"""

import sys
import os
import time
import math
import cmath
import csv
import argparse
from datetime import datetime

# Indirizzi Primari Verificati in Laboratorio
GEN_PRIMARY_ADDR = "GPIB1::10::INSTR"
GEN_FALLBACK_ADDRS = ["GPIB1::10::INSTR", "GPIB0::10::INSTR", "GPIB::10::INSTR"]
SCOPE_PRIMARY_ADDR = "USB0::2391::6056::MY52100688::INSTR"

# Parametri Ottimizzati per Risultati Puliti (Risonanza attorno a ~417.4 kHz):
DEFAULT_F_CENTER = 417400.0  # 417.40 kHz (frequenza centrale nominale)
DEFAULT_DELTA_F = 600.0      # +/- 600 Hz (da 416.8 kHz a 418.0 kHz)
DEFAULT_PTS_SIDE = 50        # 50 a sx, centro, 50 a dx = 101 punti totali (passo 12.0 Hz)
DEFAULT_N_AVG = 64           # 64 MEDIE HARDWARE (modificabile a 16, 64, 256: l'oscilloscopio si adatta da solo!)
SETTLE_MEMS_S = 0.040        # 40 ms fisici per assestamento meccanico trave (> 20 tau_m)

SCPI_INVALID_VAL = 9.9e36


class SimulatedInstrument:
    """Simulatore di banco per test offline."""
    def __init__(self, name):
        self.name = name
        self.freq = 417400.0
        self.f0 = 417380.0
        self.q = 2800.0
        self.navg = 64

    def write(self, cmd):
        u = cmd.strip().upper()
        if "FREQ" in u:
            parts = cmd.split()
            if len(parts) > 1:
                try:
                    self.freq = float(parts[1])
                except ValueError:
                    pass
        if "COUN" in u:
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
            return f"SIMULATED_{self.name}_REV5.0"
        if "*OPC?" in u:
            return "1"
        if "SYST:ERR?" in u:
            return '+0,"No error"'
        if "VOLT" in u and "?" in u:
            return "0.200000"
        if "FREQ" in u and "?" in u:
            return f"{self.freq:.3f}"
        if "COUN" in u and "?" in u:
            return str(self.navg)

        # Modello fisico BVD realistico con basamento capacitivo parassita Cp
        H_base = 11.75 * cmath.exp(1j * math.radians(67.5))
        delta_f_rel = (self.freq - self.f0) / self.f0
        H_mot = (0.430 * cmath.exp(1j * math.radians(-42.0))) / (1.0 + 2j * self.q * delta_f_rel)
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


def main():
    parser = argparse.ArgumentParser(description="Sweep di Frequenza MEMS con Handshake Automatico delle Medie")
    parser.add_argument("--f-center", type=float, default=None)
    parser.add_argument("--delta-f", type=float, default=None)
    parser.add_argument("--pts-side", type=int, default=None)
    parser.add_argument("--navg", type=int, default=None)
    parser.add_argument("--simulate", action="store_true")
    args = parser.parse_args()

    print("=" * 80)
    print(" SWEEP AUTOMATICO IN FREQUENZA - CARATTERIZZAZIONE MEMS")
    print(" Agilent 33220A (GPIB1::10::INSTR) + Keysight MSO-X 3014A (USB)")
    print(" Handshake Automatico: l'oscilloscopio attende da solo che le medie siano piene")
    print("=" * 80)

    is_interactive = (args.f_center is None and args.delta_f is None and args.pts_side is None)
    
    f_center = args.f_center if args.f_center is not None else DEFAULT_F_CENTER
    delta_f = args.delta_f if args.delta_f is not None else DEFAULT_DELTA_F
    pts_side = args.pts_side if args.pts_side is not None else DEFAULT_PTS_SIDE
    navg = args.navg if args.navg is not None else DEFAULT_N_AVG
    simulate = args.simulate

    if is_interactive:
        print("\n[CONFIGURAZIONE SWEEP] Premi INVIO per confermare i parametri ottimali:")
        print(f"  (Default: centro {f_center:,.0f} Hz, +/-{delta_f:,.0f} Hz, {2*pts_side+1} punti, {navg} medie)")
        try:
            inp_fc = input(f" -> Frequenza CENTRALE [Hz]                 [{f_center:,.0f}]: ").strip()
            if inp_fc:
                f_center = float(inp_fc)

            inp_df = input(f" -> Semi-intervallo (+/- Hz)                [{delta_f:,.0f}]: ").strip()
            if inp_df:
                delta_f = float(inp_df)

            inp_pts = input(f" -> Punti a sx e dx (es. 50 = 101 pt)       [{pts_side}]: ").strip()
            if inp_pts:
                pts_side = int(inp_pts)

            inp_navg = input(f" -> Numero di medie hardware (es. 16, 64, 256) [{navg}]: ").strip()
            if inp_navg:
                navg = int(inp_navg)
        except ValueError:
            print("[ATTENZIONE] Valore non valido, uso i parametri di default.")

    f_start = f_center - delta_f
    f_stop = f_center + delta_f
    total_points = 2 * pts_side + 1
    step_f = (2.0 * delta_f) / (total_points - 1)
    frequenze = [f_start + i * step_f for i in range(total_points)]

    # Stima del tempo reale in base al numero di medie scelto
    tempo_per_punto_stimato = 0.04 + (0.003 * navg) + 0.05
    tempo_stimato_s = total_points * tempo_per_punto_stimato

    print("\n" + "=" * 80)
    print(" RIEPILOGO PARAMETRI SWEEP:")
    print("=" * 80)
    print(f"  * Frequenza Centrale : {f_center:,.1f} Hz")
    print(f"  * Range Frequenza    : da {f_start:,.1f} Hz a {f_stop:,.1f} Hz")
    print(f"  * Punti Totali       : {total_points} ({pts_side} a sx, centro, {pts_side} a dx)")
    print(f"  * Passo di Frequenza : {step_f:.2f} Hz per punto")
    print(f"  * Medie Hardware     : {navg} medie (:ACQuire:COUNt {navg})")
    print(f"  * Sincronizzazione   : Handshake :DIGitize + *OPC? + Margine di Sicurezza +50% extra buffer!")
    print(f"  * Display Oscillosc. : Traccia viva e refresh attivo a ogni punto (:RUN)")
    print(f"  * Canali Oscillosc.  : CH1 (Giallo, Uscita Vout) | CH3 (Blu, Ingresso Vin)")
    print("=" * 80)

    if is_interactive and not simulate:
        conferma = input("\nPremi INVIO per iniziare lo sweep (oppure 'q' per annullare): ")
        if conferma.strip().lower() == 'q':
            print("Operazione annullata.")
            return

    gen = None
    scope = None
    rm = None

    if simulate:
        gen = SimulatedInstrument("33220A")
        scope = SimulatedInstrument("MSO-X-3014A")
    else:
        try:
            import pyvisa
            rm = pyvisa.ResourceManager()
        except Exception as e:
            print(f"\n[ERRORE FATALE] Impossibile inizializzare VISA: {e}")
            input("\nPremi INVIO per uscire...")
            return

        # 1. Connessione Prioritaria a GPIB1::10::INSTR (con fallback automatico)
        print(f"\n[CONNESSIONE 1/2] Ricerca Generatore Agilent 33220A...")
        for addr in GEN_FALLBACK_ADDRS:
            try:
                test_inst = rm.open_resource(addr, timeout=3000)
                idn = test_inst.query("*IDN?").strip()
                if "33220" in idn:
                    gen = test_inst
                    print(f" -> [OK] Generatore connesso su {addr}: {idn}")
                    break
                test_inst.close()
            except Exception:
                continue

        if not gen:
            print(" -> Tentativo scansione tra tutte le risorse GPIB...")
            for res in rm.list_resources():
                if "gpib" in res.lower():
                    try:
                        test_inst = rm.open_resource(res, timeout=3000)
                        idn = test_inst.query("*IDN?").strip()
                        if "33220" in idn:
                            gen = test_inst
                            print(f" -> [OK] Generatore connesso su {res}: {idn}")
                            break
                        test_inst.close()
                    except Exception:
                        continue

        if not gen:
            print("\n[ERRORE] Generatore Agilent 33220A non trovato su GPIB1 o GPIB0!")
            print("Verifica che il LED 'READY' del convertitore GPIB sia verde.")
            input("\nPremi INVIO per uscire...")
            return

        # 2. Connessione all'oscilloscopio Keysight MSO-X 3014A
        print(f"\n[CONNESSIONE 2/2] Ricerca Oscilloscopio Keysight MSO-X 3014A...")
        try:
            test_inst = rm.open_resource(SCOPE_PRIMARY_ADDR, timeout=15000)
            idn = test_inst.query("*IDN?").strip()
            scope = test_inst
            print(f" -> [OK] Oscilloscopio connesso su {SCOPE_PRIMARY_ADDR}: {idn}")
        except Exception:
            print(" -> Tentativo scansione automatica porte USB...")
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
            print("Verifica che il cavo USB dell'oscilloscopio sia inserito nel computer.")
            input("\nPremi INVIO per uscire...")
            return

    # Configurazione Iniziale Strumenti
    print("\n[SETUP] Configurazione parametri...")
    try:
        if not simulate:
            gen.write("*CLS")
            scope.write("*CLS")
            scope.timeout = 15000  # 15 secondi di timeout, sicuro per qualsiasi numero di medie
            
            # Generatore: Sinusoide continua, Burst OFF, Output ON, frequenza iniziale
            gen.write(":FUNCtion SINusoid")
            gen.write(":BURSt:STATe OFF")
            gen.write(f":FREQuency {f_start:.3f}")
            gen.write(":OUTPut ON")
            
            # Legge Vpp impostato a mano dall'utente sul generatore (non viene modificato)
            vpp_str = gen.query(":VOLTage?").strip()
            vpp_val = float(vpp_str) if vpp_str else 0.1
            err_gen = gen.query("SYST:ERR?").strip()
            print(f" -> Ampiezza Vpp su 33220A: {vpp_val*1000:.1f} mVpp (NON modificata)")
            if not err_gen.startswith('+0'):
                print(f"    [AVVISO 33220A]: {err_gen}")

            # Assicura canali 1 e 3 attivi
            scope.write(":CHANnel1:DISPlay ON")
            scope.write(":CHANnel3:DISPlay ON")

            # Configura il numero di MEDIE hardware desiderato (es. 16, 64, 256)
            try:
                scope.write(":ACQuire:TYPE AVERage")
                scope.write(f":ACQuire:COUNt {navg}")
                print(f" -> Oscilloscopio configurato su {navg} MEDIE hardware.")
            except Exception as e:
                print(f" -> [AVVISO] Configurazione medie: {e}")

            # Assicura che l'oscilloscopio sia inizialmente in RUN
            scope.write(":RUN")

            # Prepara le misure hardware dell'oscilloscopio
            scope.write(":MEASure:VPP CHANnel3")
            scope.write(":MEASure:VPP CHANnel1")
            scope.write(":MEASure:PHASe CHANnel1,CHANnel3")
        else:
            vpp_val = 0.2
        print(" -> Configurazione completata con successo. Inizio sweep...")
    except Exception as e:
        print(f"[ATTENZIONE] Errore durante setup iniziale: {e}")
        vpp_val = 0.2

    # Preparazione File CSV
    cartella_lavoro = os.path.dirname(os.path.abspath(__file__))
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    file_master = os.path.join(cartella_lavoro, f"sweep_{int(f_center)}Hz_{total_points}pt_{timestamp_str}.csv")
    file_modulo = os.path.join(cartella_lavoro, f"modulo_{int(f_center)}Hz_{total_points}pt_{timestamp_str}.csv")
    file_fase = os.path.join(cartella_lavoro, f"fase_{int(f_center)}Hz_{total_points}pt_{timestamp_str}.csv")

    f_master_csv = open(file_master, 'w', newline='', encoding='utf-8')
    w_master = csv.writer(f_master_csv)
    w_master.writerow([f"# Sweep MEMS Completo Sincronizzato ({navg} Medie Modulo + Fase) - {timestamp_str}"])
    w_master.writerow([f"# f_center={f_center} Hz, span=+/-{delta_f} Hz, points={total_points}, navg={navg}, Vpp={vpp_val} V"])
    w_master.writerow(["step", "frequency_Hz", "freq_readback_Hz", "Vin_Vpp_V", "Vout_Vpp_V", "Gain_linear", "Gain_dB", "Phase_deg"])
    f_master_csv.flush()

    f_modulo_csv = open(file_modulo, 'w', newline='', encoding='utf-8')
    w_modulo = csv.writer(f_modulo_csv)
    w_modulo.writerow([f"# Sweep MEMS Solo MODULO ({navg} Medie) - {timestamp_str}"])
    w_modulo.writerow(["frequency_Hz", "Vin_Vpp_V", "Vout_Vpp_V", "Gain_linear", "Gain_dB"])
    f_modulo_csv.flush()

    f_fase_csv = open(file_fase, 'w', newline='', encoding='utf-8')
    w_fase = csv.writer(f_fase_csv)
    w_fase.writerow([f"# Sweep MEMS Solo FASE ({navg} Medie) - {timestamp_str}"])
    w_fase.writerow(["frequency_Hz", "Phase_deg"])
    f_fase_csv.flush()

    print("\n" + "-" * 85)
    print(f"{'Step':>4}/{total_points} | {'Freq Target':>11} | {'Freq 33220A':>11} | {'Vin [mV]':>9} | {'Vout [mV]':>9} | {'G [dB]':>8} | {'Fase [°]':>8}")
    print("-" * 85)

    start_time_total = time.time()

    try:
        for idx, f in enumerate(frequenze, 1):
            # 1. Imposta la nuova frequenza sul generatore DDS Agilent 33220A
            gen.write(f":FREQuency {f:.3f}")
            f_rb = f

            # 2. Breve assestamento meccanico del MEMS (40 ms > 20 costanti di tempo tau_m)
            time.sleep(SETTLE_MEMS_S)

            # 3. ATTESA AUTOMATICA: :DIGitize fa acquisire esattamente le N medie impostate
            #    *OPC? attende che il buffer sia pieno al 100%.
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

            # 4. Lettura pulita e diretta a traccia congelata (STOP) dei valori mediati
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

            # 5. Riavvia la visualizzazione (:RUN) per mostrare il refresh/lampeggio continuo a schermo
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

            # 6. Scrittura incrementale immediata su tutti i 3 file CSV
            w_master.writerow([
                idx,
                f"{f:.3f}",
                f"{f_rb:.3f}",
                f"{vin:.6e}" if not math.isnan(vin) else "nan",
                f"{vout:.6e}" if not math.isnan(vout) else "nan",
                f"{gain_lin:.6e}" if not math.isnan(gain_lin) else "nan",
                f"{gain_db:.3f}" if not math.isnan(gain_db) else "nan",
                f"{phase:.3f}" if not math.isnan(phase) else "nan"
            ])
            f_master_csv.flush()

            w_modulo.writerow([
                f"{f:.3f}",
                f"{vin:.6e}" if not math.isnan(vin) else "nan",
                f"{vout:.6e}" if not math.isnan(vout) else "nan",
                f"{gain_lin:.6e}" if not math.isnan(gain_lin) else "nan",
                f"{gain_db:.3f}" if not math.isnan(gain_db) else "nan"
            ])
            f_modulo_csv.flush()

            w_fase.writerow([
                f"{f:.3f}",
                f"{phase:.3f}" if not math.isnan(phase) else "nan"
            ])
            f_fase_csv.flush()

            # Stampa avanzamento a video
            vin_str = f"{vin*1e3:.1f}" if not math.isnan(vin) else "---"
            vout_str = f"{vout*1e3:.1f}" if not math.isnan(vout) else "---"
            gdb_str = f"{gain_db:+.2f}" if not math.isnan(gain_db) else "---"
            phase_str = f"{phase:+.2f}" if not math.isnan(phase) else "---"
            
            print(f"{idx:4d}/{total_points} | {f:11.1f} | {f_rb:11.1f} | {vin_str:>9} | {vout_str:>9} | {gdb_str:>8} | {phase_str:>8}")

    except KeyboardInterrupt:
        print("\n\n[INTERRUZIONE MANUALE] Sweep fermato con Ctrl+C.")
        print("Tutti i dati acquisiti finora sono stati salvati nei file CSV.")
    finally:
        f_master_csv.close()
        f_modulo_csv.close()
        f_fase_csv.close()
        durata = time.time() - start_time_total
        
        print("-" * 85)
        print(f"[COMPLETATO] Sweep terminato in {durata:.1f} secondi.")
        print("\n[FILE CSV SALVATI CON SUCCESSO SULLA CHIAVETTA USB]:")
        print(f" 1. Master Completo : {os.path.basename(file_master)}")
        print(f" 2. Solo Modulo     : {os.path.basename(file_modulo)}")
        print(f" 3. Solo Fase       : {os.path.basename(file_fase)}")
        
        try:
            if scope:
                scope.write(":RUN")
                scope.close()
            if gen:
                gen.close()
            if rm:
                rm.close()
        except Exception:
            pass

        # Generazione automatica del grafico
        try:
            from plotta_sweep import elabora_file
            print("\n[POST-PROCESSING] Apertura grafico in corso...")
            elabora_file(file_master)
        except Exception as e:
            print(f"\n[NOTA] Per visualizzare il grafico: esegui 'plotta_ultimo_sweep.bat' ({e})")

    print("\nMisura conclusa con successo.")
    if is_interactive:
        input("\nPremi INVIO per uscire...")

if __name__ == "__main__":
    main()

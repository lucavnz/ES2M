"""
Sweep Automatico Burst Phase (Agilent 33220A + Keysight MSO-X 3014A)
===================================================================
Funzionalita':
  1. Configura l'Agilent 33220A in modalita' Burst con Trigger Interno (:BURSt:MODE TRIG, :TRIG:SOUR INT).
  2. Esegue lo sweep della fase di burst (:BURSt:PHASe) da -180° a +180° (o range/passo a scelta, es. 5°).
  3. Handshake hardware con medie sull'oscilloscopio MSO-X 3014A (:ACQuire:COUNt, :DIGitize, *OPC?).
  4. Acquisizione diretta della forma d'onda su CH1 e CH3 (es. 10.000 punti) e salvataggio in un CSV dedicato per ogni fase.
  5. Acquisizione e salvataggio opzionale dello screenshot PNG della schermata dell'oscilloscopio per ogni fase.
  6. Generazione di un file indice riepilogativo 'riepilogo_sweep_burst_fase.csv'.
  7. Compatibile al 100% con Python Portatile (richiede solo PyVISA e libreria standard Python).
  8. Include modalita' simulatore (--simulate) per test offline immediati.
"""

import sys
import os
import time
import math
import csv
import argparse
from datetime import datetime

# Indirizzi Primari e Fallback verificati in Laboratorio
GEN_PRIMARY_ADDR = "GPIB1::10::INSTR"
GEN_FALLBACK_ADDRS = ["GPIB1::10::INSTR", "GPIB0::10::INSTR", "GPIB::10::INSTR"]
SCOPE_PRIMARY_ADDR = "USB0::2391::6056::MY52100688::INSTR"

# Parametri di Default
DEFAULT_PHASE_START = -180.0  # Gradi
DEFAULT_PHASE_STOP  =  180.0  # Gradi
DEFAULT_PHASE_STEP  =    5.0  # Gradi
DEFAULT_N_AVG       =     32  # Medie hardware oscilloscopio (:ACQuire:COUNt 32)
DEFAULT_POINTS      =  10000  # Campioni per traccia CSV (es. 10000)
DEFAULT_SETTLE_S    =   0.050 # 50 ms di assestamento dopo ogni cambio fase
SCPI_INVALID_VAL    = 9.9e36


class SimulatedScopeWaveform:
    """Genera campioni simulati per test offline senza strumenti fisici."""
    def __init__(self, phase_deg, points=10000, freq=417400.0):
        self.phase_deg = phase_deg
        self.points = points
        self.freq = freq
        self.t_span = 5.0 / freq  # Mostra ~5 periodi sullo schermo
        self.dt = self.t_span / points

    def get_preamble(self, ch=1):
        # format, type, points, count, xinc, xorig, xref, yinc, yorig, yref
        return f"0,2,{self.points},32,{self.dt:.9e},0.0,0,0.00195,0.0,128"

    def get_data(self, ch=1):
        # Valori da 0 a 255 (BYTE format)
        phase_rad = math.radians(self.phase_deg)
        data = []
        for i in range(self.points):
            t = i * self.dt
            if ch == 1:
                # Vout (sfasata in base alla fase di burst e al risonatore)
                val_v = 0.150 * math.sin(2.0 * math.pi * self.freq * t + phase_rad)
            else:
                # Vin (CH3)
                val_v = 0.200 * math.sin(2.0 * math.pi * self.freq * t)
            # Scala in byte (0-255 con centro a 128)
            byte_val = int(round(128 + (val_v / 0.00195)))
            byte_val = max(0, min(255, byte_val))
            data.append(byte_val)
        return data


class SimulatedInstrument:
    """Simulatore di Generatore 33220A e Oscilloscopio MSO-X 3014A."""
    def __init__(self, name):
        self.name = name
        self.phase = 0.0
        self.burst_state = "ON"
        self.freq = 417400.0
        self.navg = 32
        self.points = 10000
        self.current_channel = "CHAN1"

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
        elif "POIN" in u:
            parts = cmd.split()
            if len(parts) > 1:
                try:
                    self.points = int(parts[1])
                except ValueError:
                    pass
        elif "SOUR" in u:
            if "CHAN1" in u:
                self.current_channel = "CHAN1"
            elif "CHAN3" in u:
                self.current_channel = "CHAN3"

    def query(self, cmd):
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
        if "FREQ" in u and "?" in u:
            return f"{self.freq:.3f}"
        if "VOLT" in u and "?" in u:
            return "0.200000"
        if "BURS:STAT?" in u:
            return "1"
        if "COUN" in u and "?" in u:
            return str(self.navg)
        if "POIN" in u and "?" in u:
            return str(self.points)
        if "PRE?" in u or "PREAMBLE?" in u:
            ch_num = 1 if "1" in self.current_channel else 3
            sim = SimulatedScopeWaveform(self.phase, self.points, self.freq)
            return sim.get_preamble(ch_num)
        if "MEAS" in u:
            if "CHAN3" in u or "CHANNEL3" in u:
                return "0.200000"
            if "CHAN1" in u or "CHANNEL1" in u:
                return "0.150000"
            if "PHAS" in u:
                return f"{self.phase:.2f}"
            return "0.150;0.200"
        return "0.0"

    def query_binary_values(self, cmd, datatype='B', is_big_endian=False, container=list, header_fmt='ieee'):
        u = cmd.strip().upper()
        if "DATA?" in u and "DISP" in u:
            # Ritorna un finto file PNG valido di 1x1 pixel trasparente
            fake_png = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
            return fake_png if container == bytes else list(fake_png)
        # Forma d'onda
        ch_num = 1 if "1" in self.current_channel else 3
        sim = SimulatedScopeWaveform(self.phase, self.points, self.freq)
        data = sim.get_data(ch_num)
        return bytes(data) if container == bytes else data

    def close(self):
        pass


def parsa_valore_scpi(val_str):
    """Converte una stringa SCPI in float, gestendo NaN e valori di overflow."""
    try:
        val = float(val_str.strip())
        if abs(val) >= SCPI_INVALID_VAL:
            return float('nan')
        return val
    except (ValueError, AttributeError):
        return float('nan')


def acquisisci_forma_onda_canale(scope, channel_str, punti_richiesti):
    """
    Acquisisce i dati campionati di una forma d'onda da un canale dell'oscilloscopio.
    Ritorna:
      tempi: lista di valori di tempo in secondi
      tensioni: lista di valori di tensione in Volt
      preamble_dict: dizionario con i metadati del preambolo
    """
    # 1. Seleziona la sorgente del canale
    scope.write(f":WAVeform:SOURce {channel_str}")
    scope.write(":WAVeform:FORMat BYTE")
    
    # 2. Imposta modalita' e numero di punti richiesti
    try:
        scope.write(":WAVeform:POINts:MODE MAXimum")
    except Exception:
        pass
    try:
        scope.write(f":WAVeform:POINts {punti_richiesti}")
    except Exception:
        pass

    # 3. Leggi il preambolo
    preamble_raw = scope.query(":WAVeform:PREamble?").strip()
    parts = [p.strip() for p in preamble_raw.split(',')]
    if len(parts) < 10:
        raise ValueError(f"Preambolo non valido ricevuto da {channel_str}: '{preamble_raw}'")

    format_id = int(parts[0])
    type_id   = int(parts[1])
    n_points  = int(parts[2])
    count     = int(parts[3])
    xinc      = float(parts[4])
    xorig     = float(parts[5])
    xref      = float(parts[6])
    yinc      = float(parts[7])
    yorig     = float(parts[8])
    yref      = float(parts[9])

    preamble_dict = {
        "format": format_id,
        "type": type_id,
        "points": n_points,
        "count": count,
        "xinc": xinc,
        "xorig": xorig,
        "xref": xref,
        "yinc": yinc,
        "yorig": yorig,
        "yref": yref
    }

    # 4. Scarica i dati binari dei campioni
    raw_bytes = scope.query_binary_values(
        ":WAVeform:DATA?",
        datatype='B',
        is_big_endian=False,
        container=list,
        header_fmt='ieee'
    )

    actual_len = len(raw_bytes)
    # Conversione rapida in tempo (s) e tensione (V)
    # Formula SCPI InfiniiVision:
    #   t[i] = xorig + (i - xref) * xinc
    #   v[i] = yorig + (raw[i] - yref) * yinc
    tempi = [xorig + (i - xref) * xinc for i in range(actual_len)]
    tensioni = [yorig + (val - yref) * yinc for val in raw_bytes]

    return tempi, tensioni, preamble_dict


def salva_screenshot_display(scope, file_path_png):
    """Cattura lo screenshot a colori del display dell'oscilloscopio in formato PNG."""
    try:
        img_bytes = scope.query_binary_values(
            ":DISPlay:DATA? PNG, COLor",
            datatype='B',
            container=bytes,
            header_fmt='ieee'
        )
        with open(file_path_png, 'wb') as f:
            f.write(img_bytes)
        return True
    except Exception:
        try:
            img_bytes = scope.query_binary_values(
                ":DISPlay:DATA? PNG",
                datatype='B',
                container=bytes,
                header_fmt='ieee'
            )
            with open(file_path_png, 'wb') as f:
                f.write(img_bytes)
            return True
        except Exception as e:
            print(f"    [AVVISO SCREENSHOT]: Impossibile catturare immagine: {e}")
            return False


def connetti_generatore(rm, simulate=False):
    """Connessione robusta al generatore Agilent 33220A."""
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

    # Scansione dinamica se non trovato sugli indirizzi noti
    print(" -> Ricerca tra tutte le risorse VISA disponibili...")
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
    """Connessione robusta all'oscilloscopio Keysight MSO-X 3014A."""
    if simulate:
        return SimulatedInstrument("MSO-X-3014A")

    print("[CONNESSIONE 2/2] Ricerca Oscilloscopio Keysight MSO-X 3014A...")
    try:
        inst = rm.open_resource(SCOPE_PRIMARY_ADDR, timeout=25000)
        idn = inst.query("*IDN?").strip()
        print(f" -> [OK] Oscilloscopio connesso su {SCOPE_PRIMARY_ADDR}: {idn}")
        return inst
    except Exception:
        pass

    # Scansione dinamica porte USB
    print(" -> Ricerca tra le porte USB collegate...")
    for res in rm.list_resources():
        if "usb" in res.lower():
            try:
                inst = rm.open_resource(res, timeout=25000)
                idn = inst.query("*IDN?").strip()
                if any(k in idn for k in ["3014", "Keysight", "Agilent", "InfiniiVision"]):
                    print(f" -> [OK] Oscilloscopio trovato su {res}: {idn}")
                    return inst
                inst.close()
            except Exception:
                continue

    return None


def main():
    parser = argparse.ArgumentParser(description="Sweep Burst Phase Agilent 33220A + Acquisizione MSO-X 3014A")
    parser.add_argument("--phase-start", type=float, default=None, help="Fase iniziale in gradi (default: -180.0)")
    parser.add_argument("--phase-stop", type=float, default=None, help="Fase finale in gradi (default: +180.0)")
    parser.add_argument("--phase-step", type=float, default=None, help="Passo di fase in gradi (default: 5.0)")
    parser.add_argument("--navg", type=int, default=None, help="Numero di medie hardware oscilloscopio (default: 32)")
    parser.add_argument("--points", type=int, default=None, help="Numero di campioni per traccia CSV (default: 10000)")
    parser.add_argument("--save-png", type=str, default=None, help="Salvare screenshot PNG? [s/n] (default: s)")
    parser.add_argument("--settle", type=float, default=DEFAULT_SETTLE_S, help="Tempo assestamento fase in secondi")
    parser.add_argument("--simulate", action="store_true", help="Modalita' simulatore offline senza hardware")
    args = parser.parse_args()

    print("=" * 80)
    print(" SWEEP BURST PHASE AGILENT 33220A + ACQUISIZIONE FORME D'ONDA CSV 10k")
    print(" Strumenti: Agilent 33220A (GPIB) + Keysight MSO-X 3014A (USB)")
    print(" Canali: CH1 (Vout MEMS) + CH3 (Vin Riferimento Generatore)")
    print("=" * 80)

    is_interactive = (args.phase_start is None and args.phase_stop is None and args.phase_step is None)

    phase_start = args.phase_start if args.phase_start is not None else DEFAULT_PHASE_START
    phase_stop  = args.phase_stop  if args.phase_stop  is not None else DEFAULT_PHASE_STOP
    phase_step  = args.phase_step  if args.phase_step  is not None else DEFAULT_PHASE_STEP
    navg        = args.navg        if args.navg        is not None else DEFAULT_N_AVG
    points      = args.points      if args.points      is not None else DEFAULT_POINTS
    save_png_str= args.save_png.strip().lower() if args.save_png is not None else "s"
    salva_png   = (save_png_str != 'n')
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

            inp = input(f" -> Risoluzione campioni traccia CSV      [{points}]: ").strip()
            if inp:
                points = int(inp)

            inp = input(f" -> Salvare screenshot PNG del display?   [{'S' if salva_png else 'n'}]: ").strip().lower()
            if inp:
                salva_png = (inp != 'n')

        except ValueError:
            print("[ATTENZIONE] Valore non valido, ripristino valori predefiniti.")

    # Generazione lista angoli di fase
    if phase_stop < phase_start:
        step_dir = -abs(phase_step)
    else:
        step_dir = abs(phase_step)

    fasi = []
    curr = phase_start
    # Includi l'estremo finale con tolleranza per floating point
    while (step_dir > 0 and curr <= phase_stop + 1e-6) or (step_dir < 0 and curr >= phase_stop - 1e-6):
        fasi.append(round(curr, 3))
        curr += step_dir

    total_steps = len(fasi)
    if total_steps == 0:
        print("[ERRORE] Nessun passo di fase da eseguire. Controlla inizio/fine/passo.")
        return

    print("\n" + "=" * 80)
    print(" RIEPILOGO SESSIONE ACQUISIZIONE BURST PHASE:")
    print("=" * 80)
    print(f"  * Intervallo Fase      : da {phase_start:+.1f}° a {phase_stop:+.1f}°")
    print(f"  * Passo di Fase        : {phase_step:.2f}° ({total_steps} passi totali)")
    print(f"  * Medie Hardware       : {navg} medie (:ACQuire:COUNt {navg})")
    print(f"  * Campioni CSV per traccia: {points} punti per ciascun canale (CH1 + CH3)")
    print(f"  * Cattura Screenshot PNG : {'ATTIVA' if salva_png else 'DISATTIVATA'}")
    print(f"  * Canali Acquisiti     : CH1 (Vout) e CH3 (Vin)")
    print(f"  * Modalita' Burst      : Trigger Interno (:BURSt:MODE TRIG, :TRIG:SOUR INT)")
    print("=" * 80)

    if is_interactive and not simulate:
        conferma = input("\nPremi INVIO per iniziare l'acquisizione (oppure 'q' per annullare): ")
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
        print("\n[MODALITA SIMULAZIONE ATTIVA]: Esecuzione offline con strumenti virtuali.")
    else:
        try:
            import pyvisa
            rm = pyvisa.ResourceManager()
        except Exception as e:
            print(f"\n[ERRORE FATALE] Impossibile inizializzare PyVISA: {e}")
            input("\nPremi INVIO per uscire...")
            return

        gen = connetti_generatore(rm, simulate=False)
        if not gen:
            print("\n[ERRORE] Generatore Agilent 33220A non trovato!")
            print("Verifica che il cavo GPIB sia collegato e che il convertitore USB-GPIB sia riconosciuto.")
            input("\nPremi INVIO per uscire...")
            return

        scope = connetti_oscilloscopio(rm, simulate=False)
        if not scope:
            print("\n[ERRORE] Oscilloscopio Keysight MSO-X 3014A non trovato su porta USB!")
            print("Verifica che il cavo USB dell'oscilloscopio sia inserito nel computer.")
            input("\nPremi INVIO per uscire...")
            return

    # Configurazione Banco di Misura
    print("\n[SETUP] Configurazione parametri...")
    try:
        if not simulate:
            gen.write("*CLS")
            scope.write("*CLS")
            # Calcolo timeout dinamico in base al numero di medie (es. 2048 medie richiedono fino a 120-180s)
            timeout_dinamico = max(30000, navg * 100)
            scope.timeout = timeout_dinamico
            print(f" -> Timeout VISA impostato a {timeout_dinamico//1000}s per gestire {navg} medie in sicurezza.")

            # 1. Configurazione Burst Phase sull'Agilent 33220A
            gen.write(":UNIT:ANGLe DEG")
            gen.write(":BURSt:MODE TRIGgered")
            gen.write(":TRIGger:SOURce INTernal")
            gen.write(":BURSt:STATe ON")
            gen.write(":OUTPut ON")

            # Lettura parametri correnti del generatore per conferma
            try:
                freq_str = gen.query(":FREQuency?").strip()
                vpp_str  = gen.query(":VOLTage?").strip()
                print(f" -> Generatore 33220A impostato in Burst Trigger Interno:")
                print(f"    - Frequenza portante: {float(freq_str):,.1f} Hz")
                print(f"    - Ampiezza segnale  : {float(vpp_str)*1000:.1f} mVpp")
            except Exception:
                pass

            # 2. Configurazione Oscilloscopio
            scope.write(":CHANnel1:DISPlay ON")
            scope.write(":CHANnel3:DISPlay ON")
            
            # Imposta tipo di acquisizione e numero di medie hardware
            scope.write(":ACQuire:TYPE AVERage")
            scope.write(f":ACQuire:COUNt {navg}")
            print(f" -> Oscilloscopio configurato su {navg} MEDIE hardware.")

            # Prepara comandi di misura Vpp e sfasamento
            scope.write(":MEASure:VPP CHANnel1")
            scope.write(":MEASure:VPP CHANnel3")
            scope.write(":MEASure:PHASe CHANnel1,CHANnel3")
            
            # Metti inizialmente in RUN
            scope.write(":RUN")

        print(" -> Setup completato con successo. Avvio acquisizione...")

    except Exception as e:
        print(f"[ATTENZIONE] Avviso durante configurazione iniziale: {e}")

    # Creazione cartella per la sessione
    base_dir = os.path.dirname(os.path.abspath(__file__))
    ts_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    folder_name = f"sessione_burst_{ts_str}"
    session_dir = os.path.join(base_dir, folder_name)
    os.makedirs(session_dir, exist_ok=True)

    print(f"\n[CARTELLA SESSIONE CREATA]:\n -> {session_dir}")

    # File Riepilogo Master CSV
    master_csv_path = os.path.join(session_dir, "riepilogo_sweep_burst_fase.csv")
    f_master = open(master_csv_path, 'w', newline='', encoding='utf-8')
    w_master = csv.writer(f_master)
    w_master.writerow([f"# Riepilogo Sweep Burst Phase Agilent 33220A + MSO-X 3014A - {ts_str}"])
    w_master.writerow([f"# Range: {phase_start}° a {phase_stop}°, passo: {phase_step}°, medie: {navg}, campioni_csv: {points}"])
    w_master.writerow([
        "step",
        "phase_set_deg",
        "vpp_ch1_mV",
        "vpp_ch3_mV",
        "gain_linear",
        "phase_meas_deg",
        "points_ch1",
        "points_ch3",
        "csv_file",
        "png_file"
    ])
    f_master.flush()

    print("\n" + "-" * 88)
    print(f"{'Step':>4}/{total_steps:<4} | {'Fase Set':>9} | {'CH1 [mV]':>9} | {'CH3 [mV]':>9} | {'Fase Mis':>9} | {'Campioni':>9} | {'File CSV':<22}")
    print("-" * 88)

    start_total_time = time.time()
    num_csv_salvati = 0

    try:
        for idx, fase in enumerate(fasi, 1):
            # 1. Imposta la nuova fase di burst sull'Agilent 33220A
            gen.write(f":BURSt:PHASe {fase:.3f}")

            # 2. Breve assestamento
            time.sleep(args.settle)

            # 3. Handshake Hardware: :DIGitize accumula le N medie impostate, *OPC? attende fine
            if not simulate:
                try:
                    scope.write(":DIGitize CHANnel1,CHANnel3")
                    scope.query("*OPC?")
                    # Piccolo margine fisso per assestamento completato
                    time.sleep(0.050)
                except Exception as e:
                    print(f"\n[AVVISO DIGITIZE step {idx}]: {e}")
                    try:
                        scope.clear()
                        scope.write("*CLS")
                    except Exception:
                        pass

            # 4. Scarica le forme d'onda complete di CH1 e CH3
            tempi_ch1, v_ch1, pre_ch1 = acquisisci_forma_onda_canale(scope, "CHANnel1", points)
            tempi_ch3, v_ch3, pre_ch3 = acquisisci_forma_onda_canale(scope, "CHANnel3", points)

            # 5. Lettura rapida dei valori Vpp e Sfasamento hardware
            vpp_ch1 = float('nan')
            vpp_ch3 = float('nan')
            phase_meas = float('nan')
            try:
                meas_resp = scope.query(":MEASure:VPP? CHANnel1;:MEASure:VPP? CHANnel3;:MEASure:PHASe? CHANnel1,CHANnel3")
                parts = [p.strip() for p in meas_resp.split(';')]
                if len(parts) > 0:
                    vpp_ch1 = parsa_valore_scpi(parts[0])
                if len(parts) > 1:
                    vpp_ch3 = parsa_valore_scpi(parts[1])
                if len(parts) > 2:
                    phase_meas = parsa_valore_scpi(parts[2])
            except Exception:
                pass

            # 6. Salva screenshot PNG se abilitato
            csv_filename = f"traccia_fase_{fase:+.1f}deg.csv"
            png_filename = f"schermata_fase_{fase:+.1f}deg.png" if salva_png else ""

            csv_path = os.path.join(session_dir, csv_filename)
            if salva_png:
                png_path = os.path.join(session_dir, png_filename)
                salva_screenshot_display(scope, png_path)

            # 7. Riavvia la visualizzazione a schermo (:RUN)
            if not simulate:
                try:
                    scope.write(":RUN")
                except Exception:
                    pass

            # 8. Scrittura del file CSV ad alta risoluzione (10.000 campioni)
            n_rows = min(len(tempi_ch1), len(tempi_ch3))
            with open(csv_path, 'w', newline='', encoding='utf-8') as f_step:
                w_step = csv.writer(f_step)
                w_step.writerow([f"# Forma d'onda Burst Phase Agilent 33220A = {fase:.3f} deg"])
                w_step.writerow([f"# Medie: {navg}, Campioni: {n_rows}, CH1: Vout, CH3: Vin"])
                w_step.writerow(["tempo_s", "tensione_CH1_Vout_V", "tensione_CH3_Vin_V"])
                for i in range(n_rows):
                    w_step.writerow([
                        f"{tempi_ch1[i]:.9e}",
                        f"{v_ch1[i]:.6e}",
                        f"{v_ch3[i]:.6e}"
                    ])

            num_csv_salvati += 1

            # Calcolo guadagno lineare
            if not math.isnan(vpp_ch1) and not math.isnan(vpp_ch3) and vpp_ch3 > 1e-9:
                gain_lin = vpp_ch1 / vpp_ch3
            else:
                gain_lin = float('nan')

            # 9. Aggiornamento riga del Master CSV
            w_master.writerow([
                idx,
                f"{fase:+.2f}",
                f"{vpp_ch1*1e3:.2f}" if not math.isnan(vpp_ch1) else "nan",
                f"{vpp_ch3*1e3:.2f}" if not math.isnan(vpp_ch3) else "nan",
                f"{gain_lin:.4f}" if not math.isnan(gain_lin) else "nan",
                f"{phase_meas:+.2f}" if not math.isnan(phase_meas) else "nan",
                len(v_ch1),
                len(v_ch3),
                csv_filename,
                png_filename
            ])
            f_master.flush()

            # Stampa progresso a video
            ch1_s = f"{vpp_ch1*1e3:.1f}" if not math.isnan(vpp_ch1) else "---"
            ch3_s = f"{vpp_ch3*1e3:.1f}" if not math.isnan(vpp_ch3) else "---"
            ph_s  = f"{phase_meas:+.1f}°" if not math.isnan(phase_meas) else "---"
            pts_s = f"{n_rows}"

            print(f"{idx:4d}/{total_steps:<4} | {fase:+8.1f}° | {ch1_s:>9} | {ch3_s:>9} | {ph_s:>9} | {pts_s:>9} | {csv_filename:<22}")

    except KeyboardInterrupt:
        print("\n\n[INTERRUZIONE MANUALE] Acquisizione fermata dall'utente (Ctrl+C).")
        print("Tutti i dati acquisiti finora sono stati salvati correttamente.")

    finally:
        f_master.close()
        elapsed_total = time.time() - start_total_time

        print("-" * 88)
        print(f"[COMPLETATO] Acquisizione terminata in {elapsed_total:.1f} secondi.")
        print("\n[DATI SALVATI SUL COMPUTER]:")
        print(f" -> Cartella Sessione  : {session_dir}")
        print(f" -> Indice Riepilogo   : {os.path.basename(master_csv_path)}")
        print(f" -> File CSV Tracce    : {num_csv_salvati} file (ciascuno da {points} campioni CH1+CH3)")
        if salva_png:
            print(f" -> Screenshot Display : {num_csv_salvati} file PNG")
        print("=" * 80)

        if not simulate and scope:
            try:
                scope.write(":RUN")
            except Exception:
                pass


if __name__ == "__main__":
    main()

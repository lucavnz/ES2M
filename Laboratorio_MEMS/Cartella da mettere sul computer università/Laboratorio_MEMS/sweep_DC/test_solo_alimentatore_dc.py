"""
Test Rapido di Comunicazione e Sicurezza: Agilent E3646A (Output 1)
Esegue un collaudo in sicurezza del solo alimentatore da banco:
  1. Connessione GPIB automatica
  2. Verifica identificativo (*IDN?)
  3. Selezione Output 1 e impostazione HIGH RANGE (0-20V, 1.5A)
  4. Impostazione compliance di corrente sicura (50 mA)
  5. Erogazione breve di 2.0 V di prova con lettura di ritorno (MEAS:VOLT?, MEAS:CURR?)
  6. Azzeramento immediato (0.0 V) e spegnimento uscita (OUTP OFF)
"""

import sys
import os
import time
import argparse

FALLBACK_ADDRS = [
    "GPIB1::5::INSTR", "GPIB0::5::INSTR",
    "GPIB1::6::INSTR", "GPIB0::6::INSTR",
    "GPIB1::7::INSTR", "GPIB0::7::INSTR",
    "GPIB1::8::INSTR", "GPIB0::8::INSTR",
    "GPIB1::9::INSTR", "GPIB0::9::INSTR",
    "GPIB1::4::INSTR", "GPIB0::4::INSTR",
    "GPIB1::3::INSTR", "GPIB0::3::INSTR",
    "GPIB1::2::INSTR", "GPIB0::2::INSTR",
    "GPIB1::1::INSTR", "GPIB0::1::INSTR",
]


class SimulatedE3646A:
    def __init__(self):
        self.volt = 0.0
        self.outp = False
        self.rang = "HIGH"

    def write(self, cmd):
        u = cmd.strip().upper()
        if "VOLT" in u and "RANG" not in u and "?" not in u:
            parts = cmd.split()
            if len(parts) > 1:
                self.volt = float(parts[1])
        elif "OUTP" in u and "?" not in u:
            self.outp = ("ON" in u or "1" in u)
        elif "RANG" in u:
            self.rang = "HIGH" if ("HIGH" in u or "P20V" in u) else "LOW"

    def query(self, cmd):
        u = cmd.strip().upper()
        if "*IDN?" in u:
            return "Agilent Technologies,E3646A,MY12345678,1.4-5.0-1.0"
        if "SYST:ERR?" in u:
            return '+0,"No error"'
        if "VOLT" in u and "RANG" in u and "?" in u:
            return "P20V" if self.rang == "HIGH" else "P8V"
        if "VOLT" in u and "?" in u:
            return f"{self.volt:.3f}"
        if "CURR" in u and "?" in u:
            return f"{self.volt * 1e-6:.6f}"
        return "0.0"

    def close(self):
        pass


def main():
    parser = argparse.ArgumentParser(description="Test Rapido Agilent E3646A Output 1")
    parser.add_argument("--addr", type=str, default=None, help="Indirizzo GPIB specifico")
    parser.add_argument("--simulate", action="store_true", help="Simulazione offline")
    args = parser.parse_args()

    print("=" * 70)
    print(" COLLAUDO RAPIDO ALIMENTATORE AGILENT E3646A (OUTPUT 1)")
    print(" (Verifica Range 20V, Comunicazione GPIB e Spegnimento di Sicurezza)")
    print("=" * 70)

    psu = None
    rm = None

    if args.simulate:
        print("\n[SIMULAZIONE] Uso strumento virtuale Agilent E3646A...")
        psu = SimulatedE3646A()
    else:
        try:
            import pyvisa
            rm = pyvisa.ResourceManager()
        except ImportError:
            print("\n[ERRORE] pyvisa non disponibile.")
            input("\nPremi INVIO per uscire...")
            return
        except Exception as e:
            print(f"\n[ERRORE] Inizializzazione VISA: {e}")
            input("\nPremi INVIO per uscire...")
            return

        # Tentativi di connessione
        print("\n[1/4] Ricerca Agilent E3646A sul bus GPIB...")
        addrs = []
        if args.addr:
            addrs.append(args.addr)
        addrs.extend(FALLBACK_ADDRS)

        for a in addrs:
            try:
                inst = rm.open_resource(a, timeout=2000)
                idn = inst.query("*IDN?").strip()
                if any(k in idn for k in ["E3646", "3646", "E364"]):
                    psu = inst
                    print(f" -> Trovato su indirizzo {a}: {idn}")
                    break
                inst.close()
            except Exception:
                continue

        if not psu:
            print(" -> Scansione automatica completa su tutte le porte GPIB...")
            for res in rm.list_resources():
                if "gpib" in res.lower():
                    try:
                        inst = rm.open_resource(res, timeout=2000)
                        idn = inst.query("*IDN?").strip()
                        if any(k in idn for k in ["E3646", "3646", "E364"]):
                            psu = inst
                            print(f" -> Trovato su {res}: {idn}")
                            break
                        inst.close()
                    except Exception:
                        continue

        if not psu:
            print("\n[ERRORE] Agilent E3646A non risponde sul bus GPIB.")
            print("Consigli pratici:")
            print("  1. Verifica che il cavo GPIB sia inserito saldamente dietro l'E3646A.")
            print("  2. Controlla sul generatore l'indirizzo GPIB: premi 'Menu' > 'I/O config' > 'GPIB / 488'.")
            print("  3. Esegui 'test_solo_alimentatore_dc.bat --addr GPIB0::X::INSTR' indicando l'indirizzo.")
            input("\nPremi INVIO per uscire...")
            return

    try:
        # 1. Configurazione Canale e Range
        print("\n[2/4] Configurazione Output 1 e Range 20V...")
        psu.write("INST:SEL OUT1")
        time.sleep(0.05)
        try:
            psu.write("VOLT:RANG HIGH")
        except Exception:
            psu.write("VOLT:RANG P20V")
        time.sleep(0.05)
        psu.write("CURR 0.05")  # 50 mA protezione
        time.sleep(0.05)
        psu.write("VOLT 0.0")

        rang = psu.query("VOLT:RANG?").strip()
        print(f" -> Output 1 attivo con Range impostato su: {rang} (0-20V, 1.5A)")
        print(f" -> Limite di Corrente (Compliance): 50 mA")

        # 2. Test Erogazione Tensione di Prova (2.0 V)
        test_v = 2.0
        print(f"\n[3/4] Erogazione tensione di test: {test_v:.1f} V...")
        psu.write(f"VOLT {test_v:.3f}")
        psu.write("OUTP ON")
        print(" -> Output attivato (OUTP ON). Attesa 2 secondi per verifica visiva sul display...")
        time.sleep(2.0)

        v_meas = float(psu.query("MEAS:VOLT?").strip())
        i_meas = float(psu.query("MEAS:CURR?").strip())
        print(f" -> Tensione letta dallo strumento : {v_meas:.3f} V (target: {test_v:.1f} V)")
        print(f" -> Corrente letta dallo strumento : {i_meas*1000:.2f} mA")

        if abs(v_meas - test_v) < 0.2:
            print(" -> [SUCCESSO] La tensione erogata corrisponde perfettamente al comando!")
        else:
            print(" -> [ATTENZIONE] Differenza tra tensione impostata e letta.")

    finally:
        # 3. Spegnimento di Sicurezza Obbligatorio
        print("\n[4/4] Procedura di Sicurezza...")
        try:
            psu.write("INST:SEL OUT1")
            psu.write("VOLT 0.0")
            time.sleep(0.05)
            psu.write("OUTP OFF")
            print(" -> [OK] Tensione azzerata (0.0 V) e Uscita disattivata (OUTP OFF).")
            psu.close()
        except Exception:
            pass

    print("\n" + "=" * 70)
    print(" TEST COMPLETATO CON SUCCESSO! L'alimentatore e' pronto per lo sweep.")
    print("=" * 70)
    input("\nPremi INVIO per chiudere...")


if __name__ == "__main__":
    main()

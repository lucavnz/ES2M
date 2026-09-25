"""
Diagnostica Avanzata Strumenti di Laboratorio (VISA)
Esegue una scansione approfondita, verifica la libreria VISA caricata
e tenta la connessione diretta a:
  - Agilent 33220A su GPIB0::10::INSTR
  - Keysight MSO-X 3014A su USB0::2391::6056::MY52100688::INSTR
  - Eventuali porte seriali (es. ASRL10)
"""

import sys
import os

def test_connessione_diretta(rm, addr, nome):
    print(f"\n[-] Test Connessione Diretta a {nome} ({addr})...")
    try:
        inst = rm.open_resource(addr, timeout=2000)
        idn = inst.query("*IDN?").strip()
        print(f"    [SUCCESSO!] Risposta: {idn}")
        inst.close()
        return True
    except Exception as e:
        print(f"    [NON RISPONDE]: {e}")
        return False

def main():
    print("=" * 65)
    print(" DIAGNOSTICA AVANZATA STRUMENTAZIONE MEMS (VISA)")
    print("=" * 65)

    try:
        import pyvisa
    except ImportError:
        print("[ERRORE FATALE] pyvisa non e' disponibile.")
        input("\nPremi INVIO per uscire...")
        return

    # 1. Informazioni sulla libreria VISA di sistema
    print("\n[1] LIBRERIA VISA RILEVATA:")
    try:
        rm = pyvisa.ResourceManager()
        print(f" -> Backend VISA attivo: {rm}")
        try:
            # Informazioni dettagliate su pyvisa
            import platform
            print(f" -> Architettura Python: {platform.architecture()[0]}")
            print(f" -> Sistema Operativo:   {platform.platform()}")
        except Exception:
            pass
    except Exception as e:
        print(f" -> Errore apertura ResourceManager: {e}")
        input("\nPremi INVIO per uscire...")
        return

    # 2. Test Connessione Diretta agli indirizzi noti
    print("\n" + "=" * 65)
    print("[2] TENTATIVO DI CONNESSIONE DIRETTA:")
    print("=" * 65)

    # Test Agilent 33220A (con priorit su GPIB1::10::INSTR verificato in lab)
    ok_gen = test_connessione_diretta(rm, "GPIB1::10::INSTR", "Generatore Agilent 33220A (GPIB1::10)")
    if not ok_gen:
        ok_gen = test_connessione_diretta(rm, "GPIB0::10::INSTR", "Generatore Agilent 33220A (GPIB0::10)")
    if not ok_gen:
        test_connessione_diretta(rm, "GPIB::10::INSTR", "Generatore Agilent 33220A (GPIB::10)")

    # Test Keysight MSO-X 3014A
    ok_scope = test_connessione_diretta(rm, "USB0::2391::6056::MY52100688::INSTR", "Oscilloscopio MSO-X 3014A (USB)")

    # Test Agilent E3646A (Alimentatore DC Duale)
    ok_psu = False
    for a in ["GPIB1::5::INSTR", "GPIB0::5::INSTR", "GPIB1::6::INSTR", "GPIB0::6::INSTR", "GPIB1::7::INSTR", "GPIB0::7::INSTR"]:
        if test_connessione_diretta(rm, a, f"Alimentatore Agilent E3646A ({a})"):
            ok_psu = True
            break

    # 3. Elenco Risorse Trovate da list_resources
    print("\n" + "=" * 65)
    print("[3] ELENCO RISORSE RILEVATE AUTOMATICAMENTE (list_resources):")
    print("=" * 65)
    try:
        resources = rm.list_resources("?*")
        print(f" -> Totale risorse visibili: {len(resources)}")
        for r in resources:
            print(f"    * {r}")
            # Se e' una porta seriale ASRL10, prova a interrogarla con baudrate standard
            if "ASRL10" in r or "ASRL" in r:
                try:
                    s = rm.open_resource(r, timeout=1000, baud_rate=9600)
                    s.write_termination = '\n'
                    s.read_termination = '\n'
                    idn = s.query("*IDN?").strip()
                    print(f"      -> IDN trovato su seriale: {idn}")
                    s.close()
                except Exception:
                    pass
    except Exception as e:
        print(f" -> Errore durante list_resources: {e}")

    # 4. Diagnostica e Consigli pratici
    print("\n" + "=" * 65)
    print("[4] GUIDA RISOLUZIONE SE GLI STRUMENTI NON COMPAIONO:")
    print("=" * 65)
    if not ok_gen:
        print("\n [?] GENERATORE AGILENT 33220A (GPIB 10) non risponde:")
        print("     1. Il cavo GPIB (quello grosso grigio) e' collegato dietro al 33220A?")
        print("     2. L'adattatore NI GPIB-USB e' inserito in una porta USB di questo PC?")
        print("     3. Il LED 'READY' sull'adattatore NI GPIB-USB e' acceso verde?")
        print("     4. Apri 'NI-MAX' (l'icona con il logo National Instruments sulla barra):")
        print("        sotto 'Dispositivi e interfacce' vedi 'GPIB0'?")

    if not ok_scope:
        print("\n [?] OSCILLOSCOPIO MSO-X 3014A (USB) non risponde:")
        print("     1. Il cavo USB (quadrato da stampante) dietro l'oscilloscopio")
        print("        e' collegato direttamente a una porta USB di questo PC?")
        print("     2. Quando inserisci il cavo USB dell'oscilloscopio, Windows fa il classico 'suono'?")
        print("     3. In 'NI-MAX', compare sotto i dispositivi USB?")

    print("\n" + "=" * 65)
    input("Premi INVIO per chiudere...")

if __name__ == "__main__":
    main()

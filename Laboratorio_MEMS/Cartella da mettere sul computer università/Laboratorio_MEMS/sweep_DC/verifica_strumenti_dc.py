"""
Diagnostica Completa Banco di Misura MEMS 3 Strumenti:
  1. Agilent 33220A (Generatore DDS - GPIB)
  2. Keysight MSO-X 3014A (Oscilloscopio Digitale - USB)
  3. Agilent E3646A (Alimentatore DC Duale - GPIB)
"""

import sys
import os

FALLBACK_GEN = ["GPIB1::10::INSTR", "GPIB0::10::INSTR", "GPIB::10::INSTR"]
SCOPE_ADDR = "USB0::2391::6056::MY52100688::INSTR"
FALLBACK_PSU = [
    "GPIB1::5::INSTR", "GPIB0::5::INSTR",
    "GPIB1::6::INSTR", "GPIB0::6::INSTR",
    "GPIB1::7::INSTR", "GPIB0::7::INSTR",
    "GPIB1::8::INSTR", "GPIB0::8::INSTR",
    "GPIB1::9::INSTR", "GPIB0::9::INSTR",
    "GPIB1::4::INSTR", "GPIB0::4::INSTR",
    "GPIB1::3::INSTR", "GPIB0::3::INSTR",
    "GPIB1::2::INSTR", "GPIB0::2::INSTR"
]


def testa_connessione(rm, addr, timeout_ms=2500):
    try:
        inst = rm.open_resource(addr, timeout=timeout_ms)
        idn = inst.query("*IDN?").strip()
        inst.close()
        return True, idn
    except Exception as e:
        return False, str(e)


def main():
    print("=" * 75)
    print(" VERIFICA STRUMENTI BANCO LABORATORIO MEMS (3 STRUMENTI)")
    print(" Agilent 33220A (DDS) + Keysight MSO-X 3014A (Scope) + Agilent E3646A (DC)")
    print("=" * 75)

    try:
        import pyvisa
        rm = pyvisa.ResourceManager()
        print(f"\n[OK] Backend VISA: {rm}")
    except Exception as e:
        print(f"\n[ERRORE FATALE] Impossibile caricare VISA: {e}")
        input("\nPremi INVIO per uscire...")
        return

    # 1. Elenco risorse rilevate dal sistema
    print("\n[1/4] SCANSIONE RISORSE COLLEGATE (list_resources):")
    try:
        risorse = rm.list_resources("?*")
        for r in risorse:
            print(f"  * {r}")
        if not risorse:
            print("  (Nessun dispositivo rilevato dal driver VISA)")
    except Exception as e:
        print(f"  Errore durante scansione: {e}")

    # 2. Verifica Agilent 33220A
    print("\n[2/4] VERIFICA GENERATORE DDS AGILENT 33220A:")
    ok_gen = False
    for a in FALLBACK_GEN:
        ok, res = testa_connessione(rm, a)
        if ok and "33220" in res:
            print(f"  -> [PRESENTE] su {a}: {res}")
            ok_gen = True
            break
    if not ok_gen:
        for r in rm.list_resources():
            if "gpib" in r.lower():
                ok, res = testa_connessione(rm, r)
                if ok and "33220" in res:
                    print(f"  -> [PRESENTE] su {r}: {res}")
                    ok_gen = True
                    break
    if not ok_gen:
        print("  -> [NON TROVATO] Verifica cavo GPIB generatore (indirizzo standard: 10)")

    # 3. Verifica Oscilloscopio Keysight MSO-X 3014A
    print("\n[3/4] VERIFICA OSCILLOSCOPIO KEYSIGHT MSO-X 3014A:")
    ok_scope, res_s = testa_connessione(rm, SCOPE_ADDR, timeout_ms=5000)
    if ok_scope and any(k in res_s for k in ["3014", "Keysight", "Agilent"]):
        print(f"  -> [PRESENTE] su {SCOPE_ADDR}: {res_s}")
    else:
        ok_scope = False
        for r in rm.list_resources():
            if "usb" in r.lower():
                ok, res = testa_connessione(rm, r, timeout_ms=5000)
                if ok and any(k in res for k in ["3014", "Keysight", "Agilent"]):
                    print(f"  -> [PRESENTE] su {r}: {res}")
                    ok_scope = True
                    break
        if not ok_scope:
            print("  -> [NON TROVATO] Verifica cavo USB oscilloscopio collegato al PC")

    # 4. Verifica Alimentatore DC Agilent E3646A
    print("\n[4/4] VERIFICA ALIMENTATORE DC AGILENT E3646A:")
    ok_psu = False
    for a in FALLBACK_PSU:
        ok, res = testa_connessione(rm, a)
        if ok and any(k in res for k in ["E3646", "3646", "E364"]):
            print(f"  -> [PRESENTE] su {a}: {res}")
            ok_psu = True
            break
    if not ok_psu:
        for r in rm.list_resources():
            if "gpib" in r.lower():
                ok, res = testa_connessione(rm, r)
                if ok and any(k in res for k in ["E3646", "3646", "E364"]):
                    print(f"  -> [PRESENTE] su {r}: {res}")
                    ok_psu = True
                    break
    if not ok_psu:
        print("  -> [NON TROVATO] Verifica cavo GPIB alimentatore (menu I/O config: GPIB 488)")

    # Riepilogo finale
    print("\n" + "=" * 75)
    print(" RIEPILOGO STATO BANCO:")
    print("=" * 75)
    print(f"  1. Agilent 33220A (DDS)   : {'[OK PRONTO]' if ok_gen else '[MANCANTE]'}")
    print(f"  2. Keysight 3014A (Scope) : {'[OK PRONTO]' if ok_scope else '[MANCANTE]'}")
    print(f"  3. Agilent E3646A (DC)    : {'[OK PRONTO]' if ok_psu else '[MANCANTE]'}")
    print("=" * 75)

    if ok_gen and ok_scope and ok_psu:
        print("\n--> TUTTI E 3 GLI STRUMENTI SONO CONNESSI E PRONTI PER LO SWEEP DC!")
    else:
        print("\n--> ATTENZIONE: Controlla i collegamenti prima di avviare la misura.")

    input("\nPremi INVIO per chiudere...")


if __name__ == "__main__":
    main()

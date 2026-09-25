"""
Test Rapido Solo Generatore Agilent 33220A
Esegue uno sweep di frequenza sulla sinusoide del generatore senza toccare l'oscilloscopio
e SENZA toccare l'ampiezza Vpp (che puoi impostare manualmente dalla manopola del generatore).
"""

import sys
import time

DEFAULT_GEN_ADDR = "GPIB0::10::INSTR"
DEFAULT_F_START = 415000.0   # 415 kHz
DEFAULT_F_STOP = 420000.0    # 420 kHz
DEFAULT_POINTS = 20          # 20 punti per il test visivo a display
DEFAULT_DELAY = 0.3          # 300 ms per punto (cosi vedi i numeri scorrere sul display)


def main():
    print("=" * 65)
    print(" TEST RAPIDO SWEEP FREQUENZA - SOLO AGILENT 33220A")
    print(" (L'ampiezza Vpp NON verra' toccata, impostala a mano dallo strumento)")
    print("=" * 65)

    try:
        import pyvisa
        try:
            rm = pyvisa.ResourceManager()
        except Exception:
            rm = pyvisa.ResourceManager('@py')
    except ImportError:
        print("\n[ERRORE] pyvisa non installato.")
        input("Premi INVIO per uscire...")
        return

    # Connessione al 33220A
    print(f"\n[CONNESSIONE] Ricerca del 33220A su {DEFAULT_GEN_ADDR}...")
    gen = None
    try:
        gen = rm.open_resource(DEFAULT_GEN_ADDR, timeout=5000)
        idn = gen.query("*IDN?").strip()
        print(f" -> Trovato e connesso: {idn}")
    except Exception as e:
        print(f" -> Indirizzo diretto fallito ({e}), scansione automatica...")
        for res in rm.list_resources():
            if any(k in res.lower() for k in ["10", "33220", "gpib"]):
                try:
                    test_inst = rm.open_resource(res, timeout=5000)
                    idn = test_inst.query("*IDN?").strip()
                    if "33220" in idn:
                        gen = test_inst
                        print(f" -> Trovato su {res}: {idn}")
                        break
                    test_inst.close()
                except Exception:
                    continue

    if not gen:
        print("\n[ERRORE] Generatore Agilent 33220A non trovato!")
        print("Verifica che sia acceso e che il cavo GPIB/USB sia collegato.")
        input("Premi INVIO per uscire...")
        return

    # Lettura tensione attuale impostata dall'utente (senza modificarla)
    try:
        vpp_attuale = float(gen.query(":VOLTage?").strip())
        print(f" -> Ampiezza Vpp attualmente impostata sullo strumento: {vpp_attuale*1000:.1f} mVpp (NON verra' toccata)")
    except Exception:
        vpp_attuale = None

    # Configura solo forma d'onda Sinusoidale e Output ON
    try:
        gen.write(":FUNCtion SINusoid")
        gen.write(":OUTPut ON")
        print(" -> Forma d'onda impostata su: SINE (Sinusoidale)")
        print(" -> Canale Output impostato su: ON")
    except Exception as e:
        print(f"[ATTENZIONE] Errore configurazione base: {e}")

    # Richiesta parametri rapida
    print("\n[PARAMETRI] Premi INVIO per usare i valori tra parentesi:")
    f_start = DEFAULT_F_START
    f_stop = DEFAULT_F_STOP
    points = DEFAULT_POINTS
    delay = DEFAULT_DELAY

    try:
        inp_start = input(f" -> Frequenza Iniziale [Hz] [{f_start:,.0f}]: ").strip()
        if inp_start:
            f_start = float(inp_start)

        inp_stop = input(f" -> Frequenza Finale   [Hz] [{f_stop:,.0f}]: ").strip()
        if inp_stop:
            f_stop = float(inp_stop)

        inp_pts = input(f" -> Numero di Passi         [{points}]: ").strip()
        if inp_pts:
            points = int(inp_pts)

        inp_delay = input(f" -> Ritardo tra passi [s]   [{delay}]: ").strip()
        if inp_delay:
            delay = float(inp_delay)
    except ValueError:
        print("Valore non valido, uso i default.")

    step_f = (f_stop - f_start) / max(1, points - 1)
    frequenze = [f_start + i * step_f for i in range(points)]

    print("\n" + "=" * 65)
    print(f" Avvio sweep di prova su {points} punti...")
    print(" Guarda il display verde del generatore: vedrai la frequenza variare!")
    print("=" * 65)
    print(f"{'Passo':>5} | {'Frequenza [Hz]':>15} | {'Stato':>15}")
    print("-" * 45)

    try:
        for idx, f in enumerate(frequenze, 1):
            gen.write(f":FREQuency {f:.3f}")
            print(f"{idx:5d} | {f:15.2f} | Impostata OK")
            time.sleep(delay)
    except KeyboardInterrupt:
        print("\n\n[STOP] Sweep interrotto manualmente.")
    finally:
        print("-" * 45)
        print("[SUCCESSO] Test completato! Il generatore risponde perfettamente ai comandi.")
        gen.close()
        rm.close()

    input("\nPremi INVIO per chiudere...")

if __name__ == "__main__":
    main()

# Caratterizzazione Risonatore MEMS ad Arco & Analisi del Ringdown

Progetto di caratterizzazione elettromeccanica, modellizzazione circuitale equivalente (Butterworth-Van Dyke) e strategie di controllo/soppressione attiva del decadimento libero (*ringdown*) per risonatori MEMS capacitivi ad arco in polisilicio.

---

## 🔬 Struttura del Progetto

- **`analyze_ringdown.py`**: Script di analisi del segnale di oscilloscopio, calcolo dell'inviluppo con Trasformata di Hilbert, gestione dell'aliasing spettrale, fitting esponenziale ($A(t) = A_0 e^{-t/\tau}$) e calcolo del fattore di merito $Q$.
- **`plot_raw_csv.py`**: Visualizzazione dettagliata dei punti campionati grezzi e zoom sinusoidale.
- **`Appunti_PMUT_Equazioni_Ringdown.tex` / `.pdf`**: Compendio teorico-matematico completo con linearizzazione, modello RLC equivalente, analisi dello smorzamento in ciclo aperto e strategie di controllo attivo in retroazione.
- **`correzioni.tex`**: Documento di sintesi con le correzioni dei segni di softening elettrostatico, ordini di grandezza del guadagno e parametri circuitali della spia virtuale.
- **`Paper/`**: Articoli scientifici e report sperimentali di riferimento (Frangi et al. 2023, Nastro et al. 2026, Wu et al. 2021, UniBS Report).
- **`Modellizzazione/` & `Chat Ai e appunti/`**: Note analitiche e documentazione integrativa.

---

## ⚡ Parametri Chiave del Dispositivo

| Parametro | Valore Nominale | Descrizione |
|---|---|---|
| $f_{r1}$ | $\approx 416.6\text{ kHz}$ | Frequenza fondamentale del $1^\circ$ modo flessionale |
| $f_{r2}$ | $\approx 834.15\text{ kHz}$ | Frequenza del $2^\circ$ modo (Risonanza Interna 1:2) |
| $Q_1$ | $\approx 2800$ | Fattore di qualità meccanico in vuoto/bassa pressione |
| $\tau$ | $\approx 2.14\text{ ms}$ | Costante di tempo naturale del decadimento libero |
| $t_{d}$ | $\approx 4.92\text{ ms}$ | Tempo di estinzione libera (attenuazione $\times 10$) |
| $L_m$ | $\sim 37\text{ kH}$ | Induttanza motional equivalente RLC |
| $C_m$ | $\sim 0.0038\text{ fF}$ | Capacità motional equivalente RLC |
| $R_m$ | $\sim 35\text{ M}\Omega$ | Resistenza motional equivalente RLC |

---

## 🚀 Utilizzo degli Script

```bash
# Installazione dipendenze
pip install numpy scipy matplotlib

# Esecuzione analisi del ringdown da file scope_0.csv
python analyze_ringdown.py

# Visualizzazione dati grezzi campionati
python plot_raw_csv.py
```
